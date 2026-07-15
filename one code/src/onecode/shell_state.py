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
