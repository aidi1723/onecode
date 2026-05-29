from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .audit import append_audit_record, build_evidence_record


def freeze_halt_snapshot(
    active_context: dict[str, Any],
    snapshot_dir: str | Path,
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(snapshot_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    last_transition = _last_transition(active_context)
    trigger = _halt_trigger(active_context, last_transition)
    snapshot = {
        "status": "halted",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "halt_reason": trigger,
        "trigger": trigger,
        "retry_count": int(active_context.get("retry_count", 0)),
        "last_transition": last_transition,
        "active_context": active_context,
    }
    path = target_dir / _snapshot_filename(active_context)
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")
    evidence = build_evidence_record(
        command=f"freeze_halt_snapshot {path}",
        exit_code=3,
        stdout=payload,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "risk": active_context.get("guard_risk"),
        "path": str(path),
        "snapshot": snapshot,
        "evidence": evidence,
    }


def _snapshot_filename(active_context: dict[str, Any]) -> str:
    state = str(active_context.get("last_state") or "unknown")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", state).strip("-").lower() or "halt"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{slug}-halt-snapshot.json"


def _last_transition(active_context: dict[str, Any]) -> dict[str, Any] | None:
    transitions = active_context.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        return None
    transition = transitions[-1]
    return dict(transition) if isinstance(transition, dict) else None


def _halt_trigger(
    active_context: dict[str, Any],
    last_transition: dict[str, Any] | None,
) -> str:
    if isinstance(last_transition, dict) and last_transition.get("trigger"):
        return str(last_transition["trigger"])
    if active_context.get("guard_risk") == "high":
        return "risk_high"
    if int(active_context.get("retry_count", 0)) >= 3:
        return "retry_limit_exceeded"
    return "halted"
