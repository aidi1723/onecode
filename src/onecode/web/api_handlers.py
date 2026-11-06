# ruff: noqa: F403, F405
"""HTTP handlers for the OneCode API."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any

from onecode.web.responses import error_payload
from onecode.web.workspace import (
    require_allowed_workspace,
    workspace_from_request,
    workspace_from_value,  # noqa: F401
)

from onecode.kernel.diagnostics import run_doctor  # noqa: F401
from onecode.kernel.effective_model_config import resolve_effective_model_config
from onecode.kernel.run_inspection import inspect_run, list_runs  # noqa: F401
from onecode.kernel.model_loop import (
    _generate_missing_artifacts,
    _modified_paths_from_result,
    _src_files_for_repair,
    execute_model_plan,  # noqa: F401
    missing_required_files,
    repair_prompt,
    required_python_files,
    run_model_task,  # noqa: F401
)
from onecode.kernel.sandbox import SandboxConfig
from onecode.kernel.approval_plans import claim_approval_plan, finalize_approval_plan
from onecode.kernel.model_config import (
    DEFAULT_ONECODE_MODEL,
    discover_models,  # noqa: F401
    read_bounded_response,
    read_model_config,  # noqa: F401
    write_model_config,  # noqa: F401
)
from onecode.kernel.gateway_engine import adjudicate_gateway_prediction, validate_assistant_content
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError, api_key_from_env, build_provider_config  # noqa: F401
from onecode.kernel.allow_evidence import complete_allow_evidence
from onecode.kernel.path_guard import PathGuard, PathGuardError  # noqa: F401
from onecode.kernel.preset_tests import (
    authoritative_preset_test_hashes,
)
from onecode.kernel.run_inspection import ledger_matches_workspace  # noqa: F401
from onecode.kernel.prompt_rules import decide_prompt
from onecode.kernel.runner import run_task  # noqa: F401
from onecode.self_audit import audit_self  # noqa: F401
from onecode.kernel.shell_projection import (
    attach_shell_projection,  # noqa: F401
    attach_shell_projection_to_runs_payload,  # noqa: F401
    project_run_to_shell,
    shell_projection_schema,
)
from onecode.kernel.task_classification import classify_task
from onecode.kernel.run_id import validate_optional_run_id, validate_run_id  # noqa: F401
from onecode.kernel.wal import global_wal_metrics_summary  # noqa: F401
from onecode.kernel.verifier import (
    DEFAULT_VERIFIER_POLICY_PATH,
    load_verifier_policy,
    verifier_policy_presets_summary,  # noqa: F401
    write_verifier_policy,
)

from onecode.web.api_shell import *  # noqa: F403

def _bound(name: str):
    from onecode.web import api
    return getattr(api, name)


def handle_onecode_project_status(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return _bound("project_status_payload")(workspace), 200


def handle_onecode_shell_schema() -> tuple[dict[str, Any], int]:
    return shell_projection_schema(), 200


def handle_onecode_project_init(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = _bound("workspace_from_value")(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    if body.get("git") is True and not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(workspace), check=True, capture_output=True, text=True)
    if body.get("verifierPolicy") is True and not (workspace / DEFAULT_VERIFIER_POLICY_PATH).exists():
        write_verifier_policy(workspace, output=DEFAULT_VERIFIER_POLICY_PATH)
    return _bound("project_status_payload")(workspace), 200


def parse_limit(value: Any, default: int = 20, maximum: int = 100) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def parse_window_seconds(value: Any, default: int = 60, maximum: int = 86_400) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def handle_onecode_runs_list(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    payload = _bound("list_runs")(workspace)
    payload["runs"] = payload["runs"][-parse_limit(params.get("limit")) :]
    return _bound("attach_shell_projection_to_runs_payload")(payload), 200


def handle_onecode_metrics(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    window_seconds = parse_window_seconds(params.get("window_seconds"))
    try:
        wal_summary = _bound("global_wal_metrics_summary")(workspace, window_seconds=window_seconds)
    except ValueError as exc:
        return error_payload("invalid_metrics_request", str(exc)), 400
    return {
        "workspace": str(workspace),
        "control_plane": {
            "scope": "summary",
            "raw_entries_included": False,
            "source": "global_wal",
        },
        "global_wal_summary": wal_summary,
    }, 200


def handle_onecode_run_inspect(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = _bound("validate_run_id")(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, payload = _bound("inspect_run")(workspace, run_id)
    payload = _bound("attach_shell_projection")(payload)
    return payload, 200 if exit_code == 0 else 404


def handle_onecode_run_resume(run_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = _bound("validate_run_id")(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = _bound("workspace_from_value")(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    message = body.get("message")
    task = message if isinstance(message, str) and message.strip() else f"继续运行 {run_id}"
    stored_config = _bound("read_model_config")(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    try:
        prepared = prepare_shell_model_call(task, workspace)
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    if "stop" in prepared:
        stopped = prepared["stop"]
        code = {"model_provider_timeout": 504, "model_provider_error": 502}.get(str(stopped.get("reason")))
        if code is not None:
            payload = error_payload(str(stopped.get("reason")), "model planning failed before execution")
            payload["onecode"] = {"mode": "model", "result": stopped}
            return payload, code
        return _bound("attach_shell_projection")(stopped), 200
    try:
        result = _bound("run_model_task")(
            prepared["task"],
            workspace=workspace,
            run_id=None,
            resume_from_run_id=run_id,
            model=effective_model.model,
            api_key=effective_model.api_key,
            provider_kind=effective_model.provider,
            endpoint=effective_model.endpoint,
            require_explicit_approval=True,
            **prepared["extras"],
        )
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502
    return _bound("attach_shell_projection")(result), 200


def handle_onecode_plan_approval(
    plan_id: str,
    body: dict[str, Any],
    on_turn: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], int]:
    approved = body.get("approved")
    if not isinstance(approved, bool):
        return error_payload("invalid_approval", "approved must be boolean"), 400
    try:
        workspace = _bound("workspace_from_value")(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
        stored = claim_approval_plan(workspace, plan_id)
    except ValueError as exc:
        status = 409 if str(exc) in {"approval_plan_in_progress", "approval_plan_already_resolved"} else 400
        return error_payload("invalid_approval_plan", str(exc)), status
    if not approved:
        result = {  # type: ignore
            "run_id": None,
            "status": "cancelled",
            "reason": "approval_rejected",
            "partial": False,
            "requested_count": 0,
            "completed_count": 0,
            "skipped_count": 1,
            "failed_count": 0,
            "assets": [],
            "plan_id": plan_id,
        }
        finalize_approval_plan(stored, "rejected", result)
        return result, 200
    before = authoritative_preset_test_hashes(workspace)
    try:
        _reject_existing_preset_test_stage(workspace, body, before)
        _stage_approved_host_bytes(workspace, body)
    except (ValueError, PathGuardError) as exc:
        finalize_approval_plan(stored, "rejected", {"status": "halted", "reason": "sovereignty_breach", "assets": []})
        return error_payload("invalid_stage", str(exc)), 400
    ledger_mismatch = _bound("ledger_matches_workspace")(workspace)
    if ledger_mismatch is not None:
        halt_result = {"status": "halted", "reason": ledger_mismatch, "assets": []}
        finalize_approval_plan(stored, "rejected", halt_result)
        return halt_result, 400
    user_task = stored.model_metadata.get("user_task")
    user_task = user_task if isinstance(user_task, str) else ""
    written_before = set(required_python_files(user_task)) - set(missing_required_files(user_task, workspace)) if user_task else set()
    result = _bound("execute_model_plan")(
        stored.plan,
        workspace=workspace,
        http_timeout_seconds=60,
        run_id=None,
        resume_from_run_id=None,
        run_metadata={**stored.model_metadata, "approved_plan_id": plan_id},
        approval_callback=lambda _step: True,
        on_turn=on_turn,
    )
    if user_task:
        _generate_missing_artifacts(
            user_task,
            workspace,
            _modified_paths_from_result(result)
            or [a.path for a in stored.plan.assets] + [p.path for p in stored.plan.patches],
        )
    if user_task and missing_required_files(user_task, workspace):
        try:
            continued = continue_named_files(user_task, workspace, written_before)
        except (MissingModelApiKey, ModelProviderError):
            continued = None
        if continued is not None:
            finalize_approval_plan(stored, "approved", result)
            return _bound("attach_shell_projection")(continued), 200
    result = verify_shell_write(result, workspace, before)
    patch_only = bool(stored.plan.patches) and not stored.plan.assets and not stored.plan.execution_steps
    if _opens_complete_rewrite(result, patch_only) and not _rewrite_already_offered(user_task):
        rewrite = _offer_complete_rewrite(workspace, user_task or stored.plan.task, result)
        finalize_approval_plan(stored, "approved", result)
        return _bound("attach_shell_projection")(rewrite), 200
    if result.get("reason") == "verifier_failed" and not patch_only:
        failed = {**result, "workspace_files": _src_files_for_repair(workspace)}
        stored_config = _bound("read_model_config")(include_secret=True)
        effective_model = resolve_effective_model_config(os.environ, stored_config)
        try:
            repair = _bound("run_model_task")(
                repair_prompt(stored.plan.task, failed, workspace=workspace),
                workspace=workspace,
                model=effective_model.model,
                api_key=effective_model.api_key,
                provider_kind=effective_model.provider,
                endpoint=effective_model.endpoint,
                require_explicit_approval=True,
                max_repair_attempts=0,
                sandbox_config=SandboxConfig(workspace=workspace),
            )
        except (MissingModelApiKey, ModelProviderError):
            repair = result
        tail = _verifier_tail(result)
        if isinstance(repair, dict) and tail:
            repair = {**repair, "verifier_tail": tail}
        finalize_approval_plan(stored, "approved", result)
        return _bound("attach_shell_projection")(repair), 200
    finalize_approval_plan(stored, "approved", result)
    return _bound("attach_shell_projection")(result), 200


def run_light_task(task: str, *, workspace: Path, run_id: str | None = None, resume_from_run_id: str | None = None) -> dict[str, Any]:
    return _bound("run_task")(
        task,
        workspace=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        completed_evidence_mode="wal",
        evidence_durability="relaxed",
    )


def handle_onecode_verifier_presets() -> tuple[dict[str, Any], int]:
    return _bound("verifier_policy_presets_summary")(), 200


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
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    return verifier_policy_payload(workspace), 200


def handle_onecode_verifier_policy_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        workspace = _bound("workspace_from_value")(body.get("workspace") if isinstance(body.get("workspace"), str) else None)
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
        return _bound("read_model_config")(), 200
    except ValueError as exc:
        return error_payload("invalid_model_config", str(exc)), 400


def handle_onecode_model_config_write(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    endpoint = body.get("endpoint")
    api_key = body.get("apiKey") or body.get("api_key")
    model = body.get("model")
    provider = body.get("provider")
    models = body.get("models")
    try:
        payload = _bound("write_model_config")(
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
    payload = _bound("discover_models")(endpoint, api_key)
    models = payload["models"]
    selected_model = model if isinstance(model, str) and model.strip() else (models[0] if models else DEFAULT_ONECODE_MODEL)
    result: dict[str, Any] = {
        **payload,
        "selected_model": selected_model,
    }
    if body.get("save") is True:
        result["config"] = _bound("write_model_config")(
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
    facts = adjudicated_prediction.get("facts") if isinstance(adjudicated_prediction, dict) else {}
    action = adjudicated_prediction.get("action") if isinstance(adjudicated_prediction, dict) else ""
    evidence = complete_allow_evidence(
        action if isinstance(action, str) else "",
        facts if isinstance(facts, dict) else {},
        user,
        Path.cwd(),
    )
    return {
        "status": "ok",
        "user": user,
        "raw_prediction": raw_prediction,
        "adjudicated_prediction": adjudicated_prediction,
        "changed": raw_prediction != adjudicated_prediction,
        "prompt_decision": decide_prompt(user),
        "allow_evidence": evidence,
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
    return _bound("run_doctor")(), 200


def handle_onecode_audit_self() -> tuple[dict[str, Any], int]:
    return _bound("audit_self")(Path.cwd(), _bound("run_doctor"), run_unittest=False), 200


def handle_onecode_run_evidence(run_id: str, params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    try:
        run_id = _bound("validate_run_id")(run_id)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    try:
        workspace = _bound("workspace_from_value")(params.get("workspace") if isinstance(params.get("workspace"), str) else None)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    exit_code, summary = _bound("inspect_run")(workspace, run_id)
    if exit_code != 0:
        return _bound("attach_shell_projection")(summary), 404
    summary = _bound("attach_shell_projection")(summary)
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
    evidence_root = workspace / ".onecode" / "runs" / run_id
    try:
        ledger_path = _bound("PathGuard").resolve_contained(evidence_root, ledger_path_value)
        manifest_path = _bound("PathGuard").resolve_contained(evidence_root, manifest_path_value)
    except PathGuardError:
        return error_payload("path_outside_evidence", "evidence path escapes the run directory"), 400
    ledger, ledger_error = _bound("read_json_document")(ledger_path)
    manifest, manifest_error = _bound("read_json_document")(manifest_path)
    checkpoints = []
    for record in (manifest or {}).get("checkpoints", []):
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            checkpoints.append({"record": record, "error": "invalid_checkpoint_record"})
            continue
        try:
            checkpoint_path = _bound("PathGuard").resolve_contained(evidence_root, record["path"])
        except PathGuardError:
            checkpoints.append({"path": record["path"], "record": record, "document": None, "error": "path_outside_evidence"})
            continue
        document, error = _bound("read_json_document")(checkpoint_path)
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


def should_run_onecode_task(user_message: str) -> bool:
    return classify_task(user_message) != "chat"


def parse_approval_message(user_message: str) -> tuple[str, bool] | None:
    match = APPROVAL_MESSAGE_PATTERN.fullmatch(user_message.strip())
    if match is None:
        return None
    return match.group(2), match.group(1) != "拒绝"


def direct_chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str,
    provider_kind: str,
    endpoint: str | None,
    api_key: str | None = None,
    timeout_seconds: float = 60,
) -> str:
    config = _bound("build_provider_config")(provider_kind, endpoint=endpoint, model=model)
    resolved_api_key = api_key if api_key is not None else _bound("api_key_from_env")(provider_kind=provider_kind)
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
            payload = json.loads(read_bounded_response(response).decode("utf-8"))
    except TimeoutError as exc:
        raise TimeoutError("direct chat request timed out") from exc
    except urllib.error.URLError as exc:
        raise ModelProviderError(f"direct chat request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ModelProviderError("direct chat response was not valid JSON") from exc
    except ValueError as exc:
        raise ModelProviderError("direct chat response exceeds maximum size") from exc
    if not isinstance(payload, dict):
        raise ModelProviderError("direct chat response must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelProviderError("direct chat response missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None  # type: ignore
    content = message.get("content") if isinstance(message, dict) else None  # type: ignore
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


def handle_chat_completion(
    body: dict[str, Any],
    on_turn: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], int]:
    user_message = latest_user_message(body.get("messages"))
    if user_message.strip() == "":
        return error_payload("invalid_request", "messages must include a user message"), 400

    try:
        workspace = workspace_from_request(body)
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    model = str(body.get("model") or DEFAULT_MODEL_ID)
    approval_message = parse_approval_message(user_message)
    if approval_message is not None:
        plan_id, approved = approval_message
        result, status_code = handle_onecode_plan_approval(
            plan_id,
            {"workspace": str(workspace), "approved": approved},
            on_turn=on_turn,
        )
        if status_code != 200:
            return result, status_code
        return chat_completion_payload(format_run_result(result, "approval"), model, result, "approval"), 200
    raw_metadata = body.get("metadata")
    metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
    explicit_mode = metadata.get("onecode_mode") if isinstance(metadata.get("onecode_mode"), str) else None
    try:
        task_mode = classify_task(user_message, explicit_mode=explicit_mode)
    except ValueError as exc:
        return error_payload("invalid_task_mode", str(exc)), 400
    stored_config = _bound("read_model_config")(include_secret=True)
    effective_model = resolve_effective_model_config(os.environ, stored_config)
    execution_model = effective_model.model if model == DEFAULT_MODEL_ID else model
    provider_kind = effective_model.provider
    endpoint = effective_model.endpoint
    stored_api_key = effective_model.api_key
    run_id = metadata.get("run_id")  # type: ignore
    try:
        run_id = validate_optional_run_id(str(run_id) if run_id else None)
    except ValueError as exc:
        return error_payload("invalid_run_id", str(exc)), 400
    if task_mode == "chat":
        try:
            content = _bound("direct_chat_completion")(
                body.get("messages") if isinstance(body.get("messages"), list) else [],  # type: ignore
                model=execution_model,
                provider_kind=provider_kind,
                endpoint=endpoint,
                api_key=stored_api_key,
            )
        except MissingModelApiKey as exc:
            return error_payload("model_configuration_missing", str(exc)), 503
        except ModelProviderError as exc:
            return error_payload("model_provider_error", str(exc)), 502
        return chat_completion_payload(content, model, {"status": "completed", "run_id": run_id}, "chat"), 200

    try:
        model_timeout_seconds = model_timeout_seconds_from_env()
    except ValueError as exc:
        return error_payload("invalid_model_timeout", str(exc)), 503

    try:
        prepared = prepare_shell_model_call(user_message, workspace, run_id=str(run_id) if run_id else None)
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    if "stop" in prepared:
        return shell_stop_response(prepared["stop"], model)
    meta_repairs = metadata.get("max_repair_attempts")
    if meta_repairs is not None:
        if str(meta_repairs).lower() == "auto":
            from onecode.kernel.model_loop import resolve_task_bureau

            prepared["extras"]["max_repair_attempts"] = resolve_task_bureau(workspace).get("turn_budget", 3)
        else:
            try:
                prepared["extras"]["max_repair_attempts"] = int(meta_repairs)
            except (ValueError, TypeError):
                pass
    try:
        result = _bound("run_model_task")(
            prepared["task"],
            workspace=workspace,
            run_id=str(run_id) if run_id else None,
            model=execution_model,
            api_key=stored_api_key,
            provider_kind=provider_kind,
            endpoint=endpoint,
            task_mode=task_mode,
            require_explicit_approval=True,
            http_timeout_seconds=model_timeout_seconds,
            on_turn=on_turn,
            **prepared["extras"],
        )
        failure_statuses = {
            "model_provider_timeout": 504,
            "model_provider_error": 502,
            "invalid_model_plan": 502,
        }
        failure_reason = result.get("reason")
        if failure_reason in failure_statuses:
            detail = result.get("payload")
            extra = detail.get("detail") if isinstance(detail, dict) else None
            message = "model planning failed before execution"
            if isinstance(extra, str) and extra.strip():
                message = f"{message}: {extra.strip()[:300]}"
            payload = error_payload(str(failure_reason), message)
            payload["onecode"] = {"mode": "model", "result": result}
            return payload, failure_statuses[failure_reason]
        if failure_reason == "no_actionable_plan":
            mode = "no_action"
        elif failure_reason == "approval_required":
            mode = "approval_required"
        else:
            mode = "model"
    except MissingModelApiKey as exc:
        return error_payload("model_configuration_missing", str(exc)), 503
    except ValueError as exc:
        if "plan must include at least one asset" not in str(exc):
            return error_payload("invalid_model_plan", str(exc)), 502
        result = {
            "run_id": str(run_id) if run_id else None,
            "status": "halted",
            "reason": "no_actionable_plan",
            "detail": str(exc),
            "partial": True,
            "intent_type": "no_action",
            "requested_count": 0,
            "completed_count": 0,
            "skipped_count": 0,
            "failed_count": 1,
            "assets": [],
        }
        mode = "no_action"
    except ModelProviderError as exc:
        return error_payload("model_provider_error", str(exc)), 502

    content = format_run_result(result, mode)
    if isinstance(metadata, dict):
        _remember_confirmed_completion(workspace, metadata, user_message, result)
    return chat_completion_payload(content, model, result, mode), 200


def stream_chat_completion(
    body: dict[str, Any],
    write: Callable[[bytes], None],
) -> tuple[dict[str, Any], int]:
    def on_turn(turn: dict[str, Any]) -> None:
        write(_sse_bytes(tool_turn_chunk(turn)))

    payload, status = handle_chat_completion(body, on_turn=on_turn)
    if status != 200:
        return payload, status
    write(_sse_bytes(content_chunk(payload)))
    write(_sse_bytes(stop_chunk(payload)))
    write(b"data: [DONE]\n\n")
    return payload, status


def tool_turn_chunk(turn: dict[str, Any]) -> dict[str, Any]:
    tool_names = [name for name in turn.get("tool_names", []) if isinstance(name, str)]
    reason = turn.get("reason")
    label = ", ".join(tool_names) or str(turn.get("step_id") or "tool")
    content = f"{label}: {turn.get('status') or 'completed'}"
    if isinstance(reason, str) and reason:
        content += f" | {reason}"
    return {
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content + "\n"}, "finish_reason": None}],
        "onecode": {
            "event": "tool_turn",
            "step_id": turn.get("step_id"),
            "tool_names": tool_names,
            "status": turn.get("status"),
            "reason": reason,
        },
    }


def content_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    choice = payload.get("choices", [{}])[0] if isinstance(payload.get("choices"), list) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    return {
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


def stop_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "object": "chat.completion.chunk",
        "created": payload.get("created"),
        "model": payload.get("model"),
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }


def _sse_bytes(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def format_run_result(result: dict[str, Any], mode: str) -> str:
    if mode == "approval" and result.get("status") == "cancelled":
        return "计划已拒绝，未执行任何变更。"
    if mode == "approval" and result.get("status") == "completed":
        return "计划已批准并执行完成，结果已写入 OneCode 证据链。"
    if result.get("reason") == "approval_required":
        message = (
            "计划已生成，但包含写入或命令操作，尚未执行。"
            f"审批计划 ID：`{result.get('plan_id')}`。确认后再执行。"
        )
        summary = result.get("plan_summary")
        actions = summary.get("actions") if isinstance(summary, dict) else None
        if isinstance(actions, list):
            message += "\n待审批操作：\n```json\n" + json.dumps(actions, ensure_ascii=False, indent=2) + "\n```"
        visible = _approval_visible_text(result, actions if isinstance(actions, list) else [])
        if visible:
            message += "\n" + visible
        return message
    if result.get("reason") == "no_actionable_plan":
        return "模型没有生成可执行计划，本次任务未执行。请补充明确目标或检查模型配置。"
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


def _verifier_tail(result: dict[str, Any]) -> str:
    raw = result.get("verifier_results")
    if not isinstance(raw, list):
        return ""
    tails = [
        str(item.get("stderr_tail")).strip()[-400:]
        for item in raw
        if isinstance(item, dict) and isinstance(item.get("stderr_tail"), str) and str(item.get("stderr_tail")).strip()
    ]
    return "\n".join(tails)


def _approval_visible_text(result: dict[str, Any], actions: list[Any]) -> str:
    parts: list[str] = []
    tail = result.get("verifier_tail")
    if isinstance(tail, str) and tail.strip():
        parts.append("测试失败：\n```\n" + tail.strip()[:4000] + "\n```")
    for action in actions:
        if not isinstance(action, dict):
            continue
        diff = action.get("diff")
        if isinstance(diff, str) and diff.strip():
            label = action.get("path") if isinstance(action.get("path"), str) and action.get("path") else action.get("tool")
            parts.append(f"变更 {label}：\n```diff\n{diff.rstrip()}\n```")
        if action.get("tool") == "patch_text":
            search = action.get("search_preview")
            replace = action.get("replace_preview")
            path = action.get("path") if isinstance(action.get("path"), str) else ""
            if isinstance(search, str) and isinstance(replace, str):
                parts.append(f"补丁 {path}：\n查找：\n```\n{search.rstrip()}\n```\n替换：\n```\n{replace.rstrip()}\n```")
        if action.get("host_execution") or (isinstance(action.get("tool"), str) and action["tool"].startswith("mcp.")):
            cmd = action.get("command")
            cmd_str = " ".join(cmd) if isinstance(cmd, list) and cmd else "<未配置命令>"
            args = action.get("arguments", {})
            args_str = json.dumps(args, ensure_ascii=False) if args else "{}"
            where = "宿主机" if action.get("host_execution") else "沙盒"
            parts.append(f"MCP 外部命令（将在{where}执行）：`{cmd_str}`\n参数：`{args_str}`")
    return "\n".join(parts)


def gateway_console_html() -> str:
    return Path(__file__).with_name("gateway_console.html").read_text(encoding="utf-8")


def handle_onecode_pending_approvals(params: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from onecode.kernel.cycle_approvals import load_pending_approvals

    try:
        workspace = _bound("workspace_from_value")(params.get("workspace"))
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400
    approvals = load_pending_approvals(workspace)
    return {
        "status": "ok",
        "workspace": str(workspace),
        "count": len(approvals),
        "approvals": approvals,
    }, 200


def _record_resolved_approval(workspace: Path, approval_id: str, tool_name: str, body: dict[str, Any]) -> None:
    res_dir = workspace / ".onecode"
    res_dir.mkdir(parents=True, exist_ok=True)
    res_file = res_dir / "resolved_approvals.json"
    records: list[dict[str, Any]] = []
    if res_file.is_file():
        try:
            records = json.loads(res_file.read_text(encoding="utf-8"))
        except Exception:
            records = []
    resolution = body.get("resolution") or body.get("selected_slug")
    records.append({
        "id": approval_id,
        "tool_name": tool_name,
        "resolution": resolution,
    })
    res_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_onecode_approval_resolve(approval_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from onecode.kernel.cycle_approvals import load_pending_approvals, resume_pending_approval

    decision = body.get("decision")
    if decision not in {"approved", "rejected"}:
        return error_payload("invalid_decision", "decision must be 'approved' or 'rejected'"), 400
    try:
        workspace = _bound("workspace_from_value")(body.get("workspace"))
    except ValueError as exc:
        return error_payload("invalid_workspace", str(exc)), 400

    match = next((item for item in load_pending_approvals(workspace) if item.get("id") == approval_id), None)
    if match is None:
        return error_payload("approval_not_found", f"No pending approval with id: {approval_id}"), 404

    if decision == "rejected":
        result = resume_pending_approval(workspace, approval_id, "rejected", lambda _t, _p: None)
        return {"status": "rejected", "approval_id": approval_id, "result": result}, 200

    res_payload = {
        "status": "approved",
        "approval_id": approval_id,
        "tool_name": match["tool_name"],
        "params": match["params"],
    }
    if "resolution" in body:
        res_payload["resolution"] = body["resolution"]
    if "selected_slug" in body:
        res_payload["selected_slug"] = body["selected_slug"]
    if "resolution" in body or "selected_slug" in body:
        _record_resolved_approval(workspace, approval_id, str(match["tool_name"]), body)

    return res_payload, 200



__all__ = [
    "handle_onecode_project_status",
    "handle_onecode_shell_schema",
    "handle_onecode_project_init",
    "parse_limit",
    "parse_window_seconds",
    "handle_onecode_runs_list",
    "handle_onecode_metrics",
    "handle_onecode_run_inspect",
    "handle_onecode_run_resume",
    "handle_onecode_plan_approval",
    "run_light_task",
    "handle_onecode_verifier_presets",
    "verifier_policy_payload",
    "handle_onecode_verifier_policy_get",
    "handle_onecode_verifier_policy_write",
    "handle_onecode_model_config_get",
    "handle_onecode_model_config_write",
    "handle_onecode_models_discover",
    "handle_onecode_gateway_adjudicate",
    "read_json_document",
    "handle_onecode_doctor",
    "handle_onecode_audit_self",
    "handle_onecode_run_evidence",
    "message_content_to_text",
    "should_run_onecode_task",
    "parse_approval_message",
    "direct_chat_completion",
    "chat_completion_payload",
    "handle_chat_completion",
    "stream_chat_completion",
    "tool_turn_chunk",
    "content_chunk",
    "stop_chunk",
    "_sse_bytes",
    "format_run_result",
    "_verifier_tail",
    "_approval_visible_text",
    "gateway_console_html",
    "handle_onecode_pending_approvals",
    "handle_onecode_approval_resolve",
]
