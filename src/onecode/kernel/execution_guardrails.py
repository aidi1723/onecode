import time

from onecode.kernel.execution_contracts import (
    ExecutionPlan,
    ExecutionStep,
    GuardrailConfig,
    GuardrailValidation,
    StepResult,
)


def validate_plan(plan: ExecutionPlan, config: GuardrailConfig) -> GuardrailValidation:
    if len(plan.steps) > config.max_steps:
        return GuardrailValidation(
            valid=False,
            reason="max_steps_exceeded",
            detail=f"plan has {len(plan.steps)} steps, max is {config.max_steps}",
        )

    seen_step_ids: set[str] = set()
    for step in plan.steps:
        if step.id in seen_step_ids:
            return GuardrailValidation(valid=False, reason="duplicate_step_id", detail=step.id)
        seen_step_ids.add(step.id)

        if len(step.tool_calls) > config.max_tool_calls_per_step:
            return GuardrailValidation(
                valid=False,
                reason="max_tool_calls_exceeded",
                detail=step.id,
            )

        for tool_call in step.tool_calls:
            if tool_call.tool_name in config.forbidden_tools:
                return GuardrailValidation(
                    valid=False,
                    reason="forbidden_tool",
                    detail=tool_call.tool_name,
                )

    return GuardrailValidation(valid=True)


def should_require_approval(step: ExecutionStep, config: GuardrailConfig) -> bool:
    if step.mode in {"review", "manual"}:
        return True
    return any(tool_call.tool_name in config.require_approval_for for tool_call in step.tool_calls)


def dependencies_met(step: ExecutionStep, results: list[StepResult]) -> bool:
    completed = {result.step_id for result in results if result.status == "completed"}
    return all(dependency in completed for dependency in step.depends_on)


def time_budget_exceeded(started_at: float, config: GuardrailConfig) -> bool:
    return (time.monotonic() - started_at) * 1000 > config.max_duration_ms
