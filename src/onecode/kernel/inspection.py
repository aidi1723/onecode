import json
import string
from pathlib import Path

from onecode.kernel.checkpoint import evidence_chain_hash, sha256_file, sha256_text


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


def validate_trace_completion(ledger: dict, trace_path: Path) -> tuple[str | None, str | None]:
    if not trace_path.exists():
        return str(trace_path), "missing_trace"
    completed_seen = False
    try:
        lines = trace_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return str(trace_path), "trace_unreadable"
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return str(trace_path), "invalid_trace_json"
        if not isinstance(event, dict):
            return str(trace_path), "invalid_trace_event"
        if event.get("event_type") == "run_completed":
            completed_seen = True
            if event.get("status") != ledger.get("status"):
                return str(trace_path), "trace_status_mismatch"
    if not completed_seen:
        return str(trace_path), "missing_trace_run_completed"
    return None, None


def validate_evidence_chain(chain_path: Path) -> tuple[str | None, str | None]:
    if not chain_path.exists():
        return None, None
    previous_hash = "0" * SHA256_HEX_LENGTH
    expected_sequence = 1
    try:
        lines = chain_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return str(chain_path), "evidence_chain_unreadable"
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return str(chain_path), "invalid_evidence_chain_json"
        if not isinstance(record, dict):
            return str(chain_path), "invalid_evidence_chain_record"
        if record.get("sequence") != expected_sequence:
            return str(chain_path), "evidence_chain_sequence_mismatch"
        if record.get("previous_chain_hash") != previous_hash:
            return str(chain_path), "evidence_chain_previous_hash_mismatch"
        chain_hash = record.get("chain_hash")
        if not isinstance(chain_hash, str) or len(chain_hash) != SHA256_HEX_LENGTH:
            return str(chain_path), "invalid_evidence_chain_hash"
        if chain_hash != evidence_chain_hash(record):
            return str(chain_path), "evidence_chain_hash_mismatch"
        artifact_path_value = record.get("artifact_path")
        artifact_sha256 = record.get("artifact_sha256")
        if not isinstance(artifact_path_value, str) or not isinstance(artifact_sha256, str):
            return str(chain_path), "invalid_evidence_chain_artifact"
        artifact_path = Path(artifact_path_value)
        if not artifact_path.exists():
            return str(chain_path), "missing_evidence_chain_artifact"
        artifact_line_number = record.get("artifact_line_number")
        if isinstance(artifact_line_number, int):
            lines = [line + "\n" for line in artifact_path.read_text(encoding="utf-8").splitlines()]
            index = artifact_line_number - 1
            if index < 0 or index >= len(lines):
                return str(chain_path), "missing_evidence_chain_artifact_line"
            artifact_hash = sha256_text(lines[index])
        else:
            artifact_hash = sha256_file(artifact_path)
        if artifact_hash != artifact_sha256:
            return str(chain_path), "evidence_chain_artifact_mismatch"
        previous_hash = chain_hash
        expected_sequence += 1
    return None, None
