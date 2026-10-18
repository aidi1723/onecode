import sys
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, GuardrailConfig, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.hexagram import IchingKernel


def _execute(workspace: Path, task: str, steps: list[ExecutionStep]):
    return execute_plan(
        ExecutionPlan(task=task, steps=steps),
        workspace=workspace,
        run_id=task,
        tool_registry=default_tool_registry(),
        guardrails=GuardrailConfig(max_steps=64),
        approval_callback=lambda step: True,
    )


class ParallelRuleTaskTests(unittest.TestCase):
    def test_siblings_are_judged_separately(self):
        dam = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN)
        nourish = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.DUI)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            trace = _execute(
                workspace,
                "siblings",
                [
                    ExecutionStep(
                        id="dam",
                        description="dam",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/water.py", "content": "WATER = 1\n", "status_code": dam},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="nourish",
                        description="nourish",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/metal.py", "content": "METAL = 1\n", "status_code": nourish},
                            )
                        ],
                    ),
                ],
            )
            reasons = {step.step_id: step.reason for step in trace.step_results}
            self.assertEqual(reasons["dam"], "earth_dams_water_flow")
            self.assertIsNone(reasons["nourish"])
            self.assertFalse((workspace / "src" / "water.py").exists())
            self.assertEqual((workspace / "src" / "metal.py").read_text(encoding="utf-8"), "METAL = 1\n")

    def test_every_hexagram_patches_and_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            patch_steps = []
            command_steps = []
            for code in range(64):
                path = workspace / "src" / f"p{code}.py"
                path.write_text("VALUE = 1\n", encoding="utf-8")
                patch_steps.append(
                    ExecutionStep(
                        id=f"patch-{code}",
                        description=f"patch {code}",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="patch_text",
                                params={
                                    "path": f"src/p{code}.py",
                                    "search_block": "VALUE = 1\n",
                                    "replace_block": "VALUE = 2\n",
                                    "status_code": code,
                                },
                            )
                        ],
                    )
                )
                command_steps.append(
                    ExecutionStep(
                        id=f"command-{code}",
                        description=f"command {code}",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="run_command",
                                params={
                                    "argv": [sys.executable, "-c", f"open('c{code}.txt','w').write('ran')"],
                                    "status_code": code,
                                },
                            )
                        ],
                    )
                )
            patch_trace = _execute(workspace, "patches", patch_steps)
            command_trace = _execute(workspace, "commands", command_steps)
            patch_by_id = {step.step_id: step for step in patch_trace.step_results}
            command_by_id = {step.step_id: step for step in command_trace.step_results}
            self.assertEqual(len(patch_by_id), 64)
            self.assertEqual(len(command_by_id), 64)
            for code in range(64):
                ruling = IchingKernel.action_ruling(code, "patch_text")
                command_ruling = IchingKernel.action_ruling(code, "run_command")
                patched = (workspace / "src" / f"p{code}.py").read_text(encoding="utf-8")
                marker = workspace / f"c{code}.txt"
                with self.subTest(code=code):
                    if ruling["outcome"] == "write":
                        self.assertEqual(patched, "VALUE = 2\n")
                        self.assertEqual(patch_by_id[f"patch-{code}"].status, "completed")
                    else:
                        self.assertEqual(patched, "VALUE = 1\n")
                        self.assertEqual(patch_by_id[f"patch-{code}"].reason, ruling["reason"])
                    if command_ruling["outcome"] == "write":
                        self.assertEqual(marker.read_text(encoding="utf-8"), "ran")
                    else:
                        self.assertFalse(marker.exists())
                        self.assertEqual(command_by_id[f"command-{code}"].reason, command_ruling["reason"])
