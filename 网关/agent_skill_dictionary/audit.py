from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import threading
from pathlib import Path
from typing import Any


_AUDIT_LOCKS: dict[Path, threading.Lock] = {}
_AUDIT_LOCKS_GUARD = threading.Lock()


def build_evidence_record(
    command: str,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> dict[str, object]:
    stdout_digest = _sha256_text(stdout)
    stderr_digest = _sha256_text(stderr)
    base_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "exit_code": exit_code,
        "stdout_digest": stdout_digest,
        "stderr_digest": stderr_digest,
    }
    canonical = json.dumps(base_record, ensure_ascii=False, sort_keys=True)
    return {**base_record, "sha256": _sha256_text(canonical)}


def append_audit_record(path: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(log_path):
        previous = _last_record(log_path)
        previous_sha256 = previous.get("sha256") if previous else None
        chained = {**record, "previous_sha256": previous_sha256}
        canonical = json.dumps(
            {key: value for key, value in chained.items() if key != "sha256"},
            ensure_ascii=False,
            sort_keys=True,
        )
        written = {**chained, "sha256": _sha256_text(canonical)}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(written, ensure_ascii=False, sort_keys=True) + "\n")
        return written


def read_audit_log(path: str | Path) -> list[dict[str, Any]]:
    log_path = Path(path)
    if not log_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def verify_audit_chain(path: str | Path) -> dict[str, Any]:
    records = read_audit_log(path)
    errors: list[dict[str, Any]] = []
    previous_sha256 = None
    for index, record in enumerate(records):
        expected_previous = previous_sha256
        if record.get("previous_sha256") != expected_previous:
            errors.append(
                {
                    "index": index,
                    "reason": "previous_sha256_mismatch",
                    "expected": expected_previous,
                    "actual": record.get("previous_sha256"),
                }
            )
        canonical = json.dumps(
            {key: value for key, value in record.items() if key != "sha256"},
            ensure_ascii=False,
            sort_keys=True,
        )
        expected_sha256 = _sha256_text(canonical)
        if record.get("sha256") != expected_sha256:
            errors.append(
                {
                    "index": index,
                    "reason": "sha256_mismatch",
                    "expected": expected_sha256,
                    "actual": record.get("sha256"),
                }
            )
        previous_sha256 = record.get("sha256")
    return {"valid": not errors, "count": len(records), "errors": errors}


def _last_record(path: Path) -> dict[str, Any] | None:
    records = read_audit_log(path)
    return records[-1] if records else None


def _lock_for(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _AUDIT_LOCKS_GUARD:
        if resolved not in _AUDIT_LOCKS:
            _AUDIT_LOCKS[resolved] = threading.Lock()
        return _AUDIT_LOCKS[resolved]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
