from __future__ import annotations

import json
import os
import secrets
import subprocess
import urllib.error
import urllib.request
import time
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
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError, api_key_from_env, build_provider_config
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.runner import run_task
from onecode.kernel.self_audit import audit_self
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    project_run_to_shell,
    shell_projection_schema,
)
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    verifier_policy_presets_summary,
    write_verifier_policy,
)


DEFAULT_MODEL_ID = "onecode-agent"
DIRECT_CHAT_SYSTEM_PROMPT = (
    "你是 OneCode agent 的对话脑。直接回答用户的问题。"
    "当用户要求改文件、写代码到项目、执行命令、检查仓库或生成落盘产物时，说明需要 OneCode 执行任务。"
    "其它数学、理论、解释、设计和普通问答都用自然语言回答。"
)
TASK_PREFIXES = (
    "查：",
    "造：",
    "改：",
    "写：",
    "跑：",
    "执行：",
    "修：",
    "测试：",
)
TASK_MARKERS = (
    "修改",
    "创建",
    "生成文件",
    "写入",
    "检查项目",
    "检查仓库",
    "修复",
    "patch",
    "commit",
)
PATH_MARKERS = ("src/", "tests/", ".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml")
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


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


def request_authorized(
    headers: dict[str, str],
    token: str | None,
    *,
    allow_unauthenticated: bool = False,
    host: str = "127.0.0.1",
) -> bool:
    if token is None or token.strip() == "":
        return allow_unauthenticated and host in LOOPBACK_HOSTS
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    return secrets.compare_digest(authorization, f"Bearer {token}")


def latest_user_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        return message_content_to_text(message.get("content"))
    return ""


def configured_allowed_workspace_roots() -> list[Path]:
    raw_roots = os.getenv("ONECODE_ALLOWED_WORKSPACE_ROOTS", "")
    roots = [part for part in raw_roots.split(os.pathsep) if part.strip()]
    if not roots:
        roots = [os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())]
    return [Path(root).expanduser().resolve() for root in roots]


def path_inside_root(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def workspace_allowed(workspace: Path, roots: list[Path] | None = None) -> bool:
    allowed_roots = roots if roots is not None else configured_allowed_workspace_roots()
    return any(path_inside_root(workspace, root) for root in allowed_roots)


def require_allowed_workspace(workspace: Path) -> Path:
    resolved = workspace.resolve()
    if not workspace_allowed(resolved):
        raise ValueError(f"workspace outside allowed workspace roots: {resolved}")
    return resolved


def workspace_from_value(value: str | None) -> Path:
    workspace = Path(
        value if isinstance(value, str) and value.strip() else os.getenv("ONECODE_WORKSPACE_ROOT", os.getcwd())
    ).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ValueError(f"workspace does not exist or is not a directory: {workspace}")
    return require_allowed_workspace(workspace)


def workspace_from_request(body: dict[str, Any]) -> Path:
    metadata = body.get("metadata")
    workspace_value = metadata.get("workspace") if isinstance(metadata, dict) else None
    return workspace_from_value(workspace_value if isinstance(workspace_value, str) else None)


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


def should_run_onecode_task(user_message: str) -> bool:
    stripped = user_message.strip()
    lowered = stripped.lower()
    if any(marker in stripped for marker in ("吗", "？", "?")) and not any(marker in lowered for marker in PATH_MARKERS):
        return False
    if stripped.startswith(TASK_PREFIXES):
        return True
    if any(marker in lowered for marker in PATH_MARKERS):
        return True
    return any(marker in stripped for marker in TASK_MARKERS)


def direct_chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str,
    provider_kind: str,
    endpoint: str | None,
    api_key: str | None = None,
    timeout_seconds: float = 60,
) -> str:
    config = build_provider_config(provider_kind, endpoint=endpoint, model=model)
    resolved_api_key = api_key if api_key is not None else api_key_from_env(provider_kind=provider_kind)
    if resolved_api_key is None:
        raise MissingModelApiKey(f"{config.env_key} is required for direct chat")
    chat_messages = [{"role": "system", "content": DIRECT_CHAT_SYSTEM_PROMPT}]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant", "system"}:
            continue
        content = message_content_to_text(message.get("content"))
        if content.strip():
            chat_messages.append({"role": message["role"], "content": content})
    body = json.dumps({"model": config.model, "messages": chat_messages}).encode("utf-8")
    request = urllib.request.Request(
        config.endpoint,
        data=body,
        headers={"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise TimeoutError("direct chat request timed out") from exc
    except urllib.error.URLError as exc:
        raise ModelProviderError(f"direct chat request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ModelProviderError("direct chat response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelProviderError("direct chat response must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelProviderError("direct chat response missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or content.strip() == "":
        raise ModelProviderError("direct chat response missing message content")
    return content


def chat_completion_payload(
    content: str,
    model: str,
    run_result: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    created = int(time.time())
    summary = project_run_to_shell(run_result)
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
            "summary": summary,
            "result": run_result,
        },
    }


def handle_chat_completion(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    user_message = latest_user_message(body.get("messages"))
    if user_message.strip() == "":
        return error_payload("invalid_request", "messages must include a user message"), 400

    try:
        workspace = workspace_from_request(body)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    model = str(body.get("model") or DEFAULT_MODEL_ID)
    execution_model = model
    stored_config = read_model_config(include_secret=True)
    if execution_model == DEFAULT_MODEL_ID:
        execution_model = os.getenv("ONECODE_MODEL") or os.getenv("OPENAI_MODEL") or stored_config.get("model") or None
    provider_kind = os.getenv("ONECODE_MODEL_PROVIDER") or stored_config.get("provider") or "responses"
    endpoint = os.getenv("ONECODE_MODEL_ENDPOINT") or stored_config.get("endpoint") or None
    stored_api_key = stored_config.get("api_key") if isinstance(stored_config.get("api_key"), str) else None
    run_id = body.get("metadata", {}).get("run_id") if isinstance(body.get("metadata"), dict) else None
    if not should_run_onecode_task(user_message):
        try:
            content = direct_chat_completion(
                body.get("messages") if isinstance(body.get("messages"), list) else [],
                model=execution_model,
                provider_kind=provider_kind,
                endpoint=endpoint,
                api_key=stored_api_key,
            )
        except MissingModelApiKey:
            result = run_light_task(
                user_message,
                workspace=workspace,
                run_id=str(run_id) if run_id else None,
            )
            return chat_completion_payload(format_run_result(result, "chat_fallback"), model, result, "chat_fallback"), 200
        except ModelProviderError as exc:
            result = run_light_task(
                user_message,
                workspace=workspace,
                run_id=str(run_id) if run_id else None,
            )
            return chat_completion_payload(
                f"{format_run_result(result, 'chat_fallback')}\n\n模型直连失败：{exc}",
                model,
                result,
                "chat_fallback",
            ), 200
        return chat_completion_payload(content, model, {"status": "completed", "run_id": run_id}, "chat"), 200

    try:
        result = run_model_task(
            user_message,
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
            model=execution_model,
            api_key=stored_api_key,
            provider_kind=provider_kind,
            endpoint=endpoint,
        )
        mode = "model"
    except MissingModelApiKey:
        result = run_light_task(
            user_message,
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
        )
        mode = "rule_fallback"
    except ValueError as exc:
        if "plan must include at least one asset" not in str(exc):
            return error_payload("invalid_model_plan", str(exc)), 502
        result = run_light_task(
            user_message,
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
        )
        mode = "chat_fallback"
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502

    content = format_run_result(result, mode)
    return chat_completion_payload(content, model, result, mode), 200


def format_run_result(result: dict[str, Any], mode: str) -> str:
    if mode == "chat_fallback":
        return (
            "我收到了这条消息，但模型没有生成文件变更或执行计划。"
            "这次已记录为普通 OneCode 对话运行；如果你要我改代码或写文件，请明确说明目标文件和期望内容。"
        )
    projection = project_run_to_shell(result)
    evidence_ref = projection["evidence_ref"]
    lines = [
        f"{projection['compact_message']} ({mode} mode).",
    ]
    ledger_path = evidence_ref.get("ledger_path")
    wal_path = evidence_ref.get("wal_path")
    if ledger_path is not None:
        lines.append(f"Evidence ledger: `{ledger_path}`.")
    elif wal_path is not None:
        lines.append(f"Evidence WAL: `{wal_path}`.")
    return "\n".join(lines)


def gateway_console_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OneCode Shell</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101010;
      --panel: #171717;
      --panel-2: #202020;
      --text: #f2f0ec;
      --muted: #a8a29a;
      --accent: #f59e0b;
      --accent-2: #38bdf8;
      --danger: #fb7185;
      --border: #3f3a33;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    main {
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }
    .shell {
      border: 1px solid var(--accent);
      background: var(--panel);
      padding: 20px;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .muted { color: var(--muted); }
    .badge {
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--accent);
      padding: 4px 8px;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    label {
      display: block;
      color: var(--muted);
      margin-bottom: 6px;
    }
    textarea, pre {
      width: 100%;
      min-height: 170px;
      margin: 0;
      border: 1px solid var(--border);
      background: #0b0b0b;
      color: var(--text);
      padding: 12px;
      font: inherit;
      overflow: auto;
    }
    textarea { resize: vertical; }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 14px 0;
    }
    button, a.button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #1c1203;
      padding: 9px 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }
    button.secondary, a.button.secondary {
      background: transparent;
      color: var(--accent);
    }
    .status {
      min-height: 24px;
      color: var(--accent-2);
    }
    .danger { color: var(--danger); }
    @media (max-width: 760px) {
      header { display: block; }
      .badge { display: inline-block; margin-top: 10px; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="shell">
      <header>
        <div>
          <h1>OneCode Shell</h1>
          <div class="muted">Bundled browser shell for the deterministic OneCode execution kernel.</div>
        </div>
        <div class="badge">service: ok</div>
      </header>
      <div class="grid">
        <div>
          <label for="input">Candidate input</label>
          <textarea id="input">User: handle this project safely
Model candidate: ALLOW_PATCH_WITH_SHA</textarea>
        </div>
        <div>
          <label for="result">Kernel result</label>
          <pre id="result">Click "Run demo adjudication" to inspect a deterministic kernel decision.</pre>
        </div>
      </div>
      <div class="actions">
        <button id="demo" type="button">Run demo adjudication</button>
        <a class="button secondary" href="/v1/onecode/gateway/adjudicate?demo=1">Open JSON demo</a>
        <a class="button secondary" href="/health">Health check</a>
      </div>
      <div id="status" class="status">POST /v1/onecode/gateway/adjudicate</div>
    </section>
  </main>
  <script>
    const result = document.getElementById('result');
    const status = document.getElementById('status');
    document.getElementById('demo').addEventListener('click', async () => {
      status.textContent = 'running...';
      try {
        const response = await fetch('/v1/onecode/gateway/adjudicate?demo=1');
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
        status.textContent = payload.changed ? 'changed: true' : 'changed: false';
      } catch (error) {
        status.textContent = 'request failed';
        status.className = 'status danger';
        result.textContent = String(error);
      }
    });
  </script>
</body>
</html>
"""


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
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_project_init(body)
            self._send_json(payload, status_code=status_code)
            return
        if path.startswith("/v1/onecode/runs/") and path.endswith("/resume"):
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            run_id = path.removeprefix("/v1/onecode/runs/").removesuffix("/resume").strip("/")
            payload, status_code = handle_onecode_run_resume(run_id, body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/verifier/policy":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_verifier_policy_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/model-config":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_model_config_write(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/models/discover":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
                return
            payload, status_code = handle_onecode_models_discover(body)
            self._send_json(payload, status_code=status_code)
            return
        if path == "/v1/onecode/gateway/adjudicate":
            if not self._authorized():
                self._send_json(error_payload("unauthorized", "invalid OneCode API token"), status_code=401)
                return
            body = self._read_json()
            if body is None:
                self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
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
        body = self._read_json()
        if body is None:
            self._send_json(error_payload("invalid_json", "request body must be valid JSON"), status_code=400)
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
