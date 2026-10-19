import sys
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.agent_cycle import run_agent_cycle
from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import validate_model_plan
from onecode.kernel.outcome_policy import agent_cycle_decision
from onecode.kernel.run_inspection import apply_verifier_evidence
from onecode.kernel.sandbox import SandboxConfig
from onecode.kernel.verifier import VerifierSpec, run_verifier


def _code(outer: int, inner: int) -> int:
    return IchingKernel.compute_status(outer, inner)


def _expect_outcome(status: str, reason: str | None, action: str, outer: int, inner: int) -> None:
    classified = IchingKernel.classify_outcome(status, reason)
    transition = IchingKernel.transition(classified)
    if classified != _code(outer, inner):
        raise AssertionError(f"{reason}: code {classified} != {_code(outer, inner)}")
    if transition.action != action:
        raise AssertionError(f"{reason}: action {transition.action} != {action}")


def _tagged(workspace: Path, name: str, code: int):
    plan = ExecutionPlan(
        task=name,
        steps=[
            ExecutionStep(
                id="write",
                description=name,
                tool_calls=[
                    ToolCallSpec(
                        tool_name="write_text",
                        params={"path": f"src/{name}.py", "content": f"NAME = {name!r}\n", "status_code": code},
                    )
                ],
            )
        ],
    )
    trace = execute_plan(
        plan,
        workspace=workspace,
        run_id=name,
        tool_registry=default_tool_registry(),
        approval_callback=lambda step: True,
    )
    return trace, workspace / "src" / f"{name}.py"


class _Plan:
    def __init__(self, plan) -> None:
        self.plan = plan

    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        if isinstance(self.plan, Exception):
            raise self.plan
        return self.plan


class RuleTaskVarietyTests(unittest.TestCase):
    def test_different_tasks_follow_their_rules(self):
        report = []
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            written = validate_model_plan(
                {"task": "write", "assets": [{"path": "src/note.py", "content": "NOTE = 1\n"}]}
            )
            completed = run_model_task(
                "write a note",
                workspace=workspace,
                run_id="note",
                api_key="key",
                model="m",
                provider=_Plan(written),
                execution_approval=lambda step: True,
            )
            decision = agent_cycle_decision("completed", None)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["iching_transition_action"], "cooldown")
            self.assertEqual(decision["schedule_action"], "accelerate")
            self.assertTrue((workspace / "src" / "note.py").exists())
            report.append("write completed -> cooldown, next accelerate")

            refused = run_model_task(
                "write a note",
                workspace=workspace,
                run_id="refused",
                api_key="key",
                model="m",
                provider=_Plan(written),
            )
            _expect_outcome("halted", "approval_required", "halt", IchingKernel.LI, IchingKernel.KUN)
            self.assertEqual(refused["reason"], "approval_required")
            report.append("write without approval -> Li/Kun halt")

            truncated = run_model_task(
                "large",
                workspace=workspace,
                run_id="truncated",
                api_key="key",
                model="m",
                provider=_Plan(ValueError("model response was truncated")),
            )
            self.assertEqual(truncated["reason"], "resource_budget_exceeded")
            _expect_outcome("halted", truncated["reason"], "halt", IchingKernel.LI, IchingKernel.KUN)
            report.append("truncated plan -> Li/Kun halt")

            empty = run_model_task(
                "empty",
                workspace=workspace,
                run_id="empty",
                api_key="key",
                model="m",
                provider=_Plan(ValueError("asset content must be a non-empty string")),
            )
            self.assertEqual(empty["reason"], "invalid_model_plan")
            _expect_outcome("halted", empty["reason"], "halt", IchingKernel.LI, IchingKernel.KUN)
            report.append("empty asset -> Li/Kun halt")

        def propose(history, allowed):
            if not history:
                return [{"tool_name": "search_text", "params": {"query": "missing"}}]
            return []

        def execute(tool_name, params):
            return {"status": "completed", "reason": "search_miss", "matches": []}

        found = run_agent_cycle(propose=propose, execute=execute, max_turns=4)
        miss = agent_cycle_decision("completed", "search_miss")
        self.assertEqual(found["status"], "completed")
        self.assertEqual(miss["cycle"], "read_only_continue")
        self.assertEqual(miss["status_code"], _code(IchingKernel.KUN, IchingKernel.KUN))
        report.append("search miss -> Kun/Kun discover, read only")

        def time_out(tool_name, params):
            return {"status": "halted", "reason": "http_timeout"}

        timed = run_agent_cycle(propose=lambda history, allowed: [{"tool_name": "read_text", "params": {"path": "x"}}], execute=time_out, max_turns=2)
        timeout_rule = agent_cycle_decision("halted", "http_timeout")
        self.assertEqual(timed["reason"], "http_timeout")
        self.assertEqual(timeout_rule["cycle"], "verify")
        self.assertEqual(timeout_rule["status_code"], _code(IchingKernel.KAN, IchingKernel.ZHEN))
        report.append("http timeout -> Kan/Zhen checkpoint")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            missing = execute_plan(
                ExecutionPlan(
                    task="missing binary",
                    steps=[
                        ExecutionStep(
                            id="run",
                            description="missing",
                            tool_calls=[ToolCallSpec(tool_name="run_command", params={"argv": ["python-not-installed-for-onecode"]})],
                        )
                    ],
                ),
                workspace=workspace,
                approval_callback=lambda step: True,
            )
            self.assertEqual(missing.step_results[0].reason, "action_exception")
            _expect_outcome("halted", "action_exception", "checkpoint", IchingKernel.GEN, IchingKernel.KUN)
            report.append("missing command -> Gen/Kun checkpoint")

            cases = [
                ("dam", _code(IchingKernel.KUN, IchingKernel.KAN), False, "earth_dams_water_flow"),
                ("nourish", _code(IchingKernel.KUN, IchingKernel.DUI), True, None),
                ("recover", _code(IchingKernel.KUN, IchingKernel.LI), True, None),
                ("break_ground", _code(IchingKernel.ZHEN, IchingKernel.GEN), True, None),
                ("controlled", _code(IchingKernel.KUN, IchingKernel.ZHEN), False, "controlled_by_relation_requires_verifier"),
                ("fire", _code(IchingKernel.LI, IchingKernel.QIAN), False, "sovereignty_fire_suppresses_asset"),
            ]
            for name, code, wrote, reason in cases:
                trace, path = _tagged(workspace, name, code)
                self.assertEqual(path.exists(), wrote, name)
                if reason is not None:
                    self.assertEqual(trace.step_results[0].reason, reason, name)
                report.append(f"{name} -> exists={wrote} reason={trace.step_results[0].reason}")

            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_note.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n def test_bad(self):\n  self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            verifier = run_verifier(
                workspace,
                VerifierSpec(
                    id="python-unittest",
                    command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    cwd=".",
                    timeout_ms=5000,
                ),
                sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
            )
            checked = apply_verifier_evidence(completed, workspace, [verifier])
            reason = checked["reason"]
            if reason == "sandbox_required":
                self.assertEqual(checked["iching_transition_action"], "checkpoint")
                self.assertEqual(checked["iching_status_code"], _code(IchingKernel.GEN, IchingKernel.KUN))
            elif reason == "image_platform_mismatch":
                self.assertEqual(checked["iching_transition_action"], "checkpoint")
                self.assertEqual(checked["iching_status_code"], _code(IchingKernel.KAN, IchingKernel.ZHEN))
            elif reason == "verifier_failed":
                self.assertIn("AssertionError", verifier.stderr_tail)
                self.assertEqual(checked["iching_transition_action"], "halt")
                self.assertEqual(checked["iching_status_code"], _code(IchingKernel.LI, IchingKernel.KUN))
            else:
                self.fail(reason)
            report.append(f"verifier {reason}")

        self.assertGreaterEqual(len(report), 12)
        if __name__ == "__main__":
            print("\n".join(report))
