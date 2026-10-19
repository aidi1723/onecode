"""Explicit local-deployment boundary reported by doctor.

A checkout is production-ready only when command execution can use Docker,
unauthenticated local access is off, and an API token is set.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_PUBLISHED_LOCAL_CREDENTIALS = frozenset({"dev-local-token", "OneCode123!"})


def _docker_daemon_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def api_token() -> str:
    """Return the process token, or the private file when the environment is unset."""
    if "ONECODE_API_TOKEN" in os.environ:
        value = os.environ["ONECODE_API_TOKEN"].strip()
        if value and value not in _PUBLISHED_LOCAL_CREDENTIALS:
            return value
        return ""
    home = Path(os.environ.get("ONECODE_HOME", "~/.onecode")).expanduser()
    path = home / "shell" / "api-token"
    try:
        if not path.is_file() or path.stat().st_mode & 0o077:
            return ""
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not value or value in _PUBLISHED_LOCAL_CREDENTIALS:
        return ""
    return value


def deployment_boundary() -> dict[str, object]:
    mode = os.environ.get("ONECODE_RUN_COMMAND_SANDBOX", "auto").strip().lower() or "auto"
    if mode not in {"auto", "host", "docker", "on", "off", "true", "false", "0", "1"}:
        mode = "auto"
    docker_ready = _docker_daemon_ready()
    unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}
    token_set = bool(api_token())
    sandbox_effective = mode in {"docker", "on", "true", "1"} or (mode not in {"host", "off", "false", "0"} and docker_ready)
    production_ready = bool(sandbox_effective and docker_ready and token_set and not unauthenticated)
    return {
        "command_sandbox": mode,
        "docker_ready": docker_ready,
        "sandbox_effective": sandbox_effective,
        "unauthenticated_local": unauthenticated,
        "api_token_set": token_set,
        "production_ready": production_ready,
    }
