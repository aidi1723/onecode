from __future__ import annotations

import hmac
import time
from hashlib import sha256

import jwt


MAX_CLOCK_SKEW_SECONDS = 300


def build_signature(secret: str, method: str, path: str, body: str, timestamp: int | None = None) -> str:
    issued_at = int(time.time()) if timestamp is None else int(timestamp)
    canonical = f"{method.upper()}\n{path}\n{issued_at}\n{body}"
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), sha256).hexdigest()
    return jwt.encode({"iat": issued_at, "sig": digest}, secret, algorithm="HS256")


def verify_signature(secret: str, method: str, path: str, body: str, token: str) -> bool:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return False

    issued_at = int(payload.get("iat", 0))
    if abs(int(time.time()) - issued_at) > MAX_CLOCK_SKEW_SECONDS:
        return False

    canonical = f"{method.upper()}\n{path}\n{issued_at}\n{body}"
    expected = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), sha256).hexdigest()
    return hmac.compare_digest(str(payload.get("sig", "")), expected)
