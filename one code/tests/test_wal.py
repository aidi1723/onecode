import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import global_wal_entry, skill_selection_sha256
from onecode.kernel.context import create_context
from onecode.kernel.wal import (
    global_wal_evidence_metrics,
    global_wal_metrics_summary,
    read_validated_global_wal_entries,
    wal_entry_hash,
)


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

    def test_read_validated_global_wal_entries_rejects_invalid_json_with_stable_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            wal_path.write_text("{not json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid_global_wal_json"):
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

    def test_global_wal_paths_ignore_non_numeric_archive_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            onecode_root = workspace / ".onecode"
            onecode_root.mkdir()
            archive_path = onecode_root / "global-ledger.1.jsonl"
            active_path = onecode_root / "global-ledger.jsonl"
            backup_path = onecode_root / "global-ledger.backup.jsonl"
            archive_entry = {"v": 1, "rid": "old-run", "st": "completed", "prev": None}
            archive_entry["hash"] = wal_entry_hash(archive_entry)
            active_entry = {"v": 1, "rid": "new-run", "st": "completed", "prev": None}
            active_entry["hash"] = wal_entry_hash(active_entry)
            archive_path.write_text(json.dumps(archive_entry, sort_keys=True) + "\n", encoding="utf-8")
            active_path.write_text(json.dumps(active_entry, sort_keys=True) + "\n", encoding="utf-8")
            backup_path.write_text("{not part of rotation\n", encoding="utf-8")

            entries = read_validated_global_wal_entries(workspace)

            self.assertEqual([entry["rid"] for entry in entries], ["old-run", "new-run"])

    def test_global_wal_entry_records_risk_tier_and_capture_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="wal-classification")

            entry = global_wal_entry(
                context,
                {
                    "run_id": "wal-classification",
                    "status": "completed",
                    "partial": False,
                    "reason": None,
                    "intent_type": "write_text",
                    "evidence_mode": "wal",
                },
            )

            self.assertEqual(entry["em"], "wal")
            self.assertEqual(entry["rt"], "critical")
            self.assertEqual(entry["cm"], "full")
            self.assertEqual(entry["cr"], "critical_trust_event")

    def test_global_wal_entry_records_compact_skill_selection_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="wal-skill-selection")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_count": 1,
                "selected_skills": [
                    {
                        "name": "private-skill",
                        "mode": "method_only",
                        "risk": "low",
                        "matched_capabilities": ["test"],
                        "content_sha256": "b" * 64,
                    }
                ],
            }
            skill_selection["selection_sha256"] = skill_selection_sha256(skill_selection)

            entry = global_wal_entry(
                context,
                {
                    "run_id": "wal-skill-selection",
                    "status": "completed",
                    "partial": False,
                    "reason": None,
                    "intent_type": "write_text",
                    "evidence_mode": "wal",
                    "skill_selection": skill_selection,
                },
            )

            self.assertEqual(entry["ssh"], skill_selection["selection_sha256"])
            self.assertEqual(entry["ssr"], "capability_match")
            self.assertEqual(entry["ssc"], 1)
            self.assertNotIn("selected_skills", entry)
            self.assertNotIn("private-skill", json.dumps(entry))

    def test_global_wal_entry_rejects_invalid_skill_selection_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="wal-invalid-skill-selection")

            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_field:selection_sha256"):
                global_wal_entry(
                    context,
                    {
                        "run_id": "wal-invalid-skill-selection",
                        "status": "completed",
                        "partial": False,
                        "reason": None,
                        "intent_type": "write_text",
                        "evidence_mode": "wal",
                        "skill_selection": {
                            "status": "ok",
                            "selection_sha256": "not-a-hash",
                            "selection_reason": "capability_match",
                            "selected_count": 1,
                            "selected_skills": [
                                {
                                    "name": "private-skill",
                                    "mode": "method_only",
                                    "risk": "low",
                                    "matched_capabilities": ["test"],
                                    "content_sha256": "b" * 64,
                                }
                            ],
                        },
                    },
                )

    def test_global_wal_entry_unknown_family_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="wal-unknown-classification")

            entry = global_wal_entry(
                context,
                {
                    "run_id": "wal-unknown-classification",
                    "status": "observed",
                    "partial": True,
                    "reason": "diagnostic",
                    "intent_type": "new_intent_family",
                    "evidence_mode": "wal",
                },
            )

            self.assertEqual(entry["rt"], "critical")
            self.assertEqual(entry["cm"], "full")
            self.assertEqual(entry["cr"], "unknown_event_family_fail_closed")

    def test_global_wal_evidence_metrics_groups_bytes_by_risk_and_capture_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            entry = {
                "v": 1,
                "rid": "run-1",
                "st": "completed",
                "rt": "critical",
                "cm": "full",
                "prev": None,
            }
            entry["hash"] = wal_entry_hash(entry)
            wal_path.write_text(json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8")

            metrics = global_wal_evidence_metrics(workspace)

            self.assertEqual(metrics["entry_count"], 1)
            self.assertEqual(metrics["entries_by_risk_tier"]["critical"], 1)
            self.assertEqual(metrics["entries_by_capture_mode"]["full"], 1)
            self.assertGreater(metrics["total_bytes"], 0)
            self.assertGreater(metrics["bytes_by_risk_tier"]["critical"], 0)

    def test_global_wal_metrics_summary_is_windowed_and_omits_raw_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            lines = []
            previous = None
            for index in range(3):
                entry = {
                    "v": 1,
                    "ts": f"2026-06-02T00:00:0{index}+00:00",
                    "rid": f"run-{index}",
                    "st": "completed",
                    "rt": "critical" if index == 0 else "low",
                    "cm": "full" if index == 0 else "aggregate",
                    "prev": previous,
                }
                entry["hash"] = wal_entry_hash(entry)
                previous = entry["hash"]
                lines.append(json.dumps(entry, sort_keys=True))
            wal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            summary = global_wal_metrics_summary(workspace, window_seconds=60)

            self.assertEqual(summary["summary_schema_version"], 1)
            self.assertEqual(summary["window_seconds"], 60)
            self.assertEqual(summary["entry_count"], 3)
            self.assertEqual(summary["entries_by_capture_mode"], {"aggregate": 2, "full": 1})
            self.assertEqual(summary["windows"][0]["entry_count"], 3)
            self.assertNotIn("entries", summary)
            self.assertNotIn("raw_entries", summary)


if __name__ == "__main__":
    unittest.main()
