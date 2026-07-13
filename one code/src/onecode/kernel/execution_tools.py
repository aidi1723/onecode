from dataclasses import dataclass
import re
import subprocess
from pathlib import Path
from typing import Any

from onecode.kernel.path_guard import PathGuard


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    requires_approval: bool
    runner_managed: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class WriteTextTool(ToolDefinition):
    name: str = "write_text"
    requires_approval: bool = True
    runner_managed: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        action = {
            "action_type": "write_text",
            "path": params.get("path", ""),
            "content": params.get("content", ""),
        }
        if "status_code" in params:
            action["status_code"] = params["status_code"]
        return action


@dataclass(frozen=True)
class PatchTextTool(ToolDefinition):
    name: str = "patch_text"
    requires_approval: bool = True
    runner_managed: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        action = {
            "action_type": "patch_text",
            "path": params.get("path", ""),
            "search_block": params.get("search_block", ""),
            "replace_block": params.get("replace_block", ""),
        }
        if "status_code" in params:
            action["status_code"] = params["status_code"]
        return action


@dataclass(frozen=True)
class ReadTextTool(ToolDefinition):
    name: str = "read_text"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_type": self.name,
            "path": _required_string(params, "path"),
            "max_bytes": _bounded_int(params.get("max_bytes", 200_000), "max_bytes", 1, 1_000_000),
            "max_lines": _bounded_int(params.get("max_lines", 400), "max_lines", 1, 10_000),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        target = PathGuard.resolve_read_target(workspace, action["path"])
        if not target.is_file():
            raise ValueError("read_target_not_file")
        raw = target.read_bytes()
        byte_truncated = len(raw) > action["max_bytes"]
        text = raw[: action["max_bytes"]].decode("utf-8")
        lines = text.splitlines(keepends=True)
        line_truncated = len(lines) > action["max_lines"]
        content = "".join(lines[: action["max_lines"]])
        return {
            "path": str(target.relative_to(workspace.resolve())),
            "content": content,
            "byte_count": len(content.encode("utf-8")),
            "line_count": min(len(lines), action["max_lines"]),
            "truncated": byte_truncated or line_truncated,
        }


@dataclass(frozen=True)
class ListFilesTool(ToolDefinition):
    name: str = "list_files"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_type": self.name,
            "path": params.get("path", "."),
            "max_entries": _bounded_int(params.get("max_entries", 200), "max_entries", 1, 5_000),
            "max_depth": _bounded_int(params.get("max_depth", 4), "max_depth", 0, 20),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        target = PathGuard.resolve_read_target(workspace, _required_string(action, "path"))
        if not target.exists():
            raise ValueError("list_target_not_found")
        root = workspace.resolve()
        candidates = [target] if target.is_file() else sorted(target.rglob("*"), key=lambda path: str(path))
        files = []
        truncated = False
        for candidate in candidates:
            relative = candidate.relative_to(root)
            if PathGuard.is_sensitive_read_path(relative) or len(relative.parts) - len(
                target.relative_to(root).parts
            ) > action["max_depth"]:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if len(files) >= action["max_entries"]:
                truncated = True
                break
            files.append(str(relative))
        return {"path": str(target.relative_to(root)), "files": files, "truncated": truncated}


@dataclass(frozen=True)
class SearchTextTool(ToolDefinition):
    name: str = "search_text"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        regex = params.get("regex", False)
        if not isinstance(regex, bool):
            raise ValueError("regex must be boolean")
        return {
            "action_type": self.name,
            "query": _required_string(params, "query"),
            "path": params.get("path", "."),
            "regex": regex,
            "max_matches": _bounded_int(params.get("max_matches", 200), "max_matches", 1, 5_000),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        target = PathGuard.resolve_read_target(workspace, _required_string(action, "path"))
        pattern = re.compile(action["query"] if action["regex"] else re.escape(action["query"]))
        root = workspace.resolve()
        candidates = [target] if target.is_file() else sorted(target.rglob("*"), key=lambda path: str(path))
        matches = []
        truncated = False
        for candidate in candidates:
            if (
                not candidate.is_file()
                or candidate.is_symlink()
                or PathGuard.is_sensitive_read_path(candidate.relative_to(root))
            ):
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line) is None:
                    continue
                if len(matches) >= action["max_matches"]:
                    truncated = True
                    break
                matches.append(
                    {
                        "path": str(candidate.relative_to(root)),
                        "line": line_number,
                        "text": line[:500],
                    }
                )
            if truncated:
                break
        return {"query": action["query"], "matches": matches, "truncated": truncated}


@dataclass(frozen=True)
class GitStatusTool(ToolDefinition):
    name: str = "git_status"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        if params:
            raise ValueError("git_status does not accept parameters")
        return {"action_type": self.name}

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        self.plan_action(params)
        completed = subprocess.run(
            ["git", "status", "--short", "--untracked-files=normal"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            raise ValueError("git_status_failed")
        lines = completed.stdout.splitlines()[:1_000]
        return {"entries": lines, "truncated": len(completed.stdout.splitlines()) > len(lines)}


@dataclass(frozen=True)
class RunCommandTool(ToolDefinition):
    name: str = "run_command"
    requires_approval: bool = True
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        argv = params.get("argv")
        if not isinstance(argv, list) or not argv or len(argv) > 64:
            raise ValueError("argv must be a non-empty bounded string list")
        if not all(isinstance(item, str) and item and len(item) <= 4_096 for item in argv):
            raise ValueError("argv must be a non-empty bounded string list")
        return {
            "action_type": self.name,
            "argv": list(argv),
            "timeout_seconds": _bounded_int(params.get("timeout_seconds", 60), "timeout_seconds", 1, 600),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        completed = subprocess.run(
            action["argv"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=action["timeout_seconds"],
            check=False,
            shell=False,
        )
        return {
            "argv": action["argv"],
            "returncode": completed.returncode,
            "stdout": completed.stdout[-100_000:],
            "stderr": completed.stderr[-100_000:],
            "truncated": len(completed.stdout) > 100_000 or len(completed.stderr) > 100_000,
        }


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            WriteTextTool(),
            PatchTextTool(),
            ReadTextTool(),
            ListFilesTool(),
            SearchTextTool(),
            GitStatusTool(),
            RunCommandTool(),
        ]
    )


def _required_string(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value
