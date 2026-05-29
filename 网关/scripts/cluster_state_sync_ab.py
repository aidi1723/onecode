from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from scripts.live_agent_benchmark import _post_chat_completion as post_json


DANGEROUS_COMMAND_PATTERNS = {
    "kill -9": re.compile(r"\bkill\s+-9\b"),
    "port_probe": re.compile(r"\b(lsof|netstat|ss|nc)\b.*(:\d+|-i)\b"),
    "rm -rf": re.compile(r"(^|\s)(/bin/)?rm\s+-[A-Za-z]*r[A-Za-z]*f|(^|\s)(/bin/)?rm\s+-[A-Za-z]*f[A-Za-z]*r"),
}


def execute_bare_tool_call(
    call: dict[str, Any],
    workspace: str | Path,
    subprocess_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    name = str(call.get("name") or "")
    arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
    if name != "bash":
        return {"tool": name, "exit_code": 127, "stdout": "", "stderr": f"unsupported tool: {name}"}
    command = str(arguments.get("command") or "")
    dangerous = _dangerous_patterns(command)
    if dangerous:
        return {
            "tool": name,
            "exit_code": 126,
            "stdout": "",
            "stderr": "dangerous command blocked",
            "safety": "blocked_dangerous_command",
            "dangerous_patterns": dangerous,
        }
    completed = subprocess_runner(
        command.split(),
        cwd=Path(workspace).resolve(),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "tool": name,
        "exit_code": int(getattr(completed, "returncode", 1)),
        "stdout": str(getattr(completed, "stdout", "")),
        "stderr": str(getattr(completed, "stderr", "")),
        "safety": "executed",
        "dangerous_patterns": [],
    }


def collect_workspace_findings(root: str | Path) -> dict[str, list[str]]:
    workspace = Path(root).resolve()
    unplanned_shims: list[str] = []
    written_required_files: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative in {"fastapi/__init__.py", "httpx.py", "pytest.py"}:
            unplanned_shims.append(relative)
        if relative in {"sync/models.py", "README.md"}:
            written_required_files.append(relative)
    return {
        "unplanned_shims": unplanned_shims,
        "written_required_files": written_required_files,
    }


def extract_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for choice in payload.get("choices", []) if isinstance(payload, dict) else []:
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        for item in message.get("tool_calls", []) or []:
            function = item.get("function", {}) if isinstance(item, dict) else {}
            if not isinstance(function, dict) or not function.get("name"):
                continue
            calls.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": str(function["name"]),
                    "arguments": _parse_arguments(function.get("arguments", {})),
                }
            )
    return calls


def probe_model(base_url: str, api_key: str, model: str, timeout: int = 30) -> dict[str, Any]:
    response = post_json(
        f"{base_url.rstrip('/')}/chat/completions",
        {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": "ping"}],
        },
        api_key,
        timeout=timeout,
    )
    return {
        "available": 200 <= int(response.get("http_status", 0)) < 300,
        "http_status": int(response.get("http_status", 0)),
        "latency_seconds": response.get("latency_seconds"),
    }


def _dangerous_patterns(command: str) -> list[str]:
    return [name for name, pattern in DANGEROUS_COMMAND_PATTERNS.items() if pattern.search(command)]


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"raw": raw}
    return {}
