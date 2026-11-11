import json
import tempfile
import unittest
from pathlib import Path


class ApprovalTests(unittest.TestCase):
    def test_write_approval_decision_appends_jsonl(self):
        from onecode.kernel.approval import ApprovalDecision, write_approval_decision

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approvals.jsonl"
            write_approval_decision(
                path,
                ApprovalDecision(
                    run_id="run-1",
                    decision_id="decision-1",
                    action="approve",
                    reason="safe write",
                    edited_payload=None,
                ),
            )
            payload = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(payload["run_id"], "run-1")
        self.assertEqual(payload["action"], "approve")
        self.assertIn("timestamp", payload)

    def test_approval_decision_rejects_unknown_action(self):
        from onecode.kernel.approval import ApprovalDecision

        with self.assertRaises(ValueError):
            ApprovalDecision(
                run_id="run-1",
                decision_id="decision-1",
                action="maybe",
                reason="invalid",
                edited_payload=None,
            )
