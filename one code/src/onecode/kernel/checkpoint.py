import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from onecode.kernel.context import OneCodeContext
from onecode.kernel.hexagram import HexagramStatusCode


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def append_json_line(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ready_assets_summary(context: OneCodeContext) -> dict[str, dict[str, Any]]:
    if context.resume_state is None:
        return {}
    return {
        path: {
            "sha256": asset.sha256,
            "source_run_id": asset.source_run_id,
            "source_turn_index": asset.source_turn_index,
        }
        for path, asset in sorted(context.resume_state.ready_assets.items())
    }


def resume_audit_events_summary(context: OneCodeContext) -> list[dict[str, Any]]:
    if context.resume_state is None:
        return []
    return list(context.resume_state.audit_events)


def write_checkpoint(
    context: OneCodeContext,
    payload: dict[str, Any],
    next_state: HexagramStatusCode,
    status: str,
    partial: bool,
    reason: str | None,
    intent_type: str | None = None,
    decision: str | None = None,
    iching_status_code: int | None = None,
    iching_transition_action: str | None = None,
    iching_transition_reason: str | None = None,
    iching_profile: dict[str, Any] | None = None,
    duration_ms: int = 0,
    run_control: dict[str, Any] | None = None,
) -> Path:
    existing_manifest = read_manifest(context.manifest_path)
    existing_checkpoints = []
    if existing_manifest is not None:
        existing_checkpoints = list(existing_manifest.get("checkpoints", []))

    turn_number = len(existing_checkpoints) + 1
    checkpoint_path = context.evidence_root / "checkpoints" / f"{turn_number:04d}.json"
    resumed_from = context.resume_from_run_id
    ready_assets = ready_assets_summary(context)
    resume_audit_events = resume_audit_events_summary(context)
    checkpoint = {
        "run_id": context.run_id,
        "turn_index": turn_number,
        "previous_state": str(context.state),
        "next_state": str(next_state),
        "status": status,
        "partial": partial,
        "reason": reason,
        "intent_type": intent_type,
        "decision": decision,
        "iching_status_code": iching_status_code,
        "iching_transition_action": iching_transition_action,
        "iching_transition_reason": iching_transition_reason,
        "iching_profile": iching_profile,
        "duration_ms": duration_ms,
        "run_control": run_control,
        "resumed_from": resumed_from,
        "ready_assets": ready_assets,
        "resume_audit_events": resume_audit_events,
        "created_at": utc_now_iso(),
        "payload": payload,
    }
    atomic_write_json(checkpoint_path, checkpoint)

    checkpoint_hash = sha256_file(checkpoint_path)
    checkpoint_record = {
        "path": str(checkpoint_path),
        "sha256": checkpoint_hash,
        "turn_index": turn_number,
        "status": status,
        "partial": partial,
        "reason": reason,
        "intent_type": intent_type,
        "decision": decision,
        "iching_status_code": iching_status_code,
        "iching_transition_action": iching_transition_action,
        "iching_transition_reason": iching_transition_reason,
        "iching_profile": iching_profile,
        "duration_ms": duration_ms,
        "run_control": run_control,
        "resumed_from": resumed_from,
        "ready_assets": ready_assets,
        "resume_audit_events": resume_audit_events,
    }
    if intent_type == "patch_text":
        patch_evidence_keys = [
            "pre_sha256",
            "post_sha256",
            "search_block_sha256",
            "replace_block_sha256",
        ]
        patch_evidence = {
            key: payload[key]
            for key in patch_evidence_keys
            if isinstance(payload.get(key), str)
        }
        if patch_evidence:
            checkpoint_record["patch_evidence"] = patch_evidence
    manifest = {
        "run_id": context.run_id,
        "created_at": existing_manifest.get("created_at") if existing_manifest else utc_now_iso(),
        "updated_at": utc_now_iso(),
        "workspace_root": str(context.workspace_root),
        "current_state": str(next_state),
        "status": status,
        "partial": partial,
        "reason": reason,
        "iching_status_code": iching_status_code,
        "iching_transition_action": iching_transition_action,
        "iching_transition_reason": iching_transition_reason,
        "iching_profile": iching_profile,
        **(run_control or {}),
        "resumed_from": resumed_from,
        "ready_assets": ready_assets,
        "resume_audit_events": resume_audit_events,
        "checkpoints": existing_checkpoints + [checkpoint_record],
    }
    atomic_write_json(context.manifest_path, manifest)
    return checkpoint_path


def write_ledger(context: OneCodeContext, result: dict[str, Any]) -> Path:
    ledger_path = context.evidence_root / "ledger.json"
    atomic_write_json(ledger_path, result)
    append_json_line(context.evidence_root / "ledger.jsonl", result)
    return ledger_path
