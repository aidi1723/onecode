from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any
from urllib import request as urlrequest

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import http_gateway_smoke


def run_live_smoke(
    host: str = "127.0.0.1",
    port: int = 8765,
    workspace: str | None = None,
    token: str | None = None,
    timeout_seconds: int = 15,
    include_proxy_tool_call: bool = False,
) -> dict[str, Any]:
    if workspace is None:
        with TemporaryDirectory(prefix="oneword-live-smoke-") as tmpdir:
            return _run_live_smoke_with_workspace(
                host=host,
                port=port,
                workspace=tmpdir,
                token=token,
                timeout_seconds=timeout_seconds,
                include_proxy_tool_call=include_proxy_tool_call,
            )
    return _run_live_smoke_with_workspace(
        host=host,
        port=port,
        workspace=workspace,
        token=token,
        timeout_seconds=timeout_seconds,
        include_proxy_tool_call=include_proxy_tool_call,
    )


def _run_live_smoke_with_workspace(
    host: str,
    port: int,
    workspace: str,
    token: str | None,
    timeout_seconds: int,
    include_proxy_tool_call: bool,
) -> dict[str, Any]:
    base_url = f"http://{host}:{port}"
    workspace_path = str(Path(workspace).resolve())
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", "/private/tmp/uv-cache")
    env.setdefault("ONEWORD_WORKSPACE_ROOT", workspace_path)
    env.setdefault("ONEWORD_BUILD_MODE", "1")
    env.setdefault("ONEWORD_UPSTREAM_API_KEY", "live-smoke-upstream-key")
    if token:
        env["ONEWORD_GATEWAY_TOKEN"] = token
    upstream_process: subprocess.Popen[str] | None = None
    upstream_base_url = None
    if include_proxy_tool_call:
        upstream_port = port + 1
        upstream_base_url = f"http://{host}:{upstream_port}/v1"
        upstream_process = _start_mock_upstream(host, upstream_port, workspace_path, env)
        _wait_until_ready(f"http://{host}:{upstream_port}", timeout_seconds=timeout_seconds)
        env["ONEWORD_UPSTREAM_BASE_URL"] = upstream_base_url
        env["ONEWORD_ANTHROPIC_BASE_URL"] = upstream_base_url
        env.setdefault("ONEWORD_ANTHROPIC_API_KEY", "live-smoke-anthropic-key")

    command = [
        "uv",
        "run",
        "--with-requirements",
        "requirements-gateway.txt",
        "python",
        "-m",
        "uvicorn",
        "agent_skill_dictionary.gateway_server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    process = subprocess.Popen(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until_ready(base_url, timeout_seconds=timeout_seconds)
        smoke = http_gateway_smoke.run_smoke(base_url, workspace=workspace_path, token=token)
        proxy_tool_call = (
            _run_proxy_tool_call_smoke(base_url, workspace_path, token=token, include_failure_case=True)
            if include_proxy_tool_call
            else None
        )
        ok = bool(smoke.get("ok")) and (proxy_tool_call is None or bool(proxy_tool_call.get("ok")))
        return {
            "ok": ok,
            "base_url": base_url,
            "gateway_pid": process.pid,
            "workspace": workspace_path,
            "smoke": smoke,
            "proxy_tool_call": proxy_tool_call,
        }
    finally:
        _stop_process(process)
        if upstream_process is not None:
            _stop_process(upstream_process)


def _start_mock_upstream(
    host: str,
    port: int,
    workspace: str,
    env: dict[str, str],
) -> subprocess.Popen[str]:
    command = [
        "uv",
        "run",
        "python",
        "scripts/mock_tool_call_upstream.py",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(
        command,
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_proxy_tool_call_smoke(
    base_url: str,
    workspace: str,
    token: str | None = None,
    include_failure_case: bool = False,
) -> dict[str, Any]:
    path = Path(workspace) / "proxy_build" / "main.py"
    session_id = "live-smoke-proxy"
    tools = [
        {
            "type": "function",
            "function": {"name": "write_file", "parameters": {"type": "object"}},
        },
        {
            "type": "function",
            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
        },
        {
            "type": "function",
            "function": {"name": "native_inspect_card", "parameters": {"type": "object"}},
        },
    ]
    payload = _json_request(
        "POST",
        f"{base_url}/v1/chat/completions",
        json={
            "model": "mock-tool-call-model",
            "session_id": session_id,
            "metadata": {"workspace": workspace},
            "messages": [{"role": "user", "content": "写一个 proxy build 文件"}],
            "tools": tools,
        },
        token=token,
    )
    gateway = payload.get("yizijue_gateway", {}) if isinstance(payload, dict) else {}
    file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 42\n"
    next_hexagram = (
        gateway.get("build_mode_tool_results", [{}])[0].get("next_hexagram")
        if isinstance(gateway.get("build_mode_tool_results"), list)
        else None
    )
    second_payload = _json_request(
        "POST",
        f"{base_url}/v1/chat/completions",
        json={
            "model": "mock-tool-call-model",
            "session_id": session_id,
            "metadata": {"workspace": workspace},
            "messages": [{"role": "user", "content": "inspect_tools"}],
            "tools": tools,
        },
        token=token,
    )
    second_turn_tools = _extract_received_tools(second_payload)
    verify_payload = _json_request(
        "POST",
        f"{base_url}/v1/chat/completions",
        json={
            "model": "mock-tool-call-model",
            "session_id": session_id,
            "metadata": {"workspace": workspace},
            "messages": [{"role": "user", "content": "run_verify"}],
            "tools": tools,
        },
        token=token,
    )
    verify_result = _first_build_mode_tool_result(verify_payload)
    verify_next_hexagram = verify_result.get("next_hexagram")
    verify_status = verify_result.get("status")
    responses_result = _run_responses_tool_call_smoke(base_url, workspace, token=token)
    responses_status = responses_result.get("status")
    responses_next_hexagram = responses_result.get("next_hexagram")
    responses_file_written = bool(responses_result.get("file_written"))
    responses_post_write_tools = responses_result.get("post_write_tools")
    responses_verify_status = responses_result.get("verify_status")
    responses_verify_next_hexagram = responses_result.get("verify_next_hexagram")
    responses_failure_status = responses_result.get("failure_verify_status")
    responses_failure_next_hexagram = responses_result.get("failure_verify_next_hexagram")
    responses_post_failure_tools = responses_result.get("post_failure_tools")
    responses_inspect_status = responses_result.get("inspect_status")
    responses_inspect_next_hexagram = responses_result.get("inspect_next_hexagram")
    responses_post_inspect_tools = responses_result.get("post_inspect_tools")
    responses_repair_status = responses_result.get("repair_status")
    responses_repair_next_hexagram = responses_result.get("repair_next_hexagram")
    responses_repaired_file_written = bool(responses_result.get("repaired_file_written"))
    responses_post_repair_verify_status = responses_result.get("post_repair_verify_status")
    responses_post_repair_verify_next_hexagram = responses_result.get("post_repair_verify_next_hexagram")
    responses_post_repair_manifest_written = bool(responses_result.get("post_repair_manifest_written"))
    responses_post_repair_manifest_has_repaired_file = bool(
        responses_result.get("post_repair_manifest_has_repaired_file")
    )
    responses_post_repair_manifest_sha256_matches = bool(
        responses_result.get("post_repair_manifest_sha256_matches")
    )
    responses_state = _state_status(workspace, "live-smoke-responses-proxy")
    anthropic_result = _run_anthropic_tool_call_smoke(base_url, workspace, token=token)
    anthropic_status = anthropic_result.get("status")
    anthropic_next_hexagram = anthropic_result.get("next_hexagram")
    anthropic_file_written = bool(anthropic_result.get("file_written"))
    anthropic_post_write_tools = anthropic_result.get("post_write_tools")
    anthropic_verify_status = anthropic_result.get("verify_status")
    anthropic_verify_next_hexagram = anthropic_result.get("verify_next_hexagram")
    anthropic_failure_status = anthropic_result.get("failure_verify_status")
    anthropic_failure_next_hexagram = anthropic_result.get("failure_verify_next_hexagram")
    anthropic_post_failure_tools = anthropic_result.get("post_failure_tools")
    anthropic_inspect_status = anthropic_result.get("inspect_status")
    anthropic_inspect_next_hexagram = anthropic_result.get("inspect_next_hexagram")
    anthropic_post_inspect_tools = anthropic_result.get("post_inspect_tools")
    anthropic_repair_status = anthropic_result.get("repair_status")
    anthropic_repair_next_hexagram = anthropic_result.get("repair_next_hexagram")
    anthropic_repaired_file_written = bool(anthropic_result.get("repaired_file_written"))
    anthropic_post_repair_verify_status = anthropic_result.get("post_repair_verify_status")
    anthropic_post_repair_verify_next_hexagram = anthropic_result.get("post_repair_verify_next_hexagram")
    anthropic_post_repair_manifest_written = bool(anthropic_result.get("post_repair_manifest_written"))
    anthropic_post_repair_manifest_has_repaired_file = bool(
        anthropic_result.get("post_repair_manifest_has_repaired_file")
    )
    anthropic_post_repair_manifest_sha256_matches = bool(
        anthropic_result.get("post_repair_manifest_sha256_matches")
    )
    anthropic_state = _state_status(workspace, "live-smoke-anthropic-proxy")
    failure_result: dict[str, Any] = {}
    if include_failure_case:
        failure_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_verify_fail"}],
                "tools": tools,
            },
            token=token,
        )
        failure_result = _first_build_mode_tool_result(failure_payload)
        post_failure_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "inspect_tools_after_failure"}],
                "tools": tools,
            },
            token=token,
        )
        post_failure_tools = _extract_received_tools(post_failure_payload)
        inspect_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_native_inspect"}],
                "tools": tools,
            },
            token=token,
        )
        inspect_result = _first_build_mode_tool_result(inspect_payload)
        post_inspect_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "inspect_tools_after_native_inspect"}],
                "tools": tools,
            },
            token=token,
        )
        post_inspect_tools = _extract_received_tools(post_inspect_payload)
        repair_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_repair_write"}],
                "tools": tools,
            },
            token=token,
        )
        repair_result = _first_build_mode_tool_result(repair_payload)
        repaired_file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 43\n"
        post_repair_verify_payload = _json_request(
            "POST",
            f"{base_url}/v1/chat/completions",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_verify_after_repair"}],
                "tools": tools,
            },
            token=token,
        )
        post_repair_verify_result = _first_build_mode_tool_result(post_repair_verify_payload)
        post_repair_manifest = _manifest_status(
            workspace=workspace,
            result=post_repair_verify_result,
            repaired_path=path,
        )
    else:
        post_failure_tools = []
        inspect_result = {}
        post_inspect_tools = []
        repair_result = {}
        repaired_file_written = False
        post_repair_verify_result = {}
        post_repair_manifest = {
            "written": False,
            "has_repaired_file": False,
            "sha256_matches": False,
        }
    state = _state_status(workspace, session_id)
    failure_status = failure_result.get("status")
    failure_next_hexagram = failure_result.get("next_hexagram")
    failure_feedback_present = "feedback" in failure_result
    inspect_status = inspect_result.get("status")
    inspect_next_hexagram = inspect_result.get("next_hexagram")
    repair_status = repair_result.get("status")
    repair_next_hexagram = repair_result.get("next_hexagram")
    post_repair_verify_status = post_repair_verify_result.get("status")
    post_repair_verify_next_hexagram = post_repair_verify_result.get("next_hexagram")
    failure_ok = (
        not include_failure_case
        or (
            failure_status == "needs_fix"
            and failure_next_hexagram == "110"
            and failure_feedback_present
            and post_failure_tools == ["native_inspect_card"]
            and inspect_status == "ok"
            and inspect_next_hexagram == "111"
            and post_inspect_tools == ["write_file"]
            and repair_status == "ok"
            and repair_next_hexagram == "001"
            and repaired_file_written
            and post_repair_verify_status == "completed"
            and post_repair_verify_next_hexagram == "000"
            and post_repair_manifest["written"]
            and post_repair_manifest["has_repaired_file"]
            and post_repair_manifest["sha256_matches"]
            and state["written"]
            and state["next_hexagram"] == "000"
            and state["consecutive_failures"] == 0
        )
    )
    return {
        "ok": (
            gateway.get("response_mode") == "build_mode_tool_execution"
            and file_written
            and next_hexagram == "001"
            and second_turn_tools == ["run_pytest"]
            and verify_status == "completed"
            and verify_next_hexagram == "000"
            and responses_status == "ok"
            and responses_next_hexagram == "001"
            and responses_file_written
            and responses_post_write_tools == ["run_pytest"]
            and responses_verify_status == "completed"
            and responses_verify_next_hexagram == "000"
            and responses_failure_status == "needs_fix"
            and responses_failure_next_hexagram == "110"
            and responses_post_failure_tools == ["native_inspect_card"]
            and responses_inspect_status == "ok"
            and responses_inspect_next_hexagram == "111"
            and responses_post_inspect_tools == ["write_file"]
            and responses_repair_status == "ok"
            and responses_repair_next_hexagram == "001"
            and responses_repaired_file_written
            and responses_post_repair_verify_status == "completed"
            and responses_post_repair_verify_next_hexagram == "000"
            and responses_post_repair_manifest_written
            and responses_post_repair_manifest_has_repaired_file
            and responses_post_repair_manifest_sha256_matches
            and responses_state["written"]
            and responses_state["next_hexagram"] == "000"
            and responses_state["consecutive_failures"] == 0
            and anthropic_status == "ok"
            and anthropic_next_hexagram == "001"
            and anthropic_file_written
            and anthropic_post_write_tools == ["run_pytest"]
            and anthropic_verify_status == "completed"
            and anthropic_verify_next_hexagram == "000"
            and anthropic_failure_status == "needs_fix"
            and anthropic_failure_next_hexagram == "110"
            and anthropic_post_failure_tools == ["native_inspect_card"]
            and anthropic_inspect_status == "ok"
            and anthropic_inspect_next_hexagram == "111"
            and anthropic_post_inspect_tools == ["write_file"]
            and anthropic_repair_status == "ok"
            and anthropic_repair_next_hexagram == "001"
            and anthropic_repaired_file_written
            and anthropic_post_repair_verify_status == "completed"
            and anthropic_post_repair_verify_next_hexagram == "000"
            and anthropic_post_repair_manifest_written
            and anthropic_post_repair_manifest_has_repaired_file
            and anthropic_post_repair_manifest_sha256_matches
            and anthropic_state["written"]
            and anthropic_state["next_hexagram"] == "000"
            and anthropic_state["consecutive_failures"] == 0
            and failure_ok
        ),
        "response_mode": gateway.get("response_mode"),
        "file_written": file_written,
        "next_hexagram": next_hexagram,
        "second_turn_tools": second_turn_tools,
        "verify_status": verify_status,
        "verify_next_hexagram": verify_next_hexagram,
        "responses_status": responses_status,
        "responses_next_hexagram": responses_next_hexagram,
        "responses_file_written": responses_file_written,
        "responses_post_write_tools": responses_post_write_tools,
        "responses_verify_status": responses_verify_status,
        "responses_verify_next_hexagram": responses_verify_next_hexagram,
        "responses_failure_verify_status": responses_failure_status,
        "responses_failure_verify_next_hexagram": responses_failure_next_hexagram,
        "responses_post_failure_tools": responses_post_failure_tools,
        "responses_inspect_status": responses_inspect_status,
        "responses_inspect_next_hexagram": responses_inspect_next_hexagram,
        "responses_post_inspect_tools": responses_post_inspect_tools,
        "responses_repair_status": responses_repair_status,
        "responses_repair_next_hexagram": responses_repair_next_hexagram,
        "responses_repaired_file_written": responses_repaired_file_written,
        "responses_post_repair_verify_status": responses_post_repair_verify_status,
        "responses_post_repair_verify_next_hexagram": responses_post_repair_verify_next_hexagram,
        "responses_post_repair_manifest_written": responses_post_repair_manifest_written,
        "responses_post_repair_manifest_has_repaired_file": responses_post_repair_manifest_has_repaired_file,
        "responses_post_repair_manifest_sha256_matches": responses_post_repair_manifest_sha256_matches,
        "responses_state_written": responses_state["written"],
        "responses_state_next_hexagram": responses_state["next_hexagram"],
        "responses_state_consecutive_failures": responses_state["consecutive_failures"],
        "anthropic_status": anthropic_status,
        "anthropic_next_hexagram": anthropic_next_hexagram,
        "anthropic_file_written": anthropic_file_written,
        "anthropic_post_write_tools": anthropic_post_write_tools,
        "anthropic_verify_status": anthropic_verify_status,
        "anthropic_verify_next_hexagram": anthropic_verify_next_hexagram,
        "anthropic_failure_verify_status": anthropic_failure_status,
        "anthropic_failure_verify_next_hexagram": anthropic_failure_next_hexagram,
        "anthropic_post_failure_tools": anthropic_post_failure_tools,
        "anthropic_inspect_status": anthropic_inspect_status,
        "anthropic_inspect_next_hexagram": anthropic_inspect_next_hexagram,
        "anthropic_post_inspect_tools": anthropic_post_inspect_tools,
        "anthropic_repair_status": anthropic_repair_status,
        "anthropic_repair_next_hexagram": anthropic_repair_next_hexagram,
        "anthropic_repaired_file_written": anthropic_repaired_file_written,
        "anthropic_post_repair_verify_status": anthropic_post_repair_verify_status,
        "anthropic_post_repair_verify_next_hexagram": anthropic_post_repair_verify_next_hexagram,
        "anthropic_post_repair_manifest_written": anthropic_post_repair_manifest_written,
        "anthropic_post_repair_manifest_has_repaired_file": anthropic_post_repair_manifest_has_repaired_file,
        "anthropic_post_repair_manifest_sha256_matches": anthropic_post_repair_manifest_sha256_matches,
        "anthropic_state_written": anthropic_state["written"],
        "anthropic_state_next_hexagram": anthropic_state["next_hexagram"],
        "anthropic_state_consecutive_failures": anthropic_state["consecutive_failures"],
        "failure_verify_status": failure_status,
        "failure_verify_next_hexagram": failure_next_hexagram,
        "failure_feedback_present": failure_feedback_present,
        "post_failure_tools": post_failure_tools,
        "inspect_status": inspect_status,
        "inspect_next_hexagram": inspect_next_hexagram,
        "post_inspect_tools": post_inspect_tools,
        "repair_status": repair_status,
        "repair_next_hexagram": repair_next_hexagram,
        "repaired_file_written": repaired_file_written,
        "post_repair_verify_status": post_repair_verify_status,
        "post_repair_verify_next_hexagram": post_repair_verify_next_hexagram,
        "post_repair_manifest_written": post_repair_manifest["written"],
        "post_repair_manifest_has_repaired_file": post_repair_manifest["has_repaired_file"],
        "post_repair_manifest_sha256_matches": post_repair_manifest["sha256_matches"],
        "state_written": state["written"],
        "state_next_hexagram": state["next_hexagram"],
        "state_consecutive_failures": state["consecutive_failures"],
    }


def _run_anthropic_tool_call_smoke(base_url: str, workspace: str, token: str | None = None) -> dict[str, Any]:
    path = Path(workspace) / "anthropic_build" / "main.py"
    session_id = "live-smoke-anthropic-proxy"
    tools = [
        {"name": "write_file", "input_schema": {"type": "object"}},
        {"name": "run_pytest", "input_schema": {"type": "object"}},
        {"name": "native_inspect_card", "input_schema": {"type": "object"}},
    ]
    first_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "写一个 anthropic build 文件"}],
                "tools": tools,
            },
            token=token,
        )
    )
    file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 42\n"
    post_write_tools = _extract_anthropic_received_tools(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "inspect_tools"}],
                "tools": tools,
            },
            token=token,
        )
    )
    verify_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_verify"}],
                "tools": tools,
            },
            token=token,
        )
    )
    failure_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_verify_fail"}],
                "tools": tools,
            },
            token=token,
        )
    )
    post_failure_tools = _extract_anthropic_received_tools(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "inspect_tools_after_failure"}],
                "tools": tools,
            },
            token=token,
        )
    )
    inspect_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_native_inspect"}],
                "tools": tools,
            },
            token=token,
        )
    )
    post_inspect_tools = _extract_anthropic_received_tools(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "inspect_tools_after_native_inspect"}],
                "tools": tools,
            },
            token=token,
        )
    )
    repair_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_anthropic_repair_write"}],
                "tools": tools,
            },
            token=token,
        )
    )
    repaired_file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 43\n"
    post_repair_verify_result = _first_build_mode_tool_result(
        _json_request(
            "POST",
            f"{base_url}/v1/messages",
            json={
                "model": "mock-tool-call-model",
                "max_tokens": 1024,
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "messages": [{"role": "user", "content": "run_verify_after_repair"}],
                "tools": tools,
            },
            token=token,
        )
    )
    manifest = _manifest_status(workspace, post_repair_verify_result, path)
    return {
        "status": first_result.get("status"),
        "next_hexagram": first_result.get("next_hexagram"),
        "file_written": file_written,
        "post_write_tools": post_write_tools,
        "verify_status": verify_result.get("status"),
        "verify_next_hexagram": verify_result.get("next_hexagram"),
        "failure_verify_status": failure_result.get("status"),
        "failure_verify_next_hexagram": failure_result.get("next_hexagram"),
        "post_failure_tools": post_failure_tools,
        "inspect_status": inspect_result.get("status"),
        "inspect_next_hexagram": inspect_result.get("next_hexagram"),
        "post_inspect_tools": post_inspect_tools,
        "repair_status": repair_result.get("status"),
        "repair_next_hexagram": repair_result.get("next_hexagram"),
        "repaired_file_written": repaired_file_written,
        "post_repair_verify_status": post_repair_verify_result.get("status"),
        "post_repair_verify_next_hexagram": post_repair_verify_result.get("next_hexagram"),
        "post_repair_manifest_written": manifest["written"],
        "post_repair_manifest_has_repaired_file": manifest["has_repaired_file"],
        "post_repair_manifest_sha256_matches": manifest["sha256_matches"],
    }


def _run_responses_tool_call_smoke(base_url: str, workspace: str, token: str | None = None) -> dict[str, Any]:
    path = Path(workspace) / "responses_build" / "main.py"
    session_id = "live-smoke-responses-proxy"
    tools = [
        {"type": "function", "name": "write_file", "parameters": {"type": "object"}},
        {"type": "function", "name": "run_pytest", "parameters": {"type": "object"}},
        {"type": "function", "name": "native_inspect_card", "parameters": {"type": "object"}},
    ]
    payload = _sse_json_request(
        "POST",
        f"{base_url}/v1/responses",
        json={
            "model": "mock-tool-call-model",
            "session_id": session_id,
            "metadata": {"workspace": workspace},
            "input": "写一个 responses build 文件",
            "tools": tools,
        },
        token=token,
    )
    result = _first_build_mode_tool_result(payload)
    file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 42\n"
    post_write_tools = _extract_responses_received_tools(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "inspect_tools",
                "tools": tools,
            },
            token=token,
        )
    )
    verify_result = _first_build_mode_tool_result(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "run_verify",
                "tools": tools,
            },
            token=token,
        )
    )
    failure_result = _first_build_mode_tool_result(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "run_verify_fail",
                "tools": tools,
            },
            token=token,
        )
    )
    post_failure_tools = _extract_responses_received_tools(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "inspect_tools_after_failure",
                "tools": tools,
            },
            token=token,
        )
    )
    inspect_result = _first_build_mode_tool_result(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "run_native_inspect",
                "tools": tools,
            },
            token=token,
        )
    )
    post_inspect_tools = _extract_responses_received_tools(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "inspect_tools_after_native_inspect",
                "tools": tools,
            },
            token=token,
        )
    )
    repair_result = _first_build_mode_tool_result(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "run_responses_repair_write",
                "tools": tools,
            },
            token=token,
        )
    )
    repaired_file_written = path.exists() and path.read_text(encoding="utf-8") == "VALUE = 43\n"
    post_repair_verify_result = _first_build_mode_tool_result(
        _sse_json_request(
            "POST",
            f"{base_url}/v1/responses",
            json={
                "model": "mock-tool-call-model",
                "session_id": session_id,
                "metadata": {"workspace": workspace},
                "input": "run_verify_after_repair",
                "tools": tools,
            },
            token=token,
        )
    )
    manifest = _manifest_status(workspace, post_repair_verify_result, path)
    return {
        "status": result.get("status"),
        "next_hexagram": result.get("next_hexagram"),
        "file_written": file_written,
        "post_write_tools": post_write_tools,
        "verify_status": verify_result.get("status"),
        "verify_next_hexagram": verify_result.get("next_hexagram"),
        "failure_verify_status": failure_result.get("status"),
        "failure_verify_next_hexagram": failure_result.get("next_hexagram"),
        "post_failure_tools": post_failure_tools,
        "inspect_status": inspect_result.get("status"),
        "inspect_next_hexagram": inspect_result.get("next_hexagram"),
        "post_inspect_tools": post_inspect_tools,
        "repair_status": repair_result.get("status"),
        "repair_next_hexagram": repair_result.get("next_hexagram"),
        "repaired_file_written": repaired_file_written,
        "post_repair_verify_status": post_repair_verify_result.get("status"),
        "post_repair_verify_next_hexagram": post_repair_verify_result.get("next_hexagram"),
        "post_repair_manifest_written": manifest["written"],
        "post_repair_manifest_has_repaired_file": manifest["has_repaired_file"],
        "post_repair_manifest_sha256_matches": manifest["sha256_matches"],
    }


def _first_build_mode_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    gateway = payload.get("yizijue_gateway") if isinstance(payload, dict) else None
    if not isinstance(gateway, dict):
        return {}
    results = gateway.get("build_mode_tool_results")
    if not isinstance(results, list) or not results:
        return {}
    first = results[0]
    return first if isinstance(first, dict) else {}


def _manifest_status(workspace: str, result: dict[str, Any], repaired_path: Path) -> dict[str, bool]:
    archive = result.get("archive") if isinstance(result.get("archive"), dict) else {}
    manifest_rel = archive.get("manifest_path") if isinstance(archive, dict) else None
    if not isinstance(manifest_rel, str) or not manifest_rel:
        return {"written": False, "has_repaired_file": False, "sha256_matches": False}
    root = Path(workspace).resolve()
    manifest_path = (root / manifest_rel).resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError:
        return {"written": False, "has_repaired_file": False, "sha256_matches": False}
    if not manifest_path.exists():
        return {"written": False, "has_repaired_file": False, "sha256_matches": False}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"written": True, "has_repaired_file": False, "sha256_matches": False}
    sha256_map = manifest.get("sha256_map") if isinstance(manifest, dict) else None
    if not isinstance(sha256_map, dict):
        return {"written": True, "has_repaired_file": False, "sha256_matches": False}
    repaired_rel = repaired_path.resolve().relative_to(root).as_posix()
    recorded_hash = sha256_map.get(repaired_rel)
    if not isinstance(recorded_hash, str):
        return {"written": True, "has_repaired_file": False, "sha256_matches": False}
    actual_hash = hashlib.sha256(repaired_path.read_bytes()).hexdigest() if repaired_path.exists() else ""
    return {
        "written": True,
        "has_repaired_file": True,
        "sha256_matches": recorded_hash == actual_hash,
    }


def _state_status(workspace: str, session_id: str) -> dict[str, Any]:
    safe_session = "".join(ch if ch.isalnum() or ch in "_.-" else "-" for ch in session_id)[:96].strip(".-")
    path = Path(workspace).resolve() / ".yizijue" / f"build-mode-state-{safe_session or 'session'}.json"
    if not path.exists():
        return {"written": False, "next_hexagram": None, "consecutive_failures": None}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"written": True, "next_hexagram": None, "consecutive_failures": None}
    results = state.get("results") if isinstance(state, dict) and isinstance(state.get("results"), list) else []
    next_hexagram = None
    for result in reversed(results):
        if isinstance(result, dict) and result.get("next_hexagram"):
            next_hexagram = result.get("next_hexagram")
            break
    failures = state.get("consecutive_failures") if isinstance(state, dict) else None
    return {
        "written": True,
        "next_hexagram": next_hexagram,
        "consecutive_failures": failures if isinstance(failures, int) else None,
    }


def _extract_received_tools(payload: dict[str, Any]) -> list[str]:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return []
    if not isinstance(content, str):
        return []
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    tools = parsed.get("received_tools") if isinstance(parsed, dict) else None
    if not isinstance(tools, list):
        return []
    return [tool for tool in tools if isinstance(tool, str)]


def _extract_responses_received_tools(payload: dict[str, Any]) -> list[str]:
    content = payload.get("output_text")
    if not isinstance(content, str):
        return []
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return []
    tools = parsed.get("received_tools") if isinstance(parsed, dict) else None
    if not isinstance(tools, list):
        return []
    return [tool for tool in tools if isinstance(tool, str)]


def _extract_anthropic_received_tools(payload: dict[str, Any]) -> list[str]:
    content = payload.get("content")
    if not isinstance(content, list) or not content:
        return []
    first = content[0]
    if not isinstance(first, dict):
        return []
    text = first.get("text")
    if not isinstance(text, str):
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    tools = parsed.get("received_tools") if isinstance(parsed, dict) else None
    if not isinstance(tools, list):
        return []
    return [tool for tool in tools if isinstance(tool, str)]


def _wait_until_ready(base_url: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urlrequest.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - exercised by live smoke behavior.
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    raise RuntimeError(f"gateway did not become ready at {base_url}: {last_error}")


def _json_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    token = kwargs.pop("token", None)
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = None
    if "json" in kwargs:
        data = json.dumps(kwargs["json"]).encode("utf-8")
    request = urlrequest.Request(url, data=data, headers=headers, method=method)
    with urlrequest.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def _sse_json_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    token = kwargs.pop("token", None)
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = None
    if "json" in kwargs:
        data = json.dumps(kwargs["json"]).encode("utf-8")
    request = urlrequest.Request(url, data=data, headers=headers, method=method)
    with urlrequest.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8")
    completed_payload: dict[str, Any] | None = None
    for block in text.split("\n\n"):
        event = ""
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if event != "response.completed" or not data_lines:
            continue
        parsed = json.loads("\n".join(data_lines))
        if isinstance(parsed, dict):
            completed_payload = parsed
    if not isinstance(completed_payload, dict):
        raise ValueError(f"expected response.completed SSE event from {url}")
    response_payload = completed_payload.get("response")
    if not isinstance(response_payload, dict):
        raise ValueError(f"expected response object in response.completed event from {url}")
    return response_payload


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Start a temporary OneWord gateway and run HTTP smoke checks.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=15)
    parser.add_argument("--proxy-tool-call", action="store_true")
    args = parser.parse_args()
    payload = run_live_smoke(
        host=args.host,
        port=args.port,
        workspace=args.workspace,
        token=args.token,
        timeout_seconds=args.timeout_seconds,
        include_proxy_tool_call=args.proxy_tool_call,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return payload


if __name__ == "__main__":
    main()
