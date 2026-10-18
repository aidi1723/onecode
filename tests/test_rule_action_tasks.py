import sys
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.hexagram import IchingKernel


def _run(workspace: Path, name: str, tool_name: str, params: dict):
    trace = execute_plan(
        ExecutionPlan(
            task=name,
            steps=[ExecutionStep(id=name, description=name, tool_calls=[ToolCallSpec(tool_name=tool_name, params=params)])],
        ),
        workspace=workspace,
        run_id=name,
        tool_registry=default_tool_registry(),
        approval_callback=lambda step: True,
    )
    return trace


class RuleActionTaskTests(unittest.TestCase):
    def test_reads_follow_rest_and_discovery_and_stop_for_fire(self):
        for code in range(64):
            ruling = IchingKernel.action_ruling(code, "read_text")
            with self.subTest(code=code, outcome=ruling["outcome"]):
                with tempfile.TemporaryDirectory() as tmp:
                    workspace = Path(tmp)
                    (workspace / "src").mkdir()
                    (workspace / "src" / "note.py").write_text("NOTE = 1\n", encoding="utf-8")
                    trace = _run(
                        workspace,
                        f"read-{code}",
                        "read_text",
                        {"path": "src/note.py", "status_code": code},
                    )
                    if ruling["outcome"] == "allow":
                        self.assertTrue(trace.success)
                        payload = trace.step_results[0].tool_results[0].output["payload"]
                        self.assertIn("NOTE = 1", payload["content"])
                    else:
                        self.assertFalse(trace.success)
                        self.assertEqual(trace.step_results[0].reason, ruling["reason"])

    def test_command_and_patch_follow_generation_and_control(self):
        dam = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN)
        nourish = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.DUI)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            target = workspace / "src" / "line.py"
            target.write_text("VALUE = 1\n", encoding="utf-8")
            blocked = _run(
                workspace,
                "dam-command",
                "run_command",
                {
                    "argv": [sys.executable, "-c", "open('ran.txt','w').write('ran')"],
                    "status_code": dam,
                },
            )
            self.assertFalse(blocked.success)
            self.assertEqual(blocked.step_results[0].reason, "earth_dams_water_flow")
            self.assertFalse((workspace / "ran.txt").exists())

            allowed = _run(
                workspace,
                "nourish-command",
                "run_command",
                {
                    "argv": [sys.executable, "-c", "open('ran.txt','w').write('ran')"],
                    "status_code": nourish,
                },
            )
            self.assertTrue(allowed.success)
            self.assertEqual((workspace / "ran.txt").read_text(encoding="utf-8"), "ran")

            untouched = _run(
                workspace,
                "dam-patch",
                "patch_text",
                {
                    "path": "src/line.py",
                    "search_block": "VALUE = 1\n",
                    "replace_block": "VALUE = 2\n",
                    "status_code": dam,
                },
            )
            self.assertFalse(untouched.success)
            self.assertEqual(target.read_text(encoding="utf-8"), "VALUE = 1\n")

            changed = _run(
                workspace,
                "nourish-patch",
                "patch_text",
                {
                    "path": "src/line.py",
                    "search_block": "VALUE = 1\n",
                    "replace_block": "VALUE = 2\n",
                    "status_code": nourish,
                },
            )
            self.assertTrue(changed.success)
            self.assertEqual(target.read_text(encoding="utf-8"), "VALUE = 2\n")

            listed = _run(
                workspace,
                "discover-list",
                "list_files",
                {"path": "src", "status_code": 0},
            )
            self.assertTrue(listed.success)
            self.assertIn("src/line.py", listed.step_results[0].tool_results[0].output["payload"]["files"])
