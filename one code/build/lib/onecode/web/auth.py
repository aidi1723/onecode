from __future__ import annotations

import secrets


LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def request_authorized(
    headers: dict[str, str],
    token: str | None,
    *,
    allow_unauthenticated: bool = False,
    host: str = "127.0.0.1",
) -> bool:
    if token is None or token.strip() == "":
        return allow_unauthenticated and host in LOOPBACK_HOSTS
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    return secrets.compare_digest(authorization, f"Bearer {token}")
