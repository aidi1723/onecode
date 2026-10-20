from pathlib import Path
import difflib
import hashlib
import inspect
import re
import subprocess
import time
from typing import Any, Callable

from onecode.kernel.model_provider import (
    MissingModelApiKey,
    ModelExecutionStep,
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
from onecode.kernel.hexagram import COMPLETE, IchingKernel
from onecode.kernel.runner import halted_result, run_task
from onecode.kernel.trace import TraceEvent, write_trace_event
from onecode.kernel.safe_agent_router import SafeAgentRoute, route_safe_agent_task
from onecode.kernel.approval_plans import model_plan_requires_approval, persist_approval_plan
from onecode.kernel.patching import PatchIntent, PatchRejected, apply_patch_preview
from onecode.kernel.path_guard import PathGuard, PathGuardError


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


_MUTATING_MODEL_TOOLS = frozenset({"write_text", "patch_text", "run_command", "git_commit"})


def _execution_steps_mutate(steps: list[ModelExecutionStep]) -> bool:
    return any(tool.tool_name in _MUTATING_MODEL_TOOLS for step in steps for tool in step.tool_calls)


def _declared_execution_steps(plan: ModelPlan) -> list[ExecutionStep]:
    return [
        ExecutionStep(
            id=step.id,
            description=step.description,
            depends_on=list(step.depends_on),
            mode=step.mode,  # type: ignore
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
    ]


def execution_plan_from_model_plan(plan: ModelPlan) -> ExecutionPlan:
    declared = _declared_execution_steps(plan) if plan.execution_steps else []
    if declared and _execution_steps_mutate(plan.execution_steps):
        return ExecutionPlan(task=plan.task, steps=declared)

    steps = list(declared)
    prior_ids = [step.id for step in declared]
    asset_step_ids = []
    for index, asset in enumerate(plan.assets, start=1):
        step_id = f"asset-{index}"
        asset_step_ids.append(step_id)
        steps.append(
            ExecutionStep(
                id=step_id,
                description=f"write {asset.path}",
                depends_on=list(prior_ids),
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
                depends_on=[*prior_ids, *asset_step_ids],
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


def asset_patch_steps_approved(plan: ModelPlan, approval_callback: Callable[[ExecutionStep], bool]) -> bool:
    approved = True
    for step in execution_plan_from_model_plan(plan).steps:
        if not approval_callback(step):
            approved = False
    return approved


def build_provider(api_key: str, provider_kind: str, endpoint: str | None) -> Any:
    config = build_provider_config(provider_kind, endpoint=endpoint, model=None)
    if config.provider_kind == "responses":
        return OpenAIResponsesProvider(api_key, endpoint=config.endpoint)
    return OpenAIChatCompletionsProvider(api_key, endpoint=config.endpoint)


_NAMED_PYTHON_FILE = re.compile(r"\b(?:src|tests)/[A-Za-z0-9_./-]+\.py\b")


def named_python_files(task: str) -> list[str]:
    found: list[str] = []
    for match in _NAMED_PYTHON_FILE.findall(task):
        if match not in found:
            found.append(match)
    return found


def file_write_slots(task: str, max_repair_attempts: int) -> int:
    if max_repair_attempts <= 0:
        return 0
    return max(max_repair_attempts, len(named_python_files(task)))


def _same_step_retry(failure: dict[str, Any] | None) -> bool:
    if not isinstance(failure, dict) or failure.get("failure_kind") != "invalid_model_plan":
        return False
    detail = str(failure.get("detail") or "")
    return (
        "model response was not valid JSON" in detail
        or "no_action cannot be combined with actions" in detail
    )


def narrow_plan_prompt(task: str, failure: dict[str, Any], written: list[str] | None = None) -> str:
    detail = failure.get("detail") or failure.get("failure_kind") or "plan did not fit"
    already = ", ".join(written) if written else "none"
    return (
        "The previous plan did not fit in one response.\n"
        f"Failure: {detail}\n"
        f"Original task: {task}\n"
        f"Already written: {already}\n"
        "Return JSON for exactly one new Python file. "
        "Do not rewrite a file that is already written. "
        "If the task is already complete, return no_action with a concrete reason and no assets. "
        "The asset content must be complete and non-empty. "
        "Use unittest, not pytest. No relative imports. "
        "Do not include execution_plan or run_command."
    )


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
    require_explicit_approval: bool = True,
    approval_callback: Callable[[ExecutionStep], bool] | None = None,
    on_turn: Callable[[dict[str, Any]], None] | None = None,
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
            on_turn=on_turn,
        )
        trace_dict = execution_trace_to_dict(trace)
        requested_count = len(plan.execution_steps)
        completed_count = sum(step.status == "completed" for step in trace.step_results)
        skipped_count = sum(step.status == "skipped" for step in trace.step_results)
        failed_count = sum(step.status == "failed" for step in trace.step_results)
        status = "completed" if trace.success else "halted"
        rule_fields = _execution_rule_fields(
            trace,
            status=status,
            requested_count=requested_count,
            completed_count=completed_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )
        result = {
            "run_id": context.run_id,
            "status": status,
            "reason": trace.reason,
            "partial": not trace.success,
            "intent_type": "execution_plan",
            "manifest_path": str(context.manifest_path),
            "ledger_path": str(context.evidence_root / "ledger.json"),
            "requested_count": requested_count,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "assets": [],
            "execution_trace": trace_dict,
            **rule_fields,
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
            iching_status_code=rule_fields.get("iching_status_code", trace.global_status_code),
            iching_transition_action=rule_fields.get("iching_transition_action"),
            iching_transition_reason=rule_fields.get("iching_transition_reason"),
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
    if require_explicit_approval and approval_callback is None:
        return {
            "run_id": run_id,
            "status": "halted",
            "reason": "approval_required",
            "partial": True,
            "requested_count": len(plan.assets) + len(plan.patches),
            "completed_count": 0,
            "skipped_count": len(plan.assets) + len(plan.patches),
            "failed_count": 0,
            "assets": [],
        } | run_metadata
    if approval_callback is not None and not asset_patch_steps_approved(plan, approval_callback):
        return {
            "run_id": run_id,
            "status": "halted",
            "reason": "approval_rejected",
            "partial": True,
            "requested_count": len(plan.assets) + len(plan.patches),
            "completed_count": 0,
            "skipped_count": len(plan.assets) + len(plan.patches),
            "failed_count": 0,
            "assets": [],
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
            "actions": approval_action_summaries(plan, workspace),
        },
        "model_provider": model_provider,
        "model": resolved_model,
        "safe_agent": safe_agent_context,
    }


def approval_action_summaries(plan: ModelPlan, workspace: Path) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for step in execution_plan_from_model_plan(plan).steps:
        for tool_call in step.tool_calls:
            params = tool_call.params
            if tool_call.tool_name == "write_text":
                actions.append(
                    _with_change_diff(
                        workspace,
                        tool_call.tool_name,
                        params,
                        _write_approval_summary(
                            "write_text",
                            params.get("path"),
                            params.get("content"),
                        ),
                    )
                )
            elif tool_call.tool_name == "patch_text":
                actions.append(
                    _with_change_diff(
                        workspace,
                        tool_call.tool_name,
                        params,
                        _patch_approval_summary(
                            params.get("path"),
                            params.get("search_block"),
                            params.get("replace_block"),
                        ),
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
            elif tool_call.tool_name == "git_commit":
                actions.append(_with_change_diff(workspace, tool_call.tool_name, params, {"tool": "git_commit"}))
            else:
                summary: dict[str, Any] = {"tool": tool_call.tool_name}
                for key in ("path", "query", "max_entries", "max_matches"):
                    value = params.get(key)
                    if isinstance(value, (str, int)) and not isinstance(value, bool):
                        summary[key] = redact_sensitive_text(value) if isinstance(value, str) else value
                actions.append(summary)
    return actions


def _with_change_diff(workspace: Path, tool_name: str, params: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    summary["diff"] = _change_diff(workspace, tool_name, params)
    return summary


def _change_diff(workspace: Path, tool_name: str, params: dict[str, Any]) -> str:
    if tool_name == "write_text" and isinstance(params.get("path"), str):
        content = params.get("content") if isinstance(params.get("content"), str) else ""
        return _unified_diff(params["path"], _preview_text(workspace, params["path"]), content)  # type: ignore
    if tool_name == "patch_text":
        path = params.get("path") if isinstance(params.get("path"), str) else ""
        search = params.get("search_block") if isinstance(params.get("search_block"), str) else ""
        replace = params.get("replace_block") if isinstance(params.get("replace_block"), str) else ""
        try:
            preview = apply_patch_preview(workspace, PatchIntent(path=path, search_block=search, replace_block=replace))  # type: ignore
        except (PatchRejected, PathGuardError, OSError, ValueError):
            return ""
        return preview.diff[:100_000]
    if tool_name == "git_commit" and isinstance(params.get("paths"), list):
        parts = []
        for path in params["paths"]:
            if isinstance(path, str):
                parts.append(_unified_diff(path, _git_head_text(workspace, path), _preview_text(workspace, path)))
        return "".join(parts)[:100_000]
    return ""


def _preview_text(workspace: Path, relative_path: str) -> str:
    try:
        target = PathGuard.resolve_target(workspace, relative_path)
    except PathGuardError:
        return ""
    if not target.is_file():
        return ""
    return target.read_text(encoding="utf-8")


def _git_head_text(workspace: Path, relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative_path}"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _unified_diff(path: str, before: str, after: str) -> str:
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    return diff[:100_000]


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
        elif str(exc) == "model response was truncated":
            reason = "resource_budget_exceeded"
        else:
            reason = "invalid_model_plan"
        elapsed_ms = max(0, int((time.monotonic() - started_at) * 1000))
        failure = {
            "provider": provider_config.provider_kind,
            "model": resolved_model,
            "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
            "failure_kind": reason,
            "detail": str(exc)[:500],
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


def traced_provider_plan_retrying(**kwargs: Any) -> tuple[ModelPlan | None, dict[str, Any] | None]:
    plan, failure = traced_provider_plan(**kwargs)
    if not _same_step_retry(failure):
        return plan, failure
    retry_kwargs = dict(kwargs)
    retry_kwargs["span_id"] = f"{kwargs['span_id']}-retry"
    return traced_provider_plan(**retry_kwargs)


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


def _execution_rule_fields(
    trace: Any,
    *,
    status: str,
    requested_count: int,
    completed_count: int,
    skipped_count: int,
    failed_count: int,
) -> dict[str, Any]:
    transition = trace.global_transition
    fields: dict[str, Any] = {
        "global_status_code": trace.global_status_code,
        "global_transition_action": transition.action if transition is not None else None,
        "global_transition_reason": transition.reason if transition is not None else None,
        "global_entropy": trace.global_entropy,
        "global_entropy_decision": trace.global_entropy_decision,
        "global_entropy_reason": trace.global_entropy_reason,
    }
    if transition is not None:
        fields["iching_status_code"] = transition.status_code
        fields["iching_transition_action"] = transition.action
        fields["iching_transition_reason"] = transition.reason
        fields["dispatch_decision"] = IchingKernel.dispatch_decision(transition)
    return fields | IchingKernel.delivery_decision(
        status, requested_count, completed_count, skipped_count, failed_count
    )


def _merge_narrow_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(results[-1])
    assets: list[Any] = []
    requested = completed = skipped = failed = asset_count = 0
    for result in results:
        result_assets = result.get("assets")
        if isinstance(result_assets, list):
            assets.extend(result_assets)
        requested += int(result.get("requested_count") or 0)
        completed += int(result.get("completed_count") or 0)
        skipped += int(result.get("skipped_count") or 0)
        failed += int(result.get("failed_count") or 0)
        asset_count += int(result.get("model_plan_asset_count") or 0)
    merged["assets"] = assets
    merged["requested_count"] = requested
    merged["completed_count"] = completed
    merged["skipped_count"] = skipped
    merged["failed_count"] = failed
    merged["model_plan_asset_count"] = asset_count
    return merged


def _close_narrow_sequence(
    results: list[dict[str, Any]],
    *,
    status: str,
    reason: str | None,
    model_context: Any,
    outstanding: bool,
) -> dict[str, Any]:
    merged = _merge_narrow_results(results)
    if outstanding:
        merged["requested_count"] = int(merged["completed_count"]) + 1
    status_code = IchingKernel.classify_outcome(status, reason)
    transition = IchingKernel.transition(status_code)
    delivery = IchingKernel.delivery_decision(
        status,
        merged["requested_count"],
        merged["completed_count"],
        merged["skipped_count"],
        merged["failed_count"],
    )
    closed = {
        **merged,
        "status": status,
        "reason": reason,
        "partial": status != "completed",
        "iching_status_code": transition.status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "global_status_code": transition.status_code,
        "global_transition_action": transition.action,
        "global_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
        **delivery,
    }
    write_ledger(model_context, closed)
    return closed


def _write_following_narrow_files(
    *,
    task: str,
    plan: ModelPlan,
    result: dict[str, Any],
    max_repair_attempts: int,
    provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str | None,
    run_metadata: dict[str, Any],
    require_explicit_approval: bool,
    execution_approval: Callable[[ExecutionStep], bool] | None,
    on_turn: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    written = [asset.path for asset in plan.assets]
    results = [result]
    slots = file_write_slots(task, max_repair_attempts)
    for index in range(2, slots + 1):
        next_plan, failure = traced_provider_plan_retrying(
            provider=provider,
            task=narrow_plan_prompt(
                task,
                {"detail": "continue with the next file", "failure_kind": "resource_budget_exceeded"},
                written,
            ),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id=f"model-narrow-{index}",
        )
        if failure is not None or next_plan is None:
            return _close_narrow_sequence(
                results,
                status="halted",
                reason=failure["failure_kind"] if failure is not None else "invalid_model_plan",
                model_context=model_context,
                outstanding=True,
            )
        if next_plan.no_action_reason is not None:
            return _close_narrow_sequence(
                results,
                status="completed",
                reason=None,
                model_context=model_context,
                outstanding=False,
            )
        latest = execute_model_plan(
            next_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata={
                **run_metadata,
                "model_plan_asset_count": len(next_plan.assets),
                "model_plan_patch_count": len(next_plan.patches),
                "model_plan_execution_step_count": len(next_plan.execution_steps),
            },
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        results.append(latest)
        if latest["status"] != "completed":
            return _close_narrow_sequence(
                results,
                status=latest["status"],
                reason=latest.get("reason"),
                model_context=model_context,
                outstanding=False,
            )
        written.extend(asset.path for asset in next_plan.assets)
    if len(named_python_files(task)) > max_repair_attempts:
        close_plan, close_failure = traced_provider_plan_retrying(
            provider=provider,
            task=narrow_plan_prompt(task, {"detail": "close the finished files", "failure_kind": "resource_budget_exceeded"}, written),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id="model-narrow-close",
        )
        if close_failure is not None or close_plan is None:
            return _close_narrow_sequence(
                results,
                status="halted",
                reason=close_failure["failure_kind"] if close_failure is not None else "invalid_model_plan",
                model_context=model_context,
                outstanding=True,
            )
        if close_plan.no_action_reason is not None:
            return _close_narrow_sequence(
                results,
                status="completed",
                reason=None,
                model_context=model_context,
                outstanding=False,
            )
        latest = execute_model_plan(
            close_plan,
            workspace=workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata=run_metadata,
            require_explicit_approval=require_explicit_approval,
            approval_callback=execution_approval,
            on_turn=on_turn,
        )
        results.append(latest)
    return _close_narrow_sequence(
        results,
        status="halted",
        reason="resource_budget_exceeded",
        model_context=model_context,
        outstanding=True,
    )


def _initial_model_plan(
    *,
    task: str,
    max_repair_attempts: int,
    provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
) -> tuple[ModelPlan | None, dict[str, Any] | None, bool]:
    plan, failure = traced_provider_plan_retrying(
        provider=provider,
        task=task,
        model_context=model_context,
        trace_path=trace_path,
        provider_config=provider_config,
        resolved_model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
        planning_context=planning_context,
        span_id="model-call",
    )
    narrowed = False
    if failure is not None and max_repair_attempts > 0 and failure["failure_kind"] in {
        "resource_budget_exceeded",
        "invalid_model_plan",
    }:
        narrowed = True
        plan, failure = traced_provider_plan_retrying(
            provider=provider,
            task=narrow_plan_prompt(task, failure),
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            span_id="model-narrow-1",
        )
    return plan, failure, narrowed


def _repair_touches_tests(plan: ModelPlan) -> bool:
    for patch in plan.patches:
        path = patch.path.replace("\\", "/")
        if path == "tests" or path.startswith("tests/"):
            return True
    return False


def _finish_verified_task(
    result: dict[str, Any],
    task: str,
    workspace: Path,
    sandbox_config: Any | None,
    max_repair_attempts: int,
    provider: Any,
    model_context: Any,
    trace_path: Path,
    provider_config: Any,
    resolved_model: str,
    http_timeout_seconds: float,
    planning_context: dict[str, Any],
    run_id: str | None,
    resume_from_run_id: str | None,
    run_metadata: dict[str, Any],
    require_explicit_approval: bool,
    execution_approval: Callable[[ExecutionStep], bool] | None,
    on_turn: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    checked = _with_sandbox_tests(result, workspace, sandbox_config)
    if checked.get("reason") != "verifier_failed" or max_repair_attempts <= 0 or sandbox_config is None:
        return checked
    tails = [
        str(item.get("stderr_tail"))[-400:]
        for item in (checked.get("verifier_results") or [])
        if isinstance(item, dict) and item.get("stderr_tail")
    ]
    prompt = repair_prompt(task, checked) + "\nDo not patch any path under tests/. Change the implementation so the existing tests pass."
    if tails:
        prompt += "\nVerifier output:\n" + "\n".join(tails)
    plan, failure = traced_provider_plan_retrying(
        provider=provider,
        task=prompt,
        model_context=model_context,
        trace_path=trace_path,
        provider_config=provider_config,
        resolved_model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
        planning_context=planning_context,
        span_id="model-repair-after-check",
    )
    if failure is not None:
        return failed_model_result(model_context, failure)
    if plan is None or not is_patch_only_repair_plan(plan) or _repair_touches_tests(plan):
        rejected = repair_rejected_result(checked, run_id, "repair_plan_must_use_patches_only")
        transition = IchingKernel.transition(IchingKernel.classify_outcome("halted", rejected["reason"]))
        return {
            **rejected,
            "iching_status_code": transition.status_code,
            "iching_transition_action": transition.action,
            "iching_transition_reason": transition.reason,
        }
    repaired = execute_model_plan(
        plan,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        run_metadata=run_metadata,
        require_explicit_approval=require_explicit_approval,
        approval_callback=execution_approval,
        on_turn=on_turn,
    )
    if repaired.get("status") != "completed":
        return repaired
    return _with_sandbox_tests(merge_repair_result(checked, repaired, repair_attempt_count=1), workspace, sandbox_config)


def _with_sandbox_tests(result: dict[str, Any], workspace: Path, sandbox_config: Any | None) -> dict[str, Any]:
    if sandbox_config is None or result.get("status") != "completed" or not (workspace / "tests").is_dir():
        return result
    from onecode.kernel.run_inspection import apply_verifier_evidence
    from onecode.kernel.verifier import VerifierSpec, run_verifier

    checked = run_verifier(
        workspace,
        VerifierSpec(
            id="python-unittest",
            command=["python3", "-m", "unittest", "discover", "-s", "tests"],
            cwd=".",
            timeout_ms=max(1000, int(sandbox_config.timeout_seconds * 1000)),
        ),
        sandbox_config=sandbox_config,
    )
    return apply_verifier_evidence(result, workspace, [checked])


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
    require_explicit_approval: bool = True,
    execution_approval: Callable[[ExecutionStep], bool] | None = None,
    on_turn: Callable[[dict[str, Any]], None] | None = None,
    sandbox_config: Any | None = None,
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
    plan, failure, narrowed = _initial_model_plan(
        task=task,
        max_repair_attempts=max_repair_attempts,
        provider=active_provider,
        model_context=model_context,
        trace_path=trace_path,
        provider_config=provider_config,
        resolved_model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
        planning_context=planning_context,
    )
    if failure is not None:
        return failed_model_result(model_context, failure)
    assert plan is not None
    if plan.no_action_reason is not None or execution_approval is None:
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
        on_turn=on_turn,
    )
    if narrowed and file_write_slots(task, max_repair_attempts) > 1 and result["status"] == "completed":
        result = _write_following_narrow_files(
            task=task, plan=plan,
            result=result,
            max_repair_attempts=max_repair_attempts,
            provider=active_provider,
            model_context=model_context,
            trace_path=trace_path,
            provider_config=provider_config,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            planning_context=planning_context,
            workspace=workspace,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            run_metadata=run_metadata,
            require_explicit_approval=require_explicit_approval,
            execution_approval=execution_approval,
            on_turn=on_turn,
        )
    if narrowed or result["status"] == "completed" or max_repair_attempts <= 0:
        return _finish_verified_task(result, task, workspace, sandbox_config, max_repair_attempts, active_provider, model_context, trace_path, provider_config, resolved_model, http_timeout_seconds, planning_context, run_id, resume_from_run_id, run_metadata, require_explicit_approval, execution_approval, on_turn)

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
            on_turn=on_turn,
        )
        merged = merge_repair_result(result, repair_result, repair_attempt_count=attempt)
        if repair_result.get("status") == "completed":
            return _with_sandbox_tests(merged, workspace, sandbox_config)
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
