"""Explicit local-deployment boundary reported by doctor.

A checkout is production-ready only when command execution can use Docker,
unauthenticated local access is off, and an API token is set.
"""

from __future__ import annotations

import os
import shutil
import subprocess


def _docker_daemon_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def deployment_boundary() -> dict[str, object]:
    mode = os.environ.get("ONECODE_RUN_COMMAND_SANDBOX", "auto").strip().lower() or "auto"
    if mode not in {"auto", "host", "docker", "on", "off", "true", "false", "0", "1"}:
        mode = "auto"
    docker_ready = _docker_daemon_ready()
    unauthenticated = os.getenv("ONECODE_ALLOW_UNAUTHENTICATED", "").lower() in {"1", "true", "yes", "on"}
    token_set = bool(os.getenv("ONECODE_API_TOKEN", "").strip())
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
