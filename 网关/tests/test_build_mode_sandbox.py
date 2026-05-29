import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_sandbox import sandbox_evidence_from_result, run_isolated_test


class BuildModeSandboxTest(unittest.TestCase):
    def test_sandbox_evidence_maps_exit_zero_to_passed(self):
        evidence = sandbox_evidence_from_result({"exit_code": 0, "stdout": "ok", "stderr": ""}, 12)
        self.assertEqual(evidence.exit_code, 0)
        self.assertEqual(evidence.pytest_status, "passed")
        self.assertEqual(len(evidence.stdout_sha256), 64)

    def test_sandbox_evidence_maps_timeout(self):
        evidence = sandbox_evidence_from_result({"exit_code": 124, "stdout": "", "stderr": "TIMEOUT"}, 10000)
        self.assertTrue(evidence.timed_out)
        self.assertEqual(evidence.pytest_status, "timeout")

    def test_sandbox_evidence_keeps_compact_failure_summary(self):
        output = (
            "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad init\n"
            "6 failed, 4 passed in 16.38s\n"
        )
        evidence = sandbox_evidence_from_result({"exit_code": 1, "stdout": output, "stderr": ""}, 16)

        self.assertEqual(evidence.pytest_status, "failed")
        self.assertIn("test_duplicate", evidence.failure_summary)
        self.assertIn("6 failed", evidence.failure_summary)

    def test_run_isolated_test_returns_evidence_for_simple_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            evidence = run_isolated_test(["python3", "-m", "unittest", "discover"], tmp, use_docker=False, timeout_seconds=10)
            self.assertIsInstance(evidence.exit_code, int)
            self.assertEqual(len(evidence.stdout_sha256), 64)

    def test_run_isolated_test_clears_stale_python_bytecode_before_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "proxy_build").mkdir()
            (root / "proxy_build" / "main.py").write_text("VALUE = 42\n", encoding="utf-8")
            test_file = root / "test_proxy_build.py"
            test_file.write_text(
                "import unittest\n\n"
                "class ProxyBuildTest(unittest.TestCase):\n"
                "    def test_value(self):\n"
                "        namespace = {}\n"
                "        with open('proxy_build/main.py', encoding='utf-8') as handle:\n"
                "            exec(handle.read(), namespace)\n"
                "        self.assertEqual(namespace['VALUE'], 42)\n",
                encoding="utf-8",
            )
            first = run_isolated_test(["python3", "-m", "unittest", "discover"], tmp, use_docker=False, timeout_seconds=10)
            self.assertEqual(first.exit_code, 0)
            self.assertTrue((root / "__pycache__").exists())

            (root / "proxy_build" / "main.py").write_text("VALUE = 43\n", encoding="utf-8")
            test_file.write_text(test_file.read_text(encoding="utf-8").replace("42", "43"), encoding="utf-8")
            second = run_isolated_test(["python3", "-m", "unittest", "discover"], tmp, use_docker=False, timeout_seconds=10)

            self.assertEqual(second.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
