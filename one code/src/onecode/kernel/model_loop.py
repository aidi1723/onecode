from pathlib import Path
import hashlib
import inspect
import time
from typing import Any, Callable

from onecode.kernel.model_provider import (
    MissingModelApiKey,
    ModelPlan,
    ModelProviderError,
    ModelProviderTimeout,
    OpenAIChatCompletionsProvider,
    OpenAIResponsesProvider,
    api_key_from_env,
    build_provider_config,
)
from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.execution_engine import execute_plan
from onecode.kernel.execution_tools import redact_sensitive_text
from onecode.kernel.execution_plan_loader import execution_trace_to_dict
from onecode.kernel.checkpoint import write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE
from onecode.kernel.runner import halted_result, run_task
from onecode.kernel.trace import TraceEvent, write_trace_event
from onecode.kernel.safe_agent_router import SafeAgentRoute, route_safe_agent_task
from onecode.kernel.approval_plans import model_plan_requires_approval, persist_approval_plan


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
    failure_details = []
    if isinstance(trace, dict):
        for runner_result in trace.get("runner_results", []):
            payload = runner_result.get("payload", {}) if isinstance(runner_result, dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("path"), str):
                paths.append(payload["path"])
            if isinstance(runner_result, dict):
                reason = runner_result.get("reason")
                status = runner_result.get("status")
                if reason or status:
                    failure_details.append(f"runner status={status} reason={reason} payload={payload}")
        for step_result in trace.get("step_results", []):
            if not isinstance(step_result, dict):
                continue
            reason = step_result.get("reason")
            if reason:
                failure_details.append(f"step {step_result.get('step_id')}: {reason}")
            for tool_result in step_result.get("tool_results", []):
                if isinstance(tool_result, dict) and tool_result.get("reason"):
                    failure_details.append(
                        f"tool {tool_result.get('tool_name')}: {tool_result.get('reason')}"
                    )
    path_summary = ", ".join(sorted(set(paths))) if paths else "unknown"
    details = "\n".join(f"- {detail}" for detail in failure_details[:10]) or "- unavailable"
    return (
        "Repair the previous OneCode run using patches only.\n"
        f"Original task: {task}\n"
        f"Failure status: {failed_result.get('status')}\n"
        f"Failure reason: {failed_result.get('reason')}\n"
        f"Affected paths: {path_summary}\n"
        f"Failure details:\n{details}\n"
        "Return JSON with patches only. Do not return assets or execution_plan."
    )


def is_patch_only_repair_plan(plan: ModelPlan) -> bool:
    return bool(plan.patches) and not plan.assets and not plan.execution_steps


def repair_rejected_result(
    initial_result: dict[str, Any],
    run_id: str | None,
    reason: str,
    repair_attempt_count: int = 1,
) -> dict[str, Any]:
    return {
        **initial_result,
        "run_id": run_id,
        "status": "halted",
        "reason": reason,
        "partial": True,
        "repaired": False,
        "repair_attempt_count": repair_attempt_count,
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
    require_explicit_approval: bool = False,
    approval_callback: Callable[[ExecutionStep], bool] | None = None,
) -> dict[str, Any]:
    if plan.execution_steps:
        context = create_context(workspace_root=workspace, run_id=run_id, resume_from_run_id=resume_from_run_id)
        trace = execute_plan(
            execution_plan_from_model_plan(plan),
            workspace=workspace,
            run_id=context.run_id,
            resume_from_run_id=resume_from_run_id,
            approval_callback=approval_callback,
            require_explicit_approval=require_explicit_approval,
        )
        trace_dict = execution_trace_to_dict(trace)
        result = {
            "run_id": context.run_id,
            "status": "completed" if trace.success else "halted",
            "reason": trace.reason,
            "partial": not trace.success,
            "intent_type": "execution_plan",
            "manifest_path": str(context.manifest_path),
            "ledger_path": str(context.evidence_root / "ledger.json"),
            "requested_count": len(plan.execution_steps),
            "completed_count": sum(step.status == "completed" for step in trace.step_results),
            "skipped_count": sum(step.status == "skipped" for step in trace.step_results),
            "failed_count": sum(step.status == "failed" for step in trace.step_results),
            "assets": [],
            "execution_trace": trace_dict,
        } | run_metadata
        write_checkpoint(
            context=context,
            payload={"execution_trace": trace_dict},
            next_state=COMPLETE,
            status=result["status"],
            partial=result["partial"],
            reason=result["reason"],
            intent_type="execution_plan",
            decision="allowed",
            iching_status_code=trace.global_status_code,
            iching_transition_action=trace.global_transition.action if trace.global_transition else None,
            iching_transition_reason=trace.global_transition.reason if trace.global_transition else None,
            duration_ms=0,
            run_control={
                "global_status_code": trace.global_status_code,
                "global_transition_action": trace.global_transition.action if trace.global_transition else None,
                "global_transition_reason": trace.global_transition.reason if trace.global_transition else None,
                "global_entropy": trace.global_entropy,
                "global_entropy_decision": trace.global_entropy_decision,
                "global_entropy_reason": trace.global_entropy_reason,
            },
        )
        write_ledger(context, result)
        return result
    return run_task(
        plan.task,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        plan_actions=plan_actions_from_plan(plan),
        run_metadata=run_metadata,
    )


def resolve_safe_agent_planning_context(
    task: str,
    task_mode: str | None,
    safe_agent_route: SafeAgentRoute | None,
) -> tuple[SafeAgentRoute | None, dict[str, Any]]:
    route = safe_agent_route
    if task_mode is not None and route is None:
        route = route_safe_agent_task(task)
    safe_agent_context = (
        route.to_planning_context()
        if route is not None
        else {"status": "not_requested", "safety_boundary": "method_only"}
    )
    return route, {"task_mode": task_mode, "safe_agent": safe_agent_context}


def invalid_safe_agent_result(model_context: Any, trace_path: Path, route: SafeAgentRoute) -> dict[str, Any]:
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=model_context.run_id,
            run_id=model_context.run_id,
            span_id="safe-agent-route",
            parent_span_id="run",
            event_type="safe_agent_route_rejected",
            status="halted",
            payload=route.to_planning_context(),
        ),
    )
    return {
        "run_id": model_context.run_id,
        "status": "halted",
        "reason": "safe_agent_router_invalid",
        "partial": True,
        "intent_type": "safe_agent_route",
        "trace_id": model_context.run_id,
        "trace_path": str(trace_path),
        "manifest_path": None,
        "ledger_path": None,
        "requested_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
        "assets": [],
        "safe_agent": route.to_planning_context(),
    }


def no_action_result(
    *,
    model_context: Any,
    trace_path: Path,
    plan: ModelPlan,
    provider_config: Any,
    resolved_model: str,
    safe_agent_context: object,
) -> dict[str, Any]:
    return {
        "run_id": model_context.run_id,
        "status": "halted",
        "reason": "no_actionable_plan",
        "detail": plan.no_action_reason,
        "partial": True,
        "intent_type": "no_action",
        "trace_id": model_context.run_id,
        "trace_path": str(trace_path),
        "manifest_path": None,
        "ledger_path": None,
        "requested_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 1,
        "assets": [],
        "model_provider": "openai" if provider_config.env_key == "OPENAI_API_KEY" else provider_config.provider_kind,
        "model": resolved_model,
        "safe_agent": safe_agent_context,
    }


def pending_approval_result(
    *,
    workspace: Path,
    model_context: Any,
    trace_path: Path,
    plan: ModelPlan,
    provider_config: Any,
    resolved_model: str,
    safe_agent_context: object,
) -> dict[str, Any]:
    model_provider = "openai" if provider_config.env_key == "OPENAI_API_KEY" else provider_config.provider_kind
    stored = persist_approval_plan(
        workspace,
        plan,
        model_metadata={
            "model": resolved_model,
            "model_provider": model_provider,
            "safe_agent": safe_agent_context,
        },
    )
    tool_names = [tool.tool_name for step in plan.execution_steps for tool in step.tool_calls]
    return {
        "run_id": model_context.run_id,
        "status": "halted",
        "reason": "approval_required",
        "partial": False,
        "intent_type": "execution_plan",
        "trace_id": model_context.run_id,
        "trace_path": str(trace_path),
        "manifest_path": None,
        "ledger_path": None,
        "requested_count": len(plan.execution_steps) or len(plan.assets) + len(plan.patches),
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "assets": [],
        "plan_id": stored.plan_id,
        "plan_sha256": stored.plan_sha256,
        "plan_summary": {
            "task": plan.task,
            "step_count": len(plan.execution_steps),
            "asset_count": len(plan.assets),
            "patch_count": len(plan.patches),
            "tool_names": tool_names,
            "actions": approval_action_summaries(plan),
        },
        "model_provider": model_provider,
        "model": resolved_model,
        "safe_agent": safe_agent_context,
    }


def approval_action_summaries(plan: ModelPlan) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for step in execution_plan_from_model_plan(plan).steps:
        for tool_call in step.tool_calls:
            params = tool_call.params
            if tool_call.tool_name == "write_text":
                actions.append(
                    _write_approval_summary(
                        "write_text",
                        params.get("path"),
                        params.get("content"),
                    )
                )
            elif tool_call.tool_name == "patch_text":
                actions.append(
                    _patch_approval_summary(
                        params.get("path"),
                        params.get("search_block"),
                        params.get("replace_block"),
                    )
                )
            elif tool_call.tool_name == "run_command":
                argv = params.get("argv")
                actions.append(
                    {
                        "tool": "run_command",
                        "argv": [redact_sensitive_text(item) for item in argv] if isinstance(argv, list) else [],
                        "timeout_seconds": params.get("timeout_seconds", 60),
                    }
                )
            else:
                summary: dict[str, Any] = {"tool": tool_call.tool_name}
                for key in ("path", "query", "max_entries", "max_matches"):
                    value = params.get(key)
                    if isinstance(value, (str, int)) and not isinstance(value, bool):
                        summary[key] = redact_sensitive_text(value) if isinstance(value, str) else value
                actions.append(summary)
    return actions


def _write_approval_summary(tool: str, path: Any, content: Any) -> dict[str, Any]:
    text = content if isinstance(content, str) else ""
    return {
        "tool": tool,
        "path": path if isinstance(path, str) else "",
        "content_bytes": len(text.encode("utf-8")),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "content_preview": redact_sensitive_text(text[:500]),
        "content_truncated": len(text) > 500,
    }


def _patch_approval_summary(path: Any, search_block: Any, replace_block: Any) -> dict[str, Any]:
    search = search_block if isinstance(search_block, str) else ""
    replace = replace_block if isinstance(replace_block, str) else ""
    return {
        "tool": "patch_text",
        "path": path if isinstance(path, str) else "",
        "search_preview": redact_sensitive_text(search[:500]),
        "replace_preview": redact_sensitive_text(replace[:500]),
        "search_sha256": hashlib.sha256(search.encode("utf-8")).hexdigest(),
        "replace_sha256": hashlib.sha256(replace.encode("utf-8")).hexdigest(),
        "truncated": len(search) > 500 or len(replace) > 500,
    }


def maybe_pending_approval_result(
    required: bool,
    workspace: Path,
    model_context: Any,
    trace_path: Path,
    plan: ModelPlan,
    provider_config: Any,
    resolved_model: str,
    planning_context: dict[str, Any],
) -> dict[str, Any] | None:
    if not required or not model_plan_requires_approval(plan):
        return None
    return pending_approval_result(
        workspace=workspace,
        model_context=model_context,
        trace_path=trace_path,
        plan=plan,
        provider_config=provider_config,
        resolved_model=resolved_model,
        safe_agent_context=planning_context["safe_agent"],
    )


def early_model_plan_result(
    *,
    require_explicit_approval: bool,
    workspace: Path,
    model_context: Any,
    trace_path: Path,
    plan: ModelPlan,
    provider_config: Any,
    resolved_model: str,
    planning_context: dict[str, Any],
) -> dict[str, Any] | None:
    if plan.no_action_reason is not None:
        return no_action_result(
            model_context=model_context,
            trace_path=trace_path,
            plan=plan,
            provider_config=provider_config,
            resolved_model=resolved_model,
            safe_agent_context=planning_context["safe_agent"],
        )
    return maybe_pending_approval_result(
        require_explicit_approval,
        workspace,
        model_context,
        trace_path,
        plan,
        provider_config,
        resolved_model,
        planning_context,
    )


def resolve_model_runtime(
    provider_kind: str,
    endpoint: str | None,
    model: str | None,
    api_key: str | None,
) -> tuple[Any, str, str]:
    provider_config = build_provider_config(provider_kind, endpoint=endpoint, model=model)
    resolved_api_key = api_key if api_key is not None else api_key_from_env(provider_kind=provider_kind)
    if resolved_api_key is None:
        raise MissingModelApiKey(f"{provider_config.env_key} is required for model-backed runs")
    return provider_config, provider_config.model, resolved_api_key


def validate_model_task_limits(http_timeout_seconds: float, max_repair_attempts: int) -> None:
    if isinstance(http_timeout_seconds, bool) or not isinstance(http_timeout_seconds, (int, float)) or http_timeout_seconds <= 0:
        raise ValueError("http_timeout_seconds must be greater than zero")
    if isinstance(max_repair_attempts, bool) or not isinstance(max_repair_attempts, int) or max_repair_attempts < 0:
        raise ValueError("max_repair_attempts must be a non-negative integer")


def traced_provider_plan(
    *,
    provider: Any,
    task: str,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    span_id: str,
) -> tuple[ModelPlan | None, dict[str, Any] | None]:
    started_at = time.monotonic()
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=model_context.run_id,
            run_id=model_context.run_id,
            span_id=span_id,
            parent_span_id="run",
            event_type="model_call_started",
            status="started",
            payload={
                "provider": provider_config.provider_kind,
                "model": resolved_model,
            },
        ),
    )
    try:
        plan = _create_provider_plan(
            provider,
            task,
            model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
        )
    except (ModelProviderError, ValueError) as exc:
        if isinstance(exc, ModelProviderTimeout):
            reason = "model_provider_timeout"
        elif isinstance(exc, ModelProviderError):
            reason = "model_provider_error"
        elif str(exc) == "plan must include at least one asset":
            reason = "no_actionable_plan"
        else:
            reason = "invalid_model_plan"
        elapsed_ms = max(0, int((time.monotonic() - started_at) * 1000))
        failure = {
            "provider": provider_config.provider_kind,
            "model": resolved_model,
            "failure_kind": reason,
            "elapsed_ms": elapsed_ms,
            "retryable": False,
            "safe_agent": planning_context["safe_agent"],
        }
        write_trace_event(
            trace_path,
            TraceEvent(
                trace_id=model_context.run_id,
                run_id=model_context.run_id,
                span_id=span_id,
                parent_span_id="run",
                event_type="model_call_failed",
                status="halted",
                duration_ms=elapsed_ms,
                payload=failure,
            ),
        )
        return None, failure
    elapsed_ms = max(0, int((time.monotonic() - started_at) * 1000))
    write_trace_event(
        trace_path,
        TraceEvent(
            trace_id=model_context.run_id,
            run_id=model_context.run_id,
            span_id=span_id,
            parent_span_id="run",
            event_type="model_call_completed",
            status="completed",
            duration_ms=elapsed_ms,
            payload={
                "provider": provider_config.provider_kind,
                "model": resolved_model,
                "asset_count": len(plan.assets),
                "patch_count": len(plan.patches),
                "execution_step_count": len(plan.execution_steps),
                "no_action": plan.no_action_reason is not None,
            },
        ),
    )
    return plan, None


def failed_model_result(
    model_context: Any, failure: dict[str, Any]
) -> dict[str, Any]:
    return halted_result(
        model_context,
        reason=str(failure["failure_kind"]),
        payload=failure,
        trace_id=model_context.run_id,
        checkpoint_intent_type="model_plan",
        write_checkpoint_evidence=True,
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
    task_mode: str | None = None,
    safe_agent_route: SafeAgentRoute | None = None,
    require_explicit_approval: bool = False,
    execution_approval: Callable[[ExecutionStep], bool] | None = None,
) -> dict[str, Any]:
    validate_model_task_limits(http_timeout_seconds, max_repair_attempts)
    provider_config, resolved_model, resolved_api_key = resolve_model_runtime(
        provider_kind, endpoint, model, api_key
    )

    active_provider = provider or build_provider(resolved_api_key, provider_kind, endpoint)
    route, planning_context = resolve_safe_agent_planning_context(task, task_mode, safe_agent_route)
    model_context = create_context(workspace_root=workspace, run_id=run_id, resume_from_run_id=resume_from_run_id)
    trace_path = model_context.evidence_root / "trace.jsonl"
    if route is not None and route.status == "invalid":
        return invalid_safe_agent_result(model_context, trace_path, route)
    plan, failure = traced_provider_plan(
        provider=active_provider,
        task=task,
        model_context=model_context,
        trace_path=trace_path,
        provider_config=provider_config,
        resolved_model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
        planning_context=planning_context,
        span_id="model-call",
    )
    if failure is not None:
        return failed_model_result(model_context, failure)
    assert plan is not None
    early_result = early_model_plan_result(
        require_explicit_approval=require_explicit_approval, workspace=workspace, model_context=model_context,
        trace_path=trace_path, plan=plan, provider_config=provider_config, resolved_model=resolved_model,
        planning_context=planning_context,
    )
    if early_result is not None:
        return early_result
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
        "safe_agent": planning_context["safe_agent"],
    }
    result = execute_model_plan(
        plan,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        run_metadata=run_metadata,
        require_explicit_approval=require_explicit_approval,
        approval_callback=execution_approval,
    )
    if result["status"] == "completed" or max_repair_attempts <= 0:
        return result

    failed_result = result
    for attempt in range(1, max_repair_attempts + 1):
        repair_plan, failure = traced_provider_plan(
            provider=active_provider,
            task=repair_prompt(task, failed_result),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id=f"model-repair-{attempt}",
        )
        if failure is not None:
            return failed_model_result(model_context, failure)
        assert repair_plan is not None
        if not is_patch_only_repair_plan(repair_plan):
            return repair_rejected_result(
                result,
                run_id,
                "repair_plan_must_use_patches_only",
                repair_attempt_count=attempt,
            )
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
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
        )
        merged = merge_repair_result(result, repair_result, repair_attempt_count=attempt)
        if repair_result.get("status") == "completed":
            return merged
        failed_result = merged
    return failed_result


def _create_provider_plan(
    provider: Any,
    task: str,
    *,
    model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
) -> ModelPlan:
    parameters = inspect.signature(provider.create_plan).parameters
    kwargs: dict[str, Any] = {
        "model": model,
        "http_timeout_seconds": http_timeout_seconds,
    }
    if "planning_context" in parameters:
        kwargs["planning_context"] = planning_context
    return provider.create_plan(task, **kwargs)
