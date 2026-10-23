from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Sequence


def default_sandbox_image() -> str:
    chosen = os.environ.get("ONECODE_SANDBOX_IMAGE", "").strip()
    return chosen or "python:3.12-slim"


@dataclass(frozen=True)
class SandboxConfig:
    workspace: Path
    image: str = field(default_factory=default_sandbox_image)
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
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            raise ValueError("sandbox timeout_seconds must be positive")
        if isinstance(self.pids_limit, bool) or not isinstance(self.pids_limit, int) or self.pids_limit <= 0:
            raise ValueError("sandbox pids_limit must be positive")


def build_docker_command(config: SandboxConfig, command: Sequence[str], name: str | None = None) -> list[str]:
    if not command:
        raise ValueError("sandbox command must not be empty")
    docker_command = [
        "docker",
        "run",
        "--rm",
    ]
    if name:
        docker_command.extend(["--name", name])
    docker_command.extend([
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
        "--env",
        "PYTHONSAFEPATH=1",
    ])
    if ":" in config.workspace.as_posix():
        raise ValueError("sandbox workspace path must not contain ':'")
    if config.read_only:
        docker_command.append("--read-only")
    mounts = [
        "--mount",
        f"type=bind,src={config.workspace.as_posix()},dst=/workspace",
    ]
    for name in (".git", ".github", ".onecode", "tests"):
        source = config.workspace / name
        if source.is_dir():
            mounts.extend(
                [
                    "--mount",
                    f"type=bind,src={source.as_posix()},dst=/workspace/{name},readonly",
                ]
            )
    return [
        *docker_command,
        "--security-opt",
        "no-new-privileges",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        *mounts,
        "--workdir",
        "/workspace",
        config.image,
        *command,
    ]


def container_argv(command: Sequence[str]) -> list[str]:
    """Run Python with the interpreter that exists inside the image."""
    if not command:
        return []
    argv = [str(part) for part in command]
    if _host_python(argv[0]):
        argv[0] = "python3"
    return argv


def _host_python(executable: str) -> bool:
    if "/" not in executable and "\\" not in executable:
        return Path(executable).name in {"python", "python3"}
    try:
        resolved = Path(executable).resolve()
    except OSError:
        return False
    if resolved == Path(sys.executable).resolve():
        return True
    for candidate in ("python3", "python"):
        found = shutil.which(candidate)
        if found and resolved == Path(found).resolve():
            return True
    return False


def architectures_match(image_arch: str, host_machine: str) -> bool:
    return _normalized_architecture(image_arch) == _normalized_architecture(host_machine)


def _normalized_architecture(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"x86_64", "amd64"}:
        return "amd64"
    if lowered in {"aarch64", "arm64", "arm64v8"}:
        return "arm64"
    return lowered


_IMAGE_ARCH: dict[str, str | None] = {}


def image_platform_mismatch(image: str) -> bool:
    arch = _image_architecture(image)
    if arch is None:
        return False
    return not architectures_match(arch, platform.machine())


def runnable_sandbox_image(image: str) -> str:
    """Use a local native sibling when the requested tag cannot run on this host."""
    if not image_platform_mismatch(image):
        return image
    host = _normalized_architecture(platform.machine())
    if host not in {"amd64", "arm64"}:
        return image
    candidate = f"{image}-{host}"
    arch = _image_architecture(candidate)
    if arch and architectures_match(arch, platform.machine()):
        return candidate
    return image


def with_runnable_image(config: SandboxConfig) -> SandboxConfig:
    image = runnable_sandbox_image(config.image)
    if image == config.image:
        return config
    return replace(config, image=image)


def _image_architecture(image: str) -> str | None:
    if image in _IMAGE_ARCH:
        return _IMAGE_ARCH[image]
    if shutil.which("docker") is None:
        _IMAGE_ARCH[image] = None
        return None
    try:
        completed = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Architecture}}", image],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        _IMAGE_ARCH[image] = None
        return None
    raw = completed.stdout.strip().lower() if completed.returncode == 0 and completed.stdout.strip() else ""
    arch = _normalized_architecture(raw) if raw in {"x86_64", "amd64", "aarch64", "arm64", "arm64v8"} else None
    _IMAGE_ARCH[image] = arch
    return arch


def interpreter_missing(returncode: int | None, stderr: str) -> bool:
    if returncode != 127:
        return False
    for line in stderr.lower().splitlines():
        if "exec:" not in line:
            continue
        if "executable file not found" not in line and "no such file or directory" not in line:
            continue
        if 'exec: "python3"' in line or 'exec: "python"' in line:
            return True
    return False


def workspace_container_name(workspace: Path) -> str:
    digest = hashlib.sha256(workspace.resolve().as_posix().encode("utf-8")).hexdigest()[:16]
    return f"onecode-{digest}"


def build_container_create(config: SandboxConfig) -> list[str]:
    command = build_docker_command(config, ["sleep", "infinity"])
    name = workspace_container_name(config.workspace)
    run_at = command.index("run")
    return ["docker", "create", "--name", name, *command[run_at + 2 :]]


def build_container_exec(config: SandboxConfig, command: Sequence[str]) -> list[str]:
    if not command:
        raise ValueError("sandbox command must not be empty")
    return ["docker", "exec", "-w", "/workspace", workspace_container_name(config.workspace), *command]


_CONTAINER_LOCKS: dict[str, threading.Lock] = {}
_CONTAINER_LOCKS_GUARD = threading.Lock()


def _container_lock(name: str) -> threading.Lock:
    with _CONTAINER_LOCKS_GUARD:
        lock = _CONTAINER_LOCKS.get(name)
        if lock is None:
            lock = threading.Lock()
            _CONTAINER_LOCKS[name] = lock
        return lock


def run_in_reused_sandbox(config: SandboxConfig, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    config = with_runnable_image(config)
    name = workspace_container_name(config.workspace)
    with _container_lock(name):
        return _run_in_reused_sandbox(config, command, name)


def _run_in_reused_sandbox(
    config: SandboxConfig,
    command: Sequence[str],
    name: str,
) -> subprocess.CompletedProcess[str]:
    inspected = subprocess.run(["docker", "inspect", name], capture_output=True, text=True, timeout=10, check=False)
    if inspected.returncode != 0:
        if "cannot connect to the docker daemon" in inspected.stderr.lower():
            return inspected
        created = subprocess.run(build_container_create(config), capture_output=True, text=True, timeout=30, check=False)
        if created.returncode != 0:
            return created
        started = subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30, check=False)
        if started.returncode != 0:
            return started
    else:
        state = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if state.returncode != 0 or state.stdout.strip() != "true":
            started = subprocess.run(["docker", "start", name], capture_output=True, text=True, timeout=30, check=False)
            if started.returncode != 0:
                return started
    try:
        return subprocess.run(
            build_container_exec(config, command),
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        killed = subprocess.run(["docker", "restart", "-t", "1", name], capture_output=True, text=True, check=False)
        if killed.returncode != 0 and "No such container" not in killed.stderr and "is not running" not in killed.stderr:
            raise RuntimeError(f"failed to restart container after timeout: {killed.stderr}") from exc
        raise


def run_in_sandbox(config: SandboxConfig, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    config = with_runnable_image(config)
    import secrets
    name = f"onecode_ephemeral_{secrets.token_hex(8)}"
    try:
        return subprocess.run(
            build_docker_command(config, command, name=name),
            text=True,
            capture_output=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        killed = subprocess.run(["docker", "kill", name], capture_output=True, text=True, check=False)
        if killed.returncode != 0 and "is not running" not in killed.stderr and "No such container" not in killed.stderr:
            raise RuntimeError(f"failed to kill container after timeout: {killed.stderr}") from exc
        raise


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
    stderr_tail = (completed.stderr or "")[-4096:]
    stdout_tail = (completed.stdout or "")[-4096:]
    if not passed and _docker_daemon_unavailable(stderr_tail):
        result = {
            "status": "blocked",
            "reason": "docker_daemon_unavailable",
            "workspace": str(config.workspace),
            "image": config.image,
            "exit_code": completed.returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "marker_path": str(marker),
        }
        write_sandbox_smoke_report(report_path, result)
        return result

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
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "marker_path": str(marker),
    }
    write_sandbox_smoke_report(report_path, result)
    return result


def _docker_daemon_unavailable(stderr: str) -> bool:
    lowered = stderr.lower()
    return (
        "cannot connect to the docker daemon" in lowered
        or "is the docker daemon running" in lowered
        or "failed to connect to the docker api" in lowered
        or "permission denied while trying to connect to the docker api" in lowered
    )


def write_sandbox_smoke_report(path: Path | None, result: dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
