import json
import os
import subprocess
import sys
import unittest


class ModuleEntrypointTests(unittest.TestCase):
    def test_python_m_onecode_dispatches_to_cli(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        completed = subprocess.run(
            [sys.executable, "-m", "onecode", "doctor"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
