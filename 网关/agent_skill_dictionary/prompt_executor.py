from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .audit import append_audit_record, build_evidence_record


def create_confirmation_ticket(
    active_context: dict[str, Any],
    ticket_dir: str | Path,
    audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = Path(ticket_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    ticket = {
        "status": "pending_human_confirmation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_context": active_context,
        "choices": ["approve", "revise", "halt"],
    }
    path = target_dir / _ticket_filename(active_context)
    payload = json.dumps(ticket, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")
    evidence = build_evidence_record(
        command=f"create_confirmation_ticket {path}",
        exit_code=4,
        stdout=payload,
        stderr="",
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "ok": True,
        "needs_human": True,
        "path": str(path),
        "ticket": ticket,
        "evidence": evidence,
    }


def _ticket_filename(active_context: dict[str, Any]) -> str:
    request = str(active_context.get("original_request") or "confirmation")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", request).strip("-").lower()[:48] or "confirmation"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{slug}-ticket.json"
