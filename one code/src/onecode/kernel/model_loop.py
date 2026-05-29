from pathlib import Path
from typing import Any, Callable

from onecode.kernel.model_provider import (
    MissingModelApiKey,
    ModelPlan,
    OpenAIChatCompletionsProvider,
    OpenAIResponsesProvider,
    api_key_from_env,
    build_provider_config,
)
from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_plan_loader import execution_trace_to_dict
from onecode.kernel.runner import run_task


def write_texts_from_plan(plan: ModelPlan) -> list[str]:
    return [f"{asset.path}={asset.content}" for asset in plan.assets]


def plan_actions_from_plan(plan: ModelPlan) -> list[dict[str, str]]:
    actions = [
        {"action_type": "write_text", "path": asset.path, "content": asset.content}
        for asset in plan.assets
    ]
    actions.extend(
        {
            "action_type": "patch_text",
            "path": patch.path,
            "search_block": patch.search_block,
            "replace_block": patch.replace_block,
        }
        for patch in plan.patches
    )
    return actions


def execution_plan_from_model_plan(plan: ModelPlan) -> ExecutionPlan:
    if plan.execution_steps:
        return ExecutionPlan(
            task=plan.task,
            steps=[
                ExecutionStep(
                    id=step.id,
                    description=step.description,
                    depends_on=list(step.depends_on),
                    mode=step.mode,
                    tool_calls=[
                        ToolCallSpec(
                            tool_name=tool.tool_name,
                            description=tool.description,
                            params=dict(tool.params),
                        )
                        for tool in step.tool_calls
                    ],
                )
                for step in plan.execution_steps
            ],
        )

    steps = []
    asset_step_ids = []
    for index, asset in enumerate(plan.assets, start=1):
        step_id = f"asset-{index}"
        asset_step_ids.append(step_id)
        steps.append(
            ExecutionStep(
                id=step_id,
                description=f"write {asset.path}",
                tool_calls=[
                    ToolCallSpec(
                        tool_name="write_text",
                        params={"path": asset.path, "content": asset.content},
                    )
                ],
            )
        )
    for index, patch in enumerate(plan.patches, start=1):
        steps.append(
            ExecutionStep(
                id=f"patch-{index}",
                description=f"patch {patch.path}",
                depends_on=list(asset_step_ids),
                tool_calls=[
                    ToolCallSpec(
                        tool_name="patch_text",
                        params={
                            "path": patch.path,
                            "search_block": patch.search_block,
                            "replace_block": patch.replace_block,
                        },
                    )
                ],
            )
        )
    return ExecutionPlan(task=plan.task, steps=steps)


def build_provider(api_key: str, provider_kind: str, endpoint: str | None) -> Any:
    config = build_provider_config(provider_kind, endpoint=endpoint, model=None)
    if config.provider_kind == "responses":
        return OpenAIResponsesProvider(api_key, endpoint=config.endpoint)
    return OpenAIChatCompletionsProvider(api_key, endpoint=config.endpoint)


def repair_prompt(task: str, failed_result: dict[str, Any]) -> str:
    trace = failed_result.get("execution_trace", {})
    paths = []
    if isinstance(trace, dict):
        for runner_result in trace.get("runner_results", []):
            payload = runner_result.get("payload", {}) if isinstance(runner_result, dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("path"), str):
                paths.append(payload["path"])
    path_summary = ", ".join(sorted(set(paths))) if paths else "unknown"
    return (
        "Repair the previous OneCode run using patches only.\n"
        f"Original task: {task}\n"
        f"Failure status: {failed_result.get('status')}\n"
        f"Failure reason: {failed_result.get('reason')}\n"
        f"Affected paths: {path_summary}\n"
        "Return JSON with patches only. Do not return assets or execution_plan."
    )


def is_patch_only_repair_plan(plan: ModelPlan) -> bool:
    return bool(plan.patches) and not plan.assets and not plan.execution_steps


def repair_rejected_result(
    initial_result: dict[str, Any],
    run_id: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        **initial_result,
        "run_id": run_id,
        "status": "halted",
        "reason": reason,
        "partial": True,
        "repaired": False,
        "repair_attempt_count": 1,
        "initial_status": initial_result.get("status"),
        "initial_reason": initial_result.get("reason"),
    }


def merge_repair_result(
    initial_result: dict[str, Any],
    repair_result: dict[str, Any],
    repair_attempt_count: int,
) -> dict[str, Any]:
    return {
        **repair_result,
        "repaired": repair_result.get("status") == "completed",
        "repair_attempt_count": repair_attempt_count,
        "initial_status": initial_result.get("status"),
        "initial_reason": initial_result.get("reason"),
        "initial_execution_trace": initial_result.get("execution_trace"),
    }


def execute_model_plan(
    plan: ModelPlan,
    workspace: Path,
    http_timeout_seconds: float,
    run_id: str | None,
    resume_from_run_id: str | None,
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    if plan.execution_steps:
        trace = execute_plan(
            execution_plan_from_model_plan(plan),
            workspace=workspace,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
        )
        trace_dict = execution_trace_to_dict(trace)
        return {
            "run_id": run_id,
            "status": "completed" if trace.success else "halted",
            "reason": trace.reason,
            "partial": not trace.success,
            "intent_type": "execution_plan",
            "requested_count": len(plan.execution_steps),
            "completed_count": sum(step.status == "completed" for step in trace.step_results),
            "skipped_count": sum(step.status == "skipped" for step in trace.step_results),
            "failed_count": sum(step.status == "failed" for step in trace.step_results),
            "assets": [],
            "execution_trace": trace_dict,
        } | run_metadata
    return run_task(
        plan.task,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        plan_actions=plan_actions_from_plan(plan),
        run_metadata=run_metadata,
    )


def run_model_task(
    task: str,
    workspace: Path,
    http_timeout_seconds: float = 60,
    run_id: str | None = None,
    resume_from_run_id: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    provider: Any | None = None,
    provider_kind: str = "responses",
    endpoint: str | None = None,
    plan_approval: Callable[[ModelPlan], bool] | None = None,
    max_repair_attempts: int = 0,
) -> dict[str, Any]:
    provider_config = build_provider_config(provider_kind, endpoint=endpoint, model=model)
    resolved_model = provider_config.model
    resolved_api_key = api_key if api_key is not None else api_key_from_env(provider_kind=provider_kind)
    if resolved_api_key is None:
        raise MissingModelApiKey(f"{provider_config.env_key} is required for model-backed runs")

    active_provider = provider or build_provider(resolved_api_key, provider_kind, endpoint)
    plan = active_provider.create_plan(task, model=resolved_model, http_timeout_seconds=http_timeout_seconds)
    if plan_approval is not None and not plan_approval(plan):
        return {
            "run_id": run_id,
            "status": "cancelled",
            "reason": "user_rejected_diff",
            "partial": False,
            "requested_count": len(plan.assets),
            "completed_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "assets": [],
            "model_provider": "openai" if provider_config.env_key == "OPENAI_API_KEY" else provider_config.provider_kind,
            "model": resolved_model,
            "model_plan_task": plan.task,
            "model_plan_asset_count": len(plan.assets),
            "model_plan_patch_count": len(plan.patches),
            "model_plan_execution_step_count": len(plan.execution_steps),
        }
    run_metadata = {
        "model_provider": "openai" if provider_config.env_key == "OPENAI_API_KEY" else provider_config.provider_kind,
        "model": resolved_model,
        "model_plan_task": plan.task,
        "model_plan_asset_count": len(plan.assets),
        "model_plan_patch_count": len(plan.patches),
        "model_plan_execution_step_count": len(plan.execution_steps),
    }
    result = execute_model_plan(
        plan,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        run_metadata=run_metadata,
    )
    if result["status"] == "completed" or max_repair_attempts <= 0:
        return result

    repair_plan = active_provider.create_plan(
        repair_prompt(task, result),
        model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
    )
    if not is_patch_only_repair_plan(repair_plan):
        return repair_rejected_result(result, run_id, "repair_plan_must_use_patches_only")
    repair_metadata = {
        **run_metadata,
        "model_plan_task": repair_plan.task,
        "model_plan_asset_count": len(repair_plan.assets),
        "model_plan_patch_count": len(repair_plan.patches),
        "model_plan_execution_step_count": len(repair_plan.execution_steps),
        "repair_of_run_id": run_id,
    }
    repair_result = execute_model_plan(
        repair_plan,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        run_metadata=repair_metadata,
    )
    return merge_repair_result(result, repair_result, repair_attempt_count=1)
