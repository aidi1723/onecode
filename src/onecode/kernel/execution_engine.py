from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import time
from pathlib import Path
from typing import Any

from onecode.kernel.execution_contracts import (
    ApprovalCallback,
    ExecutionPlan,
    ExecutionStep,
    ExecutionTrace,
    GuardrailConfig,
    StepResult,
    ToolResult,
)
from onecode.kernel.execution_guardrails import (
    should_require_approval,
    time_budget_exceeded,
    validate_plan,
)
from onecode.kernel.execution_tools import ToolRegistry, default_tool_registry
from onecode.kernel.mcp_client import load_mcp_servers
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.checkpoint import write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.runner import run_task


SAFETY_BREAK_REASONS = {"sovereignty_breach", "permission_denied"}


def write_execution_plan_ledger(
    plan: ExecutionPlan,
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str | None,
    trace: ExecutionTrace,
) -> None:
    if run_id is None or not trace.runner_results:
        return
    last_result = trace.runner_results[-1]
    status = "completed" if trace.success else "halted"
    completed_count = sum(step.status == "completed" for step in trace.step_results)
    skipped_count = sum(step.status == "skipped" for step in trace.step_results)
    failed_count = sum(step.status == "failed" for step in trace.step_results)
    transition = trace.global_transition
    context = create_context(workspace, run_id=run_id, resume_from_run_id=resume_from_run_id)
    result = {
        "run_id": run_id,
        "status": status,
        "state": last_result.get("state", "000000"),
        "manifest_path": str(context.manifest_path),
        "ledger_path": str(context.evidence_root / "ledger.json"),
        "trace_id": run_id,
        "trace_path": str(context.evidence_root / "trace.jsonl"),
        "partial": not trace.success,
        "reason": trace.reason,
        "decision": "allowed" if trace.success else "halted",
        "intent_type": "execution_plan",
        "payload": {
            "task": plan.task,
            "step_count": len(plan.steps),
            "runner_result_count": len(trace.runner_results),
        },
        "resumed_from": resume_from_run_id,
        "resumed": resume_from_run_id is not None,
        "assets": [
            asset
            for runner_result in trace.runner_results
            for asset in runner_result.get("assets", [])
            if isinstance(runner_result.get("assets"), list)
        ],
        "requested_count": len(trace.step_results),
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "global_status_code": trace.global_status_code,
        "global_transition_action": transition.action if transition is not None else None,
        "global_transition_reason": transition.reason if transition is not None else None,
        "global_entropy": trace.global_entropy,
        "global_entropy_decision": trace.global_entropy_decision,
        "global_entropy_reason": trace.global_entropy_reason,
        "iching_status_code": transition.status_code if transition is not None else trace.global_status_code,
        "iching_transition_action": transition.action if transition is not None else None,
        "iching_transition_reason": transition.reason if transition is not None else None,
        "execution_plan": {
            "task": plan.task,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "depends_on": step.depends_on,
                    "mode": step.mode,
                    "tool_count": len(step.tool_calls),
                }
                for step in plan.steps
            ],
        },
        "execution_step_results": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "reason": step.reason,
                "duration_ms": step.duration_ms,
                "tool_results": [
                    {
                        "tool_name": tool.tool_name,
                        "success": tool.success,
                        "reason": tool.reason,
                    }
                    for tool in step.tool_results
                ],
            }
            for step in trace.step_results
        ],
    }
    write_ledger(context, result)


def ready_layer(plan: ExecutionPlan, completed_step_ids: set[str], processed_step_ids: set[str]) -> list[ExecutionStep]:
    return [
        step
        for step in plan.steps
        if step.id not in processed_step_ids and all(dependency in completed_step_ids for dependency in step.depends_on)
    ]


def blocked_steps(plan: ExecutionPlan, processed_step_ids: set[str]) -> list[ExecutionStep]:
    return [step for step in plan.steps if step.id not in processed_step_ids]


def step_has_path_breach(step: ExecutionStep, workspace: Path, registry: ToolRegistry) -> bool:
    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            continue
        action = tool.plan_action(tool_call.params)
        if action.get("action_type") not in {"write_text", "patch_text"}:
            continue
        path = action.get("path")
        if not isinstance(path, str):
            continue
        try:
            PathGuard.resolve_target(workspace, path)
        except PathGuardError:
            return True
    return False


def _recorded_status_code(step: StepResult) -> int:
    if isinstance(step.iching_status_code, int):
        return step.iching_status_code
    state = "completed" if step.status == "completed" else "halted" if step.status == "failed" else "skipped"
    return IchingKernel.classify_outcome(state, step.reason)


def _tagged_status_code(step: ExecutionStep, registry: ToolRegistry) -> int | None:
    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            continue
        action = tool.plan_action(tool_call.params)
        status_code = action.get("status_code")
        if isinstance(status_code, int) and not isinstance(status_code, bool):
            return status_code
    return None


def step_restrained_by_relation(step: ExecutionStep, registry: ToolRegistry) -> str | None:
    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            continue
        action = tool.plan_action(tool_call.params)
        status_code = action.get("status_code")
        if not isinstance(status_code, int) or isinstance(status_code, bool):
            continue
        ruling = IchingKernel.action_ruling(status_code, str(action.get("action_type") or ""))
        if ruling["outcome"] == "refuse" and ruling["reason"] != "execution_bandwidth_zero":
            reason = ruling["reason"]
            return reason if isinstance(reason, str) else None
    return None


def _drop_restrained_steps(
    layer: list[ExecutionStep],
    registry: ToolRegistry,
    step_results: list[StepResult],
    processed_step_ids: set[str],
) -> tuple[list[ExecutionStep], bool]:
    remaining: list[ExecutionStep] = []
    restrained = False
    for step in layer:
        reason = step_restrained_by_relation(step, registry)
        if reason is None:
            remaining.append(step)
            continue
        step_results.append(
            StepResult(
                step_id=step.id,
                status="failed",
                reason=reason,
                iching_status_code=_tagged_status_code(step, registry),
            )
        )
        processed_step_ids.add(step.id)
        restrained = True
    return remaining, restrained


def step_blocked_by_bandwidth(step: ExecutionStep, registry: ToolRegistry) -> bool:
    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            continue
        action = tool.plan_action(tool_call.params)
        status_code = action.get("status_code")
        if not isinstance(status_code, int) or isinstance(status_code, bool):
            continue
        ruling = IchingKernel.action_ruling(status_code, str(action.get("action_type") or ""))
        if ruling["reason"] == "execution_bandwidth_zero":
            return True
    return False


def execute_step(
    step: ExecutionStep,
    plan: ExecutionPlan,
    workspace: Path,
    run_id: str | None,
    resume_from_run_id: str | None,
    registry: ToolRegistry,
) -> tuple[StepResult, list[dict]]:
    tool_results: list[ToolResult] = []
    runner_results: list[dict] = []
    step_failed_reason: str | None = None
    started_at = time.monotonic()

    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            step_failed_reason = "tool_not_found"
            tool_results.append(
                ToolResult(tool_name=tool_call.tool_name, success=False, output=None, reason=step_failed_reason)
            )
            break

        if tool_call.tool_name == "write_text":
            path_val = tool_call.params.get("path")
            if isinstance(path_val, str):
                target = workspace / path_val
                if target.is_file() and target.stat().st_size > 0:
                    status_code = _tagged_status_code(step, registry)
                    if status_code is not None:
                        brightness = IchingKernel.star_brightness_profile(status_code)
                        breaking = IchingKernel.pattern_breaking_profile(status_code)
                        if (
                            brightness.get("governance_mode") == "degraded"
                            or breaking.get("execution_posture") in ("partially_broken_degraded", "severely_broken_quarantine")
                        ):
                            step_failed_reason = "degraded_mode_disallows_full_file_rewrite"
                            tool_results.append(
                                ToolResult(
                                    tool_name=tool_call.tool_name,
                                    success=False,
                                    output={"status": "halted", "reason": step_failed_reason, "governance_mode": "degraded"},
                                    reason=step_failed_reason,
                                )
                            )
                            break

        try:
            action = tool.plan_action(tool_call.params)
            if tool.runner_managed:
                result = run_task(
                    plan.task,
                    workspace=workspace,
                    run_id=run_id,
                    resume_from_run_id=resume_from_run_id,
                    plan_actions=[action],
                )
            else:
                output = tool.execute(tool_call.params, workspace)
                status = "completed"
                reason = None
                if isinstance(output, dict):
                    if output.get("status") == "halted" or output.get("returncode") not in {None, 0}:
                        status = "halted"
                        reason = output.get("reason") or "action_exception"
                result = {
                    "status": status,
                    "reason": reason,
                    "intent_type": tool.name,
                    "payload": output,
                    "assets": [],
                }
        except PathGuardError:
            result = {"status": "halted", "reason": "sovereignty_breach", "payload": {}, "assets": []}
        except FileNotFoundError:
            result = {"status": "halted", "reason": "action_exception", "payload": {}, "assets": []}
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result = {
                "status": "halted",
                "reason": str(exc) or "tool_failed",
                "payload": {},
                "assets": [],
            }
        runner_results.append(result)
        success = result["status"] in {"completed", "skipped"}
        reason = result.get("reason")
        tool_results.append(
            ToolResult(
                tool_name=tool_call.tool_name,
                success=success,
                output=result,
                reason=reason,
            )
        )
        if not success:
            step_failed_reason = reason or "tool_failed"
            break

    step_status = "failed" if step_failed_reason is not None else "completed"
    duration_ms = int((time.monotonic() - started_at) * 1000)
    return (
        StepResult(
            step_id=step.id,
            status=step_status,  # type: ignore
            tool_results=tool_results,
            reason=step_failed_reason,
            duration_ms=duration_ms,
            iching_status_code=_tagged_status_code(step, registry),
        ),
        runner_results,
    )


def execute_plan(
    plan: ExecutionPlan,
    workspace: Path,
    run_id: str | None = None,
    resume_from_run_id: str | None = None,
    tool_registry: ToolRegistry | None = None,
    guardrails: GuardrailConfig | None = None,
    approval_callback: ApprovalCallback | None = None,
    require_explicit_approval: bool = True,
    on_turn: Callable[[dict[str, Any]], None] | None = None,
) -> ExecutionTrace:
    config = guardrails or GuardrailConfig()
    registry = tool_registry or default_tool_registry()
    load_mcp_servers(registry, workspace)
    validation = validate_plan(plan, config)
    if not validation.valid:
        return ExecutionTrace(
            task=plan.task,
            success=False,
            step_results=[],
            runner_results=[],
            reason=validation.reason,
        )

    started_at = time.monotonic()
    step_results: list[StepResult] = []
    runner_results: list[dict] = []
    consecutive_failures = 0
    completed_step_ids: set[str] = set()
    processed_step_ids: set[str] = set()

    while len(processed_step_ids) < len(plan.steps):
        if time_budget_exceeded(started_at, config):
            remaining = blocked_steps(plan, processed_step_ids)
            if remaining:
                step_results.append(StepResult(step_id=remaining[0].id, status="failed", reason="time_budget_exceeded"))
            break

        layer = ready_layer(plan, completed_step_ids, processed_step_ids)
        if not layer:
            for step in blocked_steps(plan, processed_step_ids):
                step_results.append(StepResult(step_id=step.id, status="skipped", reason="dependencies_not_met"))
                processed_step_ids.add(step.id)
            break

        approved_layer: list[ExecutionStep] = []
        for step in layer:
            if should_require_approval(step, config):
                has_mcp = any(tc.tool_name.startswith("mcp.") for tc in step.tool_calls)
                if approval_callback is None and (require_explicit_approval or has_mcp):
                    step_results.append(StepResult(step_id=step.id, status="failed", reason="approval_required"))
                    processed_step_ids.add(step.id)
                    continue
                if approval_callback is not None and not approval_callback(step):
                    step_results.append(StepResult(step_id=step.id, status="skipped", reason="approval_rejected"))
                    processed_step_ids.add(step.id)
                    continue
            approved_layer.append(step)
        if not approved_layer:
            continue
        bandwidth_blocked = [step for step in approved_layer if step_blocked_by_bandwidth(step, registry)]
        for step in bandwidth_blocked:
            step_results.append(
                StepResult(
                    step_id=step.id,
                    status="failed",
                    reason="execution_bandwidth_zero",
                    iching_status_code=_tagged_status_code(step, registry),
                )
            )
            processed_step_ids.add(step.id)
        approved_layer = [step for step in approved_layer if step.id not in {blocked.id for blocked in bandwidth_blocked}]
        approved_layer, _ = _drop_restrained_steps(
            approved_layer, registry, step_results, processed_step_ids
        )
        if not approved_layer:
            continue
        path_breach_step = next(
            (step for step in approved_layer if step_has_path_breach(step, workspace, registry)),
            None,
        )
        if path_breach_step is not None:
            approved_layer = [path_breach_step]

        layer_results: dict[str, tuple[StepResult, list[dict]]] = {}
        with ThreadPoolExecutor(max_workers=len(approved_layer)) as executor:
            futures = {
                executor.submit(
                    execute_step,
                    step,
                    plan,
                    workspace,
                    run_id,
                    resume_from_run_id,
                    registry,
                ): step
                for step in approved_layer
            }
            for future in as_completed(futures):
                step = futures[future]
                layer_results[step.id] = future.result()

        safety_break = False
        for step in approved_layer:
            step_result, step_runner_results = layer_results[step.id]
            step_results.append(step_result)
            runner_results.extend(step_runner_results)
            processed_step_ids.add(step.id)
            if on_turn is not None:
                on_turn(
                    {
                        "step_id": step.id,
                        "status": step_result.status,
                        "reason": step_result.reason,
                        "tool_names": [tool_call.tool_name for tool_call in step.tool_calls],
                    }
                )
            if step_result.status == "completed":
                completed_step_ids.add(step.id)
                consecutive_failures = 0
                continue

            if step_result.reason in SAFETY_BREAK_REASONS:
                safety_break = True
                break
            consecutive_failures += 1
            if consecutive_failures >= config.max_consecutive_failures:
                safety_break = True
                break

        if safety_break:
            break

    success = bool(step_results) and all(result.status == "completed" for result in step_results)
    reason = None if success else next((result.reason for result in step_results if result.reason), None)
    status_codes = [_recorded_status_code(step) for step in step_results]
    entropy_regulated = IchingKernel.entropy_regulated_status(status_codes)
    global_status_code = (
        IchingKernel.aggregate_status(status_codes) if status_codes else int(entropy_regulated["status_code"])
    )
    trace = ExecutionTrace(
        task=plan.task,
        success=success,
        step_results=step_results,
        runner_results=runner_results,
        reason=reason,
        global_status_code=global_status_code,
        global_transition=IchingKernel.transition(global_status_code),
        global_entropy=float(entropy_regulated["entropy"]),
        global_entropy_decision=str(entropy_regulated["decision"]),
        global_entropy_reason=(
            str(entropy_regulated["reason"])
            if isinstance(entropy_regulated.get("reason"), str)
            else None
        ),
    )
    write_execution_plan_ledger(plan, workspace, run_id, resume_from_run_id, trace)
    return trace
