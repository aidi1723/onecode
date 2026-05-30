from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError
from onecode.kernel.runner import run_task


DEFAULT_MODEL_ID = "onecode-agent"


def build_models_payload() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL_ID,
                "object": "model",
                "created": 0,
                "owned_by": "onecode",
            }
        ],
    }


def request_authorized(headers: dict[str, str], token: str | None) -> bool:
    if token is None or token.strip() == "":
        return True
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    return authorization == f"Bearer {token}"


def latest_user_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        return message_content_to_text(message.get("content"))
    return ""


def message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def error_payload(error_type: str, message: str) -> dict[str, Any]:
    return {"error": {"type": error_type, "message": message}}


def chat_completion_payload(
    content: str,
    model: str,
    run_result: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    created = int(time.time())
    return {
        "id": f"onecode-{run_result.get('run_id') or created}",
        "object": "chat.completion",
        "created": created,
        "model": model or DEFAULT_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "onecode": {
            "mode": mode,
            "result": run_result,
        },
    }


def handle_chat_completion(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    user_message = latest_user_message(body.get("messages"))
    if user_message.strip() == "":
        return error_payload("invalid_request", "messages must include a user message"), 400

    workspace = Path(os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())).resolve()
    model = str(body.get("model") or DEFAULT_MODEL_ID)
    provider_kind = os.getenv("ONECODE_MODEL_PROVIDER", "responses")
    endpoint = os.getenv("ONECODE_MODEL_ENDPOINT") or None
    run_id = body.get("metadata", {}).get("run_id") if isinstance(body.get("metadata"), dict) else None
    try:
        result = run_model_task(
            user_message,
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
            model=None if model == DEFAULT_MODEL_ID else model,
            provider_kind=provider_kind,
            endpoint=endpoint,
        )
        mode = "model"
    except MissingModelApiKey:
        result = run_task(
            user_message,
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
        )
        mode = "rule_fallback"
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502

    content = format_run_result(result, mode)
    return chat_completion_payload(content, model, result, mode), 200


def format_run_result(result: dict[str, Any], mode: str) -> str:
    status = result.get("status")
    reason = result.get("reason")
    run_id = result.get("run_id")
    ledger_path = result.get("ledger_path")
    lines = [
        f"OneCode run `{run_id}` finished in `{mode}` mode.",
        f"Status: `{status}`.",
    ]
    if reason:
        lines.append(f"Reason: `{reason}`.")
    if ledger_path:
        lines.append(f"Evidence ledger: `{ledger_path}`.")
    return "\n".join(lines)


class OneCodeRequestHandler(BaseHTTPRequestHandler):
    server_version = "OneCodeHTTP/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json({"status": "ok", "service": "onecode"})
            return
        if path == "/v1/models":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            self._send_json(build_models_payload())
            return
        self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/v1/chat/completions":
            self._send_json(error_payload("not_found", f"unknown path: {path}"), status_code=404)
            return
        if not self._authorized():
            self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
            return
        body = self._read_json()
        if body is None:
            self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
            return
        payload, status_code = handle_chat_completion(body)
        self._send_json(payload, status_code=status_code)

    def log_message(self, format: str, *args: Any) -> None:
        if os.getenv("ONECODE_HTTP_ACCESS_LOG", "").lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)

    def _authorized(self) -> bool:
        return request_authorized(dict(self.headers.items()), os.getenv("ONECODE_API_TOKEN"))

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("content-length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), OneCodeRequestHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
