import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.runner import run_task


class RunnerTests(unittest.TestCase):
    def test_run_task_writes_manifest_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task("smoke", workspace=Path(tmp), run_id="runner-test")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["state"], "000000")
            self.assertFalse(result["partial"])
            manifest_path = Path(result["manifest_path"])
            ledger_path = Path(result["ledger_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(ledger_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["checkpoints"][0]["status"], "completed")

    def test_run_task_can_force_timeout_for_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "timeout",
                workspace=Path(tmp),
                http_timeout_seconds=0.01,
                run_id="timeout-test",
                simulated_action_seconds=0.05,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["state"], "000000")
            self.assertTrue(result["partial"])
            self.assertEqual(result["reason"], "http_timeout")
            self.assertTrue(Path(result["manifest_path"]).exists())
            self.assertTrue(Path(result["ledger_path"]).exists())


class CliTests(unittest.TestCase):
    def test_cli_run_prints_json_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "smoke",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-test",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["run_id"], "cli-test")
            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["partial"])
            self.assertTrue(Path(result["manifest_path"]).exists())


if __name__ == "__main__":
    unittest.main()
