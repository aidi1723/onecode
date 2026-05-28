import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InspectCliTests(unittest.TestCase):
    def test_cli_inspect_prints_existing_run_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "inspect source",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-run",
                    "--write-text",
                    "src/a.py=a = 1\n",
                    "--write-text",
                    "tests/test_a.py=def test_a():\n    assert True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            summary = json.loads(completed.stdout)

            self.assertEqual(summary["run_id"], "inspect-run")
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["requested_count"], 2)
            self.assertEqual(summary["completed_count"], 2)
            self.assertEqual(summary["checkpoint_count"], 2)
            self.assertTrue(Path(summary["manifest_path"]).exists())
            self.assertTrue(Path(summary["ledger_path"]).exists())
            self.assertIn("iching_status_code", summary)

    def test_cli_inspect_missing_run_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "missing")
            self.assertEqual(error["run_id"], "missing-run")

    def test_cli_inspect_corrupt_run_returns_nonzero_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "corrupt-run"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text("{not json", encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "corrupt-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "corrupt-run")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_non_object_json_returns_corrupt_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "list-run"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text("[]", encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "list-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "list-run")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "non_object_json")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_non_list_checkpoints_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "bad-checkpoints"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": {"not": "a list"}}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "bad-checkpoints",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "bad-checkpoints")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoints")

    def test_cli_inspect_non_object_checkpoint_entry_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "bad-checkpoint-entry"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": ["bad"]}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "bad-checkpoint-entry",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "bad-checkpoint-entry")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_entry")


if __name__ == "__main__":
    unittest.main()
