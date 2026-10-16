from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Sequence
from unittest.mock import patch

_original_subprocess_run = subprocess.run
_STUB_CONTROLS: dict[int, dict[str, bool]] = {}


def _workspace_from_bind_mount(command: Sequence[str]) -> Path | None:
    for arg in command:
        if arg.startswith("type=bind,src=") and ",dst=/workspace" in arg:
            return Path(arg.split("src=")[1].split(",")[0])
    return None


def _completed(command: Sequence[str], stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=list(command), returncode=0, stdout=stdout, stderr="")


def _run_host_unittest(workspace_path: Path) -> subprocess.CompletedProcess[str]:
    return _original_subprocess_run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=workspace_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_host_python_c(workspace_path: Path, script: str) -> subprocess.CompletedProcess[str]:
    return _original_subprocess_run(
        [sys.executable, "-c", script],
        cwd=workspace_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _stub_docker_run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    workspace_path = _workspace_from_bind_mount(command)
    if "unittest" in command and workspace_path is not None:
        return _run_host_unittest(workspace_path)
    if "-c" in command and workspace_path is not None:
        script_index = command.index("-c") + 1
        if script_index < len(command):
            return _run_host_python_c(workspace_path, command[script_index])
    return _completed(command, "ok\n")


def _stub_docker(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    action = command[1] if len(command) > 1 else ""
    if action in {"version", "info", "create", "start", "kill"}:
        return _completed(command)
    if action == "inspect":
        return _completed(command, "true\n")
    if action == "run":
        return _stub_docker_run(command)
    return _completed(command)


def _sandbox_subprocess_run(
    test_case: unittest.TestCase,
    command: Sequence[str],
    *args: Any,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    if command and command[0] == "docker":
        action = command[1] if len(command) > 1 else ""
        controls = _STUB_CONTROLS.get(id(test_case), {})
        if action == "run" and controls.get("timeout_docker_run"):
            raise subprocess.TimeoutExpired(cmd=list(command), timeout=0.1)
        return _stub_docker(command)
    return _original_subprocess_run(command, *args, **kwargs)


def install_sandbox_docker_stub(test_case: unittest.TestCase) -> None:
    _STUB_CONTROLS[id(test_case)] = {"timeout_docker_run": False}

    def _run(command: Sequence[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return _sandbox_subprocess_run(test_case, command, *args, **kwargs)

    patcher = patch("onecode.kernel.sandbox.subprocess.run", side_effect=_run)
    test_case.addCleanup(lambda: _STUB_CONTROLS.pop(id(test_case), None))
    test_case.addCleanup(patcher.stop)
    patcher.start()


def force_docker_run_timeout(test_case: unittest.TestCase) -> None:
    controls = _STUB_CONTROLS.get(id(test_case))
    if controls is None:
        raise RuntimeError("install_sandbox_docker_stub must be called before force_docker_run_timeout")
    controls["timeout_docker_run"] = True
    test_case.addCleanup(lambda: controls.update(timeout_docker_run=False))
