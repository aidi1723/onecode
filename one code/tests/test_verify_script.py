import subprocess
import unittest
from pathlib import Path


class VerifyScriptTests(unittest.TestCase):
    def test_verify_script_exists_and_is_executable(self):
        script = Path("scripts/verify.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_verify_script_uses_short_module_entrypoint(self):
        script = Path("scripts/verify.sh")
        text = script.read_text(encoding="utf-8")

        self.assertIn('"$PYTHON_BIN" -m onecode doctor', text)
        self.assertNotIn("-m onecode.cli doctor", text)

    def test_verify_script_uses_overridable_python_interpreter(self):
        text = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn('PYTHON_BIN="${PYTHON:-}"', text)
        self.assertIn('"$PYTHON_BIN" -m pip install -e .[tui]', text)
        self.assertIn('"$PYTHON_BIN" -m unittest discover -s tests -v', text)
        self.assertNotIn("export PYTHONPATH", text)

    def test_verify_script_runs_non_recursive_smoke_check(self):
        completed = subprocess.run(
            ["bash", "scripts/verify.sh", "--skip-tests"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("compileall", completed.stdout)
        self.assertIn("doctor", completed.stdout)


if __name__ == "__main__":
    unittest.main()
