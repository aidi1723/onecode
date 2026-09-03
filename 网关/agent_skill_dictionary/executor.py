from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any

from .audit import append_audit_record, build_evidence_record


def execute_command(
    command: list[str],
    cwd: str | Path,
    audit_log_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    timeout_seconds: int = 120,
    use_docker: bool = False,
    docker_image: str = "python:3.11-slim",
    require_docker: bool = False,
) -> dict[str, Any]:
    working_dir = Path(cwd).resolve()
    root = Path(workspace_root).resolve() if workspace_root is not None else working_dir
    if working_dir != root and root not in working_dir.parents:
        raise ValueError("cwd must be inside workspace_root")

    sandbox = "local"
    sandbox_fallback = None
    requested_command = list(command)
    physical_command = list(command)
    if use_docker:
        if shutil.which("docker"):
            sandbox = "docker"
            physical_command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "1g",
                "--cpus",
                "2",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=256m",
                "--user",
                "65534:65534",
                "-v",
                f"{root}:/workspace:ro",
                "-w",
                "/workspace",
                docker_image,
                *command,
            ]
        else:
            sandbox_fallback = "docker_unavailable"
            if require_docker:
                stderr = "Docker sandbox is required but docker is unavailable."
                evidence = build_evidence_record(
                    command=f"docker run {docker_image} {' '.join(command)}",
                    exit_code=126,
                    stdout="",
                    stderr=stderr,
                )
                if audit_log_path is not None:
                    evidence = append_audit_record(audit_log_path, evidence)
                return {
                    "command": command,
                    "physical_command": [],
                    "cwd": str(working_dir),
                    "sandbox": "docker",
                    "sandbox_fallback": sandbox_fallback,
                    "exit_code": 126,
                    "stdout": "",
                    "stderr": stderr,
                    "evidence": evidence,
                }

    command_text = " ".join(physical_command)
    exit_code, stdout, stderr = _run_physical_command(
        physical_command,
        working_dir,
        timeout_seconds,
    )
    if (
        use_docker
        and sandbox == "docker"
        and not require_docker
        and _is_docker_infrastructure_failure(stderr)
    ):
        sandbox = "local"
        sandbox_fallback = "docker_failed"
        physical_command = requested_command
        command_text = " ".join(physical_command)
        exit_code, stdout, stderr = _run_physical_command(
            physical_command,
            working_dir,
            timeout_seconds,
        )
    evidence = build_evidence_record(
        command=command_text,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )
    if audit_log_path is not None:
        evidence = append_audit_record(audit_log_path, evidence)
    return {
        "command": command,
        "physical_command": physical_command,
        "cwd": str(working_dir),
        "sandbox": sandbox,
        "sandbox_fallback": sandbox_fallback,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "evidence": evidence,
    }


def _run_physical_command(
    physical_command: list[str],
    working_dir: Path,
    timeout_seconds: int,
) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            physical_command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_output(exc.stdout)
        stderr = (_decode_timeout_output(exc.stderr) + f"\nTIMEOUT: command exceeded {timeout_seconds} seconds").strip()
        return 124, stdout, stderr
    except FileNotFoundError as exc:
        missing = physical_command[0] if physical_command else str(exc)
        return 127, "", f"Command not found: {missing}"


def _is_docker_infrastructure_failure(stderr: str) -> bool:
    normalized = stderr.lower()
    markers = (
        "permission denied while trying to connect to the docker api",
        "cannot connect to the docker daemon",
        "is the docker daemon running",
        "error during connect",
    )
    return any(marker in normalized for marker in markers)


def _decode_timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
