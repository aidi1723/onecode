import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


class VenvEntrypointTests(unittest.TestCase):
    def test_venv_onecode_command_starts_cli_without_pythonpath(self):
        command = Path(".venv/bin/onecode")
        if not command.exists():
            candidate = Path(sys.prefix) / "bin" / "onecode"
            which_candidate = shutil.which("onecode")
            if candidate.exists():
                command = candidate
            elif which_candidate:
                command = Path(which_candidate)
            else:
                self.skipTest(".venv/bin/onecode is not configured in this environment")

        self.assertTrue(command.exists())
        completed = subprocess.run(
            [str(command), "tui", "--help"],
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("usage: onecode tui", completed.stdout)

    def test_global_onecode_command_points_to_project_entrypoint(self):
        command_path = os.environ.get("ONECODE_GLOBAL_COMMAND")
        if not command_path:
            self.skipTest("ONECODE_GLOBAL_COMMAND is not configured")
        command = Path(command_path)

        self.assertTrue(command.exists())
        completed = subprocess.run(
            [str(command), "tui", "--help"],
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("usage: onecode tui", completed.stdout)


if __name__ == "__main__":
    unittest.main()
