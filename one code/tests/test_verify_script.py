import subprocess
import unittest
from pathlib import Path


class VerifyScriptTests(unittest.TestCase):
    def test_verify_script_exists_and_is_executable(self):
        script = Path("scripts/verify.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

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
