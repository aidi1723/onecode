import json
from pathlib import Path
from typing import Any

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec
from onecode.kernel.shell_projection import attach_shell_projection, project_run_to_shell


def load_execution_plan(path: Path) -> ExecutionPlan:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("invalid execution plan: missing_file") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("invalid execution plan: invalid_json") from exc

    if not isinstance(data, dict):
        raise ValueError("invalid execution plan: root must be an object")
    task = data.get("task")
    steps = data.get("steps")
    if not isinstance(task, str) or task == "":
        raise ValueError("invalid execution plan: task must be a non-empty string")
    if not isinstance(steps, list) or not steps:
        raise ValueError("invalid execution plan: steps must be a non-empty list")

    return ExecutionPlan(
        task=task,
        steps=[_parse_step(index, step) for index, step in enumerate(steps, start=1)],
    )


def _parse_step(index: int, value: Any) -> ExecutionStep:
    if not isinstance(value, dict):
        raise ValueError(f"invalid execution step {index}: step must be an object")
    tool_calls = value.get("tool_calls", [])
    if not isinstance(tool_calls, list):
        raise ValueError(f"invalid execution step {index}: tool_calls must be a list")
    depends_on = value.get("depends_on", [])
    if not isinstance(depends_on, list) or not all(isinstance(item, str) for item in depends_on):
        raise ValueError(f"invalid execution step {index}: depends_on must be a string list")
    return ExecutionStep(
        id=value.get("id", ""),
        description=value.get("description", ""),
        depends_on=depends_on,
        mode=value.get("mode", "auto"),
        tool_calls=[_parse_tool_call(index, call_index, call) for call_index, call in enumerate(tool_calls, start=1)],
    )


def _parse_tool_call(step_index: int, call_index: int, value: Any) -> ToolCallSpec:
    if not isinstance(value, dict):
        raise ValueError(f"invalid execution step {step_index} tool {call_index}: tool call must be an object")
    return ToolCallSpec(
        tool_name=value.get("tool_name", ""),
        description=value.get("description", ""),
        params=value.get("params", {}),
    )


def execution_trace_to_dict(trace: Any) -> dict[str, Any]:
    global_transition = None
    if trace.global_transition is not None:
        global_transition = {
            "status_code": trace.global_transition.status_code,
            "action": trace.global_transition.action,
            "reason": trace.global_transition.reason,
        }
    last_runner_result = trace.runner_results[-1] if trace.runner_results else {}
    trace_projection_source = {
        "run_id": last_runner_result.get("run_id") if isinstance(last_runner_result, dict) else None,
        "status": "completed" if trace.success else "halted",
        "reason": trace.reason,
        "partial": not trace.success,
        "global_status_code": trace.global_status_code,
        "global_transition_action": trace.global_transition.action if trace.global_transition is not None else None,
        "global_transition_reason": trace.global_transition.reason if trace.global_transition is not None else None,
        "iching_status_code": trace.global_status_code,
        "iching_transition_action": trace.global_transition.action if trace.global_transition is not None else None,
        "iching_transition_reason": trace.global_transition.reason if trace.global_transition is not None else None,
        "requested_count": len(trace.step_results),
        "completed_count": sum(1 for step in trace.step_results if step.status == "completed"),
        "skipped_count": sum(1 for step in trace.step_results if step.status == "skipped"),
        "failed_count": sum(1 for step in trace.step_results if step.status == "failed"),
        "decision": "allowed" if trace.success else "halted",
    }
    return {
        "task": trace.task,
        "success": trace.success,
        "reason": trace.reason,
        "shell_projection": project_run_to_shell(trace_projection_source),
        "global_status_code": trace.global_status_code,
        "global_transition": global_transition,
        "global_entropy": trace.global_entropy,
        "global_entropy_decision": trace.global_entropy_decision,
        "global_entropy_reason": trace.global_entropy_reason,
        "step_results": [
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
        "runner_results": [
            attach_shell_projection(result) if isinstance(result, dict) else result
            for result in trace.runner_results
        ],
    }
