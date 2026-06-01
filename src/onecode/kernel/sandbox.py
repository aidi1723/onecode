from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class SandboxConfig:
    workspace: Path
    image: str = "python:3.12-slim"
    network: str = "none"
    memory: str = "512m"
    cpus: str = "1"
    timeout_seconds: int = 60
    pids_limit: int = 256
    read_only: bool = True
    tmpfs: str = "/tmp:rw,noexec,nosuid,size=64m"

    def __post_init__(self) -> None:
        resolved = self.workspace.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"sandbox workspace does not exist: {resolved}")
        object.__setattr__(self, "workspace", resolved)
        if self.timeout_seconds <= 0:
            raise ValueError("sandbox timeout_seconds must be positive")
        if self.pids_limit <= 0:
            raise ValueError("sandbox pids_limit must be positive")


def build_docker_command(config: SandboxConfig, command: Sequence[str]) -> list[str]:
    if not command:
        raise ValueError("sandbox command must not be empty")
    docker_command = [
        "docker",
        "run",
        "--rm",
        "--network",
        config.network,
        "--memory",
        config.memory,
        "--cpus",
        config.cpus,
        "--pids-limit",
        str(config.pids_limit),
        "--cap-drop",
        "ALL",
        "--tmpfs",
        config.tmpfs,
    ]
    if config.read_only:
        docker_command.append("--read-only")
    return [
        *docker_command,
        "--volume",
        f"{config.workspace}:/workspace",
        "--workdir",
        "/workspace",
        config.image,
        *command,
    ]


def run_in_sandbox(config: SandboxConfig, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        build_docker_command(config, command),
        text=True,
        capture_output=True,
        timeout=config.timeout_seconds,
        check=False,
    )


def run_sandbox_smoke(
    config: SandboxConfig,
    report_path: Path | None = None,
) -> dict[str, object]:
    if shutil.which("docker") is None:
        result: dict[str, object] = {
            "status": "blocked",
            "reason": "docker_not_found",
            "workspace": str(config.workspace),
            "image": config.image,
        }
        write_sandbox_smoke_report(report_path, result)
        return result

    command = [
        "python",
        "-c",
        "from pathlib import Path; Path('sandbox-smoke.txt').write_text('ok\\n'); print(Path('/workspace').exists())",
    ]
    completed = run_in_sandbox(config, command)
    marker = config.workspace / "sandbox-smoke.txt"
    passed = completed.returncode == 0 and marker.exists() and marker.read_text(encoding="utf-8") == "ok\n"
    reason = None
    if not passed:
        if completed.returncode == 0 and "True" in (completed.stdout or "") and not marker.exists():
            reason = "sandbox_mount_not_propagated"
        else:
            reason = "sandbox_smoke_failed"
    result = {
        "status": "completed" if passed else "failed",
        "reason": reason,
        "workspace": str(config.workspace),
        "image": config.image,
        "exit_code": completed.returncode,
        "stdout_tail": (completed.stdout or "")[-4096:],
        "stderr_tail": (completed.stderr or "")[-4096:],
        "marker_path": str(marker),
    }
    write_sandbox_smoke_report(report_path, result)
    return result


def write_sandbox_smoke_report(path: Path | None, result: dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
