from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Iterable

from onecode.kernel.execution_tools import redact_sensitive_text
from onecode.kernel.model_provider import ModelPlan

if TYPE_CHECKING:
    from onecode.kernel.approval_plans import StoredApprovalPlan


def approval_action_summaries(plan: ModelPlan) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for tool_name, params in _plan_tool_calls(plan):
        if tool_name == "write_text":
            actions.append(
                _write_approval_summary(
                    params.get("path"),
                    params.get("content"),
                )
            )
        elif tool_name == "patch_text":
            actions.append(
                _patch_approval_summary(
                    params.get("path"),
                    params.get("search_block"),
                    params.get("replace_block"),
                )
            )
        elif tool_name == "run_command":
            argv = params.get("argv")
            actions.append(
                {
                    "tool": "run_command",
                    "argv": (
                        [redact_sensitive_text(item) for item in argv]
                        if isinstance(argv, list)
                        else []
                    ),
                    "timeout_seconds": params.get("timeout_seconds", 60),
                }
            )
        else:
            summary: dict[str, Any] = {"tool": tool_name}
            for key in (
                "path",
                "query",
                "max_entries",
                "max_matches",
                "max_depth",
                "max_bytes",
                "max_lines",
            ):
                value = params.get(key)
                if isinstance(value, (str, int)) and not isinstance(value, bool):
                    summary[key] = (
                        redact_sensitive_text(value) if isinstance(value, str) else value
                    )
            actions.append(summary)
    return actions


def pending_plan_summary(stored: StoredApprovalPlan) -> dict[str, Any]:
    actions = approval_action_summaries(stored.plan)
    return {
        "plan_id": stored.plan_id,
        "plan_sha256": stored.plan_sha256,
        "created_at": stored.created_at,
        "workspace": stored.workspace,
        "task": stored.plan.task,
        "status": "pending",
        "action_count": len(actions),
        "tool_names": sorted({str(action.get("tool")) for action in actions}),
        "actions": actions,
    }


def _plan_tool_calls(plan: ModelPlan) -> Iterable[tuple[str, dict[str, Any]]]:
    if plan.execution_steps:
        for step in plan.execution_steps:
            for tool_call in step.tool_calls:
                yield tool_call.tool_name, dict(tool_call.params)
        return
    for asset in plan.assets:
        yield "write_text", {"path": asset.path, "content": asset.content}
    for patch in plan.patches:
        yield "patch_text", {
            "path": patch.path,
            "search_block": patch.search_block,
            "replace_block": patch.replace_block,
        }


def _write_approval_summary(path: Any, content: Any) -> dict[str, Any]:
    text = content if isinstance(content, str) else ""
    return {
        "tool": "write_text",
        "path": path if isinstance(path, str) else "",
        "content_bytes": len(text.encode("utf-8")),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _patch_approval_summary(
    path: Any, search_block: Any, replace_block: Any
) -> dict[str, Any]:
    search = search_block if isinstance(search_block, str) else ""
    replace = replace_block if isinstance(replace_block, str) else ""
    return {
        "tool": "patch_text",
        "path": path if isinstance(path, str) else "",
        "search_bytes": len(search.encode("utf-8")),
        "replace_bytes": len(replace.encode("utf-8")),
        "search_sha256": hashlib.sha256(search.encode("utf-8")).hexdigest(),
        "replace_sha256": hashlib.sha256(replace.encode("utf-8")).hexdigest(),
    }
