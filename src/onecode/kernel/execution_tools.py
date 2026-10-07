from dataclasses import dataclass
import json
import os
import re
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from onecode.kernel.path_guard import PathGuard


_NESTED_REPEAT = re.compile(r"\([^)]*[+*][^)]*\)[+*{]")


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
    r"(?i)\b(api[_-]?key|key|token|secret|password|passwd|authorization|credential)\b(\s*[:=]\s*)([^\s,;]+)"
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
        _reject_unknown_params(params, {"path", "content", "status_code"})
        action = {
            "action_type": "write_text",
            "path": _required_string(params, "path"),
            "content": _string_value(params, "content"),
        }
        if "status_code" in params:
            action["status_code"] = _status_code(params["status_code"])  # type: ignore
        return action


@dataclass(frozen=True)
class PatchTextTool(ToolDefinition):
    name: str = "patch_text"
    requires_approval: bool = True
    runner_managed: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"path", "search_block", "replace_block", "status_code"})
        action = {
            "action_type": "patch_text",
            "path": _required_string(params, "path"),
            "search_block": _required_string(params, "search_block"),
            "replace_block": _string_value(params, "replace_block"),
        }
        if "status_code" in params:
            action["status_code"] = _status_code(params["status_code"])  # type: ignore
        return action

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        from onecode.kernel.patching import PatchIntent, commit_patch

        action = self.plan_action(params)
        result = commit_patch(
            workspace,
            PatchIntent(path=action["path"], search_block=action["search_block"], replace_block=action["replace_block"]),
        )
        if result.get("reason") in {"patch_search_not_found", "patch_search_ambiguous"}:
            return {**result, "reason": "patch_mismatch"}
        return result


@dataclass(frozen=True)
class ReadTextTool(ToolDefinition):
    name: str = "read_text"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"path", "max_bytes", "max_lines"})
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
        with target.open("rb") as handle:
            raw = handle.read(action["max_bytes"] + 1)
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
        _reject_unknown_params(params, {"path", "max_entries", "max_depth"})
        return {
            "action_type": self.name,
            "path": _optional_path(params),
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
        _reject_unknown_params(
            params,
            {
                "query",
                "path",
                "regex",
                "max_matches",
                "max_depth",
                "max_files",
                "max_file_bytes",
                "max_total_bytes",
            },
        )
        regex = params.get("regex", False)
        if not isinstance(regex, bool):
            raise ValueError("regex must be boolean")
        query = _required_string(params, "query")
        if len(query) > 2_000:
            raise ValueError("query must not exceed 2000 characters")
        if regex and _NESTED_REPEAT.search(query):
            raise ValueError("regex pattern is too expensive")
        if regex:
            try:
                re.compile(query)
            except re.error as exc:
                raise ValueError("regex pattern is invalid") from exc
        return {
            "action_type": self.name,
            "query": query,
            "regex": regex,
            "path": _optional_path(params),
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
        matches = []  # type: ignore
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
                matched = _line_matches(line, action["query"], action["regex"])
                if not matched:
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
        result = {
            "query": action["query"],
            "matches": matches,
            "scanned_file_count": scanned_file_count,
            "scanned_bytes": scanned_bytes,
            "truncated": truncated,
        }
        if not matches and not truncated:
            result["status"] = "completed"
            result["reason"] = "search_miss"
        return result


@dataclass(frozen=True)
class GlobFilesTool(ToolDefinition):
    name: str = "glob_files"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"pattern", "path", "max_matches"})
        pattern = _required_string(params, "pattern")
        if pattern.startswith("/") or ".." in Path(pattern).parts:
            raise ValueError("pattern must stay inside the workspace")
        return {
            "action_type": self.name,
            "pattern": pattern,
            "path": _optional_path(params),
            "max_matches": _bounded_int(params.get("max_matches", 200), "max_matches", 1, 5_000),
        }

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        from onecode.kernel.code_index import glob_workspace

        action = self.plan_action(params)
        start = PathGuard.resolve_read_target(workspace, action["path"])
        return glob_workspace(workspace, action["pattern"], start=start, max_matches=action["max_matches"])


@dataclass(frozen=True)
class OutlineTool(ToolDefinition):
    name: str = "outline"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"path"})
        return {"action_type": self.name, "path": _required_string(params, "path")}

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        from onecode.kernel.code_index import outline_python

        action = self.plan_action(params)
        return outline_python(workspace, action["path"])


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
        completed = _run_git(
            workspace,
            ["status", "--short", "--untracked-files=normal"],
        )
        if completed.returncode != 0:
            raise ValueError("git_status_failed")
        lines = completed.stdout.splitlines()[:1_000]
        return {"entries": lines, "truncated": len(completed.stdout.splitlines()) > len(lines)}


@dataclass(frozen=True)
class GitDiffTool(ToolDefinition):
    name: str = "git_diff"
    requires_approval: bool = False
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        if params:
            raise ValueError("git_diff does not accept parameters")
        return {"action_type": self.name}

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        self.plan_action(params)
        parts: list[str] = []
        for args in (["diff", "--no-ext-diff"], ["diff", "--cached", "--no-ext-diff"]):
            completed = _run_git(workspace, args)
            if completed.returncode != 0:
                return {"status": "halted", "reason": "action_exception", "diff": ""}
            if completed.stdout:
                parts.append(completed.stdout)
        diff = "".join(parts)
        return {"status": "completed", "diff": diff[-100_000:], "truncated": len(diff) > 100_000}


@dataclass(frozen=True)
class GitCommitTool(ToolDefinition):
    name: str = "git_commit"
    requires_approval: bool = True
    runner_managed: bool = False

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"message", "paths"})
        message = _required_string(params, "message")
        if len(message) > 500:
            raise ValueError("message is too long")
        paths = params.get("paths")
        if not isinstance(paths, list) or not paths or len(paths) > 64:
            raise ValueError("paths must be a non-empty bounded string list")
        if not all(isinstance(item, str) and item and len(item) <= 4_096 for item in paths):
            raise ValueError("paths must be a non-empty bounded string list")
        return {"action_type": self.name, "message": message, "paths": list(paths)}

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        relative_paths = [_workspace_relative(workspace, path) for path in action["paths"]]
        added = _run_git(workspace, ["add", "--", *relative_paths])
        if added.returncode != 0:
            return {"status": "halted", "reason": "action_exception"}
        committed = _run_git(
            workspace,
            ["commit", "--no-verify", "-m", action["message"], "--", *relative_paths],
        )
        if committed.returncode != 0:
            return {"status": "halted", "reason": "action_exception"}
        return {"status": "completed", "stdout": (committed.stdout or "")[-4_000:]}


_DOCKER_READY: bool | None = None


def _docker_daemon_ready() -> bool:
    global _DOCKER_READY
    if _DOCKER_READY is not None:
        return _DOCKER_READY
    if shutil.which("docker") is None:
        _DOCKER_READY = False
        return False
    try:
        probe = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        _DOCKER_READY = False
        return False
    _DOCKER_READY = probe.returncode == 0
    return _DOCKER_READY


def _run_command(
    argv: list[str],
    workspace: Path,
    timeout_seconds: int,
    on_output: Any | None = None,
) -> tuple[int, str, str]:
    mode = os.environ.get("ONECODE_RUN_COMMAND_SANDBOX", "auto").strip().lower()
    use_docker = mode in {"docker", "on", "true", "1"} or (mode not in {"host", "off", "false", "0"} and _docker_daemon_ready())
    if use_docker:
        from onecode.kernel.sandbox import SandboxConfig, run_in_reused_sandbox

        try:
            completed = run_in_reused_sandbox(
                SandboxConfig(workspace=workspace, timeout_seconds=timeout_seconds),
                argv,
            )
        except subprocess.TimeoutExpired:
            raise
        except (OSError, ValueError):
            if mode in {"docker", "on", "true", "1"}:
                raise
        else:
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            daemon_down = "cannot connect to the docker daemon" in stderr.lower()
            if mode in {"docker", "on", "true", "1"} or not daemon_down:
                if on_output is not None and stdout:
                    on_output(stdout)
                return completed.returncode, stdout, stderr
    if on_output is None:
        completed = subprocess.run(
            argv,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env=_command_environment(),
        )
        return completed.returncode, completed.stdout, completed.stderr
    return _stream_host_command(argv, workspace, timeout_seconds, on_output)


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
        _reject_unknown_params(params, {"argv", "timeout_seconds"})
        return {
            "action_type": self.name,
            "argv": list(argv),
            "timeout_seconds": _bounded_int(params.get("timeout_seconds", 60), "timeout_seconds", 1, 600),
        }

    def execute(self, params: dict[str, Any], workspace: Path, on_output: Any | None = None) -> dict[str, Any]:
        action = self.plan_action(params)
        sensitive_values = _sensitive_environment_values()
        argv = [redact_sensitive_text(item, sensitive_values=sensitive_values) for item in action["argv"]]

        def emit(chunk: str) -> None:
            if on_output is not None:
                on_output(redact_sensitive_text(chunk, sensitive_values=sensitive_values))

        try:
            returncode, stdout, stderr = _run_command(
                action["argv"],
                workspace,
                action["timeout_seconds"],
                on_output=emit if on_output is not None else None,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "halted",
                "reason": "http_timeout",
                "argv": argv,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "truncated": False,
            }
        stdout = redact_sensitive_text(stdout, sensitive_values=sensitive_values)
        stderr = redact_sensitive_text(stderr, sensitive_values=sensitive_values)
        return {
            "argv": argv,
            "returncode": returncode,
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


def tool_requires_approval(tool_name: str) -> bool:
    if tool_name.startswith("mcp."):
        server, dot, remote = tool_name.removeprefix("mcp.").partition(".")
        return bool(dot) and _mcp_name_segment(server) and _mcp_name_segment(remote)
    tool = default_tool_registry().get(tool_name)
    return tool is not None and tool.requires_approval


def _mcp_name_segment(value: str) -> bool:
    return bool(value) and len(value) <= 64 and value.replace("-", "").replace("_", "").isalnum()


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            WriteTextTool(),
            PatchTextTool(),
            ReadTextTool(),
            ListFilesTool(),
            SearchTextTool(),
            GlobFilesTool(),
            OutlineTool(),
            GitStatusTool(),
            GitDiffTool(),
            GitCommitTool(),
            RunCommandTool(),
        ]
    )


def _line_matches(line: str, query: str, regex: bool) -> bool:
    if not regex:
        return query in line
    return re.search(query, line) is not None


def _required_string(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _string_value(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_path(params: dict[str, Any]) -> str:
    value = params.get("path", ".")
    if not isinstance(value, str) or not value:
        raise ValueError("path must be a non-empty string")
    return value


def _status_code(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 63:
        raise ValueError("status_code must be between 0 and 63")
    return value


def _reject_unknown_params(params: dict[str, Any], allowed: set[str]) -> None:
    unknown = set(params) - allowed
    if unknown:
        rejected = ", ".join(sorted(unknown))
        accepted = ", ".join(sorted(allowed))
        raise ValueError(f"unknown tool parameters: {rejected}. accepted parameters: {accepted}")


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
            if entry.is_symlink() or PathGuard.is_sensitive_read_path(relative) or ".onecode" in relative.parts:
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


def _workspace_relative(workspace: Path, relative_path: str) -> str:
    target = PathGuard.resolve_target(workspace, relative_path)
    return target.relative_to(workspace.resolve()).as_posix()


def _git_environment() -> dict[str, str]:
    environment = _command_environment()
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return environment


def _git_argv(args: list[str]) -> list[str]:
    return [
        "git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        *args,
    ]


def _run_git(workspace: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _git_argv(args),
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=_git_environment(),
    )


def _stream_host_command(
    argv: list[str],
    workspace: Path,
    timeout_seconds: int,
    on_output: Any,
) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        argv,
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_command_environment(),
        shell=False,
    )
    chunks: list[str] = []
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    try:
        if proc.stdout is None:
            raise RuntimeError("command stdout was not captured")
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            ready, _, _ = select.select([proc.stdout], [], [], remaining)
            if not ready:
                timed_out = True
                break
            chunk = os.read(proc.stdout.fileno(), 4096)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            chunks.append(text)
            on_output(text)
        if timed_out:
            raise subprocess.TimeoutExpired(argv, timeout_seconds)
        return proc.wait(timeout=5), "".join(chunks), ""
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        if proc.stdout is not None:
            proc.stdout.close()


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
    try:
        from onecode.kernel.model_config import read_model_config

        stored_key = read_model_config(include_secret=True).get("api_key")
    except (OSError, ValueError, json.JSONDecodeError):
        stored_key = ""
    if isinstance(stored_key, str) and len(stored_key) >= 4:
        values.add(stored_key)
    return tuple(sorted(values, key=len, reverse=True))


def redact_sensitive_text(text: str, *, sensitive_values: tuple[str, ...] | None = None) -> str:
    redacted = text
    for value in sensitive_values if sensitive_values is not None else _sensitive_environment_values():
        redacted = redacted.replace(value, "[REDACTED]")
    return SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1\2[REDACTED]", redacted)
