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
                        if ruling["outcome"] == "write":
                            self.assertTrue(trace.success)
                            self.assertTrue(path.is_file())
                            self.assertIsNone(ruling["reason"])
                        else:
                            self.assertFalse(trace.success)
                            self.assertFalse(path.exists())
                            self.assertEqual(trace.step_results[0].reason, ruling["reason"])
