import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import ModelExecutionStep, ModelPlan, ModelToolCall, validate_model_plan


def _plan(name: str, value: int):
    return validate_model_plan(
        {"task": f"write {name}", "assets": [{"path": f"src/{name}.py", "content": f"VALUE = {value}\n"}]}
    )


def _done():
    return validate_model_plan({"task": "done", "no_action": {"reason": "already complete"}})


def _step_plan() -> ModelPlan:
    return ModelPlan(
        task="write two steps",
        execution_steps=[
            ModelExecutionStep(
                id="one",
                description="write one",
                tool_calls=[ModelToolCall(tool_name="write_text", params={"path": "src/one.py", "content": "VALUE = 1\n"})],
            ),
            ModelExecutionStep(
                id="two",
                description="write two",
                depends_on=["one"],
                tool_calls=[ModelToolCall(tool_name="write_text", params={"path": "src/two.py", "content": "VALUE = 2\n"})],
            ),
        ],
    )


class ScriptProvider:
    def __init__(self, steps: list[object]) -> None:
        self.steps = list(steps)

    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def _law(result: dict) -> dict:
    classified = IchingKernel.classify_outcome(result["status"], result.get("reason"))
    transition = IchingKernel.transition(classified)
    delivery = IchingKernel.delivery_decision(
        result["status"],
        result.get("requested_count"),
        result.get("completed_count"),
        result.get("skipped_count"),
        result.get("failed_count"),
    )
    return {
        "status_code": transition.status_code,
        "action": transition.action,
        "dispatch": IchingKernel.dispatch_decision(transition),
        "exit_code": IchingKernel.process_exit_code(result["status"], result.get("reason")),
        "delivery_status": delivery["delivery_status"],
        "next_action": delivery["next_action"],
    }


class RuleRuntimeRoundTests(unittest.TestCase):
    def test_three_rounds_keep_runtime_on_the_transition_law(self):
        scenarios = {
            "one-file": (
                [ValueError("model response was truncated"), _plan("one", 1)],
                1,
                "completed",
                None,
            ),
            "budget": (
                [ValueError("model response was truncated"), _plan("one", 1), _plan("two", 2)],
                2,
                "halted",
                "resource_budget_exceeded",
            ),
            "closed": (
                [ValueError("model response was truncated"), _plan("one", 1), _done()],
                2,
                "completed",
                None,
            ),
            "invalid": (
                [
                    ValueError("model response was truncated"),
                    _plan("one", 1),
                    ValueError("asset content must be a non-empty string"),
                ],
                2,
                "halted",
                "invalid_model_plan",
            ),
            "bare-truncate": (
                [ValueError("model response was truncated")],
                0,
                "halted",
                "resource_budget_exceeded",
            ),
            "direct": (
                [_plan("one", 1)],
                0,
                "completed",
                None,
            ),
            "steps": (
                [_step_plan()],
                0,
                "completed",
                None,
            ),
        }
        seen: dict[str, tuple] = {}
        for round_index in range(3):
            for name, (steps, repairs, status, reason) in scenarios.items():
                with self.subTest(round=round_index, scenario=name):
                    with tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        result = run_model_task(
                            "exercise the rule",
                            workspace=root,
                            run_id=name,
                            api_key="key",
                            model="m",
                            provider=ScriptProvider(list(steps)),
                            max_repair_attempts=repairs,
                            execution_approval=lambda step: True,
                        )
                        law = _law(result)
                        self.assertEqual(result["status"], status)
                        self.assertEqual(result.get("reason"), reason)
                        self.assertEqual(result["iching_status_code"], law["status_code"])
                        self.assertEqual(result["iching_transition_action"], law["action"])
                        self.assertEqual(law["exit_code"], 0 if law["dispatch"] == "continue" else 1)
                        if result.get("dispatch_decision") is not None:
                            self.assertEqual(result["dispatch_decision"], law["dispatch"])
                        if result.get("delivery_status") is not None:
                            self.assertEqual(result["delivery_status"], law["delivery_status"])
                            self.assertEqual(result["next_action"], law["next_action"])
                        ledger = json.loads(
                            (root / ".onecode" / "runs" / name / "ledger.json").read_text(encoding="utf-8")
                        )
                        self.assertEqual(ledger["status"], result["status"])
                        self.assertEqual(ledger.get("reason"), result.get("reason"))
                        self.assertEqual(ledger["completed_count"], result["completed_count"])
                        self.assertEqual(ledger["iching_status_code"], result["iching_status_code"])
                        signature = (
                            result["status"],
                            result.get("reason"),
                            result["iching_status_code"],
                            result["iching_transition_action"],
                            result["completed_count"],
                        )
                        if name in seen:
                            self.assertEqual(signature, seen[name])
                        else:
                            seen[name] = signature
