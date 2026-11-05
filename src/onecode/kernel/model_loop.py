import contextvars
import os
from pathlib import Path
from typing import Any, Callable

from onecode.kernel.model_provider import (
    ModelPlan,
)
from onecode.kernel.execution_contracts import ExecutionStep
from onecode.kernel.context import create_context
from onecode.kernel.safe_agent_router import SafeAgentRoute
from onecode.kernel.read_preface import with_preface

_KERNEL_WARNINGS: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "onecode_kernel_warnings",
    default=None,
)


def _record_kernel_fault(scope: str, exc: BaseException) -> None:
    """Keep the current control flow, and retain the exception on the active task."""
    bucket = _KERNEL_WARNINGS.get()
    if bucket is None:
        return
    message = f"{scope}: {type(exc).__name__}: {exc}"
    if message not in bucket:
        bucket.append(message)


def _merge_kernel_warnings(result: dict[str, Any], bucket: list[str]) -> dict[str, Any]:
    if not bucket:
        return result
    warnings = result.setdefault("warnings", [])
    if isinstance(warnings, list):
        for item in bucket:
            if item not in warnings:
                warnings.append(item)
    return result

from onecode.kernel.model_guidance import (  # noqa: F401
    _accepted_relative_python,
    _cached_workspace_scale_stats,
    _contract_spec_snippet,
    _extract_targeted_assertions,
    _format_ziwei_repair_guidance,
    _recovery_defense_alerts,
    _required_files_landed,
    _tuo_luo_stagnation_alert,
    _ziwei_structural_alerts,
    data_contract_guidance,
    file_write_slots,
    format_verifier_diagnostics,
    initial_asset_prompt,
    missing_required_files,
    named_python_files,
    narrow_plan_prompt,
    protected_python_files,
    repair_prompt,
    required_python_files,
    resolve_task_bureau,
    workspace_scale_stats,
)
from onecode.kernel.model_planning import (  # noqa: F401
    _change_diff,
    _create_provider_plan,
    _declared_execution_steps,
    _execution_steps_mutate,
    _git_head_text,
    _initial_model_plan,
    _patch_approval_summary,
    _preview_text,
    _run_plan_metadata,
    _unified_diff,
    _with_change_diff,
    _write_approval_summary,
    approval_action_summaries,
    asset_patch_steps_approved,
    build_provider,
    early_model_plan_result,
    execute_model_plan,
    execution_plan_from_model_plan,
    failed_model_result,
    invalid_safe_agent_result,
    maybe_pending_approval_result,
    no_action_result,
    pending_approval_result,
    plan_actions_from_plan,
    resolve_model_runtime,
    resolve_safe_agent_planning_context,
    traced_provider_plan,
    traced_provider_plan_retrying,
    validate_model_task_limits,
    write_texts_from_plan,
)
from onecode.kernel.model_repair import (  # noqa: F401
    _build_repair_metadata,
    _build_repair_prompt_context,
    _close_narrow_sequence,
    _compute_repair_cooldown,
    _detail_mentions_tests,
    _drop_protected_changes,
    _enrich_bureau_and_brightness_metadata,
    _enrich_failed_model_with_repair_state,
    _execution_rule_fields,
    _finish_verified_task,
    _generate_missing_artifacts,
    _is_test_path,
    _merge_narrow_results,
    _modified_paths_from_result,
    _plan_has_existing_file_rewrite,
    _plan_user_rejected_result,
    _repair_diff_blocks,
    _repair_roots,
    _repair_source_block,
    _repair_touches_tests,
    _resolve_governance_mode,
    _resolve_host_verifier_path,
    _restore_workspace_snapshot,
    _run_model_task_repair_loop,
    _same_step_retry,
    _snapshot_workspace_files,
    _src_files_for_repair,
    _validate_repair_plan_safety,
    _with_sandbox_tests,
    _write_following_narrow_files,
    is_patch_only_repair_plan,
    ledger_fields_for_iching,
    merge_repair_result,
    repair_rejected_result,
    synthesize_single_asset_repair,
)
from onecode.kernel.model_terminal import (  # noqa: F401
    _run_terminal_model_task,
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
    require_explicit_approval: bool = True,
    execution_approval: Callable[[ExecutionStep], bool] | None = None,
    on_turn: Callable[[dict[str, Any]], None] | None = None,
    sandbox_config: Any | None = None,
    preface: str | None = None,
    approval_mode: str = "strict",
    agent_mode: str = "classic",
    host_verifier_path: str | None = None,
) -> dict[str, Any]:
    from onecode.kernel.model_provider import begin_model_usage, finish_model_usage

    bucket: list[str] = []
    token = _KERNEL_WARNINGS.set(bucket)
    usage_token = begin_model_usage()
    try:
        result = _execute_model_task(
            task,
            workspace,
            http_timeout_seconds=http_timeout_seconds,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            model=model,
            api_key=api_key,
            provider=provider,
            provider_kind=provider_kind,
            endpoint=endpoint,
            plan_approval=plan_approval,
            max_repair_attempts=max_repair_attempts,
            task_mode=task_mode,
            safe_agent_route=safe_agent_route,
            require_explicit_approval=require_explicit_approval,
            execution_approval=execution_approval,
            on_turn=on_turn,
            sandbox_config=sandbox_config,
            preface=preface,
            approval_mode=approval_mode,
            agent_mode=agent_mode,
            host_verifier_path=host_verifier_path,
        )
    finally:
        usage = finish_model_usage(usage_token)
        _KERNEL_WARNINGS.reset(token)
    if isinstance(result, dict):
        result["model_usage"] = usage
    return _merge_kernel_warnings(result, bucket)


def _execute_model_task(
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
    preface: str | None = None,
    approval_mode: str = "strict",
    agent_mode: str = "classic",
    host_verifier_path: str | None = None,
) -> dict[str, Any]:
    task = with_preface(task, preface)
    validate_model_task_limits(http_timeout_seconds, max_repair_attempts)
    provider_config, resolved_model, resolved_api_key = resolve_model_runtime(provider_kind, endpoint, model, api_key)
    active_provider = provider or build_provider(resolved_api_key, provider_kind, endpoint)
    route, planning_context = resolve_safe_agent_planning_context(task, task_mode, safe_agent_route)
    model_context = create_context(workspace_root=workspace, run_id=run_id, resume_from_run_id=resume_from_run_id)
    trace_path = model_context.evidence_root / "trace.jsonl"
    from onecode.kernel.run_inspection import ledger_matches_workspace
    ledger_mismatch = ledger_matches_workspace(workspace)
    if ledger_mismatch is not None:
        return failed_model_result(model_context, {"failure_kind": ledger_mismatch, "reason": ledger_mismatch})
    if route is not None and route.status == "invalid":
        return invalid_safe_agent_result(model_context, trace_path, route)

    effective_agent_mode = (os.environ.get("ONECODE_AGENT_MODE") or agent_mode).strip().lower()
    if effective_agent_mode == "terminal":
        return _run_terminal_model_task(
            task=task,
            workspace=workspace,
            active_provider=active_provider,
            model_context=model_context,
            trace_path=trace_path,
            sandbox_config=sandbox_config,
            max_repair_attempts=max_repair_attempts,
            on_turn=on_turn,
            resolved_model=resolved_model,
            http_timeout_seconds=http_timeout_seconds,
            approval_mode=approval_mode,
            require_explicit_approval=require_explicit_approval,
            execution_approval=execution_approval,
            plan_approval=plan_approval,
        )
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
    if failure is not None or plan is None:
        return failed_model_result(model_context, failure if isinstance(failure, dict) else {"failure_kind": "invalid_model_plan"})
    plan = _drop_protected_changes(plan, task)
    if plan.no_action_reason is not None or execution_approval is None:
        early_result = early_model_plan_result(
            require_explicit_approval=require_explicit_approval, workspace=workspace, model_context=model_context,
            trace_path=trace_path, plan=plan, provider_config=provider_config, resolved_model=resolved_model,
            planning_context=planning_context, user_task=task,
            approval_mode=approval_mode,
        )
        if early_result is not None:
            return early_result
    if plan_approval is not None and not plan_approval(plan):
        return _plan_user_rejected_result(plan, run_id, provider_config, resolved_model)
    run_metadata = _run_plan_metadata(provider_config, resolved_model, plan, planning_context["safe_agent"])
    if host_verifier_path:
        run_metadata["host_verifier_path"] = str(host_verifier_path)
    _enrich_bureau_and_brightness_metadata(workspace, run_metadata)
    callback = execution_approval
    if callback is None and approval_mode == "scoped_auto":
        callback = lambda _step: True
    result = execute_model_plan(
        plan,
        workspace=workspace,
        http_timeout_seconds=http_timeout_seconds,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        run_metadata=run_metadata,
        require_explicit_approval=require_explicit_approval if approval_mode != "scoped_auto" else False,
        approval_callback=callback,
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
    grade_ready = sandbox_config is not None or bool(str(host_verifier_path or "").strip())
    if narrowed or result["status"] == "completed" or max_repair_attempts <= 0 or grade_ready:
        return _finish_verified_task(result, task, workspace, sandbox_config, max_repair_attempts, active_provider, model_context, trace_path, provider_config, resolved_model, http_timeout_seconds, planning_context, run_id, resume_from_run_id, run_metadata, require_explicit_approval, execution_approval, on_turn)

    return _run_model_task_repair_loop(
        result=result,
        task=task,
        workspace=workspace,
        run_metadata=run_metadata,
        max_repair_attempts=max_repair_attempts,
        active_provider=active_provider,
        model_context=model_context,
        trace_path=trace_path,
        provider_config=provider_config,
        resolved_model=resolved_model,
        http_timeout_seconds=http_timeout_seconds,
        planning_context=planning_context,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        require_explicit_approval=require_explicit_approval,
        execution_approval=execution_approval,
        on_turn=on_turn,
        sandbox_config=sandbox_config,
    )


