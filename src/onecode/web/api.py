# ruff: noqa: F403, F405
"""OneCode HTTP API."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from onecode.web.auth import LOOPBACK_HOSTS, local_request_allowed, request_authorized
from onecode.web.request_body import read_json_request_body
from onecode.web.responses import encode_json_payload, error_payload
from onecode.web.workspace import workspace_from_request  # noqa: F401


from onecode.web.api_shell import *  # noqa: F403
from onecode.web.api_handlers import *  # noqa: F403
from onecode.kernel.diagnostics import run_doctor  # noqa: F401
from onecode.kernel.model_provider import api_key_from_env, build_provider_config  # noqa: F401
from onecode.kernel.path_guard import PathGuard  # noqa: F401
from onecode.kernel.run_inspection import inspect_run, list_runs  # noqa: F401
from onecode.kernel.run_id import validate_run_id  # noqa: F401
from onecode.kernel.runner import run_task  # noqa: F401
from onecode.kernel.shell_projection import (  # noqa: F401
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
)
from onecode.kernel.verifier import verifier_policy_presets_summary  # noqa: F401
from onecode.kernel.wal import global_wal_metrics_summary  # noqa: F401
from onecode.web.workspace import workspace_from_value  # noqa: F401
from onecode.kernel.model_config import discover_models, read_model_config, write_model_config  # noqa: F401
from onecode.kernel.model_loop import execute_model_plan, run_model_task  # noqa: F401
from onecode.kernel.run_inspection import ledger_matches_workspace  # noqa: F401
from onecode.self_audit import audit_self  # noqa: F401

class OneCodeRequestHandler(BaseHTTPRequestHandler):
    server_version = "OneCodeHTTP/1.0"
    timeout = 30

    def do_GET(self) -> None:
        if not self._local_boundary_allowed():
            return
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(gateway_console_html())
            return
        if path == "/health":
            self._send_json({"status": "ok", "service": "onecode"})
            return
        if path == "/v1/models":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            self._send_json(build_models_payload())
            return
        if path == "/v1/onecode/project/status":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_project_status({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/shell/schema":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_shell_schema()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/runs":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            payload, status_code = handle_onecode_runs_list(
                {
                    "workspace": query.get("workspace", [None])[0],
                    "limit": query.get("limit", [None])[0],
                }
            )
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/metrics":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            payload, status_code = handle_onecode_metrics(
                {
                    "workspace": query.get("workspace", [None])[0],
                    "window_seconds": query.get("window_seconds", [None])[0],
                }
            )
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/presets":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_verifier_presets()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_verifier_policy_get({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/model-config":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_model_config_get()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/approvals/pending":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_pending_approvals({"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/gateway/adjudicate":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if query.get("demo", [""])[0] in {"1", "true", "yes", "on"}:
                demo_prediction = json.dumps(
                    {
                        "action": "ALLOW_PATCH_WITH_SHA",
                        "facts": {
                            "evidence_state": "required",
                            "intent_type": "patch_text",
                            "path_scope": "workspace_relative",
                            "sandbox_state": "not_required",
                        },
                        "reason": "safe_workspace_patch",
                        "yizijue_state": "111111",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                payload, status_code = handle_onecode_gateway_adjudicate(
                    {
                        "user": "随便处理一下这个项目",
                        "prediction": demo_prediction,
                    }
                )
                self._send_json(payload, status_code=status_code)
                return
            self._send_json(
                {
                    "status": "ok",
                    "endpoint": "/v1/onecode/gateway/adjudicate",
                    "method": "POST",
                    "demo_url": "/v1/onecode/gateway/adjudicate?demo=1",
                    "required_fields": ["user", "prediction"],
                    "description": "Submit a model candidate JSON string for deterministic OneCode/YiZiJue adjudication.",
                }
            )
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/inspect"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/inspect").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_inspect(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/evidence"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/evidence").strip("/")
            parsed = urlparse(self.path)
            payload, status_code = handle_onecode_run_evidence(run_id, {"workspace": query_workspace_param(parsed.query)})
            self._send_json(payload, status_code=status_code)
            return
        self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)

    def do_POST(self) -> None:
        if not self._local_boundary_allowed():
            return
        path = urlparse(self.path).path
        if path == "/v1/onecode/project/init":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_project_init(body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/resume"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/resume").strip("/")
            payload, status_code = handle_onecode_run_resume(run_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/plans/") and path.endswith("/approval"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            plan_id = path.removeprefix("/v1/onecode/plans/").removesuffix("/approval").strip("/")
            payload, status_code = handle_onecode_plan_approval(plan_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/approvals/") and path.endswith("/resolve"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            approval_id = path.removeprefix("/v1/onecode/approvals/").removesuffix("/resolve").strip("/")
            payload, status_code = handle_onecode_approval_resolve(approval_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_verifier_policy_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/model-config":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_model_config_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/models/discover":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_models_discover(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/gateway/adjudicate":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json_or_send_error()
            if body is None:
                return
            payload, status_code = handle_onecode_gateway_adjudicate(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/doctor":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_doctor()
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/audit-self":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            payload, status_code = handle_onecode_audit_self()
            self._send_json(payload, status_code=status_code)
            return
        if path != "/v1/chat/completions":
            self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)
            return
        if not self._authorized():
            self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
            return
        body = self._read_json_or_send_error()
        if body is None:
            return
        if body.get("stream") is True:
            self._send_streaming_chat(body)
            return
        payload, status_code = handle_chat_completion(body)
        self._send_json(payload, status_code=status_code)

    def log_message(self, format: str, *args: Any) -> None:
        if os.getenv("ONECODE_HTTP_ACCESS_LOG", "").lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)

    def _local_boundary_allowed(self) -> bool:
        port = int(self.server.server_address[1])  # type: ignore
        if local_request_allowed(self.headers, bound_port=port):  # type: ignore
            return True
        self._send_json(
            error_payload("forbidden_origin", "request host or origin is not local"),
            status_code=403,
        )
        return False

    def _authorized(self) -> bool:
        allow_unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}
        host = self.server.server_address[0]  # type: ignore
        from onecode.kernel.deployment_boundary import api_token

        return request_authorized(
            dict(self.headers.items()),
            api_token() or None,
            allow_unauthenticated=allow_unauthenticated,
            host=host,
        )

    def _read_json(self) -> dict[str, Any] | None:
        return read_json_request_body(self.headers, self.rfile).payload  # type: ignore

    def _read_json_or_send_error(self) -> dict[str, Any] | None:
        result = read_json_request_body(self.headers, self.rfile)  # type: ignore
        if result.payload is not None:
            return result.payload
        self._send_json(
            error_payload(result.error_type or "invalid_json", result.error_message or "request body must be valid JSON"),
            status_code=result.status_code,
        )
        return None

    def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        encoded = encode_json_payload(payload)
        self.send_response(status_code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self, html: str, status_code: int = 200) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status_code)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_streaming_chat(self, body: dict[str, Any]) -> None:
        started = False

        def write(data: bytes) -> None:
            nonlocal started
            if not started:
                self.send_response(200)
                self.send_header("content-type", "text/event-stream; charset=utf-8")
                self.send_header("cache-control", "no-cache")
                self.send_header("connection", "close")
                self.end_headers()
                started = True
            self.wfile.write(data)
            self.wfile.flush()

        payload, status = stream_chat_completion(body, write)
        if not started:
            self._send_json(payload, status_code=status)


def run_server(host: str = "127.0.0.1", port: int = 19080) -> None:
    # Security check: non-loopback hosts must have a token configured
    from onecode.kernel.deployment_boundary import api_token

    token = api_token() or None
    allow_unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}

    if host not in LOOPBACK_HOSTS and allow_unauthenticated and not token:
        raise ValueError(
            f"Security error: Cannot bind to non-loopback host '{host}' with allow_unauthenticated=true and no ONECODE_API_TOKEN. "
            "Either bind to a loopback address (127.0.0.1, localhost, ::1), set ONECODE_API_TOKEN, or disable allow_unauthenticated."
        )

    server = ThreadingHTTPServer((host, port), OneCodeRequestHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()

