import json
from pathlib import Path
from typing import Any

from onecode.kernel.execution_contracts import ExecutionPlan, ExecutionStep, ToolCallSpec


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
    return {
        "task": trace.task,
        "success": trace.success,
        "reason": trace.reason,
        "global_status_code": trace.global_status_code,
        "global_transition": global_transition,
        "global_entropy": trace.global_entropy,
        "global_entropy_decision": trace.global_entropy_decision,
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
        "runner_results": trace.runner_results,
    }
