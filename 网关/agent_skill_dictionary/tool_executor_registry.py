from __future__ import annotations

from pathlib import Path
from typing import Any

from .build_mode_repair import summarize_pytest_output
from .executor import execute_command
from .guard_executor import PhysicalGuardExecutor
from .inspect_executor import build_native_inspect_card, inspect_workspace
from .memory_executor import archive_markdown
from .patch_executor import apply_controlled_patch
from .prompt_executor import create_confirmation_ticket
from .summary_executor import summarize_active_context


REGISTERED_TOOLS = frozenset(
    {
        "append_knowledge_base",
        "ast_vulnerability_check",
        "capture_coverage",
        "compress_tokens",
        "create_new_file",
        "dependency_security_scan",
        "edit_scoped_file",
        "git_commit",
        "git_diff",
        "grep_code",
        "list_directory",
        "native_inspect_card",
        "read_file",
        "render_ui_options",
        "run_npm_test",
        "run_pytest",
        "send_user_message",
        "write_file",
        "write_markdown_doc",
    }
)


def registered_tool_names() -> set[str]:
    return set(REGISTERED_TOOLS)


def execute_registered_tool(
    tool_name: str,
    arguments: Any,
    workspace: str | Path,
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(workspace).resolve()
    try:
        if tool_name not in REGISTERED_TOOLS:
            return {
                "tool": tool_name,
                "exit_code": 127,
                "stdout": "",
                "stderr": f"unsupported registered tool: {tool_name}",
            }
        if tool_name == "list_directory":
            return _list_directory(root, arguments)
        if tool_name == "native_inspect_card":
            return _native_inspect_card(root, arguments)
        if tool_name == "read_file":
            return _read_file(root, arguments)
        if tool_name == "write_file":
            return _write_file(root, arguments)
        if tool_name == "grep_code":
            return _grep_code(root, arguments)
        if tool_name == "git_diff":
            return _run_command_tool("git_diff", root, {"command": ["git", "diff", "--"]}, audit_log_path)
        if tool_name == "edit_scoped_file":
            return _edit_scoped_file(root, arguments, audit_log_path)
        if tool_name == "create_new_file":
            return _create_new_file(root, arguments, audit_log_path)
        if tool_name == "run_pytest":
            return _run_command_tool("run_pytest", root, arguments, audit_log_path)
        if tool_name == "run_npm_test":
            return _run_command_tool("run_npm_test", root, arguments, audit_log_path)
        if tool_name == "capture_coverage":
            return _run_command_tool("capture_coverage", root, arguments, audit_log_path)
        if tool_name == "dependency_security_scan":
            return _dependency_security_scan(root, arguments, audit_log_path)
        if tool_name == "ast_vulnerability_check":
            return _ast_vulnerability_check(root, arguments, audit_log_path)
        if tool_name == "compress_tokens":
            return _compress_tokens(arguments, audit_log_path)
        if tool_name in {"append_knowledge_base", "write_markdown_doc"}:
            return _archive_markdown_tool(root, arguments, audit_log_path)
        if tool_name in {"send_user_message", "render_ui_options"}:
            return _prompt_tool(root, arguments, audit_log_path)
        if tool_name == "git_commit":
            return _blocked_side_effect_tool(tool_name)
        return _blocked_side_effect_tool(tool_name)
    except (OSError, ValueError) as exc:
        return {"tool": tool_name, "exit_code": 1, "stdout": "", "stderr": str(exc)}


def _list_directory(root: Path, arguments: Any) -> dict[str, Any]:
    target = _resolve_workspace_path(root, _argument_value(arguments, "path", "."))
    if not target.is_dir():
        return {"tool": "list_directory", "exit_code": 1, "stdout": "", "stderr": f"not a directory: {target}"}
    entries = [path.name for path in sorted(target.iterdir())]
    return {"tool": "list_directory", "exit_code": 0, "stdout": "\n".join(entries), "stderr": ""}


def _native_inspect_card(root: Path, arguments: Any) -> dict[str, Any]:
    target = _argument_value(arguments, "target", None)
    max_chars = int(_argument_value(arguments, "max_chars", 1200))
    card = build_native_inspect_card(
        root,
        target=str(target) if target else None,
        max_chars=max_chars,
    )
    return {
        "tool": "native_inspect_card",
        "exit_code": 0,
        "stdout": card["text"],
        "stderr": "",
        "card": card,
    }


def _read_file(root: Path, arguments: Any) -> dict[str, Any]:
    target = _resolve_workspace_path(root, _argument_value(arguments, "path", ""))
    return {"tool": "read_file", "exit_code": 0, "stdout": target.read_text(encoding="utf-8"), "stderr": ""}


def _write_file(root: Path, arguments: Any) -> dict[str, Any]:
    target = _resolve_workspace_path(root, _argument_value(arguments, "path", ""))
    content = str(_argument_value(arguments, "content", ""))
    target.write_text(content, encoding="utf-8")
    return {"tool": "write_file", "exit_code": 0, "stdout": str(target), "stderr": ""}


def _grep_code(root: Path, arguments: Any) -> dict[str, Any]:
    pattern = str(_argument_value(arguments, "pattern", "")).lower()
    if not pattern:
        return {"tool": "grep_code", "exit_code": 1, "stdout": "", "stderr": "pattern is required"}
    matches: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if pattern in line.lower():
                    matches.append(f"{relative}:{line_number}:{line.strip()}")
        except UnicodeDecodeError:
            continue
    return {"tool": "grep_code", "exit_code": 0, "stdout": "\n".join(matches), "stderr": ""}


def _edit_scoped_file(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    path = str(_argument_value(arguments, "path", ""))
    content = str(_argument_value(arguments, "content", ""))
    expected_sha256 = _argument_value(arguments, "expected_sha256", None)
    patch = {"path": path, "content": content}
    if expected_sha256:
        patch["expected_sha256"] = str(expected_sha256)
    result = apply_controlled_patch(root, [patch], audit_log_path=audit_log_path)
    return {
        "tool": "edit_scoped_file",
        "exit_code": 0 if result.get("ok") else 1,
        "stdout": "\n".join(result.get("changed_files", [])),
        "stderr": str(result.get("error", "")),
        "evidence": result.get("evidence"),
    }


def _create_new_file(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    return _edit_scoped_file(root, arguments, audit_log_path) | {"tool": "create_new_file"}


def _dependency_security_scan(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    result = PhysicalGuardExecutor(root).run_security_compile(
        require_enforcement=bool(_argument_value(arguments, "require_enforcement", False)),
        scanner_types=_argument_value(arguments, "scanner_types", None),
        audit_log_path=audit_log_path,
    )
    return _guard_tool_result("dependency_security_scan", result)


def _ast_vulnerability_check(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    result = PhysicalGuardExecutor(root).run_security_compile(
        require_enforcement=bool(_argument_value(arguments, "require_enforcement", False)),
        scanner_types=["semgrep"],
        audit_log_path=audit_log_path,
    )
    return _guard_tool_result("ast_vulnerability_check", result)


def _guard_tool_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "exit_code": 0 if result.get("ok") else 2,
        "stdout": str(result.get("finding_count", 0)),
        "stderr": "" if result.get("ok") else str(result.get("findings", [])),
        "evidence": result.get("evidence"),
        "trigger": result.get("trigger"),
    }


def _compress_tokens(arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    active_context = _argument_value(arguments, "active_context", {})
    result = summarize_active_context(active_context if isinstance(active_context, dict) else {}, audit_log_path=audit_log_path)
    return {
        "tool": "compress_tokens",
        "exit_code": 0 if result.get("ok") else 1,
        "stdout": str(result.get("markdown", "")),
        "stderr": str(result.get("error", "")),
        "evidence": result.get("evidence"),
    }


def _archive_markdown_tool(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    markdown = str(_argument_value(arguments, "markdown", ""))
    result = archive_markdown(markdown, memory_dir=root / ".oneword" / "memory", audit_log_path=audit_log_path)
    return {
        "tool": "write_markdown_doc",
        "exit_code": 0 if result.get("ok") else 1,
        "stdout": str(result.get("path", "")),
        "stderr": str(result.get("error", "")),
        "evidence": result.get("evidence"),
    }


def _prompt_tool(root: Path, arguments: Any, audit_log_path: str | Path | None) -> dict[str, Any]:
    prompt = _argument_value(arguments, "prompt", {})
    active_context = prompt if isinstance(prompt, dict) else {"prompt": str(prompt)}
    result = create_confirmation_ticket(active_context, ticket_dir=root / ".oneword" / "tickets", audit_log_path=audit_log_path)
    return {
        "tool": "send_user_message",
        "exit_code": 0 if result.get("needs_human") else 1,
        "stdout": str(result.get("path", "")),
        "stderr": str(result.get("error", "")),
        "evidence": result.get("evidence"),
    }


def _blocked_side_effect_tool(tool_name: str) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "exit_code": 126,
        "stdout": "",
        "stderr": f"registered tool requires explicit system workflow and is not directly executable: {tool_name}",
    }


def _run_command_tool(
    tool_name: str,
    root: Path,
    arguments: Any,
    audit_log_path: str | Path | None,
) -> dict[str, Any]:
    command = _command_from_arguments(arguments, _default_command_for(tool_name))
    result = execute_command(
        command,
        cwd=root,
        workspace_root=root,
        audit_log_path=audit_log_path,
        timeout_seconds=int(_argument_value(arguments, "timeout_seconds", 120)),
    )
    payload = {
        "tool": tool_name,
        "exit_code": result["exit_code"],
        "stdout": _tail_text(result["stdout"], 1200),
        "stderr": _tail_text(result["stderr"], 1200),
        "evidence": result["evidence"],
        "sandbox": result["sandbox"],
    }
    if tool_name == "run_pytest" and int(result["exit_code"]) != 0:
        payload["failure_summary"] = summarize_pytest_output(
            f"{result['stdout']}\n{result['stderr']}",
            max_chars=900,
        )
    return payload


def _default_command_for(tool_name: str) -> list[str]:
    if tool_name == "run_npm_test":
        return ["npm", "test"]
    if tool_name == "git_diff":
        return ["git", "diff", "--"]
    return ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]


def _tail_text(value: Any, max_chars: int) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _command_from_arguments(arguments: Any, default: list[str]) -> list[str]:
    raw = _argument_value(arguments, "command", None)
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str) and raw.strip():
        return raw.split()
    return default


def _argument_value(arguments: Any, key: str, default: Any) -> Any:
    if isinstance(arguments, dict):
        return arguments.get(key, default)
    return default


def _resolve_workspace_path(root: Path, raw_path: str) -> Path:
    candidate = (root / raw_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise OSError(f"path escapes workspace: {raw_path}")
    return candidate
