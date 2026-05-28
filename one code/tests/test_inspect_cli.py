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

    def test_cli_inspect_missing_checkpoints_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-checkpoints"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text('{"status": "completed"}', encoding="utf-8")
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
                    "missing-checkpoints",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-checkpoints")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_checkpoints")

    def test_cli_inspect_missing_manifest_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-manifest-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text('{"checkpoints": []}', encoding="utf-8")
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
                    "missing-manifest-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-manifest-status")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_missing_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-ledger-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"completed_count": 0}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-ledger-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-ledger-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_blank_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "blank-ledger-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": ""}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "blank-ledger-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "blank-ledger-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_unknown_manifest_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "unknown-manifest-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "teleported", "checkpoints": []}',
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
                    "unknown-manifest-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "unknown-manifest-status")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_mismatched_manifest_and_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "mismatched-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "halted"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "mismatched-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "mismatched-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "status_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_negative_ledger_count_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "negative-count"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                '{"status": "completed", "completed_count": -1}',
                encoding="utf-8",
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
                    "negative-count",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "negative-count")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_count")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_impossible_ledger_count_total_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "impossible-count"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 1, "failed_count": 0}'
                ),
                encoding="utf-8",
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
                    "impossible-count",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "impossible-count")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "count_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_ledger_counts_must_match_checkpoint_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-count-mismatch"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "checkpoints/0001.json", '
                    '"sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 2, '
                    '"completed_count": 2, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
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
                    "checkpoint-count-mismatch",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-count-mismatch")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "checkpoint_count_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_checkpoint_missing_evidence_fields_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-missing-evidence"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": [{"status": "completed"}]}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
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
                    "checkpoint-missing-evidence",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-missing-evidence")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_evidence")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_malformed_checkpoint_sha256_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "malformed-checkpoint-sha"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "checkpoints/0001.json", "sha256": "abc"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
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
                    "malformed-checkpoint-sha",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "malformed-checkpoint-sha")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_evidence")
            self.assertNotIn("Traceback", completed.stderr)

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
