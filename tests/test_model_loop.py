import json
import sys
import tempfile
import unittest


from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.run_inspection import apply_verifier_evidence, inspect_run
from onecode.kernel.model_loop import run_model_task as _run_model_task
from onecode.kernel.model_loop import execution_plan_from_model_plan
from onecode.kernel.model_provider import (
    DEFAULT_DOMESTIC_PROVIDER_CONFIGS,
    MissingModelApiKey,
    ModelExecutionStep,
    ModelPlan,
    ModelPlanAsset,
    ModelPlanPatch,
    ModelProviderTimeout,
    ModelToolCall,
    OpenAIChatCompletionsProvider,
    OpenAIResponsesProvider,
    parse_response_plan,
    validate_model_plan,
    api_key_from_env,
    build_provider_config,
    normalize_chat_endpoint,
)
from onecode.kernel.verifier import VerifierSpec, run_verifier
from onecode.kernel.safe_agent_router import SafeAgentRoute
from tests.sandbox_test_harness import install_sandbox_docker_stub



def run_model_task_wrapper(*args, **kwargs):
    return _run_model_task(*args, **kwargs)

class FakeModelProvider:
    def __init__(self, plan: ModelPlan) -> None:
        self.plan = plan
        self.calls: list[dict] = []

    def create_plan(self, task: str, *, model: str, http_timeout_seconds: float) -> ModelPlan:
        self.calls.append(
            {
                "task": task,
                "model": model,
                "http_timeout_seconds": http_timeout_seconds,
            }
        )
        return self.plan


class SequenceModelProvider:
    def __init__(self, plans: list[ModelPlan]) -> None:
        self.plans = list(plans)
        self.calls: list[dict] = []

    def create_plan(self, task: str, *, model: str, http_timeout_seconds: float) -> ModelPlan:
        self.calls.append(
            {
                "task": task,
                "model": model,
                "http_timeout_seconds": http_timeout_seconds,
            }
        )
        return self.plans.pop(0)


class ContextCapturingProvider:
    def __init__(self, plan: ModelPlan) -> None:
        self.plan = plan
        self.planning_context = None

    def create_plan(self, task: str, *, model: str, http_timeout_seconds: float, planning_context: dict) -> ModelPlan:
        self.planning_context = planning_context
        return self.plan


class TimeoutProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        raise ModelProviderTimeout("model request timed out")


class InvalidPlanProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        raise ValueError("model response was not valid JSON")


class TruncatedPlanProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        raise ValueError("model response was truncated")


class NarrowThenWriteProvider:
    def __init__(self) -> None:
        self.tasks: list[str] = []

    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        from onecode.kernel.model_provider import validate_model_plan

        self.tasks.append(task)
        if len(self.tasks) == 1:
            raise ValueError("model response was truncated")
        return validate_model_plan(
            {"task": "write one file", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
        )


class EmptyAssetProvider:
    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        from onecode.kernel.model_provider import validate_model_plan

        return validate_model_plan({"task": task, "assets": [{"path": "src/book.py", "content": ""}]})


class SequenceThenTimeoutProvider:
    def __init__(self, first_plan):
        self.first_plan = first_plan
        self.call_count = 0

    def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
        self.call_count += 1
        if self.call_count == 1:
            return self.first_plan
        raise ModelProviderTimeout("model request timed out")


class ModelLoopTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        install_sandbox_docker_stub(self)

    def test_model_timeout_writes_failed_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task_wrapper(
                "check project",
                workspace=Path(tmp),
                run_id="model-timeout",
                api_key="key",
                model="m",
                provider=TimeoutProvider(),
                task_mode="read_task",
                safe_agent_route=SafeAgentRoute(
                    "no_match", "no_matching_scenario", schema_version=2
                ),
            )

            events = [
                json.loads(line)
                for line in Path(result["trace_path"]).read_text().splitlines()
            ]
            model_events = [
                event["event_type"]
                for event in events
                if event["span_id"] == "model-call"
            ]

            self.assertEqual(
                (result["status"], result["reason"]),
                ("halted", "model_provider_timeout"),
            )
            self.assertEqual(model_events, ["model_call_started", "model_call_failed"])
            self.assertTrue(Path(result["ledger_path"]).is_file())
            self.assertTrue(Path(result["manifest_path"]).is_file())
            self.assertNotIn(
                "key", Path(result["ledger_path"]).read_text(encoding="utf-8")
            )

    def test_invalid_model_plan_writes_failed_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task_wrapper(
                "check project",
                workspace=Path(tmp),
                run_id="invalid-model-plan",
                api_key="key",
                model="m",
                provider=InvalidPlanProvider(),
            )
            events = [
                json.loads(line)
                for line in Path(result["trace_path"]).read_text().splitlines()
            ]
            terminal = [
                event
                for event in events
                if event["span_id"] == "model-call"
                and event["event_type"]
                in {"model_call_completed", "model_call_failed"}
            ]

            self.assertEqual(result["reason"], "invalid_model_plan")
            self.assertEqual(result["payload"]["detail"], "model response was not valid JSON")
            self.assertEqual(
                IchingKernel.classify_outcome("halted", "invalid_model_plan"),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
            )
            self.assertEqual(
                [event["event_type"] for event in terminal], ["model_call_failed"]
            )
            self.assertTrue(Path(result["ledger_path"]).is_file())
            self.assertTrue(Path(result["manifest_path"]).is_file())

    def test_empty_asset_content_halts_as_invalid_model_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task_wrapper(
                "write the bookstore",
                workspace=Path(tmp),
                run_id="empty-asset",
                api_key="key",
                model="m",
                provider=EmptyAssetProvider(),
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "invalid_model_plan")
            self.assertIn("content must be a non-empty string", result["payload"]["detail"])
            self.assertFalse((Path(tmp) / "src" / "book.py").exists())

    def test_truncated_model_plan_is_resource_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task_wrapper(
                "write a large module",
                workspace=Path(tmp),
                run_id="truncated-plan",
                api_key="key",
                model="m",
                provider=TruncatedPlanProvider(),
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(
                IchingKernel.classify_outcome("halted", result["reason"]),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
            )

    def test_truncated_plan_replans_one_file_when_repair_is_allowed(self):
        provider = NarrowThenWriteProvider()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "build the bookstore",
                workspace=workspace,
                run_id="narrow-replan",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=1,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(len(provider.tasks), 2)
            self.assertIn("exactly one", provider.tasks[1])

    def test_repair_budget_writes_one_file_per_attempt(self):
        class TwoFileProvider:
            def __init__(self) -> None:
                self.tasks: list[str] = []

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.tasks.append(task)
                if len(self.tasks) == 1:
                    raise ValueError("model response was truncated")
                name = "one.py" if len(self.tasks) == 2 else "two.py"
                return validate_model_plan(
                    {
                        "task": f"write {name}",
                        "assets": [{"path": f"src/{name}", "content": f"VALUE = {len(self.tasks)}\n"}],
                    }
                )

        provider = TwoFileProvider()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "build two modules",
                workspace=workspace,
                run_id="narrow-two",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["completed_count"], 2)
            self.assertEqual(result["requested_count"], 3)
            self.assertEqual(result["model_plan_asset_count"], 2)
            self.assertEqual(len(result["assets"]), 2)
            self.assertEqual(
                IchingKernel.classify_outcome(result["status"], result["reason"]),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
            )
            self.assertEqual(result["iching_transition_action"], "halt")
            self.assertEqual(result["delivery_status"], "blocked")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 2\n")
            self.assertEqual((workspace / "src" / "two.py").read_text(encoding="utf-8"), "VALUE = 3\n")
            self.assertEqual(len(provider.tasks), 3)
            self.assertIn("src/one.py", provider.tasks[2])
            ledger = json.loads((workspace / ".onecode" / "runs" / "narrow-two" / "ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["completed_count"], 2)
            self.assertEqual(ledger["reason"], "resource_budget_exceeded")

    def test_later_narrow_no_action_keeps_files_already_written(self):
        class StopAfterOneProvider:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 2:
                    return validate_model_plan(
                        {"task": "write one", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                    )
                return validate_model_plan({"task": "done", "no_action": {"reason": "already complete"}})

        provider = StopAfterOneProvider()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "build one module",
                workspace=workspace,
                run_id="narrow-stop",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["reason"], None)
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["requested_count"], 1)
            self.assertEqual(result["model_plan_asset_count"], 1)
            classified = IchingKernel.classify_outcome(result["status"], result["reason"])
            transition = IchingKernel.transition(classified)
            self.assertEqual(classified, IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN))
            self.assertEqual(result["iching_status_code"], transition.status_code)
            self.assertEqual(result["iching_transition_action"], transition.action)
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(provider.calls, 3)

    def test_later_narrow_plan_failure_keeps_written_files_and_halts(self):
        class FailAfterOneProvider:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 2:
                    return validate_model_plan(
                        {"task": "write one", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                    )
                raise ValueError("asset content must be a non-empty string")

        provider = FailAfterOneProvider()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "build one module",
                workspace=workspace,
                run_id="narrow-fail",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "invalid_model_plan")
            self.assertEqual(result["completed_count"], 1)
            self.assertTrue((workspace / "src" / "one.py").exists())
            self.assertEqual(
                IchingKernel.classify_outcome(result["status"], result["reason"]),
                IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
            )
            self.assertEqual(provider.calls, 3)

    def test_named_files_get_a_write_slot_plus_one_close(self):
        class FourFileProvider:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                names = ["src/workers.py", "src/jobs.py", "src/assign.py", "src/scheduler.py"]
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 6:
                    return validate_model_plan({"task": "done", "no_action": {"reason": "files are written"}})
                path = names[self.calls - 2]
                return validate_model_plan(
                    {"task": f"write {path}", "assets": [{"path": path, "content": f"VALUE = {self.calls}\n"}]}
                )

        provider = FourFileProvider()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "Build src/workers.py, src/jobs.py, src/assign.py, and src/scheduler.py.",
                workspace=workspace,
                run_id="named-four",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual(provider.calls, 6)
            self.assertTrue((workspace / "src" / "assign.py").exists())
            self.assertTrue((workspace / "src" / "scheduler.py").exists())

    def test_empty_task_string_retries_the_same_step(self):
        class EmptyTaskThenWrite:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("task must be a non-empty string")
                return validate_model_plan(
                    {"task": "write", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                )

        provider = EmptyTaskThenWrite()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "write src/one.py",
                workspace=workspace,
                run_id="retry-empty-task",
                api_key="key",
                model="m",
                provider=provider,
                execution_approval=lambda step: True,
            )
            self.assertEqual(provider.calls, 2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_finished_named_file_closes_into_the_check(self):
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import VerifierResult

        class WriteFareThenTest:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 2:
                    return validate_model_plan(
                        {"task": "fix fare", "assets": [{"path": "src/fares.py", "content": "VALUE = 1\n"}]}
                    )
                return validate_model_plan(
                    {"task": "rewrite test", "assets": [{"path": "tests/test_fares.py", "content": "CHANGED\n"}]}
                )

        passed = VerifierResult(
            id="python-unittest", status="passed", reason=None, failure_kind=None,
            exit_code=0, duration_ms=1, stdout_tail="OK", stderr_tail="",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        provider = WriteFareThenTest()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "tests").mkdir()
            (workspace / "src" / "fares.py").write_text("VALUE = 0\n", encoding="utf-8")
            original = "import unittest\n"
            (workspace / "tests" / "test_fares.py").write_text(original, encoding="utf-8")
            with patch("onecode.kernel.verifier.run_verifier", return_value=passed):
                result = run_model_task_wrapper(
                    "Fix only src/fares.py. Do not modify tests/test_fares.py.",
                    workspace=workspace,
                    run_id="fare-close",
                    api_key="key",
                    model="m",
                    provider=provider,
                    max_repair_attempts=2,
                    execution_approval=lambda step: True,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
            self.assertEqual(provider.calls, 2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual((workspace / "tests" / "test_fares.py").read_text(encoding="utf-8"), original)
            self.assertEqual((workspace / "src" / "fares.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(
                result["iching_status_code"],
                IchingKernel.transition(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN)).status_code,
            )

    def test_protected_test_in_the_same_plan_is_left_unchanged(self):
        class WritesBoth:
            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                return ModelPlan(
                    task="write",
                    assets=[
                        ModelPlanAsset(path="src/fares.py", content="VALUE = 1\n"),
                        ModelPlanAsset(path="tests/test_fares.py", content="CHANGED\n"),
                    ],
                )

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            original = "import unittest\n"
            (workspace / "tests" / "test_fares.py").write_text(original, encoding="utf-8")
            result = run_model_task_wrapper(
                "Fix only src/fares.py. Do not modify tests/test_fares.py.",
                workspace=workspace,
                run_id="fare-same-plan",
                api_key="key",
                model="m",
                provider=WritesBoth(),
                execution_approval=lambda step: True,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual((workspace / "src" / "fares.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual((workspace / "tests" / "test_fares.py").read_text(encoding="utf-8"), original)

    def test_unfinished_named_files_still_halt(self):
        class StopMidway:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 2:
                    return validate_model_plan(
                        {"task": "write one", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                    )
                raise ValueError("asset content must be a non-empty string")

        provider = StopMidway()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "Write src/one.py and src/two.py.",
                workspace=workspace,
                run_id="named-incomplete",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )
            self.assertEqual(provider.calls, 3)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "invalid_model_plan")
            self.assertTrue((workspace / "src" / "one.py").exists())
            self.assertFalse((workspace / "src" / "two.py").exists())

    def test_later_named_test_can_import_a_module_already_written(self):
        class WriteThenImport:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None, known_modules=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was truncated")
                if self.calls == 2:
                    return validate_model_plan(
                        {"task": "write cart", "assets": [{"path": "src/cart.py", "content": "class Cart:\n    pass\n"}]}
                    )
                return validate_model_plan(
                    {"task": "write checkout", "assets": [{"path": "src/checkout.py", "content": "from src.cart import Cart\n"}]},
                    known_modules=known_modules,
                )

        provider = WriteThenImport()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "Build src/cart.py and src/checkout.py.",
                workspace=workspace,
                run_id="import-existing",
                api_key="key",
                model="m",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )
            self.assertEqual(provider.calls, 3)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertIn("from src.cart import Cart", (workspace / "src" / "checkout.py").read_text(encoding="utf-8"))

    def test_invalid_json_retries_the_same_step_without_a_file_slot(self):
        class RetryThenWrite:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                from onecode.kernel.model_provider import validate_model_plan

                self.calls += 1
                if self.calls == 1:
                    raise ValueError("model response was not valid JSON")
                return validate_model_plan(
                    {"task": "write", "assets": [{"path": "src/one.py", "content": "VALUE = 1\n"}]}
                )

        provider = RetryThenWrite()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_model_task_wrapper(
                "write src/one.py",
                workspace=workspace,
                run_id="retry-json",
                api_key="key",
                model="m",
                provider=provider,
                execution_approval=lambda step: True,
            )
            self.assertEqual(provider.calls, 2)
            self.assertEqual(result["status"], "completed")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_second_invalid_json_halts_on_the_fire_boundary(self):
        class AlwaysInvalid:
            def __init__(self) -> None:
                self.calls = 0

            def create_plan(self, task, *, model, http_timeout_seconds, planning_context=None):
                self.calls += 1
                raise ValueError("model response was not valid JSON")

        provider = AlwaysInvalid()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task_wrapper(
                "write src/one.py",
                workspace=Path(tmp),
                run_id="retry-json-halt",
                api_key="key",
                model="m",
                provider=provider,
            )
        self.assertEqual(provider.calls, 2)
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "invalid_model_plan")
        self.assertEqual(result["iching_transition_action"], "halt")

    def test_completed_plan_halts_when_sandbox_unittest_fails(self):
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import VerifierResult

        plan = ModelPlan(
            task="write a test",
            assets=[ModelPlanAsset(path="tests/test_note.py", content="import unittest\nclass T(unittest.TestCase):\n def test_bad(self):\n  self.assertEqual(1, 0)\n")],
        )
        failed = VerifierResult(
            id="python-unittest",
            status="failed",
            reason="verifier_failed",
            failure_kind="command_failed",
            exit_code=1,
            duration_ms=1,
            stdout_tail="",
            stderr_tail="AssertionError",
            stdout_sha256="0" * 64,
            stderr_sha256="0" * 64,
            cwd=".",
            command=["python3", "-m", "unittest"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with patch("onecode.kernel.verifier.run_verifier", return_value=failed):
                result = run_model_task_wrapper(
                    "write tests/test_note.py",
                    workspace=workspace,
                    run_id="verify-fail",
                    api_key="key",
                    model="m",
                    provider=FakeModelProvider(plan),
                    execution_approval=lambda step: True,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "verifier_failed")
        self.assertEqual(result["delivery_status"], "blocked")
        self.assertEqual(result["iching_status_code"], IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))

    def test_failed_sandbox_check_gets_one_patch_repair_then_passes(self):
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import VerifierResult

        write_plan = ModelPlan(
            task="write",
            assets=[ModelPlanAsset(path="src/one.py", content="VALUE = 0\n")],
        )
        patch_plan = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="src/one.py", search_block="VALUE = 0\n", replace_block="VALUE = 1\n")],
        )
        failed = VerifierResult(
            id="python-unittest", status="failed", reason="verifier_failed", failure_kind="command_failed",
            exit_code=1, duration_ms=1, stdout_tail="", stderr_tail="AssertionError: 0 != 1",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        passed = VerifierResult(
            id="python-unittest", status="passed", reason=None, failure_kind=None,
            exit_code=0, duration_ms=1, stdout_tail="OK", stderr_tail="",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_one.py").write_text("import unittest\n", encoding="utf-8")
            with patch("onecode.kernel.verifier.run_verifier", side_effect=[failed, passed]):
                result = run_model_task_wrapper(
                    "fix src/one.py",
                    workspace=workspace,
                    run_id="repair-after-check",
                    api_key="key",
                    model="m",
                    provider=SequenceModelProvider([write_plan, patch_plan]),
                    execution_approval=lambda step: True,
                    max_repair_attempts=1,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(result["iching_status_code"], IchingKernel.transition(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN)).status_code)

    def test_patch_repair_after_verifier_failure_supports_multiple_attempts(self):
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import VerifierResult

        write_plan = ModelPlan(
            task="write",
            assets=[ModelPlanAsset(path="src/one.py", content="VALUE = 0\n")],
        )
        patch_plan_1 = ModelPlan(
            task="repair-1",
            patches=[ModelPlanPatch(path="src/one.py", search_block="VALUE = 0\n", replace_block="VALUE = 0.5\n")],
        )
        patch_plan_2 = ModelPlan(
            task="repair-2",
            patches=[ModelPlanPatch(path="src/one.py", search_block="VALUE = 0.5\n", replace_block="VALUE = 1\n")],
        )
        failed1 = VerifierResult(
            id="python-unittest", status="failed", reason="verifier_failed", failure_kind="command_failed",
            exit_code=1, duration_ms=1, stdout_tail="", stderr_tail="AssertionError: 0 != 1",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        failed2 = VerifierResult(
            id="python-unittest", status="failed", reason="verifier_failed", failure_kind="command_failed",
            exit_code=1, duration_ms=1, stdout_tail="", stderr_tail="AssertionError: 0.5 != 1",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        passed = VerifierResult(
            id="python-unittest", status="passed", reason=None, failure_kind=None,
            exit_code=0, duration_ms=1, stdout_tail="OK", stderr_tail="",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_one.py").write_text("import unittest\n", encoding="utf-8")
            with patch("onecode.kernel.verifier.run_verifier", side_effect=[failed1, failed2, passed]):
                result = run_model_task_wrapper(
                    "fix src/one.py",
                    workspace=workspace,
                    run_id="repair-multi-attempt",
                    api_key="key",
                    model="m",
                    provider=SequenceModelProvider([write_plan, patch_plan_1, patch_plan_2]),
                    execution_approval=lambda step: True,
                    max_repair_attempts=2,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual((workspace / "src" / "one.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(result["repair_attempt_count"], 2)

    def test_patch_repair_must_not_change_tests(self):
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import VerifierResult

        write_plan = ModelPlan(
            task="write",
            assets=[ModelPlanAsset(path="src/one.py", content="VALUE = 0\n")],
        )
        bad_patch = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="tests/test_one.py", search_block="import unittest\n", replace_block="import unittest\n# changed\n")],
        )
        failed = VerifierResult(
            id="python-unittest", status="failed", reason="verifier_failed", failure_kind="command_failed",
            exit_code=1, duration_ms=1, stdout_tail="", stderr_tail="AssertionError",
            stdout_sha256="0" * 64, stderr_sha256="0" * 64, cwd=".", command=["python3", "-m", "unittest"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            original = "import unittest\n"
            (workspace / "tests" / "test_one.py").write_text(original, encoding="utf-8")
            with patch("onecode.kernel.verifier.run_verifier", return_value=failed):
                result = run_model_task_wrapper(
                    "fix src/one.py",
                    workspace=workspace,
                    run_id="repair-keeps-tests",
                    api_key="key",
                    model="m",
                    provider=SequenceModelProvider([write_plan, bad_patch]),
                    execution_approval=lambda step: True,
                    max_repair_attempts=1,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
            self.assertEqual(result["reason"], "repair_plan_must_use_patches_only")
            self.assertEqual((workspace / "tests" / "test_one.py").read_text(encoding="utf-8"), original)
            self.assertEqual(result["iching_transition_action"], "halt")

    def test_repair_prompt_includes_the_existing_source(self):
        from onecode.kernel.model_loop import repair_prompt

        failed = {
            "status": "halted",
            "reason": "verifier_failed",
            "execution_trace": {"runner_results": [{"payload": {"path": "src/meters.py"}}]},
            "workspace_files": {"src/meters.py": "def bill_cents(kwh):\n    return kwh * 10\n"},
        }
        text = repair_prompt("fix src/meters.py", failed)
        self.assertIn("def bill_cents(kwh):", text)
        self.assertIn("return kwh * 10", text)
        self.assertIn("patches only", text)
        self.assertIn("Do not patch any path under tests/", text)

    def test_repair_prompt_omits_test_paths(self):
        from onecode.kernel.model_loop import repair_prompt

        failed = {
            "status": "halted",
            "reason": "verifier_failed",
            "execution_trace": {
                "runner_results": [
                    {"status": "failed", "reason": "verifier_failed", "payload": {"path": "tests/test_fares.py"}},
                    {"status": "completed", "reason": None, "payload": {"path": "src/fares.py"}},
                ]
            },
        }
        text = repair_prompt("fix src/fares.py", failed)
        self.assertIn("src/fares.py", text)
        self.assertNotIn("tests/test_fares.py", text)

    def test_resumable_gateway_status_is_a_checkpoint(self):
        from onecode.kernel.model_provider import ModelProviderError, ModelProviderTimeout, resumable_model_status

        self.assertTrue(resumable_model_status(429))
        self.assertTrue(resumable_model_status(502))
        self.assertFalse(resumable_model_status(401))
        resumed = IchingKernel.transition(IchingKernel.classify_outcome("halted", "model_provider_timeout"))
        refused = IchingKernel.transition(IchingKernel.classify_outcome("halted", "model_provider_error"))
        self.assertEqual(resumed.action, "checkpoint")
        self.assertEqual(refused.action, "halt")
        self.assertTrue(issubclass(ModelProviderTimeout, ModelProviderError))

    def test_repair_timeout_has_its_own_failed_terminal_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first_plan = ModelPlan(
                task="build broken module",
                execution_steps=[
                    ModelExecutionStep(
                        id="write",
                        description="write invalid python",
                        tool_calls=[
                            ModelToolCall(
                                tool_name="write_text",
                                params={
                                    "path": "src/generated.py",
                                    "content": "def status():\n    return (\n",
                                },
                            )
                        ],
                    ),
                    ModelExecutionStep(
                        id="patch",
                        description="compile-gated patch should fail",
                        depends_on=["write"],
                        tool_calls=[
                            ModelToolCall(
                                tool_name="patch_text",
                                params={
                                    "path": "src/generated.py",
                                    "search_block": "return (",
                                    "replace_block": "return [",
                                },
                            )
                        ],
                    ),
                ],
            )
            result = run_model_task_wrapper(
                "build module with repair",
                workspace=workspace,
                run_id="repair-timeout",
                model="test-model",
                api_key="test-key",
                provider=SequenceThenTimeoutProvider(first_plan),
                max_repair_attempts=1,
                execution_approval=lambda step: True,
            )
            events = [
                json.loads(line)
                for line in Path(result["trace_path"]).read_text().splitlines()
            ]
            by_span = {
                span: [
                    event["event_type"]
                    for event in events
                    if event["span_id"] == span
                ]
                for span in ("model-call", "model-repair-1")
            }

            self.assertEqual(
                by_span["model-call"],
                ["model_call_started", "model_call_completed"],
            )
            self.assertEqual(
                by_span["model-repair-1"],
                ["model_call_started", "model_call_failed"],
            )

    def test_model_task_passes_verified_route_to_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "README.md").write_text("project\n", encoding="utf-8")
            provider = ContextCapturingProvider(
                ModelPlan(
                    task="check status",
                    execution_steps=[
                        ModelExecutionStep(
                            id="status",
                            description="read project readme",
                            tool_calls=[ModelToolCall(tool_name="read_text", params={"path": "README.md"})],
                        )
                    ],
                )
            )
            route = SafeAgentRoute(
                status="ok",
                reason=None,
                schema_version=2,
                selected_skills=("code-test-regression",),
            )

            result = run_model_task_wrapper(
                "检查项目",
                workspace=Path(tmp),
                api_key="key",
                provider=provider,
                task_mode="read_task",
                safe_agent_route=route,
                provider_kind="chat",
            )

        self.assertEqual(provider.planning_context["safe_agent"]["schema_version"], 2)
        self.assertEqual(provider.planning_context["task_mode"], "read_task")
        self.assertEqual(result["status"], "completed")

    def test_invalid_safe_agent_route_is_persisted_without_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = ContextCapturingProvider(
                ModelPlan(task="unused", no_action_reason="must not be called")
            )

            result = run_model_task_wrapper(
                "检查项目",
                workspace=Path(tmp),
                api_key="key",
                provider=provider,
                task_mode="read_task",
                safe_agent_route=SafeAgentRoute("invalid", "registry_verification_failed", schema_version=2),
                provider_kind="chat",
            )

            trace_path = Path(result["trace_path"])
            events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "safe_agent_router_invalid")
        self.assertIsNotNone(result["run_id"])
        self.assertEqual(events[0]["event_type"], "safe_agent_route_rejected")
        self.assertEqual(events[0]["payload"]["reason"], "registry_verification_failed")
        self.assertIsNone(provider.planning_context)

    def test_no_action_plan_is_not_reported_as_successful_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = ContextCapturingProvider(
                ModelPlan(task="explain", no_action_reason="no workspace action")
            )

            result = run_model_task_wrapper(
                "解释一下",
                workspace=Path(tmp),
                api_key="key",
                provider=provider,
                task_mode="read_task",
                safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
                provider_kind="chat",
            )

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "no_actionable_plan")
        self.assertNotEqual(result.get("intent_type"), "noop")

    def test_no_action_plan_stays_no_action_when_execution_approval_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = ContextCapturingProvider(
                ModelPlan(task="explain", no_action_reason="no workspace action")
            )

            result = run_model_task_wrapper(
                "解释一下",
                workspace=Path(tmp),
                api_key="key",
                provider=provider,
                task_mode="read_task",
                safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
                provider_kind="chat",
                execution_approval=lambda step: True,
            )

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "no_actionable_plan")
        self.assertEqual(result["detail"], "no workspace action")
        self.assertEqual(result["intent_type"], "no_action")

    def test_guarded_model_plan_is_persisted_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = ContextCapturingProvider(
                ModelPlan(
                    task="write result",
                    assets=[ModelPlanAsset(path="docs/result.md", content="done\n")],
                    execution_steps=[
                        ModelExecutionStep(
                            id="write",
                            description="write result",
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="write_text",
                                    params={"path": "docs/result.md", "content": "done\n"},
                                )
                            ],
                        )
                    ],
                )
            )

            result = run_model_task_wrapper(
                "修改 docs/result.md",
                workspace=workspace,
                api_key="key",
                provider=provider,
                provider_kind="chat",
                task_mode="change_task",
                safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
                require_explicit_approval=True,
            )

            self.assertEqual(result["reason"], "approval_required")
            self.assertRegex(result["plan_id"], r"^[a-f0-9]{32}$")
            self.assertTrue((workspace / ".onecode" / "pending-plans" / f"{result['plan_id']}.json").exists())
            self.assertFalse((workspace / "docs" / "result.md").exists())
            self.assertEqual(result["plan_summary"]["actions"][0]["tool"], "write_text")
            self.assertEqual(result["plan_summary"]["actions"][0]["path"], "docs/result.md")
            self.assertEqual(result["plan_summary"]["actions"][0]["content_bytes"], 5)
            self.assertEqual(len(result["plan_summary"]["actions"]), 1)

    def test_approval_summary_includes_diff_without_writing(self):
        from onecode.web.api import format_run_result

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "docs" / "result.md"
            target.parent.mkdir()
            target.write_text("old\n", encoding="utf-8")
            provider = ContextCapturingProvider(
                ModelPlan(
                    task="update result",
                    execution_steps=[
                        ModelExecutionStep(
                            id="write",
                            description="write notes",
                            tool_calls=[
                                ModelToolCall(tool_name="write_text", params={"path": "notes.md", "content": "hello\n"})
                            ],
                        ),
                        ModelExecutionStep(
                            id="patch",
                            description="patch result",
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="patch_text",
                                    params={"path": "docs/result.md", "search_block": "old\n", "replace_block": "new\n"},
                                )
                            ],
                        ),
                    ],
                )
            )

            result = run_model_task_wrapper(
                "修改 docs/result.md",
                workspace=workspace,
                api_key="key",
                provider=provider,
                provider_kind="chat",
                task_mode="change_task",
                safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
                require_explicit_approval=True,
            )
            actions = {item["tool"]: item for item in result["plan_summary"]["actions"]}
            notes_exist = (workspace / "notes.md").exists()
            original = target.read_text(encoding="utf-8")

        self.assertIn("+hello", actions["write_text"]["diff"])
        self.assertIn("-old", actions["patch_text"]["diff"])
        self.assertIn("+new", actions["patch_text"]["diff"])
        self.assertFalse(notes_exist)
        self.assertEqual(original, "old\n")
        self.assertIn("+hello", format_run_result(result, "approval_required"))

    def test_guarded_command_approval_summary_displays_exact_argv(self):
        from onecode.web.api import format_run_result

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = ContextCapturingProvider(
                ModelPlan(
                    task="run tests",
                    execution_steps=[
                        ModelExecutionStep(
                            id="tests",
                            description="run focused tests",
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="run_command",
                                    params={"argv": ["python", "-m", "unittest", "tests.test_web_api"]},
                                )
                            ],
                        )
                    ],
                )
            )

            result = run_model_task_wrapper(
                "运行测试",
                workspace=workspace,
                api_key="key",
                provider=provider,
                provider_kind="chat",
                task_mode="change_task",
                safe_agent_route=SafeAgentRoute("no_match", "no_matching_scenario", schema_version=2),
                require_explicit_approval=True,
            )

        self.assertEqual(
            result["plan_summary"]["actions"][0]["argv"],
            ["python", "-m", "unittest", "tests.test_web_api"],
        )
        approval_message = format_run_result(result, "approval_required")
        self.assertIn('"argv"', approval_message)
        self.assertIn('"tests.test_web_api"', approval_message)
    def test_domestic_provider_configs_use_openai_compatible_chat_endpoints(self):
        expected = {
            "qwen": (
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "DASHSCOPE_API_KEY",
                "qwen-plus",
            ),
            "deepseek": (
                "https://api.deepseek.com/chat/completions",
                "DEEPSEEK_API_KEY",
                "deepseek-v4-flash",
            ),
            "kimi": (
                "https://api.moonshot.ai/v1/chat/completions",
                "MOONSHOT_API_KEY",
                "kimi-k2",
            ),
            "zhipu": (
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "ZHIPUAI_API_KEY",
                "glm-4.5",
            ),
        }

        for provider, (endpoint, env_key, model) in expected.items():
            with self.subTest(provider=provider):
                config = build_provider_config(provider, endpoint=None, model=None)
                self.assertEqual(config.endpoint, endpoint)
                self.assertEqual(config.env_key, env_key)
                self.assertEqual(config.model, model)
                self.assertIn(provider, DEFAULT_DOMESTIC_PROVIDER_CONFIGS)

    def test_domestic_provider_aliases_share_same_config(self):
        self.assertEqual(build_provider_config("dashscope", None, None), build_provider_config("qwen", None, None))
        self.assertEqual(build_provider_config("moonshot", None, None), build_provider_config("kimi", None, None))
        self.assertEqual(build_provider_config("glm", None, None), build_provider_config("zhipu", None, None))

    def test_api_key_from_env_uses_provider_specific_keys_before_openai_key(self):
        env = {
            "OPENAI_API_KEY": "openai-key",
            "DASHSCOPE_API_KEY": "qwen-key",
            "DEEPSEEK_API_KEY": "deepseek-key",
        }

        self.assertEqual(api_key_from_env(env, provider_kind="qwen"), "qwen-key")
        self.assertEqual(api_key_from_env(env, provider_kind="deepseek"), "deepseek-key")
        self.assertEqual(api_key_from_env(env, provider_kind="chat"), "openai-key")

    def test_normalize_chat_endpoint_accepts_base_url_or_full_chat_url(self):
        self.assertEqual(
            normalize_chat_endpoint("https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        )
        self.assertEqual(
            normalize_chat_endpoint("https://api.moonshot.ai/v1/chat/completions"),
            "https://api.moonshot.ai/v1/chat/completions",
        )

    def test_validate_model_plan_rejects_empty_assets(self):
        with self.assertRaisesRegex(ValueError, "plan must include at least one asset, patch, or execution step"):
            validate_model_plan({"task": "empty", "assets": []})

    def test_validate_model_plan_accepts_patch_only_plan(self):
        plan = validate_model_plan(
            {
                "task": "patch project",
                "patches": [
                    {
                        "path": "src/generated.py",
                        "search_block": "return False",
                        "replace_block": "return True",
                    }
                ],
            }
        )

        self.assertEqual(plan.assets, [])
        self.assertEqual(
            plan.patches,
            [
                ModelPlanPatch(
                    path="src/generated.py",
                    search_block="return False",
                    replace_block="return True",
                )
            ],
        )

    def test_validate_model_plan_accepts_kernel_owned_execution_plan(self):
        plan = validate_model_plan(
            {
                "task": "execute project",
                "execution_plan": {
                    "steps": [
                        {
                            "id": "write",
                            "description": "create file",
                            "tool_calls": [
                                {
                                    "tool_name": "write_text",
                                    "params": {"path": "src/generated.py", "content": "VALUE = 1\n"},
                                }
                            ],
                        },
                        {
                            "id": "patch",
                            "description": "patch file",
                            "depends_on": ["write"],
                            "tool_calls": [
                                {
                                    "tool_name": "patch_text",
                                    "params": {
                                        "path": "src/generated.py",
                                        "search_block": "VALUE = 1",
                                        "replace_block": "VALUE = 2",
                                    },
                                }
                            ],
                        },
                    ]
                },
            }
        )

        self.assertEqual(plan.assets, [])
        self.assertEqual(plan.patches, [])
        self.assertEqual(
            plan.execution_steps,
            [
                ModelExecutionStep(
                    id="write",
                    description="create file",
                    tool_calls=[
                        ModelToolCall(
                            tool_name="write_text",
                            params={"path": "src/generated.py", "content": "VALUE = 1\n"},
                        )
                    ],
                ),
                ModelExecutionStep(
                    id="patch",
                    description="patch file",
                    depends_on=["write"],
                    tool_calls=[
                        ModelToolCall(
                            tool_name="patch_text",
                            params={
                                "path": "src/generated.py",
                                "search_block": "VALUE = 1",
                                "replace_block": "VALUE = 2",
                            },
                        )
                    ],
                ),
            ],
        )

    def test_run_model_task_requires_api_key_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with (
                patch.dict("os.environ", {}, clear=True),
                self.assertRaises(MissingModelApiKey),
            ):
                run_model_task_wrapper("build nothing", workspace=workspace, run_id="missing-key")

            self.assertFalse((workspace / ".onecode").exists())

    def test_run_model_task_halts_immediately_when_ledger_mismatches_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with patch("onecode.kernel.run_inspection.ledger_matches_workspace", return_value="preset_test_hash_mismatch"):
                result = run_model_task_wrapper("do something", workspace=workspace, run_id="halt-mismatch", api_key="sk-test")
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "preset_test_hash_mismatch")

    def test_run_model_task_rejects_boolean_numeric_limits_before_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = FakeModelProvider(
                ModelPlan(
                    task="build generated project",
                    assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                )
            )

            with self.assertRaisesRegex(ValueError, "http_timeout_seconds must be greater than zero"):
                run_model_task_wrapper(
                    "build project",
                    workspace=workspace,
                    run_id="model-bool-timeout",
                    api_key="test-key",
                    provider=provider,
                    http_timeout_seconds=True,
                )
            with self.assertRaisesRegex(ValueError, "max_repair_attempts must be a non-negative integer"):
                run_model_task_wrapper(
                    "build project",
                    workspace=workspace,
                    run_id="model-bool-repair",
                    api_key="test-key",
                    provider=provider,
                    max_repair_attempts=True,
                )

            self.assertEqual(provider.calls, [])
            self.assertFalse((workspace / ".onecode").exists())

    def test_execution_approval_callback_completes_asset_write_by_default(self):
        plan = ModelPlan(
            task="build generated project",
            assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            approved = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="approved-asset-write",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(plan),
                execution_approval=lambda step: True,
            )
            self.assertEqual(approved["status"], "completed")
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "VALUE = 1\n")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            halted = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="unapproved-asset-write",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(plan),
            )
            self.assertEqual(halted["status"], "halted")
            self.assertEqual(halted["reason"], "approval_required")
            self.assertFalse((workspace / "src" / "generated.py").exists())

    def test_rejecting_execution_approval_does_not_write_asset_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            rejected = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="rejected-asset-write",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(
                    ModelPlan(
                        task="build generated project",
                        assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                    )
                ),
                execution_approval=lambda step: False,
            )
            target = workspace / "src" / "generated.py"
            self.assertFalse(target.exists())
            self.assertEqual(rejected["status"], "halted")
            self.assertEqual(rejected["reason"], "approval_rejected")

    def test_rejecting_execution_approval_does_not_change_patch_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "generated.py"
            target.parent.mkdir()
            original = "def status():\n    return False\n"
            target.write_text(original, encoding="utf-8")
            rejected = run_model_task_wrapper(
                "patch project",
                workspace=workspace,
                run_id="rejected-patch",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(
                    ModelPlan(
                        task="patch generated project",
                        patches=[
                            ModelPlanPatch(
                                path="src/generated.py",
                                search_block="return False",
                                replace_block="return True",
                            )
                        ],
                    )
                ),
                execution_approval=lambda step: False,
            )
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(rejected["status"], "halted")
            self.assertEqual(rejected["reason"], "approval_rejected")

    def test_rejecting_second_asset_or_patch_step_writes_nothing(self):
        def approve_unless_second(step):
            return step.tool_calls[0].params["path"] != "src/second.py"

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            rejected = run_model_task_wrapper(
                "build two files",
                workspace=workspace,
                run_id="reject-second-asset",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(
                    ModelPlan(
                        task="write two files",
                        assets=[
                            ModelPlanAsset(path="src/first.py", content="FIRST = 1\n"),
                            ModelPlanAsset(path="src/second.py", content="SECOND = 1\n"),
                        ],
                    )
                ),
                execution_approval=approve_unless_second,
            )
            self.assertFalse((workspace / "src" / "first.py").exists())
            self.assertFalse((workspace / "src" / "second.py").exists())
            self.assertEqual(rejected["status"], "halted")
            self.assertEqual(rejected["reason"], "approval_rejected")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "existing.py"
            target.parent.mkdir()
            original = "VALUE = 0\n"
            target.write_text(original, encoding="utf-8")
            rejected = run_model_task_wrapper(
                "write then patch",
                workspace=workspace,
                run_id="reject-second-patch",
                model="test-model",
                api_key="test-key",
                provider=FakeModelProvider(
                    ModelPlan(
                        task="write and patch",
                        assets=[ModelPlanAsset(path="src/first.py", content="FIRST = 1\n")],
                        patches=[
                            ModelPlanPatch(
                                path="src/existing.py",
                                search_block="VALUE = 0",
                                replace_block="VALUE = 1",
                            )
                        ],
                    )
                ),
                execution_approval=lambda step: step.tool_calls[0].params["path"] != "src/existing.py",
            )
            self.assertFalse((workspace / "src" / "first.py").exists())
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(rejected["status"], "halted")
            self.assertEqual(rejected["reason"], "approval_rejected")

    def test_run_model_task_executes_mock_plan_through_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = FakeModelProvider(
                ModelPlan(
                    task="build generated project",
                    assets=[
                        ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n"),
                        ModelPlanAsset(path="tests/test_generated.py", content="def test_generated():\n    assert True\n"),
                    ],
                )
            )

            result = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="model-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 2)
            self.assertEqual(result["completed_count"], 2)
            self.assertEqual(result["model_provider"], "openai")
            self.assertEqual(result["model"], "test-model")
            self.assertEqual(result["model_plan_asset_count"], 2)
            self.assertEqual(provider.calls, [{"task": "build project", "model": "test-model", "http_timeout_seconds": 60}])
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_run_model_task_records_model_call_trace_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = FakeModelProvider(
                ModelPlan(
                    task="build generated project",
                    assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                )
            )

            result = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="model-trace-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
            )
            trace_path = Path(result["trace_path"])
            events = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
            ]

            self.assertIn("model_call_started", [event["event_type"] for event in events])
            self.assertIn("model_call_completed", [event["event_type"] for event in events])
            self.assertTrue(
                any(
                    event["event_type"] == "model_call_completed"
                    and event["payload"]["asset_count"] == 1
                    and event["payload"]["model"] == "test-model"
                    for event in events
                )
            )

    def test_model_api_key_never_persists_to_run_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            secret = "sk-test-secret-should-not-leak"
            provider = FakeModelProvider(
                ModelPlan(
                    task="build generated project",
                    assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                )
            )

            result = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="secret-run",
                model="test-model",
                api_key=secret,
                provider=provider,
                execution_approval=lambda step: True,
            )

            evidence_root = Path(result["ledger_path"]).parent
            evidence_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in [
                    Path(result["ledger_path"]),
                    Path(result["manifest_path"]),
                    *sorted((evidence_root / "checkpoints").glob("*.json")),
                ]
            )
            self.assertNotIn(secret, evidence_text)
            self.assertNotIn("Authorization", evidence_text)
            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            self.assertEqual(ledger["model"], "test-model")
            self.assertEqual(ledger["model_provider"], "openai")

    def test_run_model_task_executes_mock_patch_plan_through_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "generated.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")
            provider = FakeModelProvider(
                ModelPlan(
                    task="patch generated project",
                    patches=[
                        ModelPlanPatch(
                            path="src/generated.py",
                            search_block="return False",
                            replace_block="return True",
                        )
                    ],
                )
            )

            result = run_model_task_wrapper(
                "patch project",
                workspace=workspace,
                run_id="model-patch-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 1)
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["model_plan_asset_count"], 0)
            self.assertEqual(result["model_plan_patch_count"], 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_model_plan_can_be_promoted_to_execution_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ModelPlan(
                task="build and patch",
                assets=[ModelPlanAsset(path="src/generated.py", content="def status():\n    return False\n")],
                patches=[
                    ModelPlanPatch(
                        path="src/generated.py",
                        search_block="return False",
                        replace_block="return True",
                    )
                ],
            )

            execution_plan = execution_plan_from_model_plan(plan)
            trace = execute_plan(
                execution_plan,
                workspace=workspace,
                run_id="model-execution-plan",
                tool_registry=default_tool_registry(),
                approval_callback=lambda step: True,
            )

            self.assertTrue(trace.success)
            self.assertEqual([step.id for step in execution_plan.steps], ["asset-1", "patch-1"])
            self.assertEqual(execution_plan.steps[1].depends_on, ["asset-1"])
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_model_execution_plan_runs_through_execution_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = FakeModelProvider(
                ModelPlan(
                    task="kernel execution",
                    execution_steps=[
                        ModelExecutionStep(
                            id="write",
                            description="create file",
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="write_text",
                                    params={"path": "src/generated.py", "content": "VALUE = 1\n"},
                                )
                            ],
                        ),
                        ModelExecutionStep(
                            id="patch",
                            description="patch file",
                            depends_on=["write"],
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="patch_text",
                                    params={
                                        "path": "src/generated.py",
                                        "search_block": "VALUE = 1",
                                        "replace_block": "VALUE = 2",
                                    },
                                )
                            ],
                        ),
                    ],
                )
            )

            result = run_model_task_wrapper(
                "execute project",
                workspace=workspace,
                run_id="model-execution-plan-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["intent_type"], "execution_plan")
            self.assertEqual(result["model_plan_execution_step_count"], 2)
            self.assertEqual(result["execution_trace"]["step_results"][0]["status"], "completed")
            self.assertEqual(result["execution_trace"]["step_results"][1]["status"], "completed")
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "VALUE = 2\n")

    def test_model_execution_plan_writes_top_level_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = FakeModelProvider(
                ModelPlan(
                    task="kernel execution",
                    execution_steps=[
                        ModelExecutionStep(
                            id="write",
                            description="create file",
                            tool_calls=[
                                ModelToolCall(
                                    tool_name="write_text",
                                    params={"path": "src/generated.py", "content": "VALUE = 1\n"},
                                )
                            ],
                        )
                    ],
                )
            )

            result = run_model_task_wrapper(
                "execute project",
                workspace=workspace,
                run_id="model-execution-evidence",
                model="test-model",
                api_key="test-key",
                provider=provider,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["run_id"], "model-execution-evidence")
            self.assertIn("ledger_path", result)
            self.assertIn("manifest_path", result)
            self.assertTrue(Path(result["ledger_path"]).exists())
            self.assertTrue(Path(result["manifest_path"]).exists())
            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            self.assertEqual(ledger["intent_type"], "execution_plan")
            self.assertEqual(ledger["run_id"], "model-execution-evidence")

    def test_model_task_repairs_failed_execution_with_patch_only_followup(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = SequenceModelProvider(
                [
                    ModelPlan(
                        task="build broken module",
                        execution_steps=[
                            ModelExecutionStep(
                                id="write",
                                description="write invalid python",
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="write_text",
                                        params={"path": "src/generated.py", "content": "def status():\n    return (\n"},
                                    )
                                ],
                            ),
                            ModelExecutionStep(
                                id="patch",
                                description="compile-gated patch should fail",
                                depends_on=["write"],
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="patch_text",
                                        params={
                                            "path": "src/generated.py",
                                            "search_block": "return (",
                                            "replace_block": "return [",
                                        },
                                    )
                                ],
                            ),
                        ],
                    ),
                    ModelPlan(
                        task="repair broken module",
                        patches=[
                            ModelPlanPatch(
                                path="src/generated.py",
                                search_block="return (",
                                replace_block="return True",
                            )
                        ],
                    ),
                ]
            )

            result = run_model_task_wrapper(
                "build module with repair",
                workspace=workspace,
                run_id="repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=1,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["repaired"])
            self.assertEqual(result["repair_attempt_count"], 1)
            self.assertEqual(result["initial_status"], "halted")
            self.assertEqual(result["initial_reason"], "patch_compile_error")
            self.assertIn("patch_compile_error", provider.calls[1]["task"])
            self.assertIn("src/generated.py", provider.calls[1]["task"])
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_model_task_uses_multiple_repair_attempts_until_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = SequenceModelProvider(
                [
                    ModelPlan(
                        task="build broken module",
                        execution_steps=[
                            ModelExecutionStep(
                                id="write",
                                description="write invalid python",
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="write_text",
                                        params={"path": "src/generated.py", "content": "def status():\n    return (\n"},
                                    )
                                ],
                            ),
                            ModelExecutionStep(
                                id="patch",
                                description="compile-gated patch should fail",
                                depends_on=["write"],
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="patch_text",
                                        params={
                                            "path": "src/generated.py",
                                            "search_block": "return (",
                                            "replace_block": "return [",
                                        },
                                    )
                                ],
                            ),
                        ],
                    ),
                    ModelPlan(
                        task="first repair still invalid",
                        patches=[
                            ModelPlanPatch(
                                path="src/generated.py",
                                search_block="return (",
                                replace_block="return [",
                            )
                        ],
                    ),
                    ModelPlan(
                        task="second repair succeeds",
                        patches=[
                            ModelPlanPatch(
                                path="src/generated.py",
                                search_block="return (",
                                replace_block="return True",
                            )
                        ],
                    ),
                ]
            )

            result = run_model_task_wrapper(
                "build module with repeated repair",
                workspace=workspace,
                run_id="multi-repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=2,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["repaired"])
            self.assertEqual(result["repair_attempt_count"], 2)
            self.assertEqual(len(provider.calls), 3)
            self.assertIn("patch_compile_error", provider.calls[1]["task"])
            self.assertIn("patch_compile_error", provider.calls[2]["task"])
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_model_repair_rejects_followup_assets_and_execution_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            provider = SequenceModelProvider(
                [
                    ModelPlan(
                        task="broken",
                        execution_steps=[
                            ModelExecutionStep(
                                id="write",
                                description="write invalid python",
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="write_text",
                                        params={"path": "src/generated.py", "content": "def status():\n    return (\n"},
                                    )
                                ],
                            ),
                            ModelExecutionStep(
                                id="patch",
                                description="compile-gated patch should fail",
                                depends_on=["write"],
                                tool_calls=[
                                    ModelToolCall(
                                        tool_name="patch_text",
                                        params={
                                            "path": "src/generated.py",
                                            "search_block": "return (",
                                            "replace_block": "return [",
                                        },
                                    )
                                ],
                            ),
                        ],
                    ),
                    ModelPlan(
                        task="unsafe repair",
                        assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                    ),
                ]
            )

            result = run_model_task_wrapper(
                "build module with unsafe repair",
                workspace=workspace,
                run_id="unsafe-repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=1,
                execution_approval=lambda step: True,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "repair_plan_must_use_patches_only")
            self.assertEqual((workspace / "src" / "generated.py").read_text(encoding="utf-8"), "def status():\n    return (\n")

    def test_openai_provider_builds_strict_structured_output_payload(self):
        provider = OpenAIResponsesProvider("test-key")

        payload = provider.request_payload("build api project", model="test-model")

        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["schema"]["required"], ["task"])
        self.assertFalse(payload["text"]["format"]["schema"]["additionalProperties"])

    def test_parse_response_plan_reads_output_text_json(self):
        plan = parse_response_plan(
            {
                "output_text": (
                    '{"task":"response plan","assets":['
                    '{"path":"src/a.py","content":"A = 1\\n"}'
                    ']}'
                )
            }
        )

        self.assertEqual(plan.task, "response plan")
        self.assertEqual(plan.assets, [ModelPlanAsset(path="src/a.py", content="A = 1\n")])

    def test_chat_provider_builds_json_object_payload(self):
        provider = OpenAIChatCompletionsProvider("test-key")

        payload = provider.request_payload("build chat project", model="test-model")

        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("assets", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "build chat project"})

    def test_chat_provider_parses_choices_message_content(self):
        provider = OpenAIChatCompletionsProvider("test-key")

        plan = provider.parse_response(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"task":"chat plan","assets":['
                                '{"path":"src/chat.py","content":"VALUE = 1\\n"}'
                                ']}'
                            )
                        }
                    }
                ]
            }
        )

        self.assertEqual(plan.task, "chat plan")
        self.assertEqual(plan.assets, [ModelPlanAsset(path="src/chat.py", content="VALUE = 1\n")])

    def test_cli_run_model_delegates_to_kernel_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch(
                    "onecode.cli.run_model_task",
                    return_value={"status": "completed", "reason": None},
                ) as run_model_task_mock,
                patch("onecode.cli.IchingKernel.process_exit_code", return_value=0) as process_exit_code,
                patch("builtins.print") as printed,
            ):
                exit_code = main(
                    [
                        "run-model",
                        "build model project",
                        "--workspace",
                        tmp,
                        "--run-id",
                        "model-cli",
                        "--resume-from",
                        "old-run",
                        "--model",
                        "test-model",
                        "--api-key",
                        "test-key",
                        "--provider",
                        "chat",
                        "--endpoint",
                        "http://relay.test/v1/chat/completions",
                        "--http-timeout-seconds",
                        "12",
                    ]
                )

        self.assertEqual(exit_code, 0)
        printed_payload = json.loads(printed.call_args.args[0])
        self.assertEqual(printed_payload["shell_projection"]["status_label"], "completed")
        self.assertEqual(printed_payload["shell_projection"]["severity"], "ok")
        run_model_task_mock.assert_called_once()
        _, kwargs = run_model_task_mock.call_args
        self.assertEqual(kwargs["workspace"], Path(tmp))
        self.assertEqual(kwargs["run_id"], "model-cli")
        self.assertEqual(kwargs["resume_from_run_id"], "old-run")
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertEqual(kwargs["provider_kind"], "chat")
        self.assertEqual(kwargs["endpoint"], "http://relay.test/v1/chat/completions")
        self.assertEqual(kwargs["http_timeout_seconds"], 12)
        self.assertIsNone(kwargs["execution_approval"])
        process_exit_code.assert_called_once_with(status="completed", reason=None)

    def test_cli_run_model_approve_grants_execution_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "onecode.cli.run_model_task",
                return_value={"status": "completed", "reason": None},
            ) as run_model_task_mock, patch("onecode.cli.IchingKernel.process_exit_code", return_value=0), patch(
                "builtins.print"
            ):
                main(
                    [
                        "run-model",
                        "build model project",
                        "--workspace",
                        tmp,
                        "--api-key",
                        "test-key",
                        "--approve",
                    ]
                )

        approval = run_model_task_mock.call_args.kwargs["execution_approval"]
        self.assertIsNotNone(approval)
        self.assertTrue(approval(object()))

    def test_cli_run_model_blocks_delivery_when_selected_verifier_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_generated.py").write_text(
                "import unittest\n\n"
                "class GeneratedTests(unittest.TestCase):\n"
                "    def test_generated(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            policy_path = workspace / "verifiers.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                                "cwd": ".",
                                "timeout_ms": 5000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch(
                    "onecode.cli.run_model_task",
                    return_value={
                        "run_id": "model-verifier",
                        "status": "completed",
                        "reason": None,
                        "partial": False,
                        "requested_count": 0,
                        "completed_count": 0,
                        "skipped_count": 0,
                        "failed_count": 0,
                        "assets": [],
                    },
                ),
                patch("builtins.print") as printed,
            ):
                exit_code = main(
                    [
                        "run-model",
                        "build broken project",
                        "--workspace",
                        tmp,
                        "--run-id",
                        "model-verifier",
                        "--api-key",
                        "test-key",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )

        result = json.loads(printed.call_args.args[0])
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "verifier_failed")
        self.assertEqual(result["delivery_status"], "blocked")
        self.assertEqual(result["verifier_results"][0]["status"], "failed")
        self.assertIn("AssertionError", result["verifier_results"][0]["stderr_tail"])

    def test_model_verifier_failure_keeps_inspection_evidence_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_generated.py").write_text(
                "import unittest\n\n"
                "class GeneratedTests(unittest.TestCase):\n"
                "    def test_generated(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            provider = FakeModelProvider(
                ModelPlan(
                    task="build generated project",
                    assets=[ModelPlanAsset(path="src/generated.py", content="VALUE = 1\n")],
                )
            )
            result = run_model_task_wrapper(
                "build project",
                workspace=workspace,
                run_id="model-verifier-inspect",
                model="test-model",
                api_key="test-key",
                provider=provider,
                execution_approval=lambda step: True,
            )
            from onecode.kernel.sandbox import SandboxConfig
            verifier = run_verifier(
                workspace,
                VerifierSpec(
                    id="python-unittest",
                    command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    cwd=".",
                    timeout_ms=5000,
                ),
                sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none")
            )

            enhanced = apply_verifier_evidence(result, workspace, [verifier])
            exit_code, summary = inspect_run(workspace, "model-verifier-inspect")

        self.assertEqual(enhanced["status"], "halted")
        self.assertEqual(enhanced["reason"], "verifier_failed")
        halt = IchingKernel.transition(IchingKernel.classify_outcome("halted", "verifier_failed"))
        self.assertEqual(halt.status_code, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(enhanced["iching_status_code"], halt.status_code)
        self.assertEqual(enhanced["iching_transition_action"], "halt")
        self.assertEqual(enhanced["task_dispatch_decision"], "stop")
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["status"], "halted")
        self.assertEqual(summary["reason"], "verifier_failed")
        self.assertEqual(summary["delivery_status"], "blocked")
        self.assertEqual(summary["verifier_results"][0]["status"], "failed")

    def test_named_python_files_include_a_flat_package_and_skip_example_paths(self):
        from onecode.kernel.model_loop import named_python_files

        self.assertEqual(named_python_files("Fix archive_like/extract.py"), ["archive_like/extract.py"])
        self.assertEqual(named_python_files("像 `/foo/a.py` 这种路径"), [])
        self.assertEqual(named_python_files("edit src/app.py"), ["src/app.py"])

    def test_repair_source_includes_a_flat_package_when_src_is_absent(self):
        from onecode.kernel.model_loop import _src_files_for_repair

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            package = workspace / "archive_like"
            package.mkdir()
            (package / "extract.py").write_text("def extract_members():\n    return []\n", encoding="utf-8")
            files = _src_files_for_repair(workspace)
        self.assertIn("def extract_members", files["archive_like/extract.py"])

    def test_repair_prompt_includes_flat_package_source(self):
        from onecode.kernel.model_loop import _src_files_for_repair, repair_prompt

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            package = workspace / "archive_like"
            package.mkdir()
            (package / "extract.py").write_text("def extract_members():\n    return []\n", encoding="utf-8")
            prompt = repair_prompt("fix the archive", {"workspace_files": _src_files_for_repair(workspace)})
        self.assertIn("archive_like/extract.py", prompt)
        self.assertIn("def extract_members", prompt)


class ExecuteModelPlanApprovalTests(unittest.TestCase):
    def test_asset_plan_without_callback_does_not_write(self):
        from onecode.kernel.model_loop import execute_model_plan

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = ModelPlan(
                task="write mesh",
                assets=[ModelPlanAsset(path="src/mesh.py", content="VALUE = 1\n")],
            )
            result = execute_model_plan(
                plan,
                workspace=workspace,
                http_timeout_seconds=5,
                run_id="no-callback",
                resume_from_run_id=None,
                run_metadata={},
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "approval_required")
            self.assertFalse((workspace / "src" / "mesh.py").exists())

    def test_read_only_steps_still_apply_patches(self):
        from onecode.kernel.model_loop import execute_model_plan
        from onecode.kernel.model_provider import ModelExecutionStep, ModelToolCall

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "claims.py"
            target.parent.mkdir()
            target.write_text('def add():\n    return {"status": "recorded"}\n', encoding="utf-8")
            plan = ModelPlan(
                task="fix the return status",
                patches=[
                    ModelPlanPatch(
                        path="src/claims.py",
                        search_block='    return {"status": "recorded"}\n',
                        replace_block='    return {"status": "added"}\n',
                    )
                ],
                execution_steps=[
                    ModelExecutionStep(
                        id="look",
                        description="read the file",
                        tool_calls=[ModelToolCall(tool_name="read_text", params={"path": "src/claims.py"})],
                    )
                ],
            )
            result = execute_model_plan(
                plan,
                workspace=workspace,
                http_timeout_seconds=5,
                run_id="read-plus-patch",
                resume_from_run_id=None,
                run_metadata={},
                approval_callback=lambda step: True,
            )

            self.assertEqual(result["status"], "completed", result.get("reason"))

    def test_run_model_task_strict_vs_scoped_auto_mode(self):
        from onecode.kernel.model_loop import run_model_task

        plan = ModelPlan(
            task="write src/mesh.py",
            assets=[ModelPlanAsset(path="src/mesh.py", content="VALUE = 1\n")],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            strict_result = run_model_task(
                "write src/mesh.py",
                workspace=workspace,
                run_id="strict-plan",
                api_key="key",
                model="m",
                provider=SequenceModelProvider([plan]),
                require_explicit_approval=True,
                execution_approval=None,
                approval_mode="strict",
            )
            self.assertEqual(strict_result["status"], "halted")
            self.assertEqual(strict_result["reason"], "approval_required")

            auto_result = run_model_task(
                "write src/mesh.py",
                workspace=workspace,
                run_id="auto-plan",
                api_key="key",
                model="m",
                provider=SequenceModelProvider([plan]),
                require_explicit_approval=True,
                execution_approval=None,
                approval_mode="scoped_auto",
            )
            self.assertEqual(auto_result["status"], "completed")
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_data_contract_guidance_added_to_initial_asset_prompt(self):
        from onecode.kernel.model_loop import initial_asset_prompt

        task = "In pipeline.py, perform text hashing and sort outputs, filling missing values with 0."
        prompt = initial_asset_prompt(task, "pipeline.py")
        self.assertIn("hashlib", prompt)
        self.assertIn("deterministic", prompt)
        self.assertIn("missing values", prompt)

    def test_generate_missing_artifacts_runs_export_script(self):
        from onecode.kernel.model_loop import _generate_missing_artifacts

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            app = workspace / "app"
            app.mkdir()
            export_py = app / "export.py"
            export_py.write_text("from pathlib import Path\nPath('export.csv').write_text('id,val\\n1,2\\n', encoding='utf-8')\n", encoding="utf-8")
            task = "Run the invoice export and produce export.csv"
            _generate_missing_artifacts(task, workspace, ["app/export.py"])
            self.assertTrue((workspace / "export.csv").is_file())
            self.assertEqual((workspace / "export.csv").read_text(encoding="utf-8"), "id,val\n1,2\n")

    def test_generate_missing_artifacts_parameterized_probe(self):
        from onecode.kernel.model_loop import _generate_missing_artifacts

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            app = workspace / "app"
            app.mkdir()
            export_py = app / "export.py"
            # Script that requires positional argument or --output
            export_py.write_text(
                "import sys\nfrom pathlib import Path\n"
                "if len(sys.argv) > 1:\n"
                "    target = sys.argv[1].replace('--output=', '').replace('--out=', '')\n"
                "    Path(target).write_text('arg,ok\\n1,1\\n', encoding='utf-8')\n",
                encoding="utf-8",
            )
            task = "Export results to metrics.csv"
            _generate_missing_artifacts(task, workspace, ["app/export.py"])
            self.assertTrue((workspace / "metrics.csv").is_file())
            self.assertEqual((workspace / "metrics.csv").read_text(encoding="utf-8"), "arg,ok\n1,1\n")

    def test_data_contract_guidance_all_domains(self):
        from onecode.kernel.model_loop import data_contract_guidance

        domains = [
            ("data_quality-hard-label_conflicts", "label conflicts"),
            ("data_quality-hard-outlier_winsorize", "winsorization"),
            ("data_quality-hard-schema_drift", "schema drift"),
            ("data_quality-hard-time_leakage", "time leakage"),
            ("data_reporting-hard-support_sla", "support SLA"),
            ("feature_pipeline-hard-text_hashing", "hashlib"),
            ("feature_pipeline-hard-train_serve_parity", "train-serve parity"),
            ("feature_pipeline-hard-window_aggregates", "window aggregates"),
            ("model_evaluation-hard-calibration_bins", "calibration bins"),
        ]
        for task_name, expected_phrase in domains:
            guidance = data_contract_guidance(task_name)
            self.assertIn(expected_phrase, guidance, f"Failed for task {task_name}")

    def test_narrow_and_repair_prompt_include_data_contract_guidance(self):
        from onecode.kernel.model_loop import narrow_plan_prompt, repair_prompt

        task = "In pipeline.py, fix calibration_bins to calculate ECE correctly"
        narrow = narrow_plan_prompt(task, {"detail": "retry"})
        self.assertIn("calibration bins", narrow)

        repair = repair_prompt(task, {"status": "failed", "reason": "verifier_failed"})
        self.assertIn("calibration bins", repair)


if __name__ == "__main__":
    unittest.main()
