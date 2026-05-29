import time
from pathlib import Path

from onecode.kernel.execution_contracts import (
    ApprovalCallback,
    ExecutionPlan,
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
from onecode.kernel.runner import run_task


SAFETY_BREAK_REASONS = {"sovereignty_breach", "permission_denied"}


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
    safety_break = False

    for step in plan.steps:
        if safety_break:
            break
        if time_budget_exceeded(started_at, config):
            step_results.append(StepResult(step_id=step.id, status="failed", reason="time_budget_exceeded"))
            break

        if not dependencies_met(step, step_results):
            step_results.append(StepResult(step_id=step.id, status="skipped", reason="dependencies_not_met"))
            continue

        if should_require_approval(step, config) and approval_callback is not None and not approval_callback(step):
            step_results.append(StepResult(step_id=step.id, status="skipped", reason="approval_rejected"))
            continue

        tool_results: list[ToolResult] = []
        step_failed_reason: str | None = None

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
                if step_failed_reason in SAFETY_BREAK_REASONS:
                    safety_break = True
                break

        step_status = "failed" if step_failed_reason is not None else "completed"
        step_results.append(
            StepResult(
                step_id=step.id,
                status=step_status,
                tool_results=tool_results,
                reason=step_failed_reason,
            )
        )

        if step_status == "failed":
            if step_failed_reason in SAFETY_BREAK_REASONS:
                break
            consecutive_failures += 1
            if consecutive_failures >= config.max_consecutive_failures:
                break
        else:
            consecutive_failures = 0

    success = bool(step_results) and all(result.status == "completed" for result in step_results)
    reason = None if success else next((result.reason for result in step_results if result.reason), None)
    return ExecutionTrace(
        task=plan.task,
        success=success,
        step_results=step_results,
        runner_results=runner_results,
        reason=reason,
    )
