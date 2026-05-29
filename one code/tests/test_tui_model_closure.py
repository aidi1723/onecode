import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.tui.app import OneCodeApp, format_execution_trace


class TuiModelClosureTests(unittest.TestCase):
    def test_natural_language_task_routes_through_model_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = OneCodeApp(workspace=Path(tmp), model="test-model")

            with patch(
                "onecode.tui.app.run_model_task",
                return_value={
                    "status": "completed",
                    "run_id": "model-task",
                    "reason": None,
                    "iching_transition_action": "continue",
                    "iching_transition_reason": None,
                    "completed_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                },
            ) as run_model_task_mock:
                app._task_worker("create src/hello.py with a greeting function")

            run_model_task_mock.assert_called_once()
            _, kwargs = run_model_task_mock.call_args
            self.assertEqual(kwargs["workspace"], Path(tmp).resolve())
            self.assertEqual(kwargs["model"], "test-model")
            self.assertEqual(kwargs["provider_kind"], "chat")

    def test_blocking_tui_workers_run_in_threads(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "plan.json").write_text(
                '{"task":"tui exec","steps":[{"id":"write","description":"write","tool_calls":[]}]}',
                encoding="utf-8",
            )
            app = OneCodeApp(workspace=workspace, model="test-model")
            app.api_key = "test-key"

            with (
                patch.object(app, "run_worker") as run_worker_mock,
                patch.object(app, "_system"),
                patch.object(app, "_error"),
            ):
                app._run_chat("hello")
                app._run_kernel_task("create src/hello.py")
                app._run_write("src/hello.py=print('hi')\n")
                app._run_execution_plan("plan.json")
                app._run_doctor()
                app._run_inspect("run-1")
                app._run_list_runs()

            self.assertEqual(
                [kwargs.get("thread") for _, kwargs in run_worker_mock.call_args_list],
                [True, True, True, True, True, True, True],
            )
            self.assertEqual(
                [kwargs.get("name") for _, kwargs in run_worker_mock.call_args_list],
                ["chat", "task", "task", "execution-plan", "doctor", "inspect", "list-runs"],
            )

    def test_execution_trace_feedback_lists_steps_tools_and_runner_ledger(self):
        trace = {
            "success": False,
            "reason": "patch_compile_error",
            "step_results": [
                {
                    "step_id": "asset-1",
                    "status": "completed",
                    "reason": None,
                    "tool_results": [{"tool_name": "write_text", "success": True, "reason": None}],
                },
                {
                    "step_id": "patch-1",
                    "status": "failed",
                    "reason": "patch_compile_error",
                    "tool_results": [{"tool_name": "patch_text", "success": False, "reason": "patch_compile_error"}],
                },
                {
                    "step_id": "after",
                    "status": "skipped",
                    "reason": "dependencies_not_met",
                    "tool_results": [],
                },
            ],
            "runner_results": [
                {
                    "run_id": "exec-run",
                    "status": "halted",
                    "completed_count": 0,
                    "skipped_count": 0,
                    "failed_count": 1,
                    "iching_transition_action": "halt",
                    "iching_transition_reason": "sovereignty_fire_boundary_halt",
                }
            ],
        }

        feedback = format_execution_trace(trace)

        self.assertIn("Execution: [red]failed[/red]", feedback)
        self.assertIn("step asset-1: completed", feedback)
        self.assertIn("tool write_text: ok", feedback)
        self.assertIn("step patch-1: failed | patch_compile_error", feedback)
        self.assertIn("tool patch_text: failed | patch_compile_error", feedback)
        self.assertIn("step after: skipped | dependencies_not_met", feedback)
        self.assertIn("ledger: exec-run halted", feedback)
        self.assertIn("action: halt | reason: sovereignty_fire_boundary_halt", feedback)

    def test_execution_plan_worker_loads_plan_and_returns_trace_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "plan.json"
            plan_path.write_text(
                '{"task":"tui exec","steps":[{"id":"write","description":"write",'
                '"tool_calls":[{"tool_name":"write_text","params":{"path":"src/a.py","content":"A = 1\\n"}}]}]}',
                encoding="utf-8",
            )
            app = OneCodeApp(workspace=workspace, model="test-model")

            trace = app._execution_plan_worker(plan_path)

            self.assertTrue(trace["success"])
            self.assertEqual(trace["step_results"][0]["status"], "completed")
            self.assertEqual((workspace / "src" / "a.py").read_text(encoding="utf-8"), "A = 1\n")

    def test_task_handler_formats_model_execution_trace_when_present(self):
        app = OneCodeApp(model="test-model")
        result = {
            "status": "completed",
            "intent_type": "execution_plan",
            "execution_trace": {
                "success": True,
                "reason": None,
                "step_results": [
                    {
                        "step_id": "write",
                        "status": "completed",
                        "reason": None,
                        "tool_results": [{"tool_name": "write_text", "success": True, "reason": None}],
                    }
                ],
                "runner_results": [{"run_id": "r1", "status": "completed"}],
            },
        }

        with patch.object(app, "_assistant") as assistant:
            app._handle_task(result)

        assistant.assert_called_once()
        self.assertIn("Execution: [green]completed[/green]", assistant.call_args.args[0])
        self.assertIn("step write: completed", assistant.call_args.args[0])

    def test_task_handler_shows_repair_summary_for_repaired_result(self):
        app = OneCodeApp(model="test-model")
        result = {
            "status": "completed",
            "run_id": "repair-run",
            "reason": None,
            "completed_count": 1,
            "skipped_count": 0,
            "failed_count": 0,
            "repaired": True,
            "repair_attempt_count": 1,
            "initial_status": "halted",
            "initial_reason": "patch_compile_error",
        }

        with patch.object(app, "_assistant") as assistant:
            app._handle_task(result)

        self.assertIn("repair: attempts=1 initial=halted | patch_compile_error", assistant.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
