"""Tests for approval gates on stagnant repairs without enumerated reason contracts."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from onecode.kernel.model_repair import (
    _contract_has_reason_enum,
    _extract_emitted_reasons,
    _extract_failing_checks,
    _handle_repair_budget_stop,
    _maybe_open_reason_clarification_approval,
)
from onecode.kernel.cycle_approvals import load_pending_approvals
from onecode.web.api_handlers import handle_onecode_approval_resolve, handle_onecode_pending_approvals


class RepairApprovalGateTests(unittest.TestCase):
    def test_contract_has_reason_enum_detects_tables_lists_and_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # 1. No enum - typical of coupon_eligibility & refund_policy
            readme = root / "README.md"
            readme.write_text(
                "# Coupon Eligibility\n"
                "Evaluate eligibility rules against order history.\n"
                "Decisions should be saved to decisions.json with status and reason.\n",
                encoding="utf-8",
            )
            self.assertFalse(_contract_has_reason_enum(root))

            # 2. Bullet list enum
            readme.write_text(
                "# Coupon Eligibility\n"
                "Allowed reasons:\n"
                "- `min_spend_not_met`\n"
                "- `expired`\n"
                "- `usage_limit_reached`\n",
                encoding="utf-8",
            )
            self.assertTrue(_contract_has_reason_enum(root))

            # 3. Markdown table enum
            readme.write_text(
                "# Seat Limit Policy\n"
                "| Reason | Description |\n"
                "| --- | --- |\n"
                "| `seat_available` | Seat is free |\n"
                "| `seat_limit_reached` | Maximum seats reached |\n",
                encoding="utf-8",
            )
            self.assertTrue(_contract_has_reason_enum(root))

            # 4. Non-policy task (e.g. svg cleaner)
            readme.write_text(
                "# SVG Cleaner\nClean malicious attributes and tags from SVG inputs.\n",
                encoding="utf-8",
            )
            self.assertTrue(_contract_has_reason_enum(root))

    def test_extract_failing_checks_and_emitted_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # Write model source file emitting a reason
            policy_file = root / "policy.py"
            policy_file.write_text(
                'def evaluate(cust):\n    return False, {"status": "ineligible", "reason": "recent_activity"}\n',
                encoding="utf-8",
            )

            # Write decisions.json
            decisions = root / "decisions.json"
            decisions.write_text(
                json.dumps([{"id": "order-1", "reason": "trial_zero_charge"}]),
                encoding="utf-8",
            )

            tested = {
                "verifier_results": [
                    {
                        "stdout_tail": '- [FAIL] test_cooloff_period: expected rejection\n- [FAIL] test_charge_status\n',
                        "stderr_tail": "AssertionError: 'recent_activity' != 'other_value'\n",
                    }
                ]
            }

            failing_checks = _extract_failing_checks(tested)
            self.assertEqual(failing_checks, ["test_cooloff_period", "test_charge_status"])

            emitted = _extract_emitted_reasons(root, tested)
            self.assertIn("trial_zero_charge", emitted)
            self.assertIn("recent_activity", emitted)

    def test_stalled_repair_on_unspecified_reason_contract_opens_pending_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Refund Policy\nOutput decisions.json with status and reason.\n",
                encoding="utf-8",
            )
            (root / "refund.py").write_text(
                'def decide():\n    return {"status": "rejected", "reason": "trial_no_charge"}\n',
                encoding="utf-8",
            )

            tested = {
                "status": "completed",
                "reason": "verifier_failed",
                "host_reward": 0.8462,
                "verifier_results": [
                    {
                        "stdout_tail": "- [FAIL] test_zero_paid_charge: assertion failed\n",
                        "stderr_tail": "",
                    }
                ],
            }
            best_checked = dict(tested)
            best_snapshot = {"refund.py": (root / "refund.py").read_text(encoding="utf-8")}

            delivered = _handle_repair_budget_stop(
                workspace=root,
                task="implement refund policy decisions",
                tested=tested,
                current_checked=tested,
                best_checked=best_checked,
                best_snapshot=best_snapshot,
                attempt=3,
            )

            self.assertEqual(delivered["status"], "halted")
            self.assertEqual(delivered["reason"], "approval_required")
            self.assertEqual(delivered["approval_status"], "PENDING_APPROVAL")
            pending_id = delivered.get("pending_approval_id")
            self.assertTrue(bool(pending_id))
            self.assertEqual(delivered["pending"]["tool_name"], "clarify_decision_reason")

            # Check that it exists in the pending approvals queue
            approvals = load_pending_approvals(root)
            self.assertEqual(len(approvals), 1)
            self.assertEqual(approvals[0]["id"], pending_id)
            self.assertIn("test_zero_paid_charge", approvals[0]["params"]["failing_checks"])
            self.assertIn("trial_no_charge", approvals[0]["params"]["emitted_reasons"])

    def test_stalled_repair_on_contract_with_reason_enum_does_not_open_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Seat Limit Policy\nAllowed reasons:\n- `seat_limit_reached`\n- `seat_available`\n",
                encoding="utf-8",
            )

            tested = {
                "status": "completed",
                "reason": "verifier_failed",
                "host_reward": 0.9231,
                "verifier_results": [
                    {
                        "stdout_tail": "- [FAIL] test_seat_allocation\n",
                        "stderr_tail": "",
                    }
                ],
            }
            best_checked = dict(tested)
            best_snapshot = {}

            delivered = _handle_repair_budget_stop(
                workspace=root,
                task="implement seat limit policy",
                tested=tested,
                current_checked=tested,
                best_checked=best_checked,
                best_snapshot=best_snapshot,
                attempt=3,
            )

            # Contract has reason enum, so no pending approval should be opened
            self.assertNotEqual(delivered.get("reason"), "approval_required")
            approvals = load_pending_approvals(root)
            self.assertEqual(len(approvals), 0)

    def test_pending_approvals_api_lists_and_resolves_reason_approval(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Coupon Eligibility\nOutput decisions.json with status and reason.\n",
                encoding="utf-8",
            )
            tested = {
                "status": "completed",
                "reason": "verifier_failed",
                "host_reward": 0.9231,
                "verifier_results": [{"stdout_tail": "- [FAIL] test_cooloff\n"}],
            }

            rec = _maybe_open_reason_clarification_approval(
                workspace=root,
                task="evaluate coupon eligibility",
                tested=tested,
                current_checked=tested,
                best_checked=tested,
                attempt=2,
            )
            self.assertIsNotNone(rec)
            approval_id = rec["id"]

            # 1. Query pending approvals endpoint
            list_res, code = handle_onecode_pending_approvals({"workspace": str(root)})
            self.assertEqual(code, 200)
            self.assertEqual(list_res["count"], 1)
            self.assertEqual(list_res["approvals"][0]["id"], approval_id)

            # 2. Resolve approval with engineer choice
            resolve_body = {
                "workspace": str(root),
                "decision": "approved",
                "resolution": {"short_code": "engineer_selected_slug"},
            }
            res_payload, res_code = handle_onecode_approval_resolve(approval_id, resolve_body)
            self.assertEqual(res_code, 200)
            self.assertEqual(res_payload["status"], "approved")
            self.assertEqual(res_payload["resolution"], {"short_code": "engineer_selected_slug"})

            # Verify resolved approvals file was written
            resolved_file = root / ".onecode" / "resolved_approvals.json"
            self.assertTrue(resolved_file.is_file())
            resolved_data = json.loads(resolved_file.read_text(encoding="utf-8"))
            self.assertEqual(len(resolved_data), 1)
            self.assertEqual(resolved_data[0]["resolution"], {"short_code": "engineer_selected_slug"})

    def test_zero_hidden_slugs_in_kernel_source(self) -> None:
        """Verify strict constraint: verifier slugs must not be hardcoded in the kernel."""
        forbidden_slugs = [
            "too" + "_" + "recently" + "_" + "active",
            "no" + "_" + "paid" + "_" + "charge",
        ]
        src_root = Path("src/onecode")
        for path in src_root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            for slug in forbidden_slugs:
                self.assertNotIn(
                    slug,
                    content,
                    f"Forbidden hidden slug '{slug}' found in kernel file: {path}",
                )


if __name__ == "__main__":
    unittest.main()
