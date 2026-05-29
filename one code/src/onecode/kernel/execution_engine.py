from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from pathlib import Path

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
    dependencies_met,
    should_require_approval,
    time_budget_exceeded,
    validate_plan,
)
from onecode.kernel.execution_tools import ToolRegistry, default_tool_registry
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.path_guard import PathGuard, PathGuardError
from onecode.kernel.runner import run_task


SAFETY_BREAK_REASONS = {"sovereignty_breach", "permission_denied"}


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


def step_blocked_by_bandwidth(step: ExecutionStep, registry: ToolRegistry) -> bool:
    for tool_call in step.tool_calls:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            continue
        action = tool.plan_action(tool_call.params)
        status_code = action.get("status_code")
        if isinstance(status_code, int) and IchingKernel.execution_bandwidth(status_code) <= 0:
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

        action = tool.plan_action(tool_call.params)
        result = run_task(
            plan.task,
            workspace=workspace,
            run_id=run_id,
            resume_from_run_id=resume_from_run_id,
            plan_actions=[action],
        )
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
            status=step_status,
            tool_results=tool_results,
            reason=step_failed_reason,
            duration_ms=duration_ms,
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
) -> ExecutionTrace:
    config = guardrails or GuardrailConfig()
    registry = tool_registry or default_tool_registry()
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
            if should_require_approval(step, config) and approval_callback is not None and not approval_callback(step):
                step_results.append(StepResult(step_id=step.id, status="skipped", reason="approval_rejected"))
                processed_step_ids.add(step.id)
            else:
                approved_layer.append(step)
        if not approved_layer:
            continue
        bandwidth_blocked = [step for step in approved_layer if step_blocked_by_bandwidth(step, registry)]
        for step in bandwidth_blocked:
            step_results.append(StepResult(step_id=step.id, status="failed", reason="execution_bandwidth_zero"))
            processed_step_ids.add(step.id)
        approved_layer = [step for step in approved_layer if step.id not in {blocked.id for blocked in bandwidth_blocked}]
        if bandwidth_blocked:
            break
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
    status_codes = [
        IchingKernel.classify_outcome(
            "completed" if step.status == "completed" else "halted" if step.status == "failed" else "skipped",
            step.reason,
        )
        for step in step_results
    ]
    entropy_regulated = IchingKernel.entropy_regulated_status(status_codes)
    global_status_code = int(entropy_regulated["status_code"])
    return ExecutionTrace(
        task=plan.task,
        success=success,
        step_results=step_results,
        runner_results=runner_results,
        reason=reason,
        global_status_code=global_status_code,
        global_transition=IchingKernel.transition(global_status_code),
        global_entropy=float(entropy_regulated["entropy"]),
        global_entropy_decision=str(entropy_regulated["decision"]),
    )
