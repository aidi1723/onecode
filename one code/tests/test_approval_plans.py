import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

from onecode.kernel.model_provider import ModelExecutionStep, ModelPlan, ModelToolCall


def guarded_plan() -> ModelPlan:
    return ModelPlan(
        task="change readme",
        execution_steps=[
            ModelExecutionStep(
                id="write",
                description="write readme",
                tool_calls=[
                    ModelToolCall(
                        tool_name="write_text",
                        params={"path": "docs/result.md", "content": "done\n"},
                    )
                ],
            )
        ],
    )


class ApprovalPlanTests(unittest.TestCase):
    def test_plan_round_trip_checks_digest_and_workspace(self):
        from onecode.kernel.approval_plans import load_approval_plan, persist_approval_plan

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            stored = persist_approval_plan(workspace, guarded_plan(), model_metadata={"model": "m"})
            loaded = load_approval_plan(workspace, stored.plan_id)

        self.assertEqual(loaded.plan_sha256, stored.plan_sha256)
        self.assertEqual(loaded.workspace, str(workspace.resolve()))
        self.assertEqual(loaded.plan.execution_steps[0].tool_calls[0].tool_name, "write_text")

    def test_tampered_plan_is_rejected(self):
        from onecode.kernel.approval_plans import load_approval_plan, persist_approval_plan

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            stored = persist_approval_plan(workspace, guarded_plan(), model_metadata={})
            document = json.loads(stored.path.read_text(encoding="utf-8"))
            document["plan"]["execution_plan"]["steps"][0]["tool_calls"][0]["params"]["path"] = "docs/other.md"
            stored.path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "approval_plan_mismatch"):
                load_approval_plan(workspace, stored.plan_id)

    def test_plan_store_rejects_secret_metadata(self):
        from onecode.kernel.approval_plans import persist_approval_plan

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "model_metadata"):
                persist_approval_plan(Path(tmp), guarded_plan(), model_metadata={"api_key": "secret"})

    def test_plan_store_rejects_invalid_tool_parameters_before_writing(self):
        from onecode.kernel.approval_plans import persist_approval_plan

        malformed = ModelPlan(
            task="bad command",
            execution_steps=[
                ModelExecutionStep(
                    id="bad",
                    description="bad argv",
                    tool_calls=[ModelToolCall(tool_name="run_command", params={"argv": ["echo", 1]})],
                )
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with self.assertRaisesRegex(ValueError, "argv"):
                persist_approval_plan(workspace, malformed, model_metadata={})

            pending = workspace / ".onecode" / "pending-plans"
            self.assertFalse(pending.exists())

    def test_only_one_concurrent_request_can_claim_pending_plan(self):
        from onecode.kernel.approval_plans import claim_approval_plan, persist_approval_plan

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            stored = persist_approval_plan(workspace, guarded_plan(), model_metadata={})
            barrier = Barrier(2)

            def claim():
                barrier.wait()
                try:
                    return claim_approval_plan(workspace, stored.plan_id).path.parent.name
                except ValueError as exc:
                    return str(exc)

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _index: claim(), range(2)))

        self.assertEqual(results.count("executing-plans"), 1)
        self.assertEqual(results.count("approval_plan_in_progress"), 1)

    def test_pending_plan_list_is_workspace_scoped_and_skips_invalid_files(self):
        from onecode.kernel.approval_plans import (
            list_pending_approval_plans,
            persist_approval_plan,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_workspace = root / "first"
            second_workspace = root / "second"
            first_workspace.mkdir()
            second_workspace.mkdir()
            first = persist_approval_plan(
                first_workspace, guarded_plan(), model_metadata={}
            )
            persist_approval_plan(second_workspace, guarded_plan(), model_metadata={})
            invalid = first.path.parent / ("f" * 32 + ".json")
            invalid.write_text("not-json", encoding="utf-8")

            plans, skipped = list_pending_approval_plans(first_workspace)

        self.assertEqual([plan.plan_id for plan in plans], [first.plan_id])
        self.assertEqual(skipped, 1)

    def test_pending_plan_list_rejects_invalid_limit(self):
        from onecode.kernel.approval_plans import list_pending_approval_plans

        with tempfile.TemporaryDirectory() as tmp:
            for limit in (True, 0, 101):
                with self.subTest(limit=limit), self.assertRaisesRegex(
                    ValueError, "limit must be between 1 and 100"
                ):
                    list_pending_approval_plans(Path(tmp), limit=limit)


if __name__ == "__main__":
    unittest.main()
