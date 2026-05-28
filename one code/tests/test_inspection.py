import ast
import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.inspection import (
    validate_checkpoint_evidence,
    validate_ledger_counts,
    validate_status_document,
)


class InspectionKernelTests(unittest.TestCase):
    def test_validate_status_document_rejects_missing_and_unknown_status(self):
        path = Path("manifest.json")

        self.assertEqual(validate_status_document({}, path), (str(path), "missing_status"))
        self.assertEqual(validate_status_document({"status": ""}, path), (str(path), "invalid_status"))
        self.assertEqual(validate_status_document({"status": "unknown"}, path), (str(path), "invalid_status"))
        self.assertEqual(validate_status_document({"status": "completed"}, path), (None, None))

    def test_validate_ledger_counts_rejects_negative_and_impossible_totals(self):
        path = Path("ledger.json")

        self.assertEqual(validate_ledger_counts({"requested_count": -1}, path), (str(path), "invalid_count"))
        self.assertEqual(
            validate_ledger_counts(
                {
                    "requested_count": 1,
                    "completed_count": 1,
                    "skipped_count": 1,
                    "failed_count": 0,
                },
                path,
            ),
            (str(path), "count_mismatch"),
        )
        self.assertEqual(
            validate_ledger_counts(
                {
                    "requested_count": 2,
                    "completed_count": 1,
                    "skipped_count": 1,
                    "failed_count": 0,
                },
                path,
            ),
            (None, None),
        )

    def test_validate_checkpoint_evidence_rejects_malformed_and_mismatched_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            checkpoint_path = root / "0001.json"
            checkpoint_path.write_text(json.dumps({"status": "completed"}), encoding="utf-8")

            self.assertEqual(
                validate_checkpoint_evidence([{"path": str(checkpoint_path), "sha256": "not-a-sha"}], manifest_path),
                (str(manifest_path), "invalid_checkpoint_evidence"),
            )
            self.assertEqual(
                validate_checkpoint_evidence(
                    [
                        {
                            "path": str(checkpoint_path),
                            "sha256": "0" * 64,
                            "status": "completed",
                        }
                    ],
                    manifest_path,
                ),
                (str(manifest_path), "checkpoint_sha_mismatch"),
            )

    def test_cli_does_not_redefine_inspection_audit_rules(self):
        tree = ast.parse(Path("src/onecode/cli.py").read_text(encoding="utf-8"))
        function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assigned_names = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        self.assertNotIn("read_json", function_names)
        self.assertNotIn("validate_status_document", function_names)
        self.assertNotIn("validate_ledger_counts", function_names)
        self.assertNotIn("validate_checkpoint_evidence", function_names)
        self.assertNotIn("VALID_RUN_STATUSES", assigned_names)
        self.assertNotIn("LEDGER_COUNT_FIELDS", assigned_names)


if __name__ == "__main__":
    unittest.main()
