from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .kernel_policy import get_kernel_policy
from .loader import DictionaryEntry, lookup_entry


READ_TOOLS = {"native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff", "summarize_state"}
WRITE_TOOLS = {
    "write_file",
    "edit_file",
    "edit_scoped_file",
    "apply_patch",
    "create_file",
    "create_new_file",
    "delete_file",
    "undo_change",
    "append_knowledge_base",
    "write_markdown_doc",
    "git_commit",
}
DEPENDENCY_TOOLS = {
    "install_dependency",
    "pip_install",
    "npm_install",
    "pnpm_install",
    "yarn_add",
}
SHELL_TOOLS = {
    "run_shell",
    "exec",
    "exec_command",
    "bash",
    "execute_command",
    "run_pytest",
    "run_npm_test",
    "run_build",
}
SPECIALIZED_TOOLS = {
    "generate_mock_data",
    "capture_coverage",
    "dependency_security_scan",
    "ast_vulnerability_check",
    "send_user_message",
    "render_ui_options",
    "compress_tokens",
}
KNOWN_TOOLS = READ_TOOLS | WRITE_TOOLS | DEPENDENCY_TOOLS | SHELL_TOOLS | SPECIALIZED_TOOLS
DANGEROUS_COMMAND_MARKERS = (
    "rm -rf",
    "sudo ",
    "chmod -R 777",
    "curl ",
    "wget ",
    "git reset --hard",
)


@dataclass(frozen=True)
class ToolGuardDecision:
    allowed: bool
    violations: list[dict[str, str]]


def inspect_tool_calls(entry: DictionaryEntry, tool_calls: list[dict[str, Any]]) -> ToolGuardDecision:
    violations: list[dict[str, str]] = []
    for call in tool_calls:
        tool_name = str(call.get("name", ""))
        arguments = call.get("arguments", {})

        if tool_name not in KNOWN_TOOLS:
            violations.append({"tool": tool_name, "reason": "unknown_tool"})
            continue

        if tool_name in WRITE_TOOLS and entry.tool_policy.get("write") == "forbidden":
            violations.append({"tool": tool_name, "reason": "write_forbidden"})

        if tool_name in DEPENDENCY_TOOLS and entry.tool_policy.get("dependency_install") == "forbidden":
            violations.append({"tool": tool_name, "reason": "dependency_install_forbidden"})

        if tool_name in SHELL_TOOLS and _is_dangerous_command(arguments):
            violations.append({"tool": tool_name, "reason": "dangerous_command"})

    return ToolGuardDecision(allowed=not violations, violations=violations)


def preflight_tool_call(
    dictionary: dict[str, Any],
    active_code: str,
    tool_name: str,
    arguments: Any,
) -> dict[str, Any]:
    try:
        entry = lookup_entry(dictionary, active_code)
    except KeyError:
        return {
            "allowed": False,
            "active_code": active_code,
            "tool": tool_name,
            "violations": [{"tool": tool_name, "reason": "unknown_execution_code"}],
        }

    decision = inspect_tool_calls(entry, [{"name": tool_name, "arguments": arguments}])
    violations = list(decision.violations)
    root_code = str(entry.raw.get("root_opcode", active_code))
    policy = get_kernel_policy(root_code)
    if tool_name not in policy.allowed_tools:
        violations.append({"tool": tool_name, "reason": "tool_not_allowed_by_kernel_policy"})
    return {
        "allowed": not violations,
        "active_code": active_code,
        "root_opcode": root_code,
        "tool": tool_name,
        "routing_target": entry.routing_target,
        "tool_policy": entry.tool_policy,
        "kernel_policy": {
            "allowed_tools": list(policy.allowed_tools),
            "blocked_tools": list(policy.blocked_tools),
        },
        "violations": violations,
    }


def _is_dangerous_command(arguments: Any) -> bool:
    if isinstance(arguments, dict):
        command = str(arguments.get("command", ""))
    else:
        command = str(arguments)
    return any(marker in command for marker in DANGEROUS_COMMAND_MARKERS)
