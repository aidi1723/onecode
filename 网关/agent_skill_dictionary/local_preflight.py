from __future__ import annotations

from typing import Any

from .tool_guard import preflight_tool_call


CLAUDE_TOOL_MAP = {
    "Read": "read_file",
    "LS": "list_directory",
    "Glob": "list_directory",
    "Grep": "grep_code",
    "Bash": "execute_command",
    "Edit": "edit_scoped_file",
    "MultiEdit": "edit_scoped_file",
    "Write": "write_file",
}


def preflight_claude_tool_call(
    dictionary: dict[str, Any],
    active_code: str,
    tool_name: str,
    tool_input: Any,
) -> dict[str, Any]:
    normalized_tool = normalize_claude_tool_name(tool_name)
    normalized_arguments = normalize_claude_tool_arguments(tool_name, tool_input)
    result = preflight_tool_call(
        dictionary,
        active_code=active_code,
        tool_name=normalized_tool,
        arguments=normalized_arguments,
    )
    return {
        **result,
        "original_tool": tool_name,
        "normalized_tool": normalized_tool,
        "normalized_arguments": normalized_arguments,
    }


def claude_hook_decision(
    dictionary: dict[str, Any],
    active_code: str,
    hook_payload: dict[str, Any],
) -> dict[str, Any]:
    result = preflight_claude_tool_call(
        dictionary,
        active_code=active_code,
        tool_name=str(hook_payload.get("tool_name", "")),
        tool_input=hook_payload.get("tool_input", {}),
    )
    decision = "allow" if result["allowed"] else "deny"
    reason = "allowed by one-word preflight"
    if not result["allowed"]:
        reason = _deny_reason(result)
    return {
        **result,
        "hook_output": {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        },
    }


def normalize_claude_tool_name(tool_name: str) -> str:
    return CLAUDE_TOOL_MAP.get(tool_name, tool_name)


def normalize_claude_tool_arguments(tool_name: str, tool_input: Any) -> Any:
    if not isinstance(tool_input, dict):
        return tool_input
    if tool_name == "Read":
        return {"path": tool_input.get("file_path", tool_input.get("path", ""))}
    if tool_name == "LS":
        return {"path": tool_input.get("path", ".")}
    if tool_name == "Glob":
        return {"path": tool_input.get("path", "."), "pattern": tool_input.get("pattern", "")}
    if tool_name == "Grep":
        return {"pattern": tool_input.get("pattern", ""), "path": tool_input.get("path", ".")}
    if tool_name == "Bash":
        return {"command": tool_input.get("command", "")}
    if tool_name in {"Edit", "MultiEdit", "Write"}:
        return {
            "path": tool_input.get("file_path", tool_input.get("path", "")),
            "content": tool_input.get("content", tool_input.get("new_string", "")),
        }
    return tool_input


def _deny_reason(result: dict[str, Any]) -> str:
    violations = result.get("violations", [])
    if not violations:
        return "denied by one-word preflight"
    reasons = [
        f"{item.get('tool', result.get('normalized_tool'))}:{item.get('reason', 'denied')}"
        for item in violations
    ]
    return "denied by one-word preflight: " + ", ".join(reasons)
