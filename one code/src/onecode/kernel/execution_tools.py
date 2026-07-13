from dataclasses import dataclass
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from onecode.kernel.path_guard import PathGuard


COMMAND_ENV_ALLOWLIST = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "TERM",
        "SHELL",
        "USER",
        "LOGNAME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "SYSTEMROOT",
    }
)
SENSITIVE_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "AUTH", "CREDENTIAL")
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|passwd|authorization|credential)\b(\s*[:=]\s*)([^\s,;]+)"
)
MAX_DIRECTORY_SCAN_ENTRIES = 10_000


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
        candidates, truncated = _collect_bounded_files(
            target,
            root,
            max_depth=action["max_depth"],
            max_files=action["max_entries"],
        )
        files = [str(candidate.relative_to(root)) for candidate in candidates]
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
        if regex:
            raise ValueError("search_text supports literal queries only")
        query = _required_string(params, "query")
        if len(query) > 2_000:
            raise ValueError("query must not exceed 2000 characters")
        return {
            "action_type": self.name,
            "query": query,
            "path": params.get("path", "."),
            "max_matches": _bounded_int(params.get("max_matches", 200), "max_matches", 1, 5_000),
            "max_depth": _bounded_int(params.get("max_depth", 8), "max_depth", 0, 20),
            "max_files": _bounded_int(params.get("max_files", 200), "max_files", 1, 1_000),
            "max_file_bytes": _bounded_int(
                params.get("max_file_bytes", 200_000), "max_file_bytes", 1, 1_000_000
            ),
            "max_total_bytes": _bounded_int(
                params.get("max_total_bytes", 20_000_000), "max_total_bytes", 1, 50_000_000
            ),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        target = PathGuard.resolve_read_target(workspace, _required_string(action, "path"))
        root = workspace.resolve()
        candidates, truncated = _collect_bounded_files(
            target,
            root,
            max_depth=action["max_depth"],
            max_files=action["max_files"],
        )
        matches = []
        scanned_file_count = 0
        scanned_bytes = 0
        match_limit_reached = False
        for candidate in candidates:
            remaining_bytes = action["max_total_bytes"] - scanned_bytes
            if remaining_bytes <= 0:
                truncated = True
                break
            read_limit = min(action["max_file_bytes"], remaining_bytes)
            try:
                with candidate.open("rb") as handle:
                    raw = handle.read(read_limit + 1)
            except (UnicodeDecodeError, OSError):
                continue
            scanned_file_count += 1
            scanned_bytes += min(len(raw), read_limit)
            if len(raw) > read_limit:
                truncated = True
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if action["query"] not in line:
                    continue
                if len(matches) >= action["max_matches"]:
                    truncated = True
                    match_limit_reached = True
                    break
                matches.append(
                    {
                        "path": str(candidate.relative_to(root)),
                        "line": line_number,
                        "text": line[:500],
                    }
                )
            if match_limit_reached:
                break
        return {
            "query": action["query"],
            "matches": matches,
            "scanned_file_count": scanned_file_count,
            "scanned_bytes": scanned_bytes,
            "truncated": truncated,
        }


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
        environment = _command_environment()
        environment.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_OPTIONAL_LOCKS": "0",
            }
        )
        completed = subprocess.run(
            [
                "git",
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "status",
                "--short",
                "--untracked-files=normal",
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=environment,
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
        sensitive_values = _sensitive_environment_values()
        completed = subprocess.run(
            action["argv"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=action["timeout_seconds"],
            check=False,
            shell=False,
            env=_command_environment(),
        )
        stdout = redact_sensitive_text(completed.stdout, sensitive_values=sensitive_values)
        stderr = redact_sensitive_text(completed.stderr, sensitive_values=sensitive_values)
        return {
            "argv": [redact_sensitive_text(item, sensitive_values=sensitive_values) for item in action["argv"]],
            "returncode": completed.returncode,
            "stdout": stdout[-100_000:],
            "stderr": stderr[-100_000:],
            "truncated": len(stdout) > 100_000 or len(stderr) > 100_000,
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


def _collect_bounded_files(
    target: Path,
    root: Path,
    *,
    max_depth: int,
    max_files: int,
) -> tuple[list[Path], bool]:
    if target.is_symlink():
        return [], True
    if target.is_file():
        return [target], False

    files: list[Path] = []
    directories: list[tuple[Path, int]] = [(target, 0)]
    scanned_entries = 0
    while directories:
        directory, directory_depth = directories.pop(0)
        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    scanned_entries += 1
                    if scanned_entries > MAX_DIRECTORY_SCAN_ENTRIES:
                        return files, True
                    entries.append(entry)
        except OSError:
            continue
        for entry in sorted(entries, key=lambda item: item.name):
            candidate = Path(entry.path)
            relative = candidate.relative_to(root)
            if entry.is_symlink() or PathGuard.is_sensitive_read_path(relative):
                continue
            candidate_depth = directory_depth + 1
            try:
                if entry.is_file(follow_symlinks=False):
                    if candidate_depth > max_depth:
                        continue
                    if len(files) >= max_files:
                        return files, True
                    files.append(candidate)
                elif entry.is_dir(follow_symlinks=False) and candidate_depth < max_depth:
                    directories.append((candidate, candidate_depth))
            except OSError:
                continue
    return files, False


def _command_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key in COMMAND_ENV_ALLOWLIST}
    environment.setdefault("PATH", os.defpath)
    return environment


def _sensitive_environment_values() -> tuple[str, ...]:
    values = {
        value
        for key, value in os.environ.items()
        if value and len(value) >= 4 and any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS)
    }
    return tuple(sorted(values, key=len, reverse=True))


def redact_sensitive_text(text: str, *, sensitive_values: tuple[str, ...] | None = None) -> str:
    redacted = text
    for value in sensitive_values if sensitive_values is not None else _sensitive_environment_values():
        redacted = redacted.replace(value, "[REDACTED]")
    return SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", redacted)
