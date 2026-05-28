import json
import string
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file


VALID_RUN_STATUSES = {"completed", "skipped", "denied", "halted"}
LEDGER_COUNT_FIELDS = ("requested_count", "completed_count", "skipped_count", "failed_count")
SHA256_HEX_LENGTH = 64
HEX_DIGITS = set(string.hexdigits)


def read_json(path: Path) -> tuple[dict | None, str | None, str | None]:
    if not path.exists():
        return None, None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, str(path), "invalid_json"
    if not isinstance(data, dict):
        return None, str(path), "non_object_json"
    return data, None, None


def validate_status_document(data: dict, path: Path) -> tuple[str | None, str | None]:
    if "status" not in data:
        return str(path), "missing_status"
    if not isinstance(data["status"], str) or not data["status"]:
        return str(path), "invalid_status"
    if data["status"] not in VALID_RUN_STATUSES:
        return str(path), "invalid_status"
    return None, None


def validate_ledger_counts(ledger: dict, path: Path) -> tuple[str | None, str | None]:
    for field in LEDGER_COUNT_FIELDS:
        if field in ledger and (not isinstance(ledger[field], int) or ledger[field] < 0):
            return str(path), "invalid_count"
    if all(field in ledger for field in LEDGER_COUNT_FIELDS):
        resolved_count = ledger["completed_count"] + ledger["skipped_count"] + ledger["failed_count"]
        if resolved_count > ledger["requested_count"]:
            return str(path), "count_mismatch"
    return None, None


def validate_checkpoint_evidence(checkpoints: list[dict], path: Path) -> tuple[str | None, str | None]:
    for checkpoint in checkpoints:
        if not isinstance(checkpoint.get("path"), str) or not checkpoint["path"]:
            return str(path), "invalid_checkpoint_evidence"
        if not isinstance(checkpoint.get("sha256"), str) or not checkpoint["sha256"]:
            return str(path), "invalid_checkpoint_evidence"
        if len(checkpoint["sha256"]) != SHA256_HEX_LENGTH:
            return str(path), "invalid_checkpoint_evidence"
        if any(character not in HEX_DIGITS for character in checkpoint["sha256"]):
            return str(path), "invalid_checkpoint_evidence"
        checkpoint_path = Path(checkpoint["path"])
        if not checkpoint_path.is_absolute():
            checkpoint_path = path.parent / checkpoint_path
        if not checkpoint_path.exists():
            return str(path), "missing_checkpoint_file"
        if sha256_file(checkpoint_path) != checkpoint["sha256"]:
            return str(path), "checkpoint_sha_mismatch"
        checkpoint_payload, corrupt_checkpoint_path, corrupt_checkpoint_reason = read_json(checkpoint_path)
        if corrupt_checkpoint_path is not None:
            return corrupt_checkpoint_path, corrupt_checkpoint_reason
        if checkpoint_payload.get("status") != checkpoint.get("status"):
            return str(path), "checkpoint_record_mismatch"
    return None, None
