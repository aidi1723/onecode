from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from onecode.kernel.checkpoint import file_lock
from onecode.kernel.model_config import write_private_text


@dataclass(frozen=True)
class ShellSecrets:
    jwt_secret: str
    jwt_refresh_secret: str
    creds_key: str
    creds_iv: str


_SECRET_HEX_LENGTHS = {
    "jwt_secret": 64,
    "jwt_refresh_secret": 64,
    "creds_key": 64,
    "creds_iv": 32,
}
_RUNTIME_STATUSES = {"starting", "running", "stopping", "stopped", "failed"}
_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+"),
    re.compile(
        r"(?i)((?:api[_-]?key|openai_api_key|onecode_api_token)\s*[:=]\s*)\S+"
    ),
    re.compile(r"(?i)(password\s*[:=]\s*)\S+"),
)


def validate_shell_secrets(payload: Any) -> ShellSecrets:
    if not isinstance(payload, dict) or set(payload) != set(_SECRET_HEX_LENGTHS):
        raise ValueError("invalid shell secret state")
    for key, length in _SECRET_HEX_LENGTHS.items():
        value = payload.get(key)
        if not isinstance(value, str) or re.fullmatch(
            rf"[0-9a-f]{{{length}}}", value
        ) is None:
            raise ValueError("invalid shell secret state")
    return ShellSecrets(**payload)


def load_or_create_shell_secrets(root: Path) -> ShellSecrets:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    path = root / "auth-secrets.json"
    with file_lock(root / ".auth-secrets.lock"):
        if path.exists():
            path.chmod(0o600)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError("invalid shell secret state") from exc
            return validate_shell_secrets(payload)

        payload = ShellSecrets(
            jwt_secret=secrets.token_hex(32),
            jwt_refresh_secret=secrets.token_hex(32),
            creds_key=secrets.token_hex(32),
            creds_iv=secrets.token_hex(16),
        )
        write_private_text(
            path,
            json.dumps(asdict(payload), sort_keys=True) + "\n",
        )
        return payload


def redact_runtime_text(value: str) -> str:
    redacted = value
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def write_runtime_status(
    root: Path,
    *,
    status: str,
    services: dict[str, int],
    last_failure: str | None = None,
) -> Path:
    if status not in _RUNTIME_STATUSES:
        raise ValueError(f"invalid shell runtime status: {status}")
    if not isinstance(services, dict) or any(
        not isinstance(name, str)
        or not name
        or isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        for name, pid in services.items()
    ):
        raise ValueError("shell runtime services must map names to positive PIDs")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    payload: dict[str, Any] = {
        "status": status,
        "services": services,
    }
    if last_failure is not None:
        payload["last_failure"] = redact_runtime_text(str(last_failure))[-2000:]
    path = root / "runtime-status.json"
    write_private_text(path, json.dumps(payload, sort_keys=True) + "\n")
    return path
