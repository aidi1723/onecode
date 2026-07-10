import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.iching_encoding import (
    CANONICAL_TRIGRAMS,
    LEGACY_TRIGRAMS,
    RULE_SCHEMA_V1,
    RULE_SCHEMA_V2,
)
from onecode.kernel.iching_migration import audit_evidence_file, audit_status_migration


class IchingMigrationTests(unittest.TestCase):
    def test_status_audit_reports_canonical_interpretation_and_affected_scopes(self):
        legacy_status = (LEGACY_TRIGRAMS["li"] << 3) | LEGACY_TRIGRAMS["xun"]
        expected_status = (CANONICAL_TRIGRAMS["li"] << 3) | CANONICAL_TRIGRAMS["xun"]

        audit = audit_status_migration(legacy_status, RULE_SCHEMA_V1)

        self.assertEqual(audit["source_schema"], RULE_SCHEMA_V1)
        self.assertEqual(audit["target_schema"], RULE_SCHEMA_V2)
        self.assertEqual(audit["source_status_code"], legacy_status)
        self.assertEqual(audit["target_status_code"], expected_status)
        self.assertEqual(audit["affected_scopes"], ["inner", "outer"])
        self.assertTrue(audit["changed"])

    def test_status_audit_preserves_unaffected_status_and_accepts_canonical_input(self):
        qian_over_kun = (CANONICAL_TRIGRAMS["qian"] << 3) | CANONICAL_TRIGRAMS["kun"]

        audit = audit_status_migration(qian_over_kun, RULE_SCHEMA_V2)

        self.assertEqual(audit["target_status_code"], qian_over_kun)
        self.assertEqual(audit["affected_scopes"], [])
        self.assertFalse(audit["changed"])

    def test_evidence_file_audit_defaults_missing_schema_to_v1_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            path.write_text(
                json.dumps(
                    {
                        "run_id": "legacy-run",
                        "iching_status_code": (LEGACY_TRIGRAMS["li"] << 3) | LEGACY_TRIGRAMS["kun"],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            before = hashlib.sha256(path.read_bytes()).hexdigest()

            audit = audit_evidence_file(path)

            after = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(audit["source_schema"], RULE_SCHEMA_V1)
            self.assertEqual(audit["path"], str(path.resolve()))
            self.assertEqual(audit["source_sha256"], before)
            self.assertEqual(audit["status_field"], "iching_status_code")
            self.assertTrue(audit["migration"]["changed"])

    def test_evidence_file_audit_rejects_missing_status_and_unknown_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_status = Path(tmp) / "missing.json"
            missing_status.write_text('{"run_id":"missing"}\n', encoding="utf-8")
            unknown_schema = Path(tmp) / "unknown.json"
            unknown_schema.write_text(
                '{"rule_schema":"onecode-iching-v3","iching_status_code":1}\n',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                audit_evidence_file(missing_status)
            with self.assertRaises(ValueError):
                audit_evidence_file(unknown_schema)


if __name__ == "__main__":
    unittest.main()
