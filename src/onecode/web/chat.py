from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from onecode.kernel.model_config import read_model_config
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.model_provider import MissingModelApiKey, ModelProviderError, api_key_from_env, build_provider_config
from onecode.kernel.runner import run_task
from onecode.kernel.shell_projection import project_run_to_shell
from onecode.web.responses import error_payload
from onecode.web.workspace import workspace_from_request


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


def run_light_task(task: str, *, workspace: Path, run_id: str | None = None, resume_from_run_id: str | None = None) -> dict[str, Any]:
    return run_task(
        task,
        workspace=workspace,
        run_id=run_id,
        resume_from_run_id=resume_from_run_id,
        completed_evidence_mode="wal",
        evidence_durability="relaxed",
    )


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
