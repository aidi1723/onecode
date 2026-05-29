from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path

from .build_mode_repair import summarize_pytest_output
from .build_mode_types import SandboxEvidence
from .executor import execute_command


def run_isolated_test(
    command: list[str],
    workspace_root: str | Path,
    use_docker: bool = True,
    timeout_seconds: int = 15,
) -> SandboxEvidence:
    root = Path(workspace_root).resolve()
    _clear_python_bytecode(root)
    start = time.monotonic()
    result = execute_command(
        command,
        cwd=root,
        workspace_root=root,
        timeout_seconds=timeout_seconds,
        use_docker=use_docker,
        require_docker=False,
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    return sandbox_evidence_from_result(result, duration_ms)


def sandbox_evidence_from_result(result: dict[str, object], duration_ms: int) -> SandboxEvidence:
    exit_code = int(result.get("exit_code", 1))
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    timed_out = exit_code == 124 or "TIMEOUT" in stderr
    oom = exit_code == 137
    if exit_code == 0:
        status = "passed"
    elif timed_out:
        status = "timeout"
    elif oom:
        status = "oom"
    else:
        status = "failed"
    failure_summary = ""
    if exit_code != 0:
        failure_summary = summarize_pytest_output(f"{stdout}\n{stderr}", max_chars=900)
    return SandboxEvidence(
        exit_code=exit_code,
        pytest_status=status,
        stdout_sha256=_sha256(stdout),
        stderr_sha256=_sha256(stderr),
        duration_ms=duration_ms,
        timed_out=timed_out,
        oom=oom,
        failure_summary=failure_summary,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _clear_python_bytecode(root: Path) -> None:
    for path in root.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("*.pyc"):
        if path.is_file():
            path.unlink(missing_ok=True)
