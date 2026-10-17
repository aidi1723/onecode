"""Durable pending approvals for one agent-cycle tool call."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from onecode.kernel.evidence_io import file_lock
from onecode.kernel.model_config import onecode_home


PENDING_STATUS = "PENDING_APPROVAL"
_DIRECTORY = ".onecode/pending-cycle"


def persist_pending_approval(workspace: Path, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    existing = find_pending_approval(workspace, tool_name, params)
    if existing is not None:
        return existing
    record = {
        "version": 1,
        "id": secrets.token_hex(16),
        "status": PENDING_STATUS,
        "tool_name": tool_name,
        "params": params,
        "reason": "approval_required",
    }
    record["signature"] = _sign_record(workspace, tool_name, params, str(record["id"]))
    path = _record_path(workspace, tool_name, params)
    _atomic_write(path, json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
    return record


def find_pending_approval(workspace: Path, tool_name: str, params: dict[str, Any]) -> dict[str, Any] | None:
    path = _record_path(workspace, tool_name, params)
    if not path.is_file():
        return None
    record = _read_record(path)
    if record is None or record.get("status") != PENDING_STATUS:
        return None
    return record


def load_pending_approvals(workspace: Path) -> list[dict[str, Any]]:
    directory = Path(workspace).resolve() / _DIRECTORY
    if not directory.is_dir():
        return []
    records = []
    for path in sorted(directory.glob("*.json")):
        record = _read_record(path)
        if record is not None and record.get("status") == PENDING_STATUS:
            records.append(record)
    return records


def consume_pending_approval(workspace: Path, tool_name: str, params: dict[str, Any]) -> None:
    _record_path(workspace, tool_name, params).unlink(missing_ok=True)


def resume_pending_approval(workspace: Path, pending_id: str, decision: str, execute) -> dict[str, Any]:
    directory = Path(workspace).resolve() / _DIRECTORY
    with file_lock(directory.parent / "pending-cycle.lock"):
        match = next((record for record in load_pending_approvals(workspace) if record.get("id") == pending_id), None)
        if match is None:
            raise ValueError("approval_not_found")
        path = _record_path(workspace, str(match["tool_name"]), match["params"])
        path.unlink(missing_ok=True)
    if decision != "approved":
        return {
            "status": "halted",
            "reason": "permission_denied",
            "pending_id": pending_id,
            "tool_name": match["tool_name"],
            "params": match["params"],
        }
    return execute(match["tool_name"], match["params"])



def _get_approval_secret(workspace: Path) -> bytes:
    root = onecode_home()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)

    key_path = root / "approval-secret.key"
    with file_lock(root / ".approval-secret.lock"):
        if key_path.exists():
            key_path.chmod(0o600)
            try:
                secret_hex = key_path.read_text(encoding="utf-8").strip()
                if len(secret_hex) != 64:
                    raise ValueError("invalid length for approval secret")
                return bytes.fromhex(secret_hex)
            except (OSError, ValueError) as exc:
                raise ValueError("approval secret is corrupted or unreadable") from exc

        new_secret = secrets.token_bytes(32)
        descriptor = os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, (new_secret.hex() + "\n").encode("utf-8"))
        finally:
            os.close(descriptor)
        return new_secret

def _sign_record(workspace: Path, tool_name: str, params: dict[str, Any], record_id: str) -> str:
    msg = json.dumps({"id": record_id, "tool": tool_name, "params": params}, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hmac.new(_get_approval_secret(workspace), msg, hashlib.sha256).hexdigest()

def _record_path(workspace: Path, tool_name: str, params: dict[str, Any]) -> Path:
    signature = hashlib.sha256(
        json.dumps({"tool": tool_name, "params": params}, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return Path(workspace).resolve() / _DIRECTORY / f"{signature}.json"


def _read_record(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    params = payload.get("params")
    if not isinstance(params, dict) or not isinstance(payload.get("tool_name"), str):
        return None
        
    expected_sig = _sign_record(path.parent.parent.parent, payload["tool_name"], params, payload.get("id", ""))
    import hmac
    if not hmac.compare_digest(expected_sig, payload.get("signature", "")):
        return None
        
    return payload


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    with file_lock(path.parent.parent / "pending-cycle.lock"):
        try:
            with NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
                temporary = handle.name
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
