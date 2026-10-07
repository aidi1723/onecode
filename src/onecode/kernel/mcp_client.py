"""Stdio MCP client. Remote tools join the existing registry and require approval."""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.execution_tools import ToolDefinition, ToolRegistry, _command_environment, _reject_unknown_params


class McpClientError(ValueError):
    pass


@dataclass(frozen=True)
class McpProxyTool(ToolDefinition):
    command: tuple[str, ...] = ()
    remote_name: str = ""

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        _reject_unknown_params(params, {"arguments"})
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        return {"action_type": self.name, "arguments": arguments}

    def execute(self, params: dict[str, Any], workspace: Path) -> dict[str, Any]:
        action = self.plan_action(params)
        try:
            with McpStdioClient(list(self.command), cwd=workspace) as client:
                content = client.call_tool(self.remote_name, action["arguments"])
        except (OSError, subprocess.SubprocessError, McpClientError):
            return {"status": "halted", "reason": "action_exception", "content": ""}
        return {"status": "completed", "content": content}


class McpStdioClient:
    def __init__(self, command: list[str], *, cwd: Path | None = None, timeout_seconds: int = 10) -> None:
        if not _valid_command(command):
            raise ValueError("mcp command must be a non-empty string list")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._command = list(command)
        self._cwd = cwd
        self._timeout = timeout_seconds
        self._proc: subprocess.Popen[bytes] | None = None
        self._buffer = b""
        self._next_id = 1

    def __enter__(self) -> McpStdioClient:
        self._proc = subprocess.Popen(
            self._command,
            cwd=self._cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=_command_environment(),
            shell=False,
        )
        try:
            self._request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "onecode", "version": "0.8.0"},
                },
            )
            self._notify("notifications/initialized")
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:  # type: ignore
        self.close()
        return False

    def list_tools(self) -> list[str]:
        result = self._request("tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise McpClientError("tools/list returned no tools")
        names = []
        for item in tools:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return names

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        return _content_text(result)

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        if proc.stdin is not None:
            proc.stdin.close()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        if proc.stdout is not None:
            proc.stdout.close()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self._timeout
        while True:
            message = self._read_message(deadline)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise McpClientError("mcp request failed")
            result = message.get("result")
            if not isinstance(result, dict):
                raise McpClientError("mcp result must be an object")
            return result

    def _notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def _send(self, payload: dict[str, Any]) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise McpClientError("mcp process is not running")
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        try:
            proc.stdin.write(encoded)
            proc.stdin.flush()
        except OSError as exc:
            raise McpClientError("mcp connection closed") from exc

    def _read_message(self, deadline: float) -> dict[str, Any]:
        while True:
            line = self._read_line(deadline)
            if line.strip():
                break
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise McpClientError("mcp response is not json") from exc
        if not isinstance(message, dict):
            raise McpClientError("mcp response must be an object")
        return message

    def _read_line(self, deadline: float) -> bytes:
        proc = self._proc
        if proc is None or proc.stdout is None:
            raise McpClientError("mcp process is not running")
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(self._command, self._timeout)
            ready, _, _ = select.select([proc.stdout], [], [], remaining)
            if not ready:
                raise subprocess.TimeoutExpired(self._command, self._timeout)
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise McpClientError("mcp connection closed")
            self._buffer += chunk
            if len(self._buffer) > 1_000_000:
                raise McpClientError("mcp response is too large")
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line


def register_mcp_tools(
    registry: ToolRegistry,
    *,
    server_name: str,
    command: list[str],
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    if not _safe_segment(server_name) or not _valid_command(command):
        return {"status": "halted", "reason": "malformed_input", "tools": []}
    try:
        with McpStdioClient(command, timeout_seconds=timeout_seconds) as client:
            remote_names = client.list_tools()
    except (OSError, subprocess.SubprocessError, McpClientError, ValueError):
        return {"status": "halted", "reason": "action_exception", "tools": []}
    tools: list[str] = []
    for remote_name in remote_names:
        if not _safe_segment(remote_name):
            continue
        tool_name = f"mcp.{server_name}.{remote_name}"
        registry.register(
            McpProxyTool(
                name=tool_name,
                requires_approval=True,
                runner_managed=False,
                command=tuple(command),
                remote_name=remote_name,
            )
        )
        tools.append(tool_name)
    return {"status": "completed", "tools": tools}


def _content_text(result: dict[str, Any]) -> str:
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    parts = [
        item["text"]
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    return "".join(parts)[:100_000]


def _safe_segment(value: object) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= 64 and value.replace("-", "").replace("_", "").isalnum()


def _valid_command(command: object) -> bool:
    return (
        isinstance(command, list)
        and 0 < len(command) <= 32
        and all(isinstance(item, str) and item and len(item) <= 4_096 for item in command)
    )
