import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.checkpoint import file_lock, sha256_file, write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE


class CheckpointTests(unittest.TestCase):
    def test_file_lock_uses_os_level_flock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "evidence.lock"

            with patch("onecode.kernel.checkpoint.fcntl.flock") as flock:
                with file_lock(lock_path):
                    pass

            self.assertEqual(flock.call_count, 2)

    def test_write_checkpoint_updates_manifest_with_matching_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="checkpoint-test")
            checkpoint_path = write_checkpoint(
                context=context,
                payload={"task": "smoke", "status": "completed"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))

            self.assertEqual(checkpoint["next_state"], "000000")
            self.assertIn("duration_ms", checkpoint)
            self.assertGreaterEqual(checkpoint["duration_ms"], 0)
            self.assertEqual(manifest["run_id"], "checkpoint-test")
            self.assertEqual(manifest["current_state"], "000000")
            self.assertEqual(manifest["status"], "completed")
            self.assertFalse(manifest["partial"])
            self.assertEqual(manifest["checkpoints"][0]["sha256"], sha256_file(checkpoint_path))
            self.assertIn("duration_ms", manifest["checkpoints"][0])

    def test_write_ledger_creates_user_facing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-test")
            ledger_path = write_ledger(
                context,
                {
                    "run_id": "ledger-test",
                    "status": "completed",
                    "state": "000000",
                    "partial": False,
                    "reason": None,
                },
            )

            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["run_id"], "ledger-test")
            self.assertEqual(ledger["status"], "completed")

    def test_write_ledger_keeps_append_only_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-history-test")

            write_ledger(context, {"run_id": "ledger-history-test", "status": "halted"})
            ledger_path = write_ledger(context, {"run_id": "ledger-history-test", "status": "completed"})

            latest = json.loads(ledger_path.read_text(encoding="utf-8"))
            history_path = ledger_path.with_suffix(".jsonl")
            history = [
                json.loads(line)
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            self.assertEqual(latest["status"], "completed")
            self.assertEqual([entry["status"] for entry in history], ["halted", "completed"])

    def test_write_ledger_appends_tamper_evident_chain_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-chain-test")

            write_ledger(context, {"run_id": "ledger-chain-test", "status": "halted"})
            write_ledger(context, {"run_id": "ledger-chain-test", "status": "completed"})

            chain_path = context.evidence_root / "evidence-chain.jsonl"
            records = [
                json.loads(line)
                for line in chain_path.read_text(encoding="utf-8").splitlines()
                if line
            ]

            self.assertEqual([record["sequence"] for record in records], [1, 2])
            self.assertEqual([record["artifact_type"] for record in records], ["ledger", "ledger"])
            self.assertEqual(records[0]["previous_chain_hash"], "0" * 64)
            self.assertEqual(records[1]["previous_chain_hash"], records[0]["chain_hash"])
            self.assertRegex(records[0]["artifact_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(records[0]["chain_hash"], r"^[0-9a-f]{64}$")


class AppendOnlyManifestTests(unittest.TestCase):
    def test_write_checkpoint_preserves_prior_checkpoint_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="append-test")

            first = write_checkpoint(
                context=context,
                payload={"task": "one"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="noop",
                decision="allowed",
            )
            second = write_checkpoint(
                context=context,
                payload={"task": "two"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="write_text",
                decision="allowed",
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertEqual(manifest["checkpoints"][0]["path"], str(first))
            self.assertEqual(manifest["checkpoints"][0]["intent_type"], "noop")
            self.assertEqual(manifest["checkpoints"][1]["path"], str(second))
            self.assertEqual(manifest["checkpoints"][1]["intent_type"], "write_text")

    def test_patch_checkpoint_manifest_record_indexes_patch_hash_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="patch-manifest-index")
            payload = {
                "path": "src/a.py",
                "sha256": "post",
                "pre_sha256": "pre",
                "post_sha256": "post",
                "search_block_sha256": "search",
                "replace_block_sha256": "replace",
            }

            write_checkpoint(
                context=context,
                payload=payload,
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="patch_text",
                decision="allowed",
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            record = manifest["checkpoints"][0]

            self.assertEqual(record["patch_evidence"], {
                "pre_sha256": "pre",
                "post_sha256": "post",
                "search_block_sha256": "search",
                "replace_block_sha256": "replace",
            })


class ResumedCheckpointMetadataTests(unittest.TestCase):
    def test_write_checkpoint_persists_resume_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            asset = workspace / "src" / "ready.py"
            asset.parent.mkdir(parents=True)
            asset.write_text("ready = True\n", encoding="utf-8")
            asset_hash = sha256_file(asset)

            old_run = workspace / ".onecode" / "runs" / "old-run"
            old_checkpoint = old_run / "checkpoints" / "0001.json"
            old_checkpoint.parent.mkdir(parents=True)
            old_checkpoint.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(asset), "sha256": asset_hash},
                    }
                ),
                encoding="utf-8",
            )
            (old_run / "manifest.json").write_text(
                json.dumps({"run_id": "old-run", "checkpoints": [{"path": str(old_checkpoint)}]}),
                encoding="utf-8",
            )

            context = create_context(workspace, run_id="retry-run", resume_from_run_id="old-run")
            checkpoint_path = write_checkpoint(
                context=context,
                payload={"path": "src/ready.py", "sha256": asset_hash},
                next_state=COMPLETE,
                status="skipped",
                partial=False,
                reason="resumed_asset_ready",
                intent_type="write_text",
                decision="allowed",
            )

            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(checkpoint["resumed_from"], "old-run")
            self.assertEqual(checkpoint["ready_assets"]["src/ready.py"]["sha256"], asset_hash)
            self.assertEqual(checkpoint["resume_audit_events"][0]["path"], "src/ready.py")
            self.assertEqual(checkpoint["resume_audit_events"][0]["status"], "ready")
            self.assertEqual(manifest["resumed_from"], "old-run")
            self.assertEqual(manifest["ready_assets"]["src/ready.py"]["source_run_id"], "old-run")
            self.assertEqual(manifest["resume_audit_events"][0]["path"], "src/ready.py")


if __name__ == "__main__":
    unittest.main()
