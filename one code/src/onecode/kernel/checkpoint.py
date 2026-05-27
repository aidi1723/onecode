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


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint(
    context: OneCodeContext,
    payload: dict[str, Any],
    next_state: HexagramStatusCode,
    status: str,
    partial: bool,
    reason: str | None,
    intent_type: str | None = None,
    decision: str | None = None,
) -> Path:
    existing_manifest = read_manifest(context.manifest_path)
    existing_checkpoints = []
    if existing_manifest is not None:
        existing_checkpoints = list(existing_manifest.get("checkpoints", []))

    turn_number = len(existing_checkpoints) + 1
    checkpoint_path = context.evidence_root / "checkpoints" / f"{turn_number:04d}.json"
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
    }
    manifest = {
        "run_id": context.run_id,
        "created_at": existing_manifest.get("created_at") if existing_manifest else utc_now_iso(),
        "updated_at": utc_now_iso(),
        "workspace_root": str(context.workspace_root),
        "current_state": str(next_state),
        "status": status,
        "partial": partial,
        "reason": reason,
        "checkpoints": existing_checkpoints + [checkpoint_record],
    }
    atomic_write_json(context.manifest_path, manifest)
    return checkpoint_path


def write_ledger(context: OneCodeContext, result: dict[str, Any]) -> Path:
    ledger_path = context.evidence_root / "ledger.json"
    atomic_write_json(ledger_path, result)
    return ledger_path
