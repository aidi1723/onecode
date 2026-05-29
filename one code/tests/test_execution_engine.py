import tempfile
import unittest
import json
import time
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.execution_contracts import (
    ExecutionPlan,
    ExecutionStep,
    GuardrailConfig,
    ToolCallSpec,
)
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_guardrails import validate_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.execution_plan_loader import execution_trace_to_dict
from onecode.kernel.hexagram import IchingKernel


class ExecutionEngineTests(unittest.TestCase):
    def test_validate_plan_rejects_excessive_steps_and_forbidden_tools(self):
        too_many_steps = ExecutionPlan(
            task="too large",
            steps=[
                ExecutionStep(id=f"s{index}", description="noop", tool_calls=[])
                for index in range(3)
            ],
        )

        excessive = validate_plan(too_many_steps, GuardrailConfig(max_steps=2))

        self.assertFalse(excessive.valid)
        self.assertEqual(excessive.reason, "max_steps_exceeded")

        forbidden_plan = ExecutionPlan(
            task="bad tool",
            steps=[
                ExecutionStep(
                    id="s1",
                    description="execute",
                    tool_calls=[ToolCallSpec(tool_name="bash_execution", params={})],
                )
            ],
        )

        forbidden = validate_plan(forbidden_plan, GuardrailConfig(forbidden_tools=["bash_execution"]))

        self.assertFalse(forbidden.valid)
        self.assertEqual(forbidden.reason, "forbidden_tool")

    def test_execute_plan_routes_write_and_patch_tools_through_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="build then patch",
                steps=[
                    ExecutionStep(
                        id="write",
                        description="create file",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/mesh.py", "content": "def status():\n    return False\n"},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="patch",
                        description="patch file",
                        depends_on=["write"],
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="patch_text",
                                params={
                                    "path": "src/mesh.py",
                                    "search_block": "return False",
                                    "replace_block": "return True",
                                },
                            )
                        ],
                    ),
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="execution-plan-run",
                tool_registry=default_tool_registry(),
            )

            self.assertTrue(trace.success)
            self.assertEqual([step.status for step in trace.step_results], ["completed", "completed"])
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "def status():\n    return True\n")
            self.assertEqual(trace.runner_results[-1]["status"], "completed")
            self.assertEqual(trace.runner_results[-1]["intent_type"], "patch_text")

    def test_execute_plan_skips_step_when_dependency_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="failed dependency",
                steps=[
                    ExecutionStep(
                        id="bad",
                        description="bad patch",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="patch_text",
                                params={
                                    "path": "src/missing.py",
                                    "search_block": "missing",
                                    "replace_block": "new",
                                },
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="dependent",
                        description="should skip",
                        depends_on=["bad"],
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/after.py", "content": "AFTER = True\n"},
                            )
                        ],
                    ),
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="execution-dependency-run",
                tool_registry=default_tool_registry(),
            )

            self.assertFalse(trace.success)
            self.assertEqual([step.status for step in trace.step_results], ["failed", "skipped"])
            self.assertEqual(trace.step_results[0].reason, "patch_target_not_found")
            self.assertEqual(trace.step_results[1].reason, "dependencies_not_met")
            self.assertFalse((workspace / "src" / "after.py").exists())

    def test_execute_plan_breaks_immediately_on_sovereignty_breach(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="unsafe then next",
                steps=[
                    ExecutionStep(
                        id="unsafe",
                        description="escape workspace",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "../outside.py", "content": "BAD = True\n"},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="next",
                        description="must not run after safety breach",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/after.py", "content": "AFTER = True\n"},
                            )
                        ],
                    ),
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="execution-safety-break-run",
                tool_registry=default_tool_registry(),
                guardrails=GuardrailConfig(max_consecutive_failures=3),
            )

            self.assertFalse(trace.success)
            self.assertEqual(len(trace.step_results), 1)
            self.assertEqual(trace.step_results[0].status, "failed")
            self.assertEqual(trace.step_results[0].reason, "sovereignty_breach")
            self.assertFalse((workspace / "src" / "after.py").exists())

    def test_execute_plan_runs_independent_steps_in_parallel_with_stable_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="parallel independent writes",
                steps=[
                    ExecutionStep(
                        id="first",
                        description="first independent write",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/first.py", "content": "FIRST = True\n"},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="second",
                        description="second independent write",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/second.py", "content": "SECOND = True\n"},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="after",
                        description="dependent write",
                        depends_on=["first", "second"],
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/after.py", "content": "AFTER = True\n"},
                            )
                        ],
                    ),
                ],
            )
            call_times: dict[str, float] = {}

            def slow_run_task(task, *, workspace, run_id, resume_from_run_id, plan_actions):
                path = plan_actions[0]["path"]
                call_times[path] = time.monotonic()
                time.sleep(0.08)
                target = workspace / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(plan_actions[0]["content"], encoding="utf-8")
                return {
                    "status": "completed",
                    "reason": None,
                    "payload": {"path": str(target)},
                    "intent_type": plan_actions[0]["action_type"],
                }

            started = time.monotonic()
            with patch("onecode.kernel.execution_engine.run_task", side_effect=slow_run_task):
                trace = execute_plan(
                    plan,
                    workspace=workspace,
                    run_id="parallel-run",
                    tool_registry=default_tool_registry(),
                )
            duration = time.monotonic() - started

            self.assertTrue(trace.success)
            self.assertEqual([step.step_id for step in trace.step_results], ["first", "second", "after"])
            self.assertLess(duration, 0.22)
            self.assertLess(abs(call_times["src/first.py"] - call_times["src/second.py"]), 0.05)
            self.assertGreater(call_times["src/after.py"], max(call_times["src/first.py"], call_times["src/second.py"]))
            self.assertTrue(all(step.duration_ms >= 80 for step in trace.step_results))
            trace_dict = execution_trace_to_dict(trace)
            self.assertTrue(all(step["duration_ms"] >= 80 for step in trace_dict["step_results"]))

    def test_execute_plan_records_global_status_from_parallel_step_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="global status",
                steps=[
                    ExecutionStep(
                        id="ok",
                        description="completed write",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/ok.py", "content": "OK = True\n"},
                            )
                        ],
                    ),
                    ExecutionStep(
                        id="bad",
                        description="missing patch",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="patch_text",
                                params={
                                    "path": "src/missing.py",
                                    "search_block": "missing",
                                    "replace_block": "new",
                                },
                            )
                        ],
                    ),
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="global-status-run",
                tool_registry=default_tool_registry(),
            )

            expected = IchingKernel.aggregate_status(
                [
                    IchingKernel.classify_outcome("completed", None),
                    IchingKernel.classify_outcome("halted", "patch_target_not_found"),
                ]
            )
            self.assertFalse(trace.success)
            self.assertEqual(trace.global_status_code, expected)
            self.assertEqual(trace.global_transition.action, IchingKernel.transition(expected).action)

    def test_execution_trace_dict_exports_global_status_and_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="trace global status",
                steps=[
                    ExecutionStep(
                        id="write",
                        description="create file",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/mesh.py", "content": "READY = True\n"},
                            )
                        ],
                    )
                ],
            )

            trace = execute_plan(plan, workspace=workspace, run_id="trace-global-run")
            trace_dict = execution_trace_to_dict(trace)

            self.assertEqual(trace_dict["global_status_code"], trace.global_status_code)
            self.assertEqual(trace_dict["global_transition"]["status_code"], trace.global_transition.status_code)
            self.assertEqual(trace_dict["global_transition"]["action"], trace.global_transition.action)
            self.assertEqual(trace_dict["global_transition"]["reason"], trace.global_transition.reason)

    def test_execute_plan_blocks_zero_bandwidth_steps_before_running_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="bandwidth block",
                steps=[
                    ExecutionStep(
                        id="blocked",
                        description="fire over metal cannot write",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={
                                    "path": "src/blocked.py",
                                    "content": "BLOCKED = True\n",
                                    "status_code": IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN),
                                },
                            )
                        ],
                    )
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="bandwidth-block-run",
                tool_registry=default_tool_registry(),
            )

            self.assertFalse(trace.success)
            self.assertEqual(trace.step_results[0].reason, "execution_bandwidth_zero")
            self.assertFalse((workspace / "src" / "blocked.py").exists())

    def test_execute_plan_requires_approval_for_guarded_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ExecutionPlan(
                task="approval",
                steps=[
                    ExecutionStep(
                        id="write",
                        description="create file",
                        tool_calls=[
                            ToolCallSpec(
                                tool_name="write_text",
                                params={"path": "src/mesh.py", "content": "VALUE = 1\n"},
                            )
                        ],
                    )
                ],
            )

            trace = execute_plan(
                plan,
                workspace=workspace,
                run_id="execution-approval-run",
                tool_registry=default_tool_registry(),
                approval_callback=lambda step: False,
            )

            self.assertFalse(trace.success)
            self.assertEqual(trace.step_results[0].status, "skipped")
            self.assertEqual(trace.step_results[0].reason, "approval_rejected")
            self.assertFalse((workspace / "src" / "mesh.py").exists())

    def test_cli_run_execution_plan_loads_json_and_executes_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            plan_path = Path(tmp) / "plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "cli execution",
                        "steps": [
                            {
                                "id": "write",
                                "description": "create file",
                                "tool_calls": [
                                    {
                                        "tool_name": "write_text",
                                        "params": {"path": "src/mesh.py", "content": "VALUE = 1\n"},
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-execution-plan",
                        "--workspace",
                        str(workspace),
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "cli-execution-plan",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            payload = json.loads(print_mock.call_args.args[0])
            self.assertTrue(payload["success"])
            self.assertEqual(payload["step_results"][0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
