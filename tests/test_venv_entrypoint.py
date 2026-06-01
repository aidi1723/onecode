import subprocess
import sys
import unittest
from pathlib import Path


class VenvEntrypointTests(unittest.TestCase):
    def test_module_entrypoint_starts_cli_without_pythonpath(self):
        completed = subprocess.run(
            [sys.executable, "-m", "onecode", "tui", "--help"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("usage: onecode tui", completed.stdout)

    def test_repo_bin_entrypoint_points_to_project_cli(self):
        command = Path("bin/onecode")

        self.assertTrue(command.exists())
        completed = subprocess.run(
            [str(command), "tui", "--help"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("usage: onecode tui", completed.stdout)


if __name__ == "__main__":
    unittest.main()
