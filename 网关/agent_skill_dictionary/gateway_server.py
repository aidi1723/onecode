from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hmac
import os
import shutil
import json
import re
import sys
import threading
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX path is used on supported deployment targets.
    fcntl = None

from .agent_protocol import build_agent_protocol_manifest
from .audit import append_audit_record, build_evidence_record
from .gateway_compression_adapter import build_compression_record
from .gateway_rule_adapter import aggregate_gateway_rule_envelope, build_gateway_rule
from .gateway_core import (
    ZERO_TOOL_MAX_TOKENS,
    annotate_chat_completion_response,
    build_stream_tool_block_response,
    block_disallowed_anthropic_response,
    block_disallowed_tool_response,
    inject_native_inspect_context,
    rewrite_anthropic_messages_request,
    rewrite_chat_completion_request,
    should_halt_model_forwarding,
    StreamBufferInterceptor,
    stream_not_supported_response,
)
from .gateway_plan import resolve_execution_plan
from .inspect_executor import build_native_inspect_card
from .loader import load_dictionary
from .runner import run_oneword_task
from .tool_guard import preflight_tool_call
from .upstream import parse_upstream_json, upstream_error_payload

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse
except ImportError:
    FastAPI = None
    Request = Any
    JSONResponse = None
    StreamingResponse = None


DICTIONARY_PATH = os.getenv(
    "ONEWORD_DICTIONARY_PATH",
    "agent_skill_dictionary/programming-agent-skill-dictionary.json",
)
UPSTREAM_BASE_URL = os.getenv("ONEWORD_UPSTREAM_BASE_URL", "https://api.openai.com/v1")
UPSTREAM_API_KEY = os.getenv("ONEWORD_UPSTREAM_API_KEY") or os.getenv("OPENAI_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ONEWORD_ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
ANTHROPIC_API_KEY = os.getenv("ONEWORD_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
_DEFAULT_UPSTREAM_API_KEY = object()
MAX_EVIDENCE_FIELD_CHARS = 256_000
_BUILD_MODE_LOCKS: dict[Path, threading.Lock] = {}
_BUILD_MODE_LOCKS_GUARD = threading.Lock()


class GatewayAuthRequired(RuntimeError):
    pass


def protocol_payload() -> dict[str, Any]:
    return build_agent_protocol_manifest()


def run_task_payload(body: dict[str, Any]) -> dict[str, Any]:
    user_input = str(body.get("input") or body.get("message") or "")
    workspace = str(body.get("workspace") or os.getcwd())
    workspace_error = _workspace_error(
        workspace,
        require_configured_root=bool(body.get("require_configured_workspace_root", True)),
    )
    if workspace_error is not None:
        return workspace_error
    if bool(body.get("require_safe_verification_command", True)):
        command_error = _verification_command_error(body.get("verification_command"))
        if command_error is not None:
            return command_error
    return run_oneword_task(
        user_input,
        workspace=workspace,
        enable_all=bool(body.get("enable_all", True)),
        verification_command=body.get("verification_command"),
        patch_plan=body.get("patch_plan"),
        use_docker=bool(body.get("use_docker", False)),
        docker_image=str(body.get("docker_image") or "python:3.11-slim"),
        require_docker=bool(body.get("require_docker", False)),
        enable_external_scanners=bool(body.get("enable_external_scanners", False)),
        require_guard_scanner=bool(body.get("require_guard_scanner", False)),
        guard_scanner_types=_parse_scanner_types(body.get("guard_scanner_types")),
    )


def _attach_gateway_rule_metadata(metadata: dict[str, Any], source: str = "gateway_server") -> dict[str, Any]:
    updated = dict(metadata)
    previous_rule = updated.get("gateway_rule") if isinstance(updated.get("gateway_rule"), dict) else {}
    updated["gateway_rule"] = build_gateway_rule(
        {
            "source": source,
            "event": _gateway_rule_event_from_metadata(updated),
            "evidence_required": previous_rule.get("evidence_required", []),
        }
    )
    return updated


def _gateway_rule_event_from_metadata(metadata: dict[str, Any]) -> str | None:
    if metadata.get("build_mode_sovereignty"):
        return "sovereignty_breach"
    build_mode = metadata.get("oneword_build_mode")
    if isinstance(build_mode, dict) and build_mode.get("failure_gate_locked"):
        return "policy_gap"
    return None


def submit_evidence_payload(body: dict[str, Any]) -> dict[str, Any]:
    workspace = str(body.get("workspace") or os.getcwd())
    workspace_error = _workspace_error(workspace)
    if workspace_error is not None:
        return workspace_error
    payload_error = _evidence_payload_error(body)
    if payload_error is not None:
        return payload_error
    root = Path(workspace).resolve()
    exit_code = int(body.get("exit_code", 0))
    evidence = build_evidence_record(
        command=str(body.get("command") or "external_agent_evidence"),
        exit_code=exit_code,
        stdout=str(body.get("stdout") or ""),
        stderr=str(body.get("stderr") or ""),
    )
    evidence = {
        **evidence,
        "source": _safe_metadata_value(body.get("source") or "external_agent"),
        "session_id": _safe_metadata_value(body.get("session_id") or "default"),
    }
    audit_log_path = root / ".oneword" / "audit.jsonl"
    written = append_audit_record(audit_log_path, evidence)
    return {
        "status": "accepted",
        "audit_log_path": str(audit_log_path),
        "evidence": written,
    }


def preflight_tool_payload(body: dict[str, Any], dictionary: dict[str, Any]) -> dict[str, Any]:
    payload = preflight_tool_call(
        dictionary,
        active_code=str(body.get("active_code", "")),
        tool_name=str(body.get("tool_name", "")),
        arguments=body.get("arguments", {}),
    )
    payload["gateway_rule"] = build_gateway_rule(
        {
            "source": "preflight_tool_payload",
            "event": None if payload.get("allowed") else "preflight_breach",
            "evidence_collected": {
                "tool": payload.get("tool"),
                "violations": payload.get("violations", []),
            },
        }
    )
    return payload


def build_tool_payload(body: dict[str, Any]) -> dict[str, Any]:
    from .build_mode_tool_executor import execute_build_mode_tool
    from .build_mode_expert_handoff import apply_timeout_flash_seed

    workspace = str(body.get("workspace") or os.getcwd())
    workspace_error = _workspace_error(workspace)
    if workspace_error is not None:
        return workspace_error
    metadata = _build_tool_state_metadata(body)
    result = execute_build_mode_tool(
        workspace=workspace,
        tool_name=str(body.get("tool_name", "")),
        arguments=body.get("arguments", {}),
        use_docker=bool(body.get("use_docker", False)),
        timeout_seconds=int(body.get("timeout_seconds", 15)),
        lockdown=bool(body.get("lockdown", False)),
        previous_failure_summary=_previous_failure_summary_for_workspace(workspace, metadata),
        assistant_text=str(body.get("assistant_text") or body.get("assistant_message") or ""),
        artifact_plan=_artifact_plan_for_build_tool_body(body, metadata),
    )
    artifact_plan = _artifact_plan_for_build_tool_body(body, metadata)
    if _should_apply_timeout_flash_handoff(result, artifact_plan):
        result = apply_timeout_flash_seed(
            workspace=workspace,
            artifact_plan=artifact_plan,
            timeout_result=result,
        )
    if not body.get("_skip_state_persist"):
        if result.get("source") == "timeout_flash_expert_handoff" and result.get("status") == "completed":
            _persist_expert_handoff_state(workspace, result, metadata)
        else:
            _persist_build_mode_state(workspace, [result], metadata)
    return result


def expert_handoff_payload(body: dict[str, Any]) -> dict[str, Any]:
    from .build_mode_expert_handoff import apply_expert_seed
    from .build_mode_orchestrator import artifact_plan_for_request

    workspace = str(body.get("workspace") or os.getcwd())
    workspace_error = _workspace_error(workspace)
    if workspace_error is not None:
        return workspace_error
    metadata = _attach_build_mode_session_metadata({}, body)
    metadata["workspace"] = str(Path(workspace).resolve())
    state_path = _build_mode_state_path_for_metadata(metadata)
    request_text = str(body.get("request_text") or body.get("input") or body.get("message") or "")
    plan = artifact_plan_for_request(request_text)
    if not plan.artifacts:
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "unknown_artifact_plan",
        }
    changes = body.get("changes")
    if not isinstance(changes, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in changes.items()):
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "invalid_changes",
        }
    verify_command = body.get("verify_command")
    if not isinstance(verify_command, list) or not all(isinstance(item, str) for item in verify_command):
        return {
            "status": "blocked",
            "hexagram": "100",
            "reason": "invalid_verify_command",
        }
    result = apply_expert_seed(
        workspace=workspace,
        artifact_plan=plan,
        token=str(body.get("token") or ""),
        changes=changes,
        verify_command=verify_command,
        lockdown=bool(body.get("lockdown", False)),
        state_path=state_path,
    )
    if result.get("status") == "completed":
        _persist_expert_handoff_state(workspace, result, metadata)
    return result


def _should_apply_timeout_flash_handoff(result: dict[str, Any], artifact_plan: Any) -> bool:
    if artifact_plan is None or getattr(artifact_plan, "project_name", "") != "secure-b2b-ledger-sync-repair":
        return False
    if result.get("hexagram") != "001" or result.get("status") != "needs_fix":
        return False
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    return evidence.get("timed_out") is True or evidence.get("pytest_status") == "timeout"


def _artifact_plan_for_build_tool_body(body: dict[str, Any], metadata: dict[str, Any]) -> Any:
    from .build_mode_orchestrator import RequiredArtifactPlan, artifact_plan_for_request

    explicit_plan = body.get("artifact_plan")
    if isinstance(explicit_plan, RequiredArtifactPlan):
        return explicit_plan
    request_text = str(
        body.get("request_text")
        or body.get("original_request")
        or metadata.get("request_text")
        or metadata.get("original_request")
        or ""
    )
    if request_text:
        plan = artifact_plan_for_request(request_text)
        if plan.artifacts:
            return plan
    build_mode = metadata.get("oneword_build_mode")
    project_name = ""
    if isinstance(build_mode, dict):
        project_name = str(build_mode.get("project_name") or build_mode.get("artifact_project") or "")
    if project_name:
        plan = artifact_plan_for_request(project_name)
        if plan.artifacts:
            return plan
    return None


def apply_build_mode_request_policy(
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return payload, metadata
    from .build_mode_intent import resolve_intent
    from .build_mode_permissions import canonical_tool_schema, filter_tools_schema

    decision = resolve_intent(payload)
    rewritten = dict(payload)
    if "tools" in rewritten:
        rewritten["tools"] = filter_tools_schema(decision.hexagram, rewritten.get("tools", []))
        forced_tool = _single_build_mode_tool_name(rewritten["tools"])
        if decision.hexagram in {"111", "001"} and forced_tool:
            _force_tool_choice(rewritten, forced_tool)
    rewritten_metadata = dict(metadata)
    rewritten_metadata["oneword_build_mode"] = {
        "hexagram": decision.hexagram,
        "quadrant": decision.quadrant,
        "yin_yang": decision.yin_yang,
        "reasons": list(decision.reasons),
    }
    return rewritten, rewritten_metadata


def _single_build_mode_tool_name(tools: Any) -> str | None:
    if not isinstance(tools, list) or len(tools) != 1:
        return None
    item = tools[0]
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("function"), dict):
        name = item["function"].get("name")
        return str(name) if name else None
    name = item.get("name")
    return str(name) if name else None


def create_app() -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError(
            "Gateway server requires fastapi and httpx. Install with: "
            "python3 -m pip install -r requirements-gateway.txt"
        ) from exc
    if FastAPI is None or JSONResponse is None or StreamingResponse is None:
        raise RuntimeError(
            "Gateway server requires fastapi and httpx. Install with: "
            "python3 -m pip install -r requirements-gateway.txt"
        )

    app = FastAPI(title="Yizijue Agent Skill Gateway", version="0.1.0")
    dictionary = load_dictionary(DICTIONARY_PATH)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "dictionary": DICTIONARY_PATH}

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        return readiness_payload(dictionary)

    @app.get("/v1/yizijue/protocol")
    async def protocol() -> dict[str, Any]:
        return protocol_payload()

    @app.post("/v1/yizijue/resolve")
    async def resolve(request: Request) -> dict[str, Any]:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        user_message = body.get("input") or body.get("message") or ""
        return resolve_execution_plan(str(user_message), dictionary)

    @app.post("/v1/yizijue/preflight-tool")
    async def preflight_tool(request: Request) -> dict[str, Any]:
        try:
            authorize_preflight_request(request.headers)
        except GatewayAuthRequired:
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        return preflight_tool_payload(body, dictionary)

    @app.post("/v1/yizijue/submit-evidence")
    async def submit_evidence(request: Request) -> dict[str, Any]:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        return submit_evidence_payload(body)

    @app.post("/v1/yizijue/build-tool")
    async def build_tool(request: Request) -> dict[str, Any]:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        return build_tool_payload(body)

    @app.post("/v1/yizijue/expert-handoff")
    async def expert_handoff(request: Request) -> dict[str, Any]:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        return expert_handoff_payload(body)

    @app.post("/v1/yizijue/run")
    async def run_task(request: Request) -> dict[str, Any]:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        if control_plane_requires_upstream_key(str(request.url.path)) and not UPSTREAM_API_KEY:
            payload, status_code = missing_upstream_key_response()
            return JSONResponse(content=payload, status_code=status_code)
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        return run_task_payload(body)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        prepared = chat_completions_payload(body, dictionary)
        rewritten = prepared["payload"]
        metadata = prepared["metadata"]
        if should_halt_model_forwarding(metadata):
            return JSONResponse(
                content={
                    "error": {
                        "type": "yizijue_halt",
                        "message": "System halted by 一字诀 kernel policy. Wait for human activation token.",
                    },
                    "yizijue_gateway": {
                        **metadata,
                        "blocked": True,
                    },
                },
                status_code=503,
            )
        headers = _upstream_headers(request.headers)
        upstream_url = f"{UPSTREAM_BASE_URL.rstrip('/')}/chat/completions"
        if bool(rewritten.get("stream")):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(upstream_url, json=rewritten, headers=headers)
            except httpx.HTTPError as exc:
                return JSONResponse(
                    content=upstream_error_payload(exc, "yizijue_gateway"),
                    status_code=502,
                )
            chunks = [chunk async for chunk in response.aiter_bytes()]
            payload, status_code = inspect_stream_chunk_for_policy(metadata, chunks)
            if status_code != 200:
                return JSONResponse(content=payload, status_code=status_code)
            if _is_stream_gateway_rewrite(payload):
                return StreamingResponse(
                    iter([_openai_stream_notice_chunk(payload), b"data: [DONE]\n\n"]),
                    media_type=response.headers.get("content-type", "text/event-stream"),
                    status_code=200,
                )
            return StreamingResponse(
                iter(chunks),
                media_type=response.headers.get("content-type", "text/event-stream"),
                status_code=response.status_code,
            )

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(upstream_url, json=rewritten, headers=headers)
        except httpx.HTTPError as exc:
            return JSONResponse(
                content=upstream_error_payload(exc, "yizijue_gateway"),
                status_code=502,
            )

        payload, status_code = parse_upstream_json(response, "yizijue_gateway")
        if isinstance(payload, dict):
            payload, guard_status_code = chat_completion_response_payload(payload, metadata, dictionary)
            status_code = guard_status_code if guard_status_code != 200 else status_code
        return JSONResponse(content=payload, status_code=status_code)

    @app.post("/v1/responses")
    async def openai_responses(request: Request) -> JSONResponse:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        if control_plane_requires_upstream_key(str(request.url.path)) and not UPSTREAM_API_KEY:
            payload, status_code = missing_upstream_key_response()
            return JSONResponse(content=payload, status_code=status_code)
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        rewritten = openai_responses_payload(body, dictionary)
        metadata = rewritten["metadata"]
        if should_halt_model_forwarding(metadata):
            return JSONResponse(
                content={
                    "error": {
                        "type": "yizijue_halt",
                        "message": "System halted by 一字诀 kernel policy. Wait for human activation token.",
                    },
                    "yizijue_gateway": {
                        **metadata,
                        "blocked": True,
                    },
                },
                status_code=503,
            )
        headers = _upstream_headers(request.headers)
        upstream_url = f"{UPSTREAM_BASE_URL.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(upstream_url, json=rewritten["chat_payload"], headers=headers)
        except httpx.HTTPError as exc:
            return JSONResponse(
                content=upstream_error_payload(exc, "yizijue_gateway"),
                status_code=502,
            )
        payload, status_code = parse_upstream_json(response, "yizijue_gateway")
        if isinstance(payload, dict):
            payload, guard_status_code = openai_responses_response_payload(
                payload,
                metadata,
                dictionary,
            )
            status_code = guard_status_code if guard_status_code != 200 else status_code
        if status_code == 200 and isinstance(payload, dict):
            return StreamingResponse(
                openai_responses_stream_chunks(payload),
                media_type="text/event-stream",
                status_code=200,
            )
        return JSONResponse(content=payload, status_code=status_code)

    @app.post("/v1/messages")
    async def anthropic_messages(request: Request) -> JSONResponse:
        if not gateway_request_authorized(request.headers):
            return JSONResponse(
                content=gateway_unauthorized_response(),
                status_code=401,
            )
        if control_plane_requires_upstream_key(str(request.url.path)) and not ANTHROPIC_API_KEY:
            payload, status_code = missing_upstream_key_response("anthropic")
            return JSONResponse(content=payload, status_code=status_code)
        body, json_error = await _request_json_payload(request)
        if json_error is not None:
            return JSONResponse(content=json_error["payload"], status_code=json_error["status_code"])
        rewritten = anthropic_messages_payload(body, dictionary)
        metadata = rewritten["metadata"]
        if should_halt_model_forwarding(metadata):
            return JSONResponse(
                content={
                    "error": {
                        "type": "yizijue_halt",
                        "message": "System halted by 一字诀 kernel policy. Wait for human activation token.",
                    },
                    "yizijue_gateway": {
                        **metadata,
                        "blocked": True,
                    },
                },
                status_code=503,
            )
        headers = _anthropic_upstream_headers(request.headers)
        upstream_url = f"{ANTHROPIC_BASE_URL.rstrip('/')}/messages"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(upstream_url, json=rewritten["payload"], headers=headers)
        except httpx.HTTPError as exc:
            return JSONResponse(
                content=upstream_error_payload(exc, "yizijue_gateway"),
                status_code=502,
            )
        if bool(rewritten["payload"].get("stream")):
            chunks = [chunk async for chunk in response.aiter_bytes()]
            payload, status_code = inspect_stream_chunk_for_policy(metadata, chunks)
            if status_code != 200:
                return JSONResponse(content=payload, status_code=status_code)
            if _is_stream_gateway_rewrite(payload):
                return StreamingResponse(
                    iter([_anthropic_stream_notice_chunk(payload)]),
                    media_type=response.headers.get("content-type", "text/event-stream"),
                    status_code=200,
                )
            return StreamingResponse(
                iter(chunks),
                media_type=response.headers.get("content-type", "text/event-stream"),
                status_code=response.status_code,
            )
        payload, status_code = parse_upstream_json(response, "yizijue_gateway")
        if isinstance(payload, dict):
            payload, guard_status_code = anthropic_messages_response_payload(payload, metadata, dictionary)
            status_code = guard_status_code if guard_status_code != 200 else status_code
        return JSONResponse(content=payload, status_code=status_code)

    return app


def chat_completions_payload(body: dict[str, Any], dictionary: dict[str, Any]) -> dict[str, Any]:
    original_tools = body.get("tools") if isinstance(body.get("tools"), list) else None
    payload, metadata = rewrite_chat_completion_request(body, dictionary)
    metadata = _attach_build_mode_session_metadata(metadata, body)
    metadata = _attach_build_mode_request_metadata(metadata, body)
    workspace_root = os.getenv("ONEWORD_WORKSPACE_ROOT")
    metadata = _attach_configured_workspace(metadata, body, workspace_root)
    build_mode_enabled = os.getenv("ONEWORD_BUILD_MODE", "").lower() in {"1", "true", "yes", "on"}
    if build_mode_enabled and original_tools is not None and not metadata.get("zero_tool_fast_path"):
        payload["tools"] = original_tools
    payload, metadata = apply_build_mode_request_policy(payload, metadata)
    payload, metadata = _apply_build_mode_state_permission_override(payload, metadata, original_tools)
    payload, metadata = _apply_build_mode_failure_gate(payload, metadata)
    payload = _inject_build_mode_artifact_instruction(payload, metadata, body, original_tools)
    payload = _inject_build_mode_state_context(payload, metadata)
    metadata = _attach_gateway_rule_metadata(metadata, "chat_completions_payload")
    return {"payload": payload, "metadata": metadata}


def anthropic_messages_payload(body: dict[str, Any], dictionary: dict[str, Any]) -> dict[str, Any]:
    original_tools = body.get("tools") if isinstance(body.get("tools"), list) else None
    payload, metadata = rewrite_anthropic_messages_request(body, dictionary)
    metadata = _attach_build_mode_session_metadata(metadata, body)
    metadata = _attach_build_mode_request_metadata(metadata, body)
    workspace_root = os.getenv("ONEWORD_WORKSPACE_ROOT")
    metadata = _attach_configured_workspace(metadata, body, workspace_root)
    build_mode_enabled = os.getenv("ONEWORD_BUILD_MODE", "").lower() in {"1", "true", "yes", "on"}
    if build_mode_enabled and original_tools is not None and not metadata.get("zero_tool_fast_path"):
        payload["tools"] = original_tools
    payload, metadata = apply_build_mode_request_policy(payload, metadata)
    payload, metadata = _apply_build_mode_state_permission_override(payload, metadata, original_tools)
    payload, metadata = _apply_build_mode_failure_gate(payload, metadata)
    payload = _inject_build_mode_artifact_instruction(payload, metadata, body, original_tools)
    build_mode_context = _build_mode_state_context_for_metadata(metadata)
    if build_mode_context:
        payload["system"] = _merge_system_text(build_mode_context, payload.get("system"))
        metadata["build_mode_state_injection"] = {
            "applied": True,
            "chars": len(build_mode_context),
        }
    payload = inject_native_inspect_context(payload, metadata)
    metadata = _attach_gateway_rule_metadata(metadata, "anthropic_messages_payload")
    return {"payload": payload, "metadata": metadata}


def anthropic_messages_response_payload(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    if _build_mode_response_execution_enabled(metadata) and _response_has_anthropic_tool_uses(payload):
        return _execute_build_mode_anthropic_tool_uses(payload, metadata, dictionary)
    return block_disallowed_anthropic_response(payload, metadata, dictionary)


def _execute_build_mode_anthropic_tool_uses(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    annotated = block_disallowed_anthropic_response(payload, metadata, dictionary)[0]
    gateway = annotated.get("yizijue_gateway", {}) if isinstance(annotated, dict) else {}
    guard = gateway.get("tool_guard", {})
    workspace = str(metadata.get("workspace") or metadata.get("workspace_root") or "")
    if not workspace:
        summary = "Build Mode workspace is not configured; tool execution was not started."
        rewritten = deepcopy(payload)
        rewritten["content"] = [{"type": "text", "text": summary}]
        rewritten["stop_reason"] = "end_turn"
        rewritten["yizijue_gateway"] = {
            **metadata,
            "blocked": True,
            "response_mode": "soft_rewrite",
            "tool_guard": guard,
            "build_mode_tool_results": [
                {
                    "status": "rejected",
                    "error": {"type": "workspace_missing"},
                }
            ],
        }
        return rewritten, 200

    results = [
        build_tool_payload(
            _build_mode_internal_tool_body(workspace, call, metadata)
        )
        for call in _iter_anthropic_tool_uses(payload)
    ]
    _persist_build_mode_state(workspace, results, metadata)
    summary = _build_mode_tool_results_summary(results)
    rewritten = deepcopy(payload)
    rewritten["content"] = [{"type": "text", "text": summary}]
    rewritten["stop_reason"] = "end_turn"
    rewritten["yizijue_gateway"] = {
        **metadata,
        "response_mode": "build_mode_tool_execution",
        "tool_guard": guard,
        "build_mode_tool_results": results,
    }
    return rewritten, 200


def chat_completion_response_payload(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    if _build_mode_response_execution_enabled(metadata) and _response_has_chat_tool_calls(payload):
        return _execute_build_mode_chat_tool_calls(payload, metadata, dictionary)
    return block_disallowed_tool_response(payload, metadata, dictionary)


def _execute_build_mode_chat_tool_calls(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    annotated = annotate_chat_completion_response(payload, metadata, dictionary)
    guard = annotated["yizijue_gateway"]["tool_guard"]
    workspace = str(metadata.get("workspace") or metadata.get("workspace_root") or "")
    if not workspace:
        rewritten = deepcopy(payload)
        for choice in rewritten.get("choices", []):
            message = choice.setdefault("message", {})
            message.pop("tool_calls", None)
            message["content"] = "Build Mode workspace is not configured; tool execution was not started."
            if choice.get("finish_reason") == "tool_calls":
                choice["finish_reason"] = "stop"
        rewritten["yizijue_gateway"] = {
            **metadata,
            "blocked": True,
            "response_mode": "soft_rewrite",
            "tool_guard": guard,
            "build_mode_tool_results": [
                {
                    "status": "rejected",
                    "error": {"type": "workspace_missing"},
                }
            ],
        }
        return rewritten, 200

    results: list[dict[str, Any]] = []
    for call in _iter_openai_chat_tool_calls(payload):
        results.append(
            build_tool_payload(_build_mode_internal_tool_body(workspace, call, metadata))
        )
    _persist_build_mode_state(workspace, results, metadata)

    rewritten = deepcopy(payload)
    summary = _build_mode_tool_results_summary(results)
    for choice in rewritten.get("choices", []):
        message = choice.setdefault("message", {})
        message.pop("tool_calls", None)
        message["content"] = summary
        if choice.get("finish_reason") == "tool_calls":
            choice["finish_reason"] = "stop"
    rewritten["yizijue_gateway"] = {
        **metadata,
        "response_mode": "build_mode_tool_execution",
        "tool_guard": guard,
        "build_mode_tool_results": results,
    }
    return rewritten, 200


def openai_responses_payload(body: dict[str, Any], dictionary: dict[str, Any]) -> dict[str, Any]:
    original_tools = body.get("tools") if isinstance(body.get("tools"), list) else None
    chat_body = _responses_to_chat_request(body)
    chat_payload, metadata = rewrite_chat_completion_request(chat_body, dictionary)
    metadata = _attach_build_mode_session_metadata(metadata, body)
    metadata = _attach_build_mode_request_metadata(metadata, body)
    workspace_root = os.getenv("ONEWORD_WORKSPACE_ROOT")
    metadata = _attach_configured_workspace(metadata, body, workspace_root)
    payload = dict(body)
    payload["instructions"] = _merge_responses_instructions(
        str(chat_payload["messages"][0]["content"]),
        payload.get("instructions"),
    )
    payload["input"] = _chat_messages_to_responses_input(chat_payload["messages"][1:])
    payload["temperature"] = chat_payload.get("temperature")
    if "tools" in payload:
        payload["tools"] = chat_payload.get("tools", [])
    if metadata.get("zero_tool_fast_path"):
        payload["tools"] = []
        payload["max_output_tokens"] = ZERO_TOOL_MAX_TOKENS
        chat_payload["tools"] = []
        chat_payload["max_tokens"] = ZERO_TOOL_MAX_TOKENS
    metadata = {
        **metadata,
        "protocol": "openai_responses",
        "upstream_protocol": "chat_completions",
    }
    if original_tools is not None and not metadata.get("zero_tool_fast_path"):
        payload["tools"] = original_tools
    payload, metadata = apply_build_mode_request_policy(payload, metadata)
    if "tools" in payload:
        chat_payload["tools"] = _responses_tools_to_chat_tools(payload.get("tools"))
    build_mode_context = _build_mode_state_context_for_metadata(metadata)
    if build_mode_context:
        payload["instructions"] = _merge_responses_instructions(build_mode_context, payload.get("instructions"))
        chat_payload["messages"].insert(1, {"role": "system", "content": build_mode_context})
        metadata["build_mode_state_injection"] = {
            "applied": True,
            "chars": len(build_mode_context),
        }
    if original_tools is not None:
        payload, metadata = _apply_build_mode_state_permission_override(payload, metadata, original_tools)
        if "tools" in payload:
            chat_payload["tools"] = _responses_tools_to_chat_tools(payload.get("tools"))
    payload, metadata = _apply_build_mode_failure_gate(payload, metadata)
    payload = _inject_build_mode_artifact_instruction(payload, metadata, body, original_tools)
    artifact_instruction = metadata.get("build_mode_artifact_instruction")
    if isinstance(artifact_instruction, str) and artifact_instruction:
        chat_payload["messages"].insert(1, {"role": "system", "content": artifact_instruction})
    if "tools" in payload:
        chat_payload["tools"] = _responses_tools_to_chat_tools(payload.get("tools"))
    if "tool_choice" in payload:
        chat_payload["tool_choice"] = _responses_tool_choice_to_chat_tool_choice(payload.get("tool_choice"))
    if (
        str(metadata.get("root_opcode") or metadata.get("active_code")) == "查"
        and not _build_mode_state_permission_override_applied(metadata)
    ):
        native_card = _native_inspect_text_for_responses(metadata)
        context = "\n".join(
            [
                "Native Inspect Context:",
                native_card,
                "Use this read-only evidence as the inspected project context.",
                "The system has already performed the physical read. Return the final answer directly.",
                "Do not call local tools, do not request more reads, and do not emit shell commands.",
            ]
        )
        payload["instructions"] = _merge_responses_instructions(context, payload.get("instructions"))
        chat_payload["messages"].insert(1, {"role": "system", "content": context})
        payload["tools"] = []
        chat_payload["tools"] = []
        metadata["native_context_injection"] = {
            "applied": True,
            "chars": len(native_card),
            "source": "native_inspect_card",
        }
    _append_build_mode_debug_record(
        "openai_responses_prepared",
        metadata,
        {
            "responses_tools": _debug_tool_schema_summary(payload.get("tools")),
            "chat_tools": _debug_chat_tool_schema_summary(chat_payload.get("tools")),
            "message_count": len(chat_payload.get("messages", [])),
        },
    )
    metadata = _attach_gateway_rule_metadata(metadata, "openai_responses_payload")
    return {"payload": payload, "chat_payload": chat_payload, "metadata": metadata}


def openai_responses_response_payload(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    response_payload = _chat_completion_to_responses_payload(payload) if "choices" in payload else dict(payload)
    _append_build_mode_debug_record(
        "openai_responses_raw_response",
        metadata,
        {
            "tool_calls": _debug_responses_tool_call_summary(response_payload),
            "output_text_chars": len(str(response_payload.get("output_text") or "")),
        },
    )
    if _build_mode_response_execution_enabled(metadata) and _response_has_responses_tool_calls(response_payload):
        return _execute_build_mode_responses_tool_calls(response_payload, metadata, dictionary)
    chat_like = _responses_to_chat_completion_payload(response_payload)
    annotated = annotate_chat_completion_response(chat_like, metadata, dictionary)
    guard = annotated["yizijue_gateway"]["tool_guard"]
    rewritten = dict(response_payload)
    rewritten["yizijue_gateway"] = {
        **metadata,
        "tool_guard": guard,
    }
    if not guard["allowed"]:
        rewritten["yizijue_gateway"]["blocked"] = True
        rewritten["yizijue_gateway"]["response_mode"] = "soft_rewrite"
        rewritten["output"] = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Kernel Notice: unauthorized tool execution blocked by OneWord state rules. Action canceled by system."}],
            }
        ]
        rewritten["output_text"] = "Kernel Notice: unauthorized tool execution blocked by OneWord state rules. Action canceled by system."
    return rewritten, 200


def _execute_build_mode_responses_tool_calls(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    dictionary: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    chat_like = _responses_to_chat_completion_payload(payload)
    annotated = annotate_chat_completion_response(chat_like, metadata, dictionary)
    guard = annotated["yizijue_gateway"]["tool_guard"]
    workspace = str(metadata.get("workspace") or metadata.get("workspace_root") or "")
    if not workspace:
        summary = "Build Mode workspace is not configured; tool execution was not started."
        rewritten = dict(payload)
        rewritten["output"] = [_responses_message_item(summary)]
        rewritten["output_text"] = summary
        rewritten["yizijue_gateway"] = {
            **metadata,
            "blocked": True,
            "response_mode": "soft_rewrite",
            "tool_guard": guard,
            "build_mode_tool_results": [
                {
                    "status": "rejected",
                    "error": {"type": "workspace_missing"},
                }
            ],
        }
        return rewritten, 200

    results = [
        build_tool_payload(
            _build_mode_internal_tool_body(workspace, call, metadata)
        )
        for call in _iter_openai_responses_tool_calls(payload)
    ]
    _persist_build_mode_state(workspace, results, metadata)
    summary = _build_mode_tool_results_summary(results)
    rewritten = dict(payload)
    rewritten["output"] = [_responses_message_item(summary)]
    rewritten["output_text"] = summary
    rewritten["yizijue_gateway"] = {
        **metadata,
        "response_mode": "build_mode_tool_execution",
        "tool_guard": guard,
        "build_mode_tool_results": results,
    }
    return rewritten, 200


def _build_mode_internal_tool_body(
    workspace: str,
    call: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "workspace": workspace,
        "tool_name": call["name"],
        "arguments": call["arguments"],
        "_skip_state_persist": True,
        "metadata": metadata,
    }
    request_text = metadata.get("request_text") or metadata.get("original_request")
    if isinstance(request_text, str) and request_text.strip():
        body["request_text"] = request_text
        body["original_request"] = request_text
    return body


def openai_responses_stream_chunks(payload: dict[str, Any]) -> list[bytes]:
    response = dict(payload)
    response.setdefault("object", "response")
    response.setdefault("status", "completed")
    response_id = str(response.get("id") or "resp_oneword")
    text = str(response.get("output_text") or "")
    item_id = f"{response_id}_msg"
    item = {
        "id": item_id,
        "type": "message",
        "status": "in_progress",
        "role": "assistant",
        "content": [],
    }
    content_part = {"type": "output_text", "text": text}
    created = {"type": "response.created", "response": {**response, "status": "in_progress"}}
    item_added = {
        "type": "response.output_item.added",
        "output_index": 0,
        "item": item,
    }
    part_added = {
        "type": "response.content_part.added",
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "part": {"type": "output_text", "text": ""},
    }
    delta = {
        "type": "response.output_text.delta",
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "delta": text,
    }
    done = {
        "type": "response.output_text.done",
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "text": text,
    }
    part_done = {
        "type": "response.content_part.done",
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "part": content_part,
    }
    item_done = {
        "type": "response.output_item.done",
        "output_index": 0,
        "item": {**item, "status": "completed", "content": [content_part]},
    }
    completed = {"type": "response.completed", "response": response}
    return [
        _sse_event("response.created", created),
        _sse_event("response.output_item.added", item_added),
        _sse_event("response.content_part.added", part_added),
        _sse_event("response.output_text.delta", delta),
        _sse_event("response.output_text.done", done),
        _sse_event("response.content_part.done", part_done),
        _sse_event("response.output_item.done", item_done),
        _sse_event("response.completed", completed),
        b"data: [DONE]\n\n",
    ]


def _build_mode_response_execution_enabled(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("oneword_build_mode"))


def _persist_build_mode_state(
    workspace: str,
    results: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    if not results:
        return
    root = Path(workspace).resolve()
    state_path = _build_mode_state_path(root, metadata or {})
    with _build_mode_state_file_lock(state_path):
        previous = _read_build_mode_state(state_path)
        try:
            repo_card = build_native_inspect_card(root, max_chars=1200)["text"]
        except (OSError, ValueError):
            repo_card = ""
        compact_results = _compact_build_mode_results(results)
        consecutive_failures = _next_consecutive_failures(previous, compact_results)
        last_exit_code = _last_exit_code(compact_results, previous)
        repair_card = _latest_repair_card(results, previous)
        compression_record = _build_state_compression_record(repair_card, compact_results)
        state = {
            "status": "updated",
            "consecutive_failures": consecutive_failures,
            "last_exit_code": last_exit_code,
            "results": compact_results,
            "gateway_rule": _gateway_rule_for_compact_results(compact_results, "build_mode_state"),
            "compressed_summary": compression_record["compressed_summary"],
            "compression_rule": compression_record,
            "repo_card": repo_card,
        }
        if repair_card:
            state["repair_card"] = repair_card
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = state_path.with_name(f"{state_path.name}.tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)


def _persist_expert_handoff_state(
    workspace: str,
    result: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    root = Path(workspace).resolve()
    state_path = _build_mode_state_path(root, metadata or {})
    with _build_mode_state_file_lock(state_path):
        previous = _read_build_mode_state(state_path)
        try:
            repo_card = build_native_inspect_card(root, max_chars=1200)["text"]
        except (OSError, ValueError):
            repo_card = str(previous.get("repo_card") or "")
        results = previous.get("results") if isinstance(previous.get("results"), list) else []
        compact_result = {
            "status": "completed",
            "hexagram": "100",
            "next_hexagram": "000",
            "source": "expert_handoff",
            "exit_code": 0,
            "gateway_rule": build_gateway_rule({"source": "expert_handoff_result"}),
        }
        state = {
            "status": "updated",
            "consecutive_failures": 0,
            "last_exit_code": 0,
            "results": [*results, compact_result],
            "gateway_rule": _gateway_rule_for_compact_results([*results, compact_result], "expert_handoff_state"),
            "repo_card": repo_card,
            "expert_handoff": {
                "status": result.get("status"),
                "hexagram": result.get("hexagram"),
                "archive": result.get("archive", {}),
            },
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = state_path.with_name(f"{state_path.name}.tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)


def _build_tool_state_metadata(body: dict[str, Any]) -> dict[str, Any]:
    metadata = body.get("metadata")
    if isinstance(metadata, dict):
        return _attach_build_mode_session_metadata(dict(metadata), body)
    return _attach_build_mode_session_metadata({}, body)


@contextmanager
def _build_mode_state_file_lock(state_path: Path) -> Iterator[None]:
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:
        with _build_mode_thread_lock(lock_path):
            yield
        return
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _build_mode_thread_lock(lock_path: Path) -> Iterator[None]:
    resolved = lock_path.resolve()
    with _BUILD_MODE_LOCKS_GUARD:
        if resolved not in _BUILD_MODE_LOCKS:
            _BUILD_MODE_LOCKS[resolved] = threading.Lock()
        lock = _BUILD_MODE_LOCKS[resolved]
    with lock:
        yield


def _read_build_mode_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        value = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _next_consecutive_failures(previous: dict[str, Any], results: list[dict[str, Any]]) -> int:
    if any(_result_completed_successfully(result) for result in results):
        return 0
    failure_increment = sum(1 for result in results if _result_counts_as_failure(result))
    if failure_increment == 0:
        return int(previous.get("consecutive_failures") or 0)
    return int(previous.get("consecutive_failures") or 0) + failure_increment


def _result_completed_successfully(result: dict[str, Any]) -> bool:
    return result.get("status") == "completed" and result.get("next_hexagram") == "000"


def _result_counts_as_failure(result: dict[str, Any]) -> bool:
    if result.get("status") in {"needs_fix", "blocked"}:
        return True
    exit_code = result.get("exit_code")
    return isinstance(exit_code, int) and exit_code != 0


def _last_exit_code(results: list[dict[str, Any]], previous: dict[str, Any]) -> int | None:
    for result in reversed(results):
        exit_code = result.get("exit_code")
        if isinstance(exit_code, int):
            return exit_code
    previous_code = previous.get("last_exit_code")
    return previous_code if isinstance(previous_code, int) else None


def _compact_build_mode_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for result in results:
        evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
        compacted.append(
            {
                "status": result.get("status"),
                "hexagram": result.get("hexagram"),
                "next_hexagram": _state_next_hexagram_from_result(result),
                "shadow_action": result.get("shadow_action"),
                "changed_files": evidence.get("changed_files") if isinstance(evidence, dict) else None,
                "pytest_status": evidence.get("pytest_status") if isinstance(evidence, dict) else None,
                "exit_code": evidence.get("exit_code") if isinstance(evidence, dict) else None,
                "failure_summary": evidence.get("failure_summary") if isinstance(evidence, dict) else None,
                "fallback_tools": result.get("fallback_tools") if isinstance(result.get("fallback_tools"), list) else None,
                "reason": result.get("reason"),
                "audit": result.get("audit") if isinstance(result.get("audit"), dict) else None,
                "decay": result.get("decay") if isinstance(result.get("decay"), dict) else None,
                "gateway_rule": build_gateway_rule(_gateway_rule_source_from_build_mode_result(result)),
            }
        )
    return compacted


def _gateway_rule_source_from_build_mode_result(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    if result.get("status") == "completed":
        return {
            "source": "build_mode_result",
            "sovereignty": True,
            "upstream": True,
            "policy": True,
            "artifact": True,
            "execution": True,
            "time": True,
            "evidence_collected": evidence,
        }
    if result.get("status") in {"blocked", "rejected"}:
        return {
            "source": "build_mode_result",
            "event": "sovereignty_breach",
            "evidence_collected": evidence,
        }
    return {
        "source": "build_mode_result",
        "sovereignty": True,
        "upstream": True,
        "policy": True,
        "artifact": bool(evidence),
        "execution": False,
        "time": True,
        "evidence_collected": evidence,
    }


def _gateway_rule_for_compact_results(results: list[dict[str, Any]], source: str) -> dict[str, Any]:
    status_codes: list[int] = []
    for result in results:
        rule = result.get("gateway_rule") if isinstance(result.get("gateway_rule"), dict) else {}
        code = rule.get("gateway_status_code")
        if isinstance(code, int):
            status_codes.append(code)
    return aggregate_gateway_rule_envelope(status_codes, source)


def _build_state_compression_record(repair_card: str, compact_results: list[dict[str, Any]]) -> dict[str, Any]:
    if repair_card:
        return build_compression_record(repair_card)
    summaries = []
    for result in compact_results:
        value = result.get("failure_summary") or result.get("reason") or result.get("status")
        if isinstance(value, str) and value.strip():
            summaries.append(value.strip())
    return build_compression_record(" | ".join(summaries))


def _latest_repair_card(results: list[dict[str, Any]], previous: dict[str, Any]) -> str:
    for result in reversed(results):
        card = result.get("repair_card")
        if isinstance(card, str) and card.strip():
            return card.strip()
    previous_card = previous.get("repair_card")
    return previous_card.strip() if isinstance(previous_card, str) else ""


def _previous_failure_summary_for_workspace(workspace: str, metadata: dict[str, Any]) -> str:
    state = _read_build_mode_state(_build_mode_state_path(Path(workspace).resolve(), metadata))
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        summary = result.get("failure_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return ""


def _state_next_hexagram_from_result(result: dict[str, Any]) -> Any:
    feedback = result.get("feedback")
    if isinstance(feedback, dict):
        feedback_evidence = feedback.get("feedback")
        if isinstance(feedback_evidence, dict) and feedback_evidence.get("next_hexagram"):
            return feedback_evidence.get("next_hexagram")
    return result.get("next_hexagram") or result.get("final_next_hexagram")


def _inject_build_mode_state_context(payload: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    context = _build_mode_state_context_for_metadata(metadata)
    if not context:
        return payload
    state_path = _build_mode_state_path_for_metadata(metadata)
    next_hexagram = _build_mode_state_next_hexagram_for_metadata(metadata)
    injected = deepcopy(payload)
    messages = injected.setdefault("messages", [])
    messages.insert(1 if messages and messages[0].get("role") == "system" else 0, {"role": "system", "content": context})
    metadata["build_mode_state_injection"] = {
        "applied": True,
        "state_path": str(state_path) if state_path is not None else "",
        "chars": len(context),
        "next_hexagram": next_hexagram,
    }
    return injected


def _apply_build_mode_state_permission_override(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    original_tools: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return payload, metadata
    next_hexagram = _build_mode_state_next_hexagram_for_metadata(metadata)
    if not next_hexagram:
        return payload, metadata
    from .build_mode_permissions import filter_tools_schema, write_file_fallback_schema

    fallback_tools = _build_mode_state_fallback_tools_for_metadata(metadata)

    rewritten = dict(payload)
    if "tools" in rewritten:
        source_tools = original_tools or rewritten.get("tools", [])
        if fallback_tools == ["write_file"]:
            rewritten["tools"] = write_file_fallback_schema(source_tools)
        else:
            rewritten["tools"] = filter_tools_schema(next_hexagram, source_tools)
    rewritten_metadata = dict(metadata)
    existing = dict(rewritten_metadata.get("oneword_build_mode") or {})
    existing.update(
        {
            "hexagram": next_hexagram,
            "source": "state_next_hexagram",
        }
    )
    if fallback_tools:
        existing["fallback_tools"] = fallback_tools
    rewritten_metadata["oneword_build_mode"] = existing
    return rewritten, rewritten_metadata


def _apply_build_mode_failure_gate(
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return payload, metadata
    from .build_mode_fsm import FAILURE_GATE_THRESHOLD

    failures = _build_mode_state_consecutive_failures_for_metadata(metadata)
    deadlock_suspected = _build_mode_state_deadlock_suspected_for_metadata(metadata)
    if failures < FAILURE_GATE_THRESHOLD and not deadlock_suspected:
        return payload, metadata
    gate_source = "v3_deadlock_decay_gate" if deadlock_suspected else "equilibrium_failure_gate"
    rewritten = deepcopy(payload)
    if "tools" in rewritten:
        rewritten["tools"] = []
    notice = (
        f"Failure Gate: Build Mode detected {failures} consecutive failed verification cycles. "
        "All tools are withheld in 艮 100 stop posture. Summarize the expert handoff evidence "
        "and wait for explicit human direction; do not write files or fabricate dependency shims."
    )
    _inject_failure_gate_notice(rewritten, notice)
    rewritten_metadata = dict(metadata)
    existing = dict(rewritten_metadata.get("oneword_build_mode") or {})
    existing.update(
        {
            "hexagram": "000",
            "source": gate_source,
            "failure_gate_locked": True,
            "consecutive_failures": failures,
        }
    )
    rewritten_metadata["oneword_build_mode"] = existing
    expert_handoff = _build_mode_expert_handoff_for_metadata(metadata, failures)
    rewritten_metadata["build_mode_equilibrium"] = {
        "hexagram": "100",
        "source": gate_source,
        "shadow_action": "expert_handoff",
        "tool_name": None,
        "target_path": None,
        "balance": {
            "total_gaps": 0,
            "present_count": 0,
            "allowed_tool_count": 0,
            "allowed_tool_names": [],
            "yin_resistance": 1.0,
            "yang_bandwidth": 0.0,
            "mode": "failure_lockdown",
            "violations": ["consecutive_failures_exceeded"],
        },
    }
    existing["hexagram"] = "100"
    rewritten_metadata["oneword_build_mode"] = existing
    rewritten_metadata["build_mode_expert_handoff"] = expert_handoff
    rewritten_metadata["build_mode_expert_handoff"]["source"] = gate_source
    return rewritten, rewritten_metadata


def _build_mode_expert_handoff_for_metadata(
    metadata: dict[str, Any],
    failures: int,
) -> dict[str, Any]:
    state_path = _build_mode_state_path_for_metadata(metadata)
    state: dict[str, Any] = {}
    if state_path is not None and state_path.exists():
        state = _read_build_mode_state(state_path)
    return {
        "hexagram": "100",
        "source": "equilibrium_failure_gate",
        "consecutive_failures": failures,
        "last_exit_code": state.get("last_exit_code"),
        "repo_card": state.get("repo_card", ""),
        "repair_card": state.get("repair_card", ""),
        "latest_result": _latest_build_mode_result(state),
        "instruction": (
            "Model privileges are revoked. A human-approved expert seed may inspect this evidence "
            "and submit explicit audited changes through the normal scoped writer path."
        ),
    }


def _latest_build_mode_result(state: dict[str, Any]) -> dict[str, Any]:
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if isinstance(result, dict):
            return result
    return {}


def _inject_failure_gate_notice(payload: dict[str, Any], notice: str) -> None:
    if "instructions" in payload:
        payload["instructions"] = _merge_responses_instructions(notice, payload.get("instructions"))
        return
    if "system" in payload:
        payload["system"] = _merge_system_text(notice, payload.get("system"))
        return
    if isinstance(payload.get("messages"), list):
        payload["messages"].insert(0, {"role": "system", "content": notice})
        return
    payload["instructions"] = notice


def _inject_build_mode_artifact_instruction(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    original_body: dict[str, Any],
    original_tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if os.getenv("ONEWORD_BUILD_MODE", "").lower() not in {"1", "true", "yes", "on"}:
        return payload
    build_mode = metadata.get("oneword_build_mode")
    if not isinstance(build_mode, dict) or build_mode.get("failure_gate_locked"):
        return payload
    workspace = metadata.get("workspace") or metadata.get("workspace_root")
    if not isinstance(workspace, str) or not workspace:
        return payload
    user_text = _build_mode_original_request_text(original_body)
    from .build_mode_equilibrium import balance_to_dict, decide_equilibrium, infer_repair_target_path
    from .build_mode_orchestrator import artifact_plan_for_request, detect_artifact_gaps, ensure_support_files
    from .build_mode_permissions import canonical_tool_schema, filter_tools_schema, write_file_fallback_schema
    from .build_mode_sovereignty import (
        audit_environment_gate,
        audit_workspace_sovereignty,
        environment_gate_to_dict,
        workspace_sovereignty_to_dict,
    )

    plan = artifact_plan_for_request(user_text)
    if not plan.artifacts:
        return payload
    env_report = None
    if os.getenv("ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS", "").lower() in {"1", "true", "yes", "on"}:
        env_python = os.getenv("ONEWORD_BUILD_MODE_PYTHON") or sys.executable
        env_report = audit_environment_gate(plan, python_executable=env_python)
        if not env_report.ok:
            rewritten = deepcopy(payload)
            if "tools" in rewritten:
                rewritten["tools"] = []
            rewritten.pop("tool_choice", None)
            instruction = _build_mode_environment_gate_instruction(env_report)
            _inject_build_mode_instruction(rewritten, instruction)
            existing = dict(metadata.get("oneword_build_mode") or {})
            existing.update({"hexagram": "100", "source": "sovereignty_environment_gate"})
            metadata["oneword_build_mode"] = existing
            metadata["build_mode_sovereignty"] = {
                "environment_gate": environment_gate_to_dict(env_report),
            }
            metadata["kernel_policy"] = {
                **dict(metadata.get("kernel_policy") or {}),
                "halt_model_forwarding": True,
                "source": "sovereignty_environment_gate",
            }
            return rewritten
    workspace_report = audit_workspace_sovereignty(workspace, plan)
    if not workspace_report.ok:
        rewritten = deepcopy(payload)
        if "tools" in rewritten:
            rewritten["tools"] = []
        rewritten.pop("tool_choice", None)
        instruction = _build_mode_workspace_gate_instruction(workspace_report)
        _inject_build_mode_instruction(rewritten, instruction)
        existing = dict(metadata.get("oneword_build_mode") or {})
        existing.update({"hexagram": "100", "source": "sovereignty_workspace_gate"})
        metadata["oneword_build_mode"] = existing
        sovereignty_metadata: dict[str, Any] = {
            "workspace_gate": workspace_sovereignty_to_dict(workspace_report),
        }
        if env_report is not None:
            sovereignty_metadata["environment_gate"] = environment_gate_to_dict(env_report)
        metadata["build_mode_sovereignty"] = sovereignty_metadata
        metadata["kernel_policy"] = {
            **dict(metadata.get("kernel_policy") or {}),
            "halt_model_forwarding": True,
            "source": "sovereignty_workspace_gate",
        }
        return rewritten
    support_files = ensure_support_files(workspace, plan)
    gap = detect_artifact_gaps(workspace, plan)
    state = _build_mode_state_for_metadata(metadata)
    repair_target_path = infer_repair_target_path(state, tuple(gap.present_paths))
    decision = decide_equilibrium(
        gap,
        state,
        repair_target_path=repair_target_path,
        available_tools=original_tools or payload.get("tools", []),
    )
    rewritten = deepcopy(payload)
    if "tools" in rewritten:
        source_tools = original_tools or rewritten.get("tools", [])
        if decision.force_empty_tools:
            rewritten["tools"] = []
        elif decision.tool_name == "write_file":
            tools = write_file_fallback_schema(source_tools)
            if not tools:
                tools = canonical_tool_schema("111", source_tools)
            if decision.target_path:
                _restrict_write_file_tool_path(tools, decision.target_path)
            rewritten["tools"] = tools
        elif decision.tool_name == "run_pytest":
            tools = filter_tools_schema("001", source_tools)
            if not tools:
                tools = canonical_tool_schema("001", source_tools)
            rewritten["tools"] = tools
        if decision.tool_name:
            _force_tool_choice(rewritten, decision.tool_name)
    _inject_build_mode_instruction(rewritten, decision.instruction)
    existing = dict(metadata.get("oneword_build_mode") or {})
    existing.update({"hexagram": decision.hexagram, "source": decision.source})
    metadata["oneword_build_mode"] = existing
    metadata["build_mode_equilibrium"] = {
        "hexagram": decision.hexagram,
        "source": decision.source,
        "shadow_action": decision.shadow_action,
        "tool_name": decision.tool_name,
        "target_path": decision.target_path,
        "balance": balance_to_dict(decision.balance),
    }
    if decision.source == "artifact_continuation_gate":
        metadata["build_mode_artifact_instruction"] = decision.instruction
        decision_metadata = dict(decision.metadata or {})
        decision_metadata["support_files"] = list(support_files)
        metadata[decision.metadata_key] = decision_metadata
    elif decision.metadata_key:
        metadata[decision.metadata_key] = dict(decision.metadata or {})
    return rewritten


def _restrict_write_file_tool_path(tools: list[dict[str, Any]], target_path: str) -> None:
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        schema = None
        if isinstance(tool.get("function"), dict):
            schema = tool["function"].get("parameters")
        else:
            schema = tool.get("parameters") or tool.get("input_schema")
        if not isinstance(schema, dict):
            continue
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            continue
        path_property = properties.get("path")
        if not isinstance(path_property, dict):
            continue
        path_property["enum"] = [target_path]


def _build_mode_environment_gate_instruction(report: Any) -> str:
    missing = ", ".join(report.missing_packages) or "unknown"
    return (
        "Missing Environment Gate: Build Mode halted before artifact generation because the "
        f"configured Python environment lacks required packages: {missing}. "
        "不要自造 fastapi/sqlmodel/pytest shim，也不要在工作区伪造第三方依赖模块。 "
        "Install or select a real isolated environment, then retry."
    )


def _build_mode_workspace_gate_instruction(report: Any) -> str:
    unplanned = ", ".join(report.unplanned_paths[:8]) or "unknown"
    return (
        "Workspace Sovereignty Gate: detected 未授权本地造物 in the workspace: "
        f"{unplanned}. Build Mode halted and all tools are withheld. "
        "Remove unplanned shim files and resume only through the scoped RequiredArtifactPlan."
    )


def _inject_build_mode_instruction(payload: dict[str, Any], instruction: str) -> None:
    if "instructions" in payload:
        payload["instructions"] = _merge_responses_instructions(instruction, payload.get("instructions"))
    elif "system" in payload:
        payload["system"] = _merge_system_text(instruction, payload.get("system"))
    elif isinstance(payload.get("messages"), list):
        messages = payload["messages"]
        messages.insert(1 if messages and messages[0].get("role") == "system" else 0, {"role": "system", "content": instruction})
    else:
        payload["instructions"] = instruction


def _force_tool_choice(payload: dict[str, Any], tool_name: str) -> None:
    tools = payload.get("tools")
    if not isinstance(tools, list) or not tools:
        return
    first = tools[0]
    if isinstance(first, dict) and "function" in first:
        payload["tool_choice"] = {"type": "function", "function": {"name": tool_name}}
    else:
        payload["tool_choice"] = {"type": "function", "name": tool_name}


def _build_mode_original_request_text(body: dict[str, Any]) -> str:
    values: list[str] = []
    input_value = body.get("input")
    if isinstance(input_value, str):
        values.append(input_value)
    elif isinstance(input_value, list):
        values.append(json.dumps(input_value, ensure_ascii=False))
    for message in body.get("messages", []) if isinstance(body.get("messages"), list) else []:
        if isinstance(message, dict):
            values.append(str(message.get("content") or ""))
    for key in ("instructions", "system"):
        value = body.get(key)
        if isinstance(value, str):
            values.append(value)
    return "\n".join(value for value in values if value)


def _build_mode_state_permission_override_applied(metadata: dict[str, Any]) -> bool:
    build_mode = metadata.get("oneword_build_mode")
    return isinstance(build_mode, dict) and build_mode.get("source") == "state_next_hexagram"


def _build_mode_state_context_for_metadata(metadata: dict[str, Any]) -> str:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return ""
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return _format_build_mode_state_context(state)


def _build_mode_state_next_hexagram_for_metadata(metadata: dict[str, Any]) -> str:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return ""
    state = _read_build_mode_state(state_path)
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        next_hexagram = str(result.get("next_hexagram") or "")
        if next_hexagram:
            return next_hexagram
    return ""


def _build_mode_state_consecutive_failures_for_metadata(metadata: dict[str, Any]) -> int:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return 0
    state = _read_build_mode_state(state_path)
    failures = state.get("consecutive_failures")
    return failures if isinstance(failures, int) else 0


def _build_mode_state_fallback_tools_for_metadata(metadata: dict[str, Any]) -> list[str]:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return []
    state = _read_build_mode_state(state_path)
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        fallback_tools = result.get("fallback_tools")
        if isinstance(fallback_tools, list):
            return [str(item) for item in fallback_tools]
    return []


def _build_mode_state_deadlock_suspected_for_metadata(metadata: dict[str, Any]) -> bool:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return False
    state = _read_build_mode_state(state_path)
    results = state.get("results") if isinstance(state.get("results"), list) else []
    for result in reversed(results):
        if not isinstance(result, dict):
            continue
        decay = result.get("decay")
        if isinstance(decay, dict) and decay.get("deadlock_suspected") is True:
            return True
        break
    return False


def _build_mode_state_for_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    state_path = _build_mode_state_path_for_metadata(metadata)
    if state_path is None or not state_path.exists():
        return {}
    return _read_build_mode_state(state_path)


def _build_mode_state_path_for_metadata(metadata: dict[str, Any]) -> Path | None:
    workspace = metadata.get("workspace") or metadata.get("workspace_root")
    if not isinstance(workspace, str) or not workspace:
        return None
    return _build_mode_state_path(Path(workspace).resolve(), metadata)


def _build_mode_state_path(workspace: Path, metadata: dict[str, Any]) -> Path:
    session_key = _build_mode_session_key(metadata)
    if not session_key:
        return workspace / ".yizijue" / "build-mode-state.json"
    return workspace / ".yizijue" / f"build-mode-state-{session_key}.json"


def _attach_build_mode_session_metadata(metadata: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    session_id = _extract_build_mode_session_id(body)
    if not session_id:
        return metadata
    enriched = dict(metadata)
    enriched["session_id"] = session_id
    return enriched


def _attach_build_mode_request_metadata(metadata: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    request_text = _build_mode_original_request_text(body)
    if not request_text:
        return metadata
    enriched = dict(metadata)
    enriched["request_text"] = request_text
    enriched["original_request"] = request_text
    return enriched


def _attach_configured_workspace(
    metadata: dict[str, Any],
    body: dict[str, Any],
    workspace_root: str | None,
) -> dict[str, Any]:
    if not workspace_root:
        return metadata
    root = Path(workspace_root).resolve()
    requested = _request_workspace_from_body(body)
    workspace = root
    if requested:
        candidate = Path(requested).resolve()
        try:
            candidate.relative_to(root)
            workspace = candidate
        except ValueError:
            workspace = root
    enriched = dict(metadata)
    enriched["workspace"] = str(workspace)
    return enriched


def _request_workspace_from_body(body: dict[str, Any]) -> str:
    metadata = body.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("workspace") or metadata.get("workspace_root")
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("workspace", "workspace_root"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_build_mode_session_id(body: dict[str, Any]) -> str:
    for key in ("session_id", "conversation_id", "thread_id"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    metadata = body.get("metadata")
    if isinstance(metadata, dict):
        for key in ("session_id", "conversation_id", "thread_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _build_mode_session_key(metadata: dict[str, Any]) -> str:
    for key in ("session_id", "conversation_id", "thread_id"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())[:96].strip(".-")
            return safe or "session"
    return ""


def _merge_system_text(context: str, existing_system: Any) -> str | list[dict[str, Any]]:
    if not existing_system:
        return context
    if isinstance(existing_system, str):
        return f"{context}\n\n{existing_system}"
    if isinstance(existing_system, list):
        return [{"type": "text", "text": context}, *existing_system]
    return f"{context}\n\n{existing_system}"


def _format_build_mode_state_context(state: dict[str, Any]) -> str:
    results = state.get("results") if isinstance(state.get("results"), list) else []
    repair_card = str(state.get("repair_card") or "")
    repo_card = str(state.get("repo_card") or "")
    lines = ["Build Mode Context:"]
    for index, result in enumerate(results[:5], start=1):
        if not isinstance(result, dict):
            continue
        changed_files = result.get("changed_files")
        file_text = ""
        if isinstance(changed_files, list) and changed_files:
            file_text = " files=" + ",".join(str(item) for item in changed_files)
        lines.append(
            " ".join(
                [
                    f"{index}.",
                    f"status={result.get('status')}",
                    f"hexagram={result.get('hexagram')}",
                    f"next={result.get('next_hexagram')}",
                    f"action={result.get('shadow_action')}",
                    file_text,
                ]
            ).strip()
        )
    if repair_card:
        lines.extend(["Repair Card:", repair_card])
    if repo_card:
        lines.extend(["Repo Card:", repo_card])
    return "\n".join(lines).strip()


def _response_has_chat_tool_calls(payload: dict[str, Any]) -> bool:
    return any(True for _ in _iter_openai_chat_tool_calls(payload))


def _response_has_responses_tool_calls(payload: dict[str, Any]) -> bool:
    return any(True for _ in _iter_openai_responses_tool_calls(payload))


def _response_has_anthropic_tool_uses(payload: dict[str, Any]) -> bool:
    return any(True for _ in _iter_anthropic_tool_uses(payload))


def _iter_openai_chat_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for choice in payload.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls", []) or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function", {})
            if not isinstance(function, dict):
                function = {}
            name = str(function.get("name") or call.get("name") or "")
            if not name:
                continue
            calls.append(
                {
                    "id": str(call.get("id") or ""),
                    "name": name,
                    "arguments": _parse_chat_tool_arguments(
                        function.get("arguments", call.get("arguments", {}))
                    ),
                }
            )
    return calls


def _iter_anthropic_tool_uses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    content = payload.get("content")
    if not isinstance(content, list):
        return calls
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = str(block.get("name") or "")
        if not name:
            continue
        calls.append(
            {
                "id": str(block.get("id") or ""),
                "name": name,
                "arguments": block.get("input", {}),
            }
        )
    return calls


def _iter_openai_responses_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    output = payload.get("output")
    if not isinstance(output, list):
        return calls
    for item in output:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "") not in {"function_call", "tool_call"}:
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        calls.append(
            {
                "id": str(item.get("call_id") or item.get("id") or ""),
                "name": name,
                "arguments": _parse_chat_tool_arguments(item.get("arguments", {})),
            }
        )
    return calls


def _parse_chat_tool_arguments(value: Any) -> Any:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"command": value}
        return decoded
    return value


def _responses_message_item(text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }


def _build_mode_tool_results_summary(results: list[dict[str, Any]]) -> str:
    lines = ["Build Mode Evidence:"]
    for index, result in enumerate(results, start=1):
        status = str(result.get("status") or "unknown")
        hexagram = str(result.get("hexagram") or "")
        next_hexagram = str(result.get("next_hexagram") or result.get("final_next_hexagram") or "")
        action = str(result.get("shadow_action") or "")
        evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
        changed_files = evidence.get("changed_files") if isinstance(evidence, dict) else None
        detail = ""
        if isinstance(changed_files, list) and changed_files:
            detail = f" files={','.join(str(item) for item in changed_files)}"
        lines.append(
            f"{index}. status={status} hexagram={hexagram} next={next_hexagram} action={action}{detail}".strip()
        )
    return "\n".join(lines)


def _append_build_mode_debug_record(
    event: str,
    metadata: dict[str, Any],
    detail: dict[str, Any],
) -> None:
    path = os.getenv("ONEWORD_BUILD_MODE_DEBUG_LOG")
    if not path:
        return
    record = {
        "event": event,
        "metadata": {
            "root_opcode": metadata.get("root_opcode"),
            "active_code": metadata.get("active_code"),
            "workspace": metadata.get("workspace") or metadata.get("workspace_root"),
            "oneword_build_mode": metadata.get("oneword_build_mode"),
            "zero_tool_fast_path": metadata.get("zero_tool_fast_path"),
        },
        "detail": detail,
    }
    try:
        debug_path = Path(path)
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return


def _debug_tool_schema_summary(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    summary: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        schema = tool.get("parameters") if isinstance(tool.get("parameters"), dict) else tool.get("input_schema")
        if not isinstance(schema, dict):
            schema = {}
        summary.append(
            {
                "name": str(tool.get("name") or tool.get("type") or ""),
                "required": schema.get("required"),
                "properties": sorted((schema.get("properties") or {}).keys())
                if isinstance(schema.get("properties"), dict)
                else [],
            }
        )
    return summary


def _debug_chat_tool_schema_summary(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    summary: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        schema = function.get("parameters") if isinstance(function.get("parameters"), dict) else {}
        summary.append(
            {
                "name": str(function.get("name") or tool.get("name") or ""),
                "required": schema.get("required"),
                "properties": sorted((schema.get("properties") or {}).keys())
                if isinstance(schema.get("properties"), dict)
                else [],
            }
        )
    return summary


def _debug_responses_tool_call_summary(payload: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for call in _iter_openai_responses_tool_calls(payload):
        arguments = call.get("arguments")
        if isinstance(arguments, dict):
            keys = sorted(arguments.keys())
            lengths = {key: len(str(arguments.get(key) or "")) for key in keys}
        else:
            keys = []
            lengths = {}
        calls.append(
            {
                "name": call.get("name"),
                "argument_keys": keys,
                "argument_lengths": lengths,
            }
        )
    return calls


def _sse_event(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def inspect_stream_chunk_for_policy(
    metadata: dict[str, Any],
    chunks: list[bytes | str],
) -> tuple[dict[str, Any], int]:
    if metadata.get("zero_tool_fast_path"):
        return (
            {
                "stream_guard": {
                    "allowed": True,
                    "inspected_chunks": 0,
                    "mode": "bypassed_zero_tool",
                }
            },
            200,
        )
    interceptor = StreamBufferInterceptor(metadata)
    buffered_chunks: list[bytes | str] = []
    for chunk in chunks:
        buffered_chunks.append(chunk)
        violation = interceptor.feed(chunk)
        if violation is not None:
            if _build_mode_response_execution_enabled(metadata):
                tool_payload = _build_mode_stream_tool_payload(metadata, buffered_chunks)
                if tool_payload is not None:
                    return tool_payload, 200
            return build_stream_tool_block_response(metadata, violation)
    if _build_mode_response_execution_enabled(metadata):
        tool_payload = _build_mode_stream_tool_payload(metadata, buffered_chunks)
        if tool_payload is not None:
            return tool_payload, 200
    return (
        {
            "stream_guard": {
                "allowed": True,
                "inspected_chunks": len(chunks),
            }
        },
        200,
    )


def _build_mode_stream_tool_payload(metadata: dict[str, Any], chunks: list[bytes | str]) -> dict[str, Any] | None:
    text = "".join(
        chunk.decode("utf-8", errors="ignore") if isinstance(chunk, bytes) else str(chunk)
        for chunk in chunks
    )
    calls = [*_extract_openai_stream_tool_calls(text), *_extract_anthropic_stream_tool_uses(text)]
    if not calls:
        return None
    workspace = str(metadata.get("workspace") or metadata.get("workspace_root") or "")
    if not workspace:
        return _build_mode_stream_workspace_missing_payload(metadata, len(calls))
    results = [
        build_tool_payload(
            _build_mode_internal_tool_body(workspace, call, metadata)
        )
        for call in calls
    ]
    _persist_build_mode_state(workspace, results, metadata)
    summary = _build_mode_tool_results_summary(results)
    return {
        "choices": [{"delta": {"content": summary}, "finish_reason": "stop"}],
        "yizijue_gateway": {
            **metadata,
            "response_mode": "build_mode_tool_execution",
            "stream_guard": {
                "allowed": True,
                "executed_tool_calls": len(calls),
            },
            "build_mode_tool_results": results,
        },
    }


def _build_mode_stream_workspace_missing_payload(metadata: dict[str, Any], call_count: int) -> dict[str, Any]:
    message = (
        "Kernel Notice: Build Mode blocked streamed tool execution because workspace is not configured. "
        "Set ONEWORD_WORKSPACE_ROOT before enabling streamed build tools."
    )
    return {
        "choices": [{"delta": {"content": message}, "finish_reason": "stop"}],
        "yizijue_gateway": {
            **metadata,
            "blocked": True,
            "response_mode": "soft_rewrite",
            "stream_guard": {
                "allowed": False,
                "executed_tool_calls": 0,
                "detected_tool_calls": call_count,
                "reason": "workspace_missing",
            },
        },
    }


def _extract_openai_stream_tool_calls(text: str) -> list[dict[str, Any]]:
    calls_by_index: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("data:"):
            continue
        data = stripped[len("data:") :].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices", []) if isinstance(payload, dict) else []:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta", {})
            if not isinstance(delta, dict):
                continue
            for call in delta.get("tool_calls", []) or []:
                if not isinstance(call, dict):
                    continue
                index = _stream_tool_call_index(call, calls_by_index)
                current = calls_by_index.setdefault(index, {"id": "", "name": "", "arguments_text": ""})
                if call.get("id"):
                    current["id"] = str(call.get("id"))
                function = call.get("function", {})
                if not isinstance(function, dict):
                    function = {}
                name = str(function.get("name") or call.get("name") or "")
                if name:
                    current["name"] = name
                arguments = function.get("arguments", call.get("arguments", ""))
                if isinstance(arguments, str):
                    current["arguments_text"] = str(current.get("arguments_text") or "") + arguments
                elif arguments:
                    current["arguments"] = arguments
    calls: list[dict[str, Any]] = []
    for current in calls_by_index.values():
        name = str(current.get("name") or "")
        if not name:
            continue
        raw_arguments = current.get("arguments", current.get("arguments_text", {}))
        parsed_arguments = _parse_stream_tool_arguments(raw_arguments)
        if parsed_arguments is None:
            continue
        calls.append(
            {
                "id": str(current.get("id") or ""),
                "name": name,
                "arguments": parsed_arguments,
            }
        )
    return calls


def _parse_stream_tool_arguments(value: Any) -> Any | None:
    if isinstance(value, str):
        if not value.strip():
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _stream_tool_call_index(call: dict[str, Any], calls_by_index: dict[int, dict[str, Any]]) -> int:
    raw_index = call.get("index")
    if isinstance(raw_index, int):
        return raw_index
    return len(calls_by_index)


def _extract_anthropic_stream_tool_uses(text: str) -> list[dict[str, Any]]:
    calls_by_index: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("data:"):
            continue
        data = stripped[len("data:") :].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        block = payload.get("content_block")
        index = payload.get("index")
        if not isinstance(index, int):
            index = len(calls_by_index)
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = str(block.get("name") or "")
            if not name:
                continue
            current = calls_by_index.setdefault(index, {"id": "", "name": "", "arguments_text": ""})
            current["id"] = str(block.get("id") or "")
            current["name"] = name
            input_value = block.get("input")
            if isinstance(input_value, dict) and input_value:
                current["arguments"] = input_value
        delta = payload.get("delta")
        if isinstance(delta, dict) and delta.get("type") == "input_json_delta":
            current = calls_by_index.setdefault(index, {"id": "", "name": "", "arguments_text": ""})
            current["arguments_text"] = str(current.get("arguments_text") or "") + str(
                delta.get("partial_json") or ""
            )
    calls: list[dict[str, Any]] = []
    for current in calls_by_index.values():
        name = str(current.get("name") or "")
        if not name:
            continue
        raw_arguments = current.get("arguments", current.get("arguments_text", {}))
        parsed_arguments = _parse_stream_tool_arguments(raw_arguments)
        if parsed_arguments is None:
            continue
        if isinstance(parsed_arguments, dict) and not parsed_arguments:
            continue
        calls.append(
            {
                "id": str(current.get("id") or ""),
                "name": name,
                "arguments": parsed_arguments,
            }
        )
    return calls


def _responses_to_chat_request(body: dict[str, Any]) -> dict[str, Any]:
    chat_body: dict[str, Any] = {
        "model": body.get("model"),
        "messages": _responses_input_to_chat_messages(body.get("input")),
    }
    if body.get("instructions"):
        chat_body["messages"].insert(0, {"role": "system", "content": str(body.get("instructions"))})
    if "tools" in body:
        chat_body["tools"] = _responses_tools_to_chat_tools(body.get("tools"))
    if "temperature" in body:
        chat_body["temperature"] = body.get("temperature")
    if "max_output_tokens" in body:
        chat_body["max_tokens"] = body.get("max_output_tokens")
    return chat_body


def _native_inspect_text_for_responses(metadata: dict[str, Any]) -> str:
    workspace = metadata.get("workspace") or metadata.get("workspace_root")
    if isinstance(workspace, str) and workspace:
        try:
            from .inspect_executor import build_native_inspect_card

            return build_native_inspect_card(workspace, max_chars=1200)["text"]
        except (OSError, ValueError):
            return (
                "[State]: 101-INSPECT | [Target]: *\n"
                "[Files]: native inspect card unavailable in gateway response context\n"
                "[Symbols]: unavailable\n"
                "[Imports]: unavailable\n"
                "[Risks]: none"
            )
    return (
        "[State]: 101-INSPECT | [Target]: *\n"
        "[Files]: workspace unavailable\n"
        "[Symbols]: unavailable\n"
        "[Imports]: unavailable\n"
        "[Risks]: none"
    )


def _responses_input_to_chat_messages(value: Any) -> list[dict[str, str]]:
    if isinstance(value, str):
        return [{"role": "user", "content": value}]
    if isinstance(value, list):
        messages: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "user")
            content = _responses_content_to_text(item.get("content", ""))
            if content:
                messages.append({"role": role, "content": content})
        if messages:
            return messages
    return [{"role": "user", "content": str(value or "")}]


def _responses_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _responses_tools_to_chat_tools(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    converted: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or tool.get("type") or "")
        if not name:
            continue
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": str(tool.get("description") or ""),
                    "parameters": tool.get("parameters") or {"type": "object"},
                },
            }
        )
    return converted


def _responses_tool_choice_to_chat_tool_choice(tool_choice: Any) -> Any:
    if not isinstance(tool_choice, dict):
        return tool_choice
    name = str(tool_choice.get("name") or "")
    if not name and isinstance(tool_choice.get("function"), dict):
        name = str(tool_choice["function"].get("name") or "")
    if str(tool_choice.get("type") or "") == "function" and name:
        return {"type": "function", "function": {"name": name}}
    return tool_choice


def _merge_responses_instructions(system_instruction: str, existing: Any) -> str:
    if not existing:
        return system_instruction
    return f"{system_instruction}\n\n上游原始 instructions:\n{existing}"


def _chat_messages_to_responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": str(message.get("role") or "user"),
            "content": [
                {
                    "type": "input_text",
                    "text": str(message.get("content") or ""),
                }
            ],
        }
        for message in messages
        if str(message.get("role") or "") != "system"
    ]


def _responses_to_chat_completion_payload(payload: dict[str, Any]) -> dict[str, Any]:
    tool_calls: list[dict[str, Any]] = []
    content = str(payload.get("output_text") or "")
    for item in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "")
        if item_type in {"function_call", "tool_call"}:
            tool_calls.append(
                {
                    "type": "function",
                    "function": {
                        "name": str(item.get("name") or item.get("type") or ""),
                        "arguments": item.get("arguments") or {},
                    },
                }
            )
        if item_type == "message" and not content:
            content = _responses_content_to_text(item.get("content", ""))
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": payload.get("id"),
        "choices": [
            {
                "message": message,
                "finish_reason": "tool_calls" if tool_calls else "stop",
            }
        ],
        "usage": _responses_usage_to_chat_usage(payload.get("usage")),
    }


def _chat_completion_to_responses_payload(payload: dict[str, Any]) -> dict[str, Any]:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = str(message.get("content") or "")
    output: list[dict[str, Any]] = []
    tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
    if isinstance(tool_calls, list) and tool_calls:
        for call in tool_calls:
            function = call.get("function", {}) if isinstance(call, dict) else {}
            output.append(
                {
                    "type": "function_call",
                    "name": str(function.get("name") or call.get("name") or ""),
                    "arguments": function.get("arguments") or call.get("arguments") or {},
                }
            )
    else:
        output.append(
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
            }
        )
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {
        "id": payload.get("id"),
        "object": "response",
        "status": "completed",
        "model": payload.get("model"),
        "output": output,
        "output_text": content,
        "usage": {
            "input_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
            "output_tokens": usage.get("output_tokens", usage.get("completion_tokens", 0)),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def _responses_usage_to_chat_usage(usage: Any) -> dict[str, Any]:
    if not isinstance(usage, dict):
        return {}
    return {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
        "total_tokens": usage.get("total_tokens", 0),
    }


def _is_stream_soft_rewrite(payload: dict[str, Any]) -> bool:
    gateway = payload.get("yizijue_gateway", {})
    return bool(gateway.get("blocked") and gateway.get("response_mode") == "soft_rewrite")


def _is_stream_gateway_rewrite(payload: dict[str, Any]) -> bool:
    gateway = payload.get("yizijue_gateway", {})
    return bool(
        gateway.get("response_mode") in {"soft_rewrite", "build_mode_tool_execution"}
    )


def _openai_stream_notice_chunk(payload: dict[str, Any]) -> bytes:
    content = str(payload.get("choices", [{}])[0].get("delta", {}).get("content", ""))
    escaped = content.replace("\\", "\\\\").replace('"', '\\"')
    return f'data: {{"choices":[{{"delta":{{"content":"{escaped}"}},"finish_reason":"stop"}}]}}\n\n'.encode(
        "utf-8"
    )


def _anthropic_stream_notice_chunk(payload: dict[str, Any]) -> bytes:
    content = str(payload.get("choices", [{}])[0].get("delta", {}).get("content", ""))
    escaped = content.replace("\\", "\\\\").replace('"', '\\"')
    return f'event: content_block_delta\ndata: {{"delta":{{"type":"text_delta","text":"{escaped}"}}}}\n\n'.encode(
        "utf-8"
    )


def _upstream_headers(
    inbound_headers: Any,
    upstream_api_key: str | None | object = _DEFAULT_UPSTREAM_API_KEY,
) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    api_key = UPSTREAM_API_KEY if upstream_api_key is _DEFAULT_UPSTREAM_API_KEY else upstream_api_key
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    return headers


def _anthropic_upstream_headers(
    inbound_headers: Any,
    upstream_api_key: str | None | object = _DEFAULT_UPSTREAM_API_KEY,
) -> dict[str, str]:
    headers = {
        "content-type": "application/json",
        "anthropic-version": str(inbound_headers.get("anthropic-version", "2023-06-01")),
    }
    api_key = ANTHROPIC_API_KEY if upstream_api_key is _DEFAULT_UPSTREAM_API_KEY else upstream_api_key
    if api_key:
        headers["x-api-key"] = str(api_key)
    return headers


def gateway_request_authorized(
    inbound_headers: Any,
    required_token: str | None = None,
) -> bool:
    token = required_token if required_token is not None else os.getenv("ONEWORD_GATEWAY_TOKEN")
    if not token:
        return False
    authorization = str(inbound_headers.get("authorization", ""))
    if authorization.startswith("Bearer ") and hmac.compare_digest(authorization[7:], token):
        return True
    if hmac.compare_digest(str(inbound_headers.get("x-oneword-token", "")), token):
        return True
    return hmac.compare_digest(str(inbound_headers.get("x-api-key", "")), token)


def gateway_unauthorized_response() -> dict[str, Any]:
    return {
        "status": "rejected",
        "error": {
            "type": "unauthorized",
            "message": "Missing or invalid 一字诀 gateway token.",
        },
    }


async def _request_json_payload(request: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        body = await request.json()
    except Exception as exc:
        return {}, {
            "status_code": 400,
            "payload": {
                "error": {
                    "type": "invalid_json",
                    "message": "Request body must be valid JSON.",
                    "detail": exc.__class__.__name__,
                },
                "yizijue_gateway": {"blocked": True},
            },
        }
    if not isinstance(body, dict):
        return {}, {
            "status_code": 400,
            "payload": {
                "error": {
                    "type": "invalid_json",
                    "message": "Request JSON body must be an object.",
                },
                "yizijue_gateway": {"blocked": True},
            },
        }
    return body, None


def authorize_preflight_request(
    inbound_headers: Any,
    required_token: str | None = None,
    protect_preflight: bool | None = None,
) -> None:
    protected = _preflight_protected() if protect_preflight is None else protect_preflight
    if protected and not gateway_request_authorized(inbound_headers, required_token=required_token):
        raise GatewayAuthRequired("preflight tool endpoint requires gateway authorization")


def control_plane_requires_upstream_key(path: str) -> bool:
    return path in {"/v1/chat/completions", "/v1/messages", "/v1/responses"}


def _preflight_protected() -> bool:
    return os.getenv("ONEWORD_PROTECT_PREFLIGHT", "1").lower() not in {"0", "false", "no", "off"}


def _evidence_payload_error(body: dict[str, Any]) -> dict[str, Any] | None:
    for field in ("stdout", "stderr"):
        value = str(body.get(field) or "")
        if len(value) > MAX_EVIDENCE_FIELD_CHARS:
            return {
                "status": "rejected",
                "error": {
                    "type": "evidence_payload_too_large",
                    "field": field,
                    "max_chars": MAX_EVIDENCE_FIELD_CHARS,
                },
            }
    return None


def _safe_metadata_value(value: Any) -> str:
    text = str(value)
    return text[:128]


def missing_upstream_key_response(provider: str = "openai") -> tuple[dict[str, Any], int]:
    return (
        {
            "error": {
                "type": "upstream_api_key_missing",
                "message": _missing_key_message(provider),
            },
            "yizijue_gateway": {
                "blocked": True,
            },
        },
        503,
    )


def _missing_key_message(provider: str) -> str:
    if provider == "anthropic":
        return "ONEWORD_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY must be configured on the gateway host."
    return "ONEWORD_UPSTREAM_API_KEY or OPENAI_API_KEY must be configured on the gateway host."


def readiness_payload(
    dictionary: dict[str, Any] | None,
    workspace_root: str | None = None,
    gateway_token: str | None = None,
    upstream_api_key: str | None = None,
    anthropic_api_key: str | None = None,
) -> dict[str, Any]:
    configured_workspace_root = (
        os.getenv("ONEWORD_WORKSPACE_ROOT") if workspace_root is None else workspace_root
    )
    configured_gateway_token = (
        os.getenv("ONEWORD_GATEWAY_TOKEN") if gateway_token is None else gateway_token
    )
    configured_upstream_api_key = UPSTREAM_API_KEY if upstream_api_key is None else upstream_api_key
    configured_anthropic_api_key = ANTHROPIC_API_KEY if anthropic_api_key is None else anthropic_api_key
    docker_required_for_verify = _env_flag("ONEWORD_REQUIRE_DOCKER_FOR_VERIFY")
    docker_available = bool(shutil.which("docker"))
    guard_scanner_required = _env_flag("ONEWORD_REQUIRE_GUARD_SCANNER")
    guard_scanner_types = _parse_scanner_types(os.getenv("ONEWORD_GUARD_SCANNER_TYPE")) or [
        "semgrep",
        "osv-scanner",
    ]
    semgrep_available = bool(shutil.which("semgrep"))
    osv_scanner_available = bool(shutil.which("osv-scanner"))
    scanner_available_by_name = {
        "semgrep": semgrep_available,
        "osv-scanner": osv_scanner_available,
    }
    guard_sandbox_ready = (not guard_scanner_required) or all(
        scanner_available_by_name.get(scanner, False) for scanner in guard_scanner_types
    )
    checks = {
        "dictionary_loaded": bool(dictionary and dictionary.get("entries")),
        "workspace_root_configured": bool(configured_workspace_root),
        "workspace_root_exists": bool(
            configured_workspace_root and Path(configured_workspace_root).resolve().exists()
        ),
        "gateway_token_configured": bool(configured_gateway_token),
        "upstream_api_key_configured": bool(configured_upstream_api_key),
        "anthropic_api_key_configured": bool(configured_anthropic_api_key),
        "docker_required_for_verify": docker_required_for_verify,
        "docker_available": docker_available,
        "guard_scanner_required": guard_scanner_required,
        "guard_scanner_types": guard_scanner_types,
        "semgrep_available": semgrep_available,
        "osv_scanner_available": osv_scanner_available,
    }
    control_plane_ready = all(
        checks[key]
        for key in (
            "dictionary_loaded",
            "workspace_root_configured",
            "workspace_root_exists",
            "gateway_token_configured",
        )
    )
    chat_proxy_ready = control_plane_ready and checks["upstream_api_key_configured"]
    anthropic_proxy_ready = control_plane_ready and checks["anthropic_api_key_configured"]
    verify_sandbox_ready = (not docker_required_for_verify) or docker_available
    return {
        "ready": control_plane_ready,
        "control_plane_ready": control_plane_ready,
        "chat_proxy_ready": chat_proxy_ready,
        "anthropic_proxy_ready": anthropic_proxy_ready,
        "verify_sandbox_ready": verify_sandbox_ready,
        "guard_sandbox_ready": guard_sandbox_ready,
        "checks": checks,
        "dictionary_path": DICTIONARY_PATH,
    }


def _workspace_error(workspace: str, require_configured_root: bool = False) -> dict[str, Any] | None:
    allowed_root = os.getenv("ONEWORD_WORKSPACE_ROOT")
    if not allowed_root:
        if require_configured_root:
            return {
                "status": "rejected",
                "error": {
                    "type": "workspace_root_required",
                    "message": "ONEWORD_WORKSPACE_ROOT must be configured before executing /v1/yizijue/run.",
                },
            }
        return None
    workspace_path = Path(workspace).resolve()
    root = Path(allowed_root).resolve()
    if workspace_path == root or root in workspace_path.parents:
        return None
    return {
        "status": "rejected",
        "error": {
            "type": "workspace_not_allowed",
            "message": "Workspace must be inside ONEWORD_WORKSPACE_ROOT.",
            "workspace": str(workspace_path),
            "allowed_root": str(root),
        },
    }


def _verification_command_error(command: Any) -> dict[str, Any] | None:
    if command is None:
        return None
    if not _verification_command_allowed(command):
        return {
            "status": "rejected",
            "error": {
                "type": "verification_command_not_allowed",
                "message": "verification_command must be an approved test command.",
            },
        }
    return None


def _verification_command_allowed(command: Any) -> bool:
    if not isinstance(command, list) or not command:
        return False
    parts = [str(item) for item in command]
    executable = Path(parts[0]).name
    if executable in {"pytest", "py.test"}:
        return True
    if executable not in {"python", "python3"}:
        return False
    if len(parts) >= 3 and parts[1] == "-m" and parts[2] in {"unittest", "pytest"}:
        return True
    return False


try:
    app = create_app()
except RuntimeError:
    app = None


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_scanner_types(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or None
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()] or None
    return None
