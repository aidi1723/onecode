import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
