from __future__ import annotations

from typing import Any


BLOCKED_STATUSES = {"denied", "halted", "blocked", "rejected"}
WARNING_STATUSES = {"partial", "skipped"}
SHELL_PROJECTION_VERSION = 1
SHELL_PROJECTION_FIELDS = (
    "version",
    "run_id",
    "status_label",
    "severity",
    "next_action",
    "compact_message",
    "rule_state",
    "control_state",
    "delivery_state",
    "evidence_ref",
    "resume_state",
)
RULE_STATE_FIELDS = (
    "status_code",
    "transition_action",
    "transition_reason",
    "dispatch_decision",
)
CONTROL_STATE_FIELDS = (
    "project_context_status",
    "runtime_config_status",
    "recovery_action",
)
DELIVERY_STATE_FIELDS = (
    "status",
    "next_action",
    "requested_count",
    "completed_count",
    "skipped_count",
    "failed_count",
)
EVIDENCE_REF_FIELDS = (
    "mode",
    "ledger_path",
    "manifest_path",
    "trace_path",
    "wal_path",
    "corrupt_path",
    "profile_sha256",
)
RESUME_STATE_FIELDS = (
    "resumed",
    "resumed_from",
)
SEVERITY_VALUES = ("blocked", "corrupt", "missing", "ok", "warning")


def shell_projection_schema() -> dict[str, Any]:
    return {
        "name": "onecode.shell_projection",
        "version": SHELL_PROJECTION_VERSION,
        "fields": {
            "version": {"type": "integer", "description": "Shell projection schema version."},
            "run_id": {"type": "string|null", "description": "OneCode run identifier."},
            "status_label": {"type": "string", "description": "Raw run status normalized for shell display."},
            "severity": {
                "type": "string",
                "values": list(SEVERITY_VALUES),
                "description": "Shell-facing status severity.",
            },
            "next_action": {"type": "string", "description": "Recommended shell action."},
            "compact_message": {"type": "string", "description": "Single-line human-readable summary."},
            "rule_state": {"type": "object", "fields": list(RULE_STATE_FIELDS)},
            "control_state": {"type": "object", "fields": list(CONTROL_STATE_FIELDS)},
            "delivery_state": {"type": "object", "fields": list(DELIVERY_STATE_FIELDS)},
            "evidence_ref": {"type": "object", "fields": list(EVIDENCE_REF_FIELDS)},
            "resume_state": {"type": "object", "fields": list(RESUME_STATE_FIELDS)},
        },
        "nested_fields": {
            "rule_state": list(RULE_STATE_FIELDS),
            "control_state": list(CONTROL_STATE_FIELDS),
            "delivery_state": list(DELIVERY_STATE_FIELDS),
            "evidence_ref": list(EVIDENCE_REF_FIELDS),
            "resume_state": list(RESUME_STATE_FIELDS),
        },
    }


def project_run_to_shell(run: dict[str, Any]) -> dict[str, Any]:
    status_label = _string(run.get("status")) or "unknown"
    severity = _severity(run, status_label)
    next_action = _next_action(run, severity)
    evidence_ref = _evidence_ref(run)
    rule_state = _rule_state(run)
    control_state = _control_state(run)
    delivery_state = _delivery_state(run)
    resume_state = {
        "resumed": run.get("resumed") if isinstance(run.get("resumed"), bool) else None,
        "resumed_from": _string(run.get("resumed_from")),
    }

    projection = {
        "version": SHELL_PROJECTION_VERSION,
        "run_id": _string(run.get("run_id")),
        "status_label": status_label,
        "severity": severity,
        "next_action": next_action,
        "compact_message": _compact_message(run, status_label, severity, next_action, evidence_ref, rule_state),
        "rule_state": rule_state,
        "control_state": control_state,
        "delivery_state": delivery_state,
        "evidence_ref": evidence_ref,
        "resume_state": resume_state,
    }
    return projection


def attach_shell_projection(run: dict[str, Any]) -> dict[str, Any]:
    return {**run, "shell_projection": project_run_to_shell(run)}


def attach_shell_projection_to_runs_payload(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return {**payload, "runs": []}
    return {
        **payload,
        "runs": [attach_shell_projection(run) if isinstance(run, dict) else run for run in runs],
    }


def _string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _first_string(*values: Any) -> str | None:
    for value in values:
        text = _string(value)
        if text is not None:
            return text
    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _severity(run: dict[str, Any], status_label: str) -> str:
    if status_label == "corrupt":
        return "corrupt"
    if status_label == "missing":
        return "missing"
    if status_label in BLOCKED_STATUSES:
        return "blocked"
    if run.get("partial") is True or status_label in WARNING_STATUSES:
        return "warning"
    if status_label == "completed":
        return "ok"
    return "warning"


def _next_action(run: dict[str, Any], severity: str) -> str:
    explicit = _string(run.get("next_action"))
    if explicit is not None:
        return explicit
    if severity in {"corrupt", "missing", "blocked"}:
        return "inspect"
    if severity == "warning":
        return "verify"
    return "idle"


def _rule_state(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_code": _integer(
            run.get("iching_status_code", run.get("global_status_code", run.get("task_status_code")))
        ),
        "transition_action": _string(
            run.get(
                "iching_transition_action",
                run.get("global_transition_action", run.get("task_transition_action")),
            )
        ),
        "transition_reason": _string(
            run.get(
                "iching_transition_reason",
                run.get("global_transition_reason", run.get("task_transition_reason")),
            )
        ),
        "dispatch_decision": _string(
            run.get("task_dispatch_decision", run.get("dispatch_decision", run.get("decision")))
        ),
    }


def _control_state(run: dict[str, Any]) -> dict[str, Any]:
    project_context = run.get("project_context")
    runtime_config = run.get("runtime_config")
    recovery_policy = run.get("recovery_policy")
    recovery = run.get("recovery")

    return {
        "project_context_status": _first_string(
            project_context.get("status") if isinstance(project_context, dict) else None,
            run.get("project_context_status"),
        ),
        "runtime_config_status": _first_string(
            runtime_config.get("status") if isinstance(runtime_config, dict) else None,
            run.get("runtime_config_status"),
        ),
        "recovery_action": _first_string(
            recovery_policy.get("recommended_action") if isinstance(recovery_policy, dict) else None,
            recovery_policy.get("action") if isinstance(recovery_policy, dict) else None,
            recovery.get("recommended_action") if isinstance(recovery, dict) else None,
            recovery.get("action") if isinstance(recovery, dict) else None,
            run.get("recovery_action"),
        ),
    }


def _delivery_state(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _string(run.get("delivery_status")),
        "next_action": _string(run.get("next_action")),
        "requested_count": _integer(run.get("requested_count")),
        "completed_count": _integer(run.get("completed_count")),
        "skipped_count": _integer(run.get("skipped_count")),
        "failed_count": _integer(run.get("failed_count")),
    }


def _evidence_ref(run: dict[str, Any]) -> dict[str, Any]:
    ledger_path = _string(run.get("ledger_path"))
    manifest_path = _string(run.get("manifest_path"))
    trace_path = _string(run.get("trace_path"))
    wal_path = _string(run.get("wal_path"))
    mode = _string(run.get("evidence_mode"))
    if mode not in {"wal", "full"}:
        if wal_path is not None:
            mode = "wal"
        elif ledger_path is not None or manifest_path is not None:
            mode = "full"
        else:
            mode = "unknown"
    return {
        "mode": mode,
        "ledger_path": ledger_path,
        "manifest_path": manifest_path,
        "trace_path": trace_path,
        "wal_path": wal_path,
        "corrupt_path": _string(run.get("corrupt_path")),
        "profile_sha256": _string(run.get("profile_sha256")),
    }


def _compact_message(
    run: dict[str, Any],
    status_label: str,
    severity: str,
    next_action: str,
    evidence_ref: dict[str, Any],
    rule_state: dict[str, Any],
) -> str:
    run_id = _string(run.get("run_id")) or "unknown-run"
    parts = [f"OneCode run {run_id}: {status_label}", f"severity={severity}"]
    action = rule_state.get("transition_action")
    if action is not None:
        parts.append(f"action={action}")
    reason = _string(run.get("reason")) or _string(run.get("corrupt_reason")) or rule_state.get("transition_reason")
    if reason is not None:
        parts.append(f"reason={reason}")
    parts.append(f"next={next_action}")
    evidence_mode = evidence_ref.get("mode")
    if evidence_mode is not None:
        parts.append(f"evidence={evidence_mode}")
    return "; ".join(parts)
