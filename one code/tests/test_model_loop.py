import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import default_tool_registry
from onecode.kernel.run_inspection import apply_verifier_evidence, inspect_run
from onecode.kernel.model_loop import run_model_task
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
    def test_model_timeout_writes_failed_terminal_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_task(
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
            result = run_model_task(
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
            self.assertEqual(
                [event["event_type"] for event in terminal], ["model_call_failed"]
            )
            self.assertTrue(Path(result["ledger_path"]).is_file())
            self.assertTrue(Path(result["manifest_path"]).is_file())

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
            result = run_model_task(
                "build module with repair",
                workspace=workspace,
                run_id="repair-timeout",
                model="test-model",
                api_key="test-key",
                provider=SequenceThenTimeoutProvider(first_plan),
                max_repair_attempts=1,
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

            result = run_model_task(
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

            result = run_model_task(
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

            result = run_model_task(
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

            result = run_model_task(
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

            result = run_model_task(
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
                run_model_task("build nothing", workspace=workspace, run_id="missing-key")

            self.assertFalse((workspace / ".onecode").exists())

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
                run_model_task(
                    "build project",
                    workspace=workspace,
                    run_id="model-bool-timeout",
                    api_key="test-key",
                    provider=provider,
                    http_timeout_seconds=True,
                )
            with self.assertRaisesRegex(ValueError, "max_repair_attempts must be a non-negative integer"):
                run_model_task(
                    "build project",
                    workspace=workspace,
                    run_id="model-bool-repair",
                    api_key="test-key",
                    provider=provider,
                    max_repair_attempts=True,
                )

            self.assertEqual(provider.calls, [])
            self.assertFalse((workspace / ".onecode").exists())

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

            result = run_model_task(
                "build project",
                workspace=workspace,
                run_id="model-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
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

            result = run_model_task(
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

            result = run_model_task(
                "build project",
                workspace=workspace,
                run_id="secret-run",
                model="test-model",
                api_key=secret,
                provider=provider,
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

            result = run_model_task(
                "patch project",
                workspace=workspace,
                run_id="model-patch-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
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

            result = run_model_task(
                "execute project",
                workspace=workspace,
                run_id="model-execution-plan-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
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

            result = run_model_task(
                "execute project",
                workspace=workspace,
                run_id="model-execution-evidence",
                model="test-model",
                api_key="test-key",
                provider=provider,
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

            result = run_model_task(
                "build module with repair",
                workspace=workspace,
                run_id="repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=1,
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

            result = run_model_task(
                "build module with repeated repair",
                workspace=workspace,
                run_id="multi-repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=2,
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

            result = run_model_task(
                "build module with unsafe repair",
                workspace=workspace,
                run_id="unsafe-repair-run",
                model="test-model",
                api_key="test-key",
                provider=provider,
                max_repair_attempts=1,
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
        process_exit_code.assert_called_once_with(status="completed", reason=None)

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
            result = run_model_task(
                "build project",
                workspace=workspace,
                run_id="model-verifier-inspect",
                model="test-model",
                api_key="test-key",
                provider=provider,
            )
            verifier = run_verifier(
                workspace,
                VerifierSpec(
                    id="python-unittest",
                    command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    cwd=".",
                    timeout_ms=5000,
                ),
            )

            enhanced = apply_verifier_evidence(result, workspace, [verifier])
            exit_code, summary = inspect_run(workspace, "model-verifier-inspect")

        self.assertEqual(enhanced["status"], "halted")
        self.assertEqual(enhanced["reason"], "verifier_failed")
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["status"], "halted")
        self.assertEqual(summary["reason"], "verifier_failed")
        self.assertEqual(summary["delivery_status"], "blocked")
        self.assertEqual(summary["verifier_results"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
