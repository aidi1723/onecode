from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from onecode.cli import inspect_run, list_runs, run_doctor
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_config import (
    DEFAULT_ONECODE_MODEL,
    discover_models,
    read_model_config,
    write_model_config,
)
from onecode.kernel.gateway_engine import adjudicate_gateway_prediction, validate_assistant_content
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.self_audit import audit_self
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    shell_projection_schema,
)
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    verifier_policy_presets_summary,
    write_verifier_policy,
)
from onecode.web.auth import LOOPBACK_HOSTS, request_authorized
from onecode.web.chat import (
    DEFAULT_MODEL_ID,
    chat_completion_payload,
    direct_chat_completion,
    format_run_result,
    handle_chat_completion,
    latest_user_message,
    message_content_to_text,
    run_light_task,
    should_run_onecode_task,
)
from onecode.web.gateway_console import gateway_console_html
from onecode.web.request_body import JsonRequestBody, max_request_bytes, read_json_request_body
from onecode.web.responses import encode_json_payload, error_payload
from onecode.web.workspace import (
    configured_allowed_workspace_roots,
    path_inside_root,
    require_allowed_workspace,
    workspace_allowed,
    workspace_from_request,
    workspace_from_value,
)


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


def latest_user_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        return message_content_to_text(message.get("content"))
    return ""


def query_workspace_param(query: str) -> str | None:
    values = parse_qs(query).get("workspace")
    return values[0] if values else None


def project_status_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    runs = list_runs(resolved)["runs"]
    latest_run = attach_shell_projection(runs[-1]) if runs else None
    return {
        "workspace": str(resolved),
        "exists": resolved.exists() and resolved.is_dir(),
        "allowed": workspace_allowed(resolved),
        "allowed_roots": [str(root) for root in configured_allowed_workspace_roots()],
        "git": {"present": (resolved / ".git").exists()},
        "verifier_policy": {"present": policy_path.exists(), "path": str(policy_path)},
        "latest_run": latest_run,
        "project_context": discover_project_context(resolved),
        "runtime_config": inspect_runtime_config(resolved),
    }


def handle_onecode_project_status(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return project_status_payload(workspace), 200


def handle_onecode_shell_schema() -> tuple[dict[str, Any], int]:
    return shell_projection_schema(), 200


def handle_onecode_project_init(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    if body.get("git") is True and not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(workspace), check=True, capture_output=True, text=True)
    if body.get("verifierPolicy") is True and not (workspace / DEFAULT_VERIFIER_POLICY_PATH).exists():
        write_verifier_policy(workspace, output=DEFAULT_VERIFIER_POLICY_PATH)
    return project_status_payload(workspace), 200


def parse_limit(value: Any, default: int = 20, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def handle_onecode_runs_list(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    payload = list_runs(workspace)
    payload["runs"] = payload["runs"][-parse_limit(params.get("limit")) :]
    return attach_shell_projection_to_runs_payload(payload), 200


def handle_onecode_run_inspect(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, payload = inspect_run(workspace, run_id)
    payload = attach_shell_projection(payload)
    return payload, 200 if exit_code == 0 else 404


def handle_onecode_run_resume(run_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    message = body.get("message")
    task = message if isinstance(message, str) and message.strip() else f"继续运行 {run_id}"
    try:
        result = run_model_task(
            task,
            workspace=workspace,
            run_id=None,
            resume_from_run_id=run_id,
            model=os.getenv("ONECODE_MODEL") or os.getenv("OPENAI_MODEL") or None,
            provider_kind=os.getenv("ONECODE_MODEL_PROVIDER", "responses"),
            endpoint=os.getenv("ONECODE_MODEL_ENDPOINT") or None,
        )
    except MissingModelApiKey:
        result = run_light_task(task, workspace=workspace, resume_from_run_id=run_id)
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502
    return attach_shell_projection(result), 200


def run_light_task(task: str, *, workspace: Path, run_id: str | None = None, resume_from_run_id: str | None = None) -> dict[str, Any]:
    return run_task(
        task,
        workspace=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        completed_evidence_mode="wal",
        evidence_durability="relaxed",
    )


def handle_onecode_verifier_presets() -> tuple[dict[str, Any], int]:
    return verifier_policy_presets_summary(), 200


def verifier_policy_payload(workspace: Path) -> dict[str, Any]:
    resolved = require_allowed_workspace(workspace)
    policy_path = resolved / DEFAULT_VERIFIER_POLICY_PATH
    payload: dict[str, Any] = {
        "workspace": str(resolved),
        "path": str(policy_path),
        "exists": policy_path.exists(),
        "valid": False,
        "policy": None,
    }
    if not policy_path.exists():
        return payload
    try:
        policy = load_verifier_policy(policy_path)
        payload["policy"] = {
            "verifiers": [
                {
                    "id": spec.id,
                    "command": spec.command,
                    "cwd": spec.cwd,
                    "timeout_ms": spec.timeout_ms,
                }
                for spec in policy.specs.values()
            ]
        }
        payload["valid"] = True
    except ValueError as exc:
        payload["error"] = str(exc)
    return payload


def handle_onecode_verifier_policy_get(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_verifier_policy_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
        preset_ids = body.get("presetIds")
        if preset_ids is not None and not isinstance(preset_ids, list):
            return error_payload("invalid_verifier_policy", "presetIds must be a list of strings"), 400
        if isinstance(preset_ids, list) and not all(isinstance(item, str) for item in preset_ids):
            return error_payload("invalid_verifier_policy", "presetIds must be a list of strings"), 400
        write_verifier_policy(
            workspace=workspace,
            output=DEFAULT_VERIFIER_POLICY_PATH,
            preset_ids=preset_ids if isinstance(preset_ids, list) else None,
            force=body.get("force") is True,
        )
    except ValueError as exc:
        return error_payload("invalid_verifier_policy", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_model_config_get() -> tuple[dict[str, Any], int]:
    try:
        return read_model_config(), 200
    except ValueError as exc:
        return error_payload("invalid_model_config", str(exc)), 400


def handle_onecode_model_config_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    endpoint = body.get("endpoint")
    api_key = body.get("apiKey") or body.get("api_key")
    model = body.get("model")
    provider = body.get("provider")
    models = body.get("models")
    try:
        payload = write_model_config(
            endpoint=endpoint if isinstance(endpoint, str) else "",
            api_key=api_key if isinstance(api_key, str) else "",
            model=model if isinstance(model, str) else None,
            provider=provider if isinstance(provider, str) and provider.strip() else "openai-compatible",
            models=models if isinstance(models, list) else None,
            preserve_existing_secret=True,
        )
    except ValueError as exc:
        return error_payload("invalid_model_config", str(exc)), 400
    return payload, 200


def handle_onecode_models_discover(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    endpoint = body.get("endpoint")
    api_key = body.get("apiKey") or body.get("api_key")
    model = body.get("model")
    if not isinstance(endpoint, str) or not endpoint.strip():
        return error_payload("invalid_model_config", "endpoint is required"), 400
    if not isinstance(api_key, str) or not api_key.strip():
        return error_payload("invalid_model_config", "apiKey is required"), 400
    payload = discover_models(endpoint, api_key)
    models = payload["models"]
    selected_model = model if isinstance(model, str) and model.strip() else (models[0] if models else DEFAULT_ONECODE_MODEL)
    result: dict[str, Any] = {
        **payload,
        "selected_model": selected_model,
    }
    if body.get("save") is True:
        result["config"] = write_model_config(
            endpoint=endpoint,
            api_key=api_key,
            model=selected_model,
            models=models,
        )
    return result, 200


def handle_onecode_gateway_adjudicate(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    user = body.get("user")
    prediction = body.get("prediction")
    if not isinstance(user, str) or user.strip() == "":
        return error_payload("invalid_request", "user must be a non-empty string"), 400
    if not isinstance(prediction, str) or prediction.strip() == "":
        return error_payload("invalid_request", "prediction must be a non-empty JSON string"), 400
    try:
        raw_prediction = validate_assistant_content(prediction)
    except ValueError:
        raw_prediction = None
    adjudicated_prediction = adjudicate_gateway_prediction(user, prediction)
    return {
        "status": "ok",
        "user": user,
        "raw_prediction": raw_prediction,
        "adjudicated_prediction": adjudicated_prediction,
        "changed": raw_prediction != adjudicated_prediction,
    }, 200


def read_json_document(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing_file"
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, None


def handle_onecode_doctor() -> tuple[dict[str, Any], int]:
    return run_doctor(), 200


def handle_onecode_audit_self() -> tuple[dict[str, Any], int]:
    return audit_self(Path.cwd(), run_doctor, run_unittest=False), 200


def handle_onecode_run_evidence(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = workspace_from_value(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, summary = inspect_run(workspace, run_id)
    if exit_code != 0:
        return attach_shell_projection(summary), 404
    summary = attach_shell_projection(summary)
    ledger_path_value = summary.get("ledger_path")
    manifest_path_value = summary.get("manifest_path")
    if summary.get("evidence_mode") == "wal" or not isinstance(ledger_path_value, str) or not isinstance(manifest_path_value, str):
        return {
            "summary": summary,
            "ledger": None,
            "ledger_error": "wal_only",
            "manifest": None,
            "manifest_error": "wal_only",
            "checkpoints": [],
            "wal_path": summary.get("wal_path"),
        }, 200
    ledger_path = Path(ledger_path_value)
    manifest_path = Path(manifest_path_value)
    ledger, ledger_error = read_json_document(ledger_path)
    manifest, manifest_error = read_json_document(manifest_path)
    checkpoints = []
    for record in (manifest or {}).get("checkpoints", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            checkpoints.append({"record": record, "error": "invalid_checkpoint_record"})
            continue
        checkpoint_path = Path(record["path"])
        document, error = read_json_document(checkpoint_path)
        checkpoints.append(
            {
                "path": str(checkpoint_path),
                "record": record,
                "document": document,
                "error": error,
            }
        )
    return {
        "summary": summary,
        "ledger": ledger,
        "ledger_error": ledger_error,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "checkpoints": checkpoints,
    }, 200


class OneCodeRequestHandler(BaseHTTPRequestHandler):
    server_version = "OneCodeHTTP/0.1"

    def do_GET(self) -> None:
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
        payload, status_code = handle_chat_completion(body)
        if status_code == 200 and body.get("stream") is True:
            self._send_sse_chat_completion(payload)
            return
        self._send_json(payload, status_code=status_code)

    def log_message(self, format: str, *args: Any) -> None:
        if os.getenv("ONECODE_HTTP_ACCESS_LOG", "").lower() in {"1", "true", "yes", "on"}:
            super().log_message(format, *args)

    def _authorized(self) -> bool:
        allow_unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}
        host = self.server.server_address[0]
        return request_authorized(
            dict(self.headers.items()),
            os.getenv("ONECODE_API_TOKEN"),
            allow_unauthenticated=allow_unauthenticated,
            host=host,
        )

    def _read_json(self) -> dict[str, Any] | None:
        return read_json_request_body(self.headers, self.rfile).payload

    def _read_json_or_send_error(self) -> dict[str, Any] | None:
        result = read_json_request_body(self.headers, self.rfile)
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

    def _send_sse_chat_completion(self, payload: dict[str, Any]) -> None:
        choice = payload.get("choices", [{}])[0] if isinstance(payload.get("choices"), list) else {}
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        chunk = {
            "id": payload.get("id"),
            "object": "chat.completion.chunk",
            "created": payload.get("created"),
            "model": payload.get("model"),
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": content if isinstance(content, str) else ""},
                    "finish_reason": None,
                }
            ],
        }
        final_chunk = {
            "id": payload.get("id"),
            "object": "chat.completion.chunk",
            "created": payload.get("created"),
            "model": payload.get("model"),
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        body = (
            f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            "data: [DONE]\n\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/event-stream; charset=utf-8")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "close")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), OneCodeRequestHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
