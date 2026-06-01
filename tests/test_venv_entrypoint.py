import os
import subprocess
import unittest
from pathlib import Path


class VenvEntrypointTests(unittest.TestCase):
    def test_venv_onecode_command_starts_cli_without_pythonpath(self):
        command = Path(".venv/bin/onecode")

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
        command = Path("/Users/aidi/.local/bin/onecode")

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
