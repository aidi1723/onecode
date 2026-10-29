import tempfile
import unittest
from pathlib import Path

from onecode.kernel.injected_test_runner import (
    classify_injected_test_failure,
    parse_junit_xml,
    parse_pytest_summary,
    resolve_task_test_command,
)


class TestInjectedTestRunner(unittest.TestCase):
    def test_parse_pytest_summary_various_orderings(self):
        # 1. Standard pytest summary: failures first
        out1 = """
============================= test session starts ==============================
collected 3 items

tests/test_a.py .F.                                                      [100%]

=================================== FAILURES ===================================
__________________________________ test_error __________________________________
assert 1 == 2
======================== 1 failed, 2 passed in 0.12s ===========================
"""
        s1 = parse_pytest_summary(out1)
        self.assertEqual(s1.passed, 2)
        self.assertEqual(s1.failed, 1)
        self.assertEqual(s1.errors, 0)
        self.assertEqual(s1.total, 3)
        self.assertAlmostEqual(s1.pass_rate, 0.667, places=3)

        # 2. Only passed
        out2 = "========================== 4 passed in 0.05s ==========================="
        s2 = parse_pytest_summary(out2)
        self.assertEqual(s2.passed, 4)
        self.assertEqual(s2.failed, 0)
        self.assertEqual(s2.total, 4)
        self.assertEqual(s2.pass_rate, 1.0)

        # 3. Only failed
        out3 = "========================== 3 failed in 0.10s ==========================="
        s3 = parse_pytest_summary(out3)
        self.assertEqual(s3.passed, 0)
        self.assertEqual(s3.failed, 3)
        self.assertEqual(s3.total, 3)
        self.assertEqual(s3.pass_rate, 0.0)

        # 4. Complex with warnings and errors
        out4 = "= 1 failed, 1 passed, 1 error, 2 warnings in 0.50s ="
        s4 = parse_pytest_summary(out4)
        self.assertEqual(s4.passed, 1)
        self.assertEqual(s4.failed, 1)
        self.assertEqual(s4.errors, 1)
        self.assertEqual(s4.total, 3)
        self.assertAlmostEqual(s4.pass_rate, 0.333, places=3)

    def test_parse_pytest_summary_line_events_fallback(self):
        out = """
test_runner.py::test_init PASSED
test_runner.py::test_validate FAILED
test_runner.py::test_save PASSED
"""
        s = parse_pytest_summary(out)
        self.assertEqual(s.passed, 2)
        self.assertEqual(s.failed, 1)
        self.assertEqual(s.total, 3)
        self.assertAlmostEqual(s.pass_rate, 0.667, places=3)

    def test_parse_junit_xml(self):
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="1" name="pytest" skipped="0" tests="4" time="0.049">
    <testcase classname="test_pkg" name="test_one" time="0.001" />
    <testcase classname="test_pkg" name="test_two" time="0.001" />
    <testcase classname="test_pkg" name="test_fail" time="0.001">
        <failure message="assertion failed" />
    </testcase>
    <testcase classname="test_pkg" name="test_err" time="0.001">
        <error message="runtime error" />
    </testcase>
</testsuite>
"""
        summary = parse_junit_xml(xml_content)
        self.assertEqual(summary.passed, 2)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.errors, 1)
        self.assertEqual(summary.total, 4)
        self.assertEqual(summary.pass_rate, 0.5)

    def test_resolve_task_test_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ws = Path(temp_dir) / "workspace"
            ws.mkdir()
            task_dir = Path(temp_dir) / "task"
            task_dir.mkdir()

            # 1. Default pytest command
            cmd1 = resolve_task_test_command("standard_task", task_dir, ws, Path("/tmp/tests"))
            self.assertIn("-m", cmd1)
            self.assertIn("pytest", cmd1)
            self.assertIn("no:cacheprovider", cmd1)
            self.assertEqual(cmd1[-1], "/tmp/tests")

            # 2. Django runtests detection
            (ws / "tests").mkdir()
            (ws / "tests" / "runtests.py").write_text("#!/usr/bin/env python\n")
            cmd2 = resolve_task_test_command("django_task", task_dir, ws, Path("/tmp/tests"))
            self.assertIn("tests/runtests.py", cmd2)

            # 3. Custom command in verifier.toml
            (task_dir / "verifier.toml").write_text('[test]\ncommand = "python -m custom_verifier --fast"\n')
            cmd3 = resolve_task_test_command("custom_task", task_dir, ws)
            self.assertEqual(cmd3, ["python", "-m", "custom_verifier", "--fast"])

    def test_classify_injected_test_failure(self):
        # Missing dependency
        out_dep = "ModuleNotFoundError: No module named 'click'"
        diag1 = classify_injected_test_failure(out_dep, "", 1)
        self.assertEqual(diag1["category"], "missing_dependency")
        self.assertIn("click", diag1["detail"])

        # Pytest plugin issue
        out_plug = "PluginValidationError: Plugin 'legacy_cov' failed hook"
        diag2 = classify_injected_test_failure("", out_plug, 3)
        self.assertEqual(diag2["category"], "plugin_incompatibility")

        # Django settings required
        out_django = "django.core.exceptions.ImproperlyConfigured: Requested setting INSTALLED_APPS, but settings are not configured."
        diag3 = classify_injected_test_failure(out_django, "", 1)
        self.assertEqual(diag3["category"], "django_environment_required")

        # Assertion failure
        out_assert = "FAILED tests/test_foo.py::test_bar - AssertionError: Expected 1 got 2"
        diag4 = classify_injected_test_failure(out_assert, "", 1)
        self.assertEqual(diag4["category"], "assertion_failure")


if __name__ == "__main__":
    unittest.main()
