import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file, write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE


class CheckpointTests(unittest.TestCase):
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
            self.assertEqual(manifest["run_id"], "checkpoint-test")
            self.assertEqual(manifest["current_state"], "000000")
            self.assertEqual(manifest["status"], "completed")
            self.assertFalse(manifest["partial"])
            self.assertEqual(manifest["checkpoints"][0]["sha256"], sha256_file(checkpoint_path))

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


if __name__ == "__main__":
    unittest.main()
