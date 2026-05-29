from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .build_mode_orchestrator import RequiredArtifactPlan
from .build_mode_sovereignty import audit_workspace_sovereignty, workspace_sovereignty_to_dict


def run_guarded_runtime(
    command: Sequence[str],
    *,
    workspace: str | Path,
    artifact_plan: RequiredArtifactPlan,
    timeout_seconds: int = 30,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    root = Path(workspace).resolve()
    preflight = audit_workspace_sovereignty(root, artifact_plan)
    if not preflight.ok:
        return {
            "status": "blocked",
            "exit_code": 126,
            "reason": "pre_run_unplanned_artifacts",
            "unplanned_paths": list(preflight.unplanned_paths),
            "sovereignty": workspace_sovereignty_to_dict(preflight),
        }
    runtime_env = _guarded_env(root, artifact_plan, env)
    try:
        completed = subprocess.run(
            list(command),
            cwd=root,
            env=runtime_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = _decode_timeout_output(exc.stdout)
        stderr = (_decode_timeout_output(exc.stderr) + f"\nTIMEOUT: command exceeded {timeout_seconds} seconds").strip()
    postflight = audit_workspace_sovereignty(root, artifact_plan)
    if not postflight.ok:
        quarantined = _quarantine_unplanned(root, postflight.unplanned_paths)
        return {
            "status": "blocked",
            "exit_code": 126,
            "reason": "post_run_unplanned_artifacts",
            "command_exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "unplanned_paths": list(postflight.unplanned_paths),
            "quarantined_paths": quarantined,
            "sovereignty": workspace_sovereignty_to_dict(postflight),
        }
    return {
        "status": "completed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "sovereignty": workspace_sovereignty_to_dict(postflight),
    }


def _guarded_env(
    workspace: Path,
    artifact_plan: RequiredArtifactPlan,
    extra_env: dict[str, str] | None,
) -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    env["PATH"] = f"{root / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    env["ONEWORD_DICTIONARY_PATH"] = str(root / "agent_skill_dictionary" / "programming-agent-skill-dictionary.json")
    env["ONEWORD_ACTIVE_CODE"] = "测"
    env["ONEWORD_BUILD_MODE"] = "1"
    env["ONEWORD_BUILD_MODE_RUNTIME_PASSTHROUGH"] = "1"
    env["ONEWORD_BUILD_MODE_WORKSPACE"] = str(workspace)
    env["ONEWORD_BUILD_MODE_REQUEST_TEXT"] = artifact_plan.project_name
    env["ONEWORD_BUILD_MODE_PROJECT"] = artifact_plan.project_name
    return env


def _quarantine_unplanned(root: Path, paths: tuple[str, ...]) -> list[str]:
    quarantine_root = root / ".yizijue" / "quarantine"
    moved: list[str] = []
    for relative in paths:
        source = (root / relative).resolve()
        if not source.exists() or root not in source.parents:
            continue
        target = quarantine_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(source), str(target))
        moved.append(relative)
        _remove_empty_parents(source.parent, stop=root)
    return moved


def _remove_empty_parents(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
