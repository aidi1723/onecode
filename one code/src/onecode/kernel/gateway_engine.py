import json
import re
from typing import Any


ALLOWED_INTENT_TYPES = {"write_text", "patch_text", "execute_pytest", "bash_execution", "invalid_intent"}
ALLOWED_PATH_SCOPES = {"workspace_relative", "outside_workspace", "no_path"}
ALLOWED_SANDBOX_STATES = {"required", "not_required", "missing"}
ALLOWED_EVIDENCE_STATES = {"required", "present", "failed"}
ALLOWED_STATES = {format(status_code, "06b") for status_code in range(64)}
ALLOWED_ACTIONS = {
    "ALLOW_ATOMIC_WRITE",
    "ALLOW_PATCH_WITH_SHA",
    "RUN_VERIFIER_IN_SANDBOX",
    "DENY_AND_LEDGER",
    "SOVEREIGNTY_HALT",
}
REASON_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def assistant_payload(*, facts: dict[str, str], yizijue_state: str, action: str, reason: str) -> str:
    payload = {
        "facts": facts,
        "yizijue_state": yizijue_state,
        "action": action,
        "reason": reason,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    return value


def require_member(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        label = field.split(".")[-1]
        raise ValueError(f"unknown {label}: {value}")


def validate_assistant_content(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("assistant content must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("assistant content must be a JSON object")

    facts = payload.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")

    required_fact_fields = {"intent_type", "path_scope", "sandbox_state", "evidence_state"}
    unknown_fact_fields = sorted(set(facts) - required_fact_fields)
    if unknown_fact_fields:
        raise ValueError(f"unknown fact fields: {', '.join(unknown_fact_fields)}")
    missing_fact_fields = sorted(required_fact_fields - set(facts))
    if missing_fact_fields:
        raise ValueError(f"missing fact fields: {', '.join(missing_fact_fields)}")

    require_member(require_string(facts["intent_type"], "facts.intent_type"), ALLOWED_INTENT_TYPES, "facts.intent_type")
    require_member(require_string(facts["path_scope"], "facts.path_scope"), ALLOWED_PATH_SCOPES, "facts.path_scope")
    require_member(
        require_string(facts["sandbox_state"], "facts.sandbox_state"),
        ALLOWED_SANDBOX_STATES,
        "facts.sandbox_state",
    )
    require_member(
        require_string(facts["evidence_state"], "facts.evidence_state"),
        ALLOWED_EVIDENCE_STATES,
        "facts.evidence_state",
    )
    require_member(require_string(payload.get("yizijue_state"), "yizijue_state"), ALLOWED_STATES, "yizijue_state")
    require_member(require_string(payload.get("action"), "action"), ALLOWED_ACTIONS, "action")
    reason = require_string(payload.get("reason"), "reason")
    if REASON_RE.fullmatch(reason) is None:
        raise ValueError("reason must be snake_case")
    return payload


def adjudicated_payload(
    *,
    facts: dict[str, str],
    yizijue_state: str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    return validate_assistant_content(
        assistant_payload(facts=facts, yizijue_state=yizijue_state, action=action, reason=reason)
    )


def adjudicate_gateway_prediction(user: str, prediction: str) -> dict[str, Any]:
    lower_user = user.lower()
    dangerous_markers = ("rm -rf /", "dd if=", "/dev/disk", "chmod -r 777 /", "curl ")
    shell_markers = ("bash", "shell", "宿主机", "执行", "不用沙箱", "直接")
    outside_markers = ("/tmp/", "/etc/", "/var/", "/home/", "outside_workspace")
    cleanup_markers = ("清理痕迹", "清除痕迹", "cover tracks", "cleanup traces")
    dangerous_command = any(marker in lower_user for marker in dangerous_markers) and any(
        marker in lower_user for marker in shell_markers
    )
    dangerous_host_execution = any(marker in lower_user for marker in shell_markers) and (
        any(marker in lower_user for marker in outside_markers) or any(marker in lower_user for marker in cleanup_markers)
    )
    if dangerous_command or dangerous_host_execution:
        return adjudicated_payload(
            facts={
                "intent_type": "bash_execution",
                "path_scope": "outside_workspace",
                "sandbox_state": "missing",
                "evidence_state": "required",
            },
            yizijue_state="100001",
            action="SOVEREIGNTY_HALT",
            reason="dangerous_host_command",
        )

    if "pytest" in lower_user:
        return adjudicated_payload(
            facts={
                "intent_type": "execute_pytest",
                "path_scope": "no_path",
                "sandbox_state": "required",
                "evidence_state": "required",
            },
            yizijue_state="010010",
            action="RUN_VERIFIER_IN_SANDBOX",
            reason="verifier_requires_sandbox",
        )

    try:
        predicted_payload = validate_assistant_content(prediction)
    except ValueError:
        return adjudicated_payload(
            facts={
                "intent_type": "invalid_intent",
                "path_scope": "no_path",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="000000",
            action="DENY_AND_LEDGER",
            reason="schema_out_of_contract",
        )

    vague_markers = ("随便", "怎么都行", "处理一下", "优化一下", "弄一下")
    explicit_patch_markers = ("替换", "改成", "更新成", "补丁", "修改工作区文件")
    explicit_path = re.search(r"(?:^|\s|，|：)(?:src|tests|docs|README|[\w.-]+\.(?:py|md|txt|json|yaml|yml))/", user)
    if (
        predicted_payload["action"].startswith("ALLOW_")
        and any(marker in user for marker in vague_markers)
        and not any(marker in user for marker in explicit_patch_markers)
        and explicit_path is None
    ):
        return adjudicated_payload(
            facts={
                "intent_type": "invalid_intent",
                "path_scope": "no_path",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="000000",
            action="DENY_AND_LEDGER",
            reason="undefined_action_intent",
        )

    return predicted_payload
