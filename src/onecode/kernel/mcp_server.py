"""Stdio MCP server for OneCode ledger, sandbox, verifier, diagnostics, and symbol locator tools.

Launch with ``python -m onecode.kernel.mcp_server`` or ``onecode mcp``. The process speaks
newline-delimited JSON-RPC 2.0.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from onecode import __version__

PROTOCOL_VERSION = "2024-11-05"
_TOOLS = (
    {
        "name": "onecode_ledger",
        "description": "List OneCode run ledger summaries for a workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
            "required": ["workspace"],
        },
    },
    {
        "name": "onecode_sandbox",
        "description": "Run the bounded OneCode sandbox smoke check. It does not accept a caller command.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
            "required": ["workspace"],
        },
    },
    {
        "name": "onecode_verify",
        "description": "Run the workspace unittest suite through the OneCode verifier.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
            "required": ["workspace"],
        },
    },
    {
        "name": "onecode_doctor",
        "description": "Run OneCode environment diagnostics, docker sandbox readiness, and deployment boundary checks.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "onecode_locate",
        "description": "Locate failure root-cause source symbols in a workspace from an error traceback or test output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "traceback": {"type": "string"},
                "max_candidates": {"type": "integer"},
            },
            "required": ["workspace", "traceback"],
        },
    },
    {
        "name": "onecode_audit",
        "description": "Verify integrity of the OneCode WAL ledger, evidence chain, and run manifests.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
            "required": ["workspace"],
        },
    },
)


def handle_mcp_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Answer one JSON-RPC message. Notifications return None."""
    if "id" not in message:
        return None
    request_id = message.get("id")
    method = message.get("method")
    raw_params = message.get("params")
    params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
    if method == "initialize":
        return _result(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "onecode", "version": __version__},
        })
    if method == "tools/list":
        return _result(request_id, {"tools": list(_TOOLS)})
    if method == "tools/call":
        return _result(request_id, _call_tool(params))
    return _error(request_id, -32601, "method not found")


def serve_stdio(stdin: Any = None, stdout: Any = None) -> None:
    reader = stdin if stdin is not None else sys.stdin
    writer = stdout if stdout is not None else sys.stdout
    for line in reader:
        if not str(line).strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            writer.write(json.dumps(_error(None, -32700, "parse error"), separators=(",", ":")) + "\n")
            writer.flush()
            continue
        if not isinstance(message, dict):
            continue
        response = handle_mcp_message(message)
        if response is None:
            continue
        writer.write(json.dumps(response, separators=(",", ":")) + "\n")
        writer.flush()


def _call_tool(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    raw_args = params.get("arguments")
    arguments: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}

    if name == "onecode_doctor":
        return _text(_doctor())

    try:
        workspace = _workspace(arguments.get("workspace"))
    except ValueError as exc:
        return _text({"status": "failed", "reason": str(exc)}, is_error=True)

    if name == "onecode_ledger":
        return _text(_ledger(workspace))
    if name == "onecode_sandbox":
        return _text(_sandbox(workspace))
    if name == "onecode_verify":
        return _text(_verify(workspace))
    if name == "onecode_locate":
        tb = str(arguments.get("traceback") or "")
        mc = int(arguments.get("max_candidates") or 5)
        return _text(_locate(workspace, tb, max_candidates=mc))
    if name == "onecode_audit":
        return _text(_audit(workspace))
    return _text({"status": "failed", "reason": "unknown_tool"}, is_error=True)


def _workspace(value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("workspace is required")
    workspace = Path(value).expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing directory")
    return workspace


def _ledger(workspace: Path) -> dict[str, Any]:
    from onecode.kernel.run_inspection import list_runs

    payload = list_runs(workspace)
    runs = payload.get("runs") if isinstance(payload, dict) else []
    summaries = []
    for run in runs if isinstance(runs, list) else []:
        if not isinstance(run, dict):
            continue
        summaries.append({
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "reason": run.get("reason"),
            "host_reward": run.get("host_reward"),
        })
    return {"status": "completed", "workspace": str(workspace), "runs": summaries}


def _sandbox(workspace: Path) -> dict[str, Any]:
    from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

    result = run_sandbox_smoke(SandboxConfig(workspace=workspace))
    return {"status": result.get("status"), "reason": result.get("reason"), "workspace": str(workspace)}


def _verify(workspace: Path) -> dict[str, Any]:
    if not (workspace / "tests").is_dir():
        return {"status": "skipped", "reason": "tests_absent", "workspace": str(workspace)}
    from onecode.kernel.sandbox import SandboxConfig
    from onecode.kernel.verifier import VerifierSpec, run_verifier

    checked = run_verifier(
        workspace,
        VerifierSpec(
            id="python-unittest",
            command=["python3", "-m", "unittest", "discover", "-s", "tests"],
            cwd=".",
            timeout_ms=60_000,
        ),
        sandbox_config=SandboxConfig(workspace=workspace, timeout_seconds=60),
    )
    return {"status": checked.status, "reason": checked.reason, "workspace": str(workspace)}


def _doctor() -> dict[str, Any]:
    from onecode.kernel.diagnostics import run_doctor
    return run_doctor()


def _locate(workspace: Path, traceback_text: str, max_candidates: int = 5) -> dict[str, Any]:
    if not traceback_text.strip():
        return {"status": "failed", "reason": "traceback_required", "workspace": str(workspace)}
    from onecode.kernel.symbol_locator import SymbolLocator
    locator = SymbolLocator(workspace)
    locations = locator.locate_fault(traceback_text, max_candidates=max_candidates)
    return {
        "status": "completed",
        "workspace": str(workspace),
        "candidate_count": len(locations),
        "candidates": [loc.to_dict() for loc in locations],
    }


def _audit(workspace: Path) -> dict[str, Any]:
    from onecode.kernel.wal import global_wal_evidence_metrics, read_validated_global_wal_entries
    try:
        entries = read_validated_global_wal_entries(workspace)
        metrics = global_wal_evidence_metrics(workspace)
        return {
            "status": "completed",
            "workspace": str(workspace),
            "validated_entry_count": len(entries),
            "tamper_detected": False,
            "evidence_metrics": metrics,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "reason": "wal_integrity_compromised",
            "detail": str(exc),
            "workspace": str(workspace),
        }


def generate_mcp_client_config(target: str = "claude", python_bin: str = "python3") -> dict[str, Any]:
    """Generate configuration dict for Claude Code / Desktop, Cursor, or Goose."""
    target_norm = target.strip().lower()
    if target_norm in {"goose"}:
        return {
            "extensions": {
                "onecode": {
                    "cmd": python_bin,
                    "args": ["-m", "onecode.kernel.mcp_server"],
                    "type": "stdio",
                }
            }
        }
    # Default format for Claude Desktop, Claude Code, Cursor, and VS Code
    return {
        "mcpServers": {
            "onecode": {
                "command": python_bin,
                "args": ["-m", "onecode.kernel.mcp_server"],
            }
        }
    }


def _text(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "isError": is_error,
    }


def _result(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> int:
    serve_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
