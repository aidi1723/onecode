from __future__ import annotations

import secrets
from typing import Mapping


LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    lowered = headers.get(name.lower())
    if isinstance(lowered, str):
        return lowered.strip()
    return ""


def _split_host_header(value: str) -> tuple[str, str] | None:
    if value.startswith("["):
        end = value.find("]")
        if end == -1 or not value[end + 1 :].startswith(":"):
            return None
        return value[1:end].lower(), value[end + 2 :]
    host, separator, port = value.rpartition(":")
    if separator == "":
        return None
    return host.lower(), port


def local_request_allowed(headers: Mapping[str, str], *, bound_port: int) -> bool:
    parsed = _split_host_header(_header(headers, "Host"))
    if parsed is None:
        return False
    host, port = parsed
    if port != str(bound_port) or host not in LOOPBACK_HOSTS:
        return False
    origin = _header(headers, "Origin").rstrip("/")
    if origin == "":
        return True
    allowed = {
        f"http://127.0.0.1:{bound_port}",
        f"http://localhost:{bound_port}",
        f"http://[::1]:{bound_port}",
    }
    return origin in allowed


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
    return secrets.compare_digest(authorization.encode("utf-8"), f"Bearer {token}".encode("utf-8"))
