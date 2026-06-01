import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.wal import read_validated_global_wal_entries, wal_entry_hash


class GlobalWalTests(unittest.TestCase):
    def test_wal_entry_hash_ignores_existing_hash_field(self):
        entry = {"v": 1, "rid": "run-1", "st": "completed", "prev": None}
        entry_with_hash = {**entry, "hash": "tampered"}

        self.assertEqual(wal_entry_hash(entry), wal_entry_hash(entry_with_hash))

    def test_read_validated_global_wal_entries_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            entry = {"v": 1, "rid": "run-1", "st": "completed", "prev": None}
            entry["hash"] = wal_entry_hash(entry)
            entry["st"] = "tampered"
            wal_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "global_wal_chain_hash_mismatch"):
                read_validated_global_wal_entries(workspace)

    def test_read_validated_global_wal_entries_preserves_segment_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            entry = {"v": 1, "rid": "run-1", "st": "completed", "prev": None}
            entry["hash"] = wal_entry_hash(entry)
            wal_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

            entries = read_validated_global_wal_entries(workspace)

            self.assertEqual(entries[0]["rid"], "run-1")
            self.assertEqual(entries[0]["_wal_path"], str(wal_path.resolve()))


if __name__ == "__main__":
    unittest.main()
