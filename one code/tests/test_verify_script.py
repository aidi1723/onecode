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

        self.assertIn("python3 -m onecode doctor", text)
        self.assertNotIn("python3 -m onecode.cli doctor", text)

    def test_verify_script_installs_editable_package_before_running_tests(self):
        text = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn("python3 -m pip install -e .[tui]", text)
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
