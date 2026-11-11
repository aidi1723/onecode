import tempfile
import unittest
from pathlib import Path

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import validate_model_plan
from onecode.kernel.outcome_policy import agent_cycle_decision


class _OneFile:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        return validate_model_plan(
            {"task": "write one", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
        )


def _run_tagged_write(workspace: Path, code: int):
    plan = ExecutionPlan(
        task=f"schedule {code}",
        steps=[
            ExecutionStep(
                id="write",
                description="tagged write",
                tool_calls=[
                    ToolCallSpec(
                        tool_name="write_text",
                        params={
                            "path": f"src/code_{code}.py",
                            "content": f"CODE = {code}\n",
                            "status_code": code,
                        },
                    )
                ],
            )
        ],
    )
    return execute_plan(
        plan,
        workspace=workspace,
        run_id=f"schedule-{code}",
        tool_registry=default_tool_registry(),
        approval_callback=lambda step: True,
    )


class ElementTaskRoundTests(unittest.TestCase):
    def test_three_rounds_schedule_matches_transition(self):
        for _round_index in range(3):
            for code in range(64):
                schedule = IchingKernel.task_schedule(code)
                self.assertEqual(schedule["schedule_action"], schedule["transition_action"])
                self.assertEqual(schedule["schedule_reason"], schedule["transition_reason"])
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                dam = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN)
                trace = _run_tagged_write(workspace, dam)
                self.assertFalse(trace.success)
                self.assertEqual(trace.step_results[0].reason, "earth_dams_water_flow")

    def test_three_rounds_nourish_then_dam_then_cooldown(self):
        dam = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN)
        nourish = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.DUI)
        signatures = []
        for _round_index in range(3):
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                plan = ExecutionPlan(
                    task="nourish then dam",
                    steps=[
                        ExecutionStep(
                            id="nourish",
                            description="earth generates metal",
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={
                                        "path": "src/metal.py",
                                        "content": "METAL = 1\n",
                                        "status_code": nourish,
                                    },
                                )
                            ],
                        ),
                        ExecutionStep(
                            id="dam",
                            description="earth dams water",
                            depends_on=["nourish"],
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={
                                        "path": "src/water.py",
                                        "content": "WATER = 1\n",
                                        "status_code": dam,
                                    },
                                )
                            ],
                        ),
                    ],
                )
                trace = execute_plan(
                    plan,
                    workspace=workspace,
                    run_id="nourish-dam",
                    tool_registry=default_tool_registry(),
                    approval_callback=lambda step: True,
                )
                self.assertTrue((workspace / "src" / "metal.py").exists())
                self.assertFalse((workspace / "src" / "water.py").exists())
                self.assertEqual(trace.step_results[-1].reason, "earth_dams_water_flow")

                result = run_model_task(
                    "cool a write",
                    workspace=workspace,
                    run_id="cooled",
                    api_key="key",
                    model="m",
                    provider=_OneFile(),
                    execution_approval=lambda step: True,
                )
                decision = agent_cycle_decision("completed", None)
                self.assertEqual(result["iching_transition_action"], "cooldown")
                self.assertEqual(decision["schedule_action"], "accelerate")
                self.assertEqual(decision["cross_relation"], "generates")
                self.assertEqual(decision["balance"], "balanced")
                signatures.append(
                    (
                        trace.step_results[-1].reason,
                        result["iching_status_code"],
                        result["iching_transition_action"],
                        decision["schedule_action"],
                    )
                )
        self.assertEqual(len(set(signatures)), 1)
