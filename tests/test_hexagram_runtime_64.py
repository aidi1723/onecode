import tempfile
import unittest
from pathlib import Path

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.hexagram import IchingKernel


def _write(workspace: Path, code: int):
    plan = ExecutionPlan(
        task=f"hexagram {code}",
        steps=[
            ExecutionStep(
                id="write",
                description=f"write under {code}",
                tool_calls=[
                    ToolCallSpec(
                        tool_name="write_text",
                        params={
                            "path": f"src/h{code}.py",
                            "content": f"CODE = {code}\n",
                            "status_code": code,
                        },
                    )
                ],
            )
        ],
    )
    trace = execute_plan(
        plan,
        workspace=workspace,
        run_id=f"h{code}",
        tool_registry=default_tool_registry(),
        approval_callback=lambda step: True,
    )
    return trace, workspace / "src" / f"h{code}.py"


class HexagramRuntimeTests(unittest.TestCase):
    def test_repeated_hexagram_stays_itself_instead_of_entropy_rollback(self):
        discover = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN)
        dam = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            trace = execute_plan(
                ExecutionPlan(
                    task="two discoveries",
                    steps=[
                        ExecutionStep(
                            id="first",
                            description="first",
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={"path": "src/a.py", "content": "A = 1\n", "status_code": discover},
                                )
                            ],
                        ),
                        ExecutionStep(
                            id="second",
                            description="second",
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={"path": "src/b.py", "content": "B = 1\n", "status_code": discover},
                                )
                            ],
                        ),
                    ],
                ),
                workspace=workspace,
                run_id="two-discover",
                tool_registry=default_tool_registry(),
                approval_callback=lambda step: True,
            )
            self.assertEqual(trace.global_status_code, discover)
            self.assertEqual(trace.global_transition.action, "discover")
            self.assertEqual({step.reason for step in trace.step_results}, {"rule_gap_requires_discovery"})
            self.assertFalse((workspace / "src" / "a.py").exists())

            dam_trace = execute_plan(
                ExecutionPlan(
                    task="two dams",
                    steps=[
                        ExecutionStep(
                            id="one",
                            description="one",
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={"path": "src/c.py", "content": "C = 1\n", "status_code": dam},
                                )
                            ],
                        ),
                        ExecutionStep(
                            id="two",
                            description="two",
                            tool_calls=[
                                ToolCallSpec(
                                    tool_name="write_text",
                                    params={"path": "src/d.py", "content": "D = 1\n", "status_code": dam},
                                )
                            ],
                        ),
                    ],
                ),
                workspace=workspace,
                run_id="two-dams",
                tool_registry=default_tool_registry(),
                approval_callback=lambda step: True,
            )
            self.assertEqual(dam_trace.global_status_code, dam)
            self.assertEqual({step.reason for step in dam_trace.step_results}, {"earth_dams_water_flow"})
            self.assertEqual(
                IchingKernel.task_schedule(dam_trace.global_status_code)["schedule_action"],
                "throttle",
            )
    def test_every_hexagram_runs_its_balance_and_element_rule(self):
        self.assertEqual(len({code for code in range(64)}), 64)
        for round_index in range(2):
            for code in range(64):
                ruling = IchingKernel.write_ruling(code)
                profile = IchingKernel.yin_yang_profile(code)
                dynamics = IchingKernel.element_dynamics(code)
                with self.subTest(round=round_index, code=code, outcome=ruling["outcome"]):
                    self.assertEqual(ruling["balance"], profile["balance"])
                    self.assertEqual(ruling["cross_relation"], dynamics["cross_relation"])
                    self.assertEqual(ruling["modulation"], dynamics["modulation"])
                    if profile["balance"] in {"pure_yang", "yang_excess"} and dynamics["outer_element"] != "fire":
                        self.assertEqual(ruling["schedule_action"], "cooldown")
                        self.assertEqual(ruling["outcome"], "refuse")
                    if profile["balance"] == "pure_yin":
                        self.assertEqual(ruling["schedule_action"], "discover")
                        self.assertEqual(ruling["outcome"], "refuse")
                    if dynamics["outer_element"] == "fire":
                        self.assertEqual(ruling["outcome"], "refuse")
                    with tempfile.TemporaryDirectory() as tmp:
                        trace, path = _write(Path(tmp), code)
                        if ruling["schedule_action"] in {"throttle", "prune", "halt", "checkpoint", "cooldown", "discover"}:
                            self.assertEqual(ruling["reason"], ruling["schedule_reason"])
                        if ruling["outcome"] == "write":
                            self.assertTrue(trace.success)
                            self.assertTrue(path.is_file())
                            self.assertIsNone(ruling["reason"])
                        else:
                            self.assertFalse(trace.success)
                            self.assertFalse(path.exists())
                            self.assertEqual(trace.step_results[0].reason, ruling["reason"])
                        self.assertEqual(trace.step_results[0].iching_status_code, code)
                        self.assertEqual(trace.global_status_code, code)
                        if ruling["outcome"] == "refuse":
                            classified = IchingKernel.classify_outcome("halted", ruling["reason"])
                            again = IchingKernel.task_schedule(classified)
                            self.assertEqual(again["schedule_action"], ruling["schedule_action"])
                            self.assertEqual(again["schedule_reason"], ruling["reason"])
                            self.assertEqual(IchingKernel.process_exit_code("halted", str(ruling["reason"])), 1)
