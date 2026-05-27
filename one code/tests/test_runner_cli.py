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


class RunnerSovereigntyTests(unittest.TestCase):
    def test_run_task_write_text_creates_file_and_records_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "write",
                workspace=Path(tmp),
                run_id="write-test",
                write_path="src/generated.py",
                write_content="print('ok')\n",
            )

            target = Path(tmp) / "src" / "generated.py"
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["decision"], "allowed")
            self.assertTrue(target.exists())
            self.assertEqual(result["sha256"], result["payload"]["sha256"])

    def test_run_task_halts_illegal_write_without_creating_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp).parent / "outside.txt"
            if outside.exists():
                outside.unlink()

            result = run_task(
                "bad write",
                workspace=Path(tmp),
                run_id="bad-write-test",
                write_path="../outside.txt",
                write_content="blocked",
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["decision"], "halted")
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertFalse(outside.exists())

    def test_run_task_denies_bash_execution_without_running_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "deny bash",
                workspace=Path(tmp),
                run_id="deny-bash-test",
                intent_type="bash_execution",
                command="echo no",
            )

            self.assertEqual(result["status"], "denied")
            self.assertEqual(result["decision"], "denied")
            self.assertEqual(result["reason"], "permission_denied")


if __name__ == "__main__":
    unittest.main()
