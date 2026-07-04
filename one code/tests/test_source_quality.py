import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_source_quality import main as check_source_quality


class SourceQualityTests(unittest.TestCase):
    def test_source_quality_gate_accepts_current_explicit_hotspot_allowlist(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(check_source_quality(["src"]), 0)

    def test_source_quality_gate_rejects_new_unlisted_long_function(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "module.py"
            body = "\n".join("    value += 1" for _ in range(170))
            path.write_text(f"def oversized():\n    value = 0\n{body}\n    return value\n", encoding="utf-8")

            with redirect_stderr(StringIO()) as stderr:
                self.assertEqual(check_source_quality([str(path)]), 1)

            self.assertIn("function too long", stderr.getvalue())

    def test_verify_scripts_run_source_quality_gate(self):
        for script_path in ["scripts/verify-core.sh", "scripts/verify.sh"]:
            text = Path(script_path).read_text(encoding="utf-8")
            self.assertIn("check_source_quality.py", text)

    def test_web_and_tui_do_not_depend_on_cli_services(self):
        forbidden = "from onecode.cli import"
        for path in ["src/onecode/web/api.py", "src/onecode/tui/app.py"]:
            text = Path(path).read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text)

    def test_cli_keeps_compatibility_exports_for_shared_services(self):
        from onecode import cli
        from onecode.kernel.diagnostics import run_doctor
        from onecode.kernel.run_inspection import delivery_summary, inspect_run, list_runs

        self.assertIs(cli.run_doctor, run_doctor)
        self.assertIs(cli.delivery_summary, delivery_summary)
        self.assertIs(cli.inspect_run, inspect_run)
        self.assertIs(cli.list_runs, list_runs)


if __name__ == "__main__":
    unittest.main()
