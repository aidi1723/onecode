#!/usr/bin/env python3
"""OneCode Harbor Agent Benchmark Adapter.

Conforms to ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.
Reads HARBOR_* environment variables or CLI arguments, executes OneCode
under Harbor harness constraints, and delivers reward.txt, reward.json,
and container.cid.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from onecode.kernel.model_loop import resolve_task_bureau, run_model_task  # noqa: E402
from onecode.kernel.sandbox import SandboxConfig  # noqa: E402
from onecode.kernel.verifier import run_host_verifier  # noqa: E402
from onecode.web.api import prepare_shell_model_call  # noqa: E402


def setup_workspace(archive_path: Path, workspace_dir: Path) -> None:
    workspace_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.is_file():
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=workspace_dir, filter="data")
    gitignore = workspace_dir / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    additions = []
    for pattern in (".onecode", ".onecode_host_verifier"):
        if pattern not in existing.splitlines():
            additions.append(pattern)
    if additions:
        suffix = "\n" if existing and not existing.endswith("\n") else ""
        gitignore.write_text(existing + suffix + "\n".join(additions) + "\n", encoding="utf-8")
    git_dir = workspace_dir / ".git"
    if not git_dir.exists():
        try:
            subprocess.run(["git", "init"], cwd=workspace_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "OneCode Harness"], cwd=workspace_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "harness@onecode.local"], cwd=workspace_dir, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=workspace_dir, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "baseline workspace"], cwd=workspace_dir, check=True, capture_output=True)
        except Exception:
            pass


def parse_effective_timeout(task_package: Path, fallback_seconds: float) -> float:
    task_toml = task_package / "task.toml"
    if task_toml.is_file():
        try:
            import tomllib
            with open(task_toml, "rb") as f:
                data = tomllib.load(f)
                v_timeout = float(data.get("verifier", {}).get("timeout_sec", 0.0))
                if v_timeout > 0:
                    return max(fallback_seconds, v_timeout)
        except Exception:
            pass
    return fallback_seconds


def run_harbor_task(
    *,
    task_id: str,
    task_package: Path,
    workspace: Path,
    hidden_tests: Path,
    log_dir: Path,
    image: str = "python:3.12-slim-amd64",
    eval_mode: str = "container",
    model: str = "deepseek-chat",
    endpoint: str = "https://api.deepseek.com/chat/completions",
    api_key: str | None = None,
    max_repairs: int = 4,
    timeout_seconds: float = 300.0,
    dry_run: bool = False,
    agent_only: bool = True,
    agent_mode: str = "classic",
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    archive = task_package / "environment" / "workspace.tar.gz"
    setup_workspace(archive, workspace)

    verifier = hidden_tests / "verifier.py"
    if verifier.is_file():
        (workspace / ".onecode_host_verifier").write_text(str(verifier), encoding="utf-8")

    bureau = resolve_task_bureau(workspace)
    instruction_file = task_package / "instruction.md"
    instruction = instruction_file.read_text(encoding="utf-8") if instruction_file.is_file() else task_id

    if dry_run:
        record = {
            "task_id": task_id,
            "status": "dry_run",
            "harbor": True,
            "agent_mode": agent_mode,
            "bureau_name": bureau.get("bureau_name"),
            "workspace": str(workspace),
            "log_dir": str(log_dir),
            "eval_mode": eval_mode,
        }
        (log_dir / "reward.txt").write_text("0.0\n", encoding="utf-8")
        (log_dir / "reward.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    if api_key:
        os.environ["ONECODE_API_KEY"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    if endpoint:
        os.environ["ONECODE_ENDPOINT"] = endpoint
        os.environ["OPENAI_BASE_URL"] = endpoint
    if model:
        os.environ["ONECODE_MODEL"] = model
    os.environ.setdefault("ONECODE_SURVEY_MAX_TURNS", "0")

    started_at = time.monotonic()
    prepared = prepare_shell_model_call(instruction, workspace, run_id=f"harbor-{task_id}")
    if "stop" in prepared:
        stop = prepared["stop"]
        record = {
            "task_id": task_id,
            "model": model,
            "status": stop.get("status") or "halted",
            "reason": stop.get("reason"),
            "harbor": True,
            "duration_s": round(time.monotonic() - started_at, 2),
            "host_reward": 0.0,
        }
        if not agent_only:
            (log_dir / "reward.txt").write_text("0.0\n", encoding="utf-8")
            (log_dir / "reward.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    extras = dict(prepared["extras"])
    extras["max_repair_attempts"] = max_repairs
    extras["provider_kind"] = "chat"
    extras["endpoint"] = endpoint
    if eval_mode == "container":
        extras["sandbox_config"] = SandboxConfig(workspace=workspace, image=image)

    effective_timeout = parse_effective_timeout(task_package, timeout_seconds)
    result = run_model_task(
        prepared["task"],
        workspace=workspace,
        run_id=f"harbor-{task_id}",
        model=model,
        execution_approval=lambda _step: True,
        require_explicit_approval=True,
        http_timeout_seconds=effective_timeout,
        agent_mode=agent_mode,
        **extras,
    )

    if agent_only:
        record = {
            "task_id": task_id,
            "model": model,
            "agent_mode": result.get("agent_mode", agent_mode),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "outcome_status_code": result.get("outcome_status_code") or result.get("global_status_code"),
            "iching_status_code": result.get("iching_status_code"),
            "repair_attempt_count": result.get("repair_attempt_count", 0),
            "bureau_name": bureau.get("bureau_name"),
            "bureau_turn_budget": bureau.get("turn_budget"),
            "harbor": True,
            "stage": "agent_completed",
            "duration_s": round(time.monotonic() - started_at, 2),
            "detail": str(result.get("detail") or result.get("reason") or "")[:300],
        }
        agent_meta = workspace / ".onecode" / "harbor_agent_manifest.json"
        agent_meta.parent.mkdir(parents=True, exist_ok=True)
        agent_meta.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    host_reward = result.get("host_reward")
    if (host_reward is None or host_reward == "ungraded") and verifier.is_file():
        _checked, graded = run_host_verifier(workspace, verifier, sandbox_config=extras.get("sandbox_config"))
        host_reward = graded
        if _checked.container_id:
            result["container_id"] = _checked.container_id
            result["container_image"] = _checked.container_image
            result["container_arch"] = _checked.container_arch

    numeric_reward = float(host_reward) if isinstance(host_reward, (int, float)) else 0.0
    (log_dir / "reward.txt").write_text(f"{numeric_reward}\n", encoding="utf-8")
    record = {
        "task_id": task_id,
        "model": model,
        "agent_mode": result.get("agent_mode", agent_mode),
        "status": result.get("status"),
        "reason": result.get("reason"),
        "outcome_status_code": result.get("outcome_status_code") or result.get("global_status_code"),
        "iching_status_code": result.get("iching_status_code"),
        "repair_attempt_count": result.get("repair_attempt_count", 0),
        "bureau_name": bureau.get("bureau_name"),
        "bureau_turn_budget": bureau.get("turn_budget"),
        "host_reward": numeric_reward,
        "harbor": True,
        "duration_s": round(time.monotonic() - started_at, 2),
        "detail": str(result.get("detail") or result.get("reason") or "")[:300],
    }
    if result.get("container_id"):
        record["container_id"] = result["container_id"]
        record["container_image"] = result.get("container_image")
        record["container_arch"] = result.get("container_arch")
        (log_dir / "container.cid").write_text(str(result["container_id"]).strip() + "\n", encoding="utf-8")
    (log_dir / "reward.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="OneCode Harbor Adapter")
    parser.add_argument("--task-id", default=os.environ.get("HARBOR_TASK_ID"))
    parser.add_argument("--task-package", default=os.environ.get("HARBOR_TASK_PACKAGE"))
    parser.add_argument("--workspace", default=os.environ.get("HARBOR_WORKSPACE"))
    parser.add_argument("--hidden-tests", default=os.environ.get("HARBOR_HIDDEN_TESTS"))
    parser.add_argument("--log-dir", default=os.environ.get("HARBOR_LOG_DIR"))
    parser.add_argument("--image", default=os.environ.get("HARBOR_IMAGE", "python:3.12-slim-amd64"))
    parser.add_argument("--eval-mode", default=os.environ.get("HARBOR_EVAL_MODE", "container"))
    parser.add_argument("--model", default=os.environ.get("ONECODE_MODEL", "deepseek-chat"))
    parser.add_argument("--endpoint", default=os.environ.get("ONECODE_ENDPOINT", "https://api.deepseek.com/chat/completions"))
    parser.add_argument("--key-file", type=Path, default=Path("/tmp/onecode_key_once"))
    parser.add_argument("--max-repairs", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--agent-mode",
        choices=["classic", "terminal"],
        default=os.environ.get("HARBOR_AGENT_MODE", "classic"),
        help="Agent loop architecture: classic (plan-repair) or terminal (interactive bash/read/patch)",
    )
    parser.add_argument(
        "--standalone-self-eval",
        action="store_true",
        help="Deprecated debug mode: self-grade inside adapter instead of relying on Harbor scheduler",
    )

    args = parser.parse_args()
    if not args.task_id:
        parser.error("--task-id or HARBOR_TASK_ID is required")
    if not args.task_package:
        parser.error("--task-package or HARBOR_TASK_PACKAGE is required")
    if not args.workspace:
        parser.error("--workspace or HARBOR_WORKSPACE is required")
    if not args.log_dir:
        parser.error("--log-dir or HARBOR_LOG_DIR is required")

    task_package = Path(args.task_package).resolve()
    hidden_tests = Path(args.hidden_tests).resolve() if args.hidden_tests else task_package / "tests"
    workspace = Path(args.workspace).resolve()
    log_dir = Path(args.log_dir).resolve()

    api_key = None
    if args.key_file and args.key_file.is_file():
        api_key = args.key_file.read_text(encoding="utf-8").strip()
    elif "ONECODE_API_KEY" in os.environ:
        api_key = os.environ["ONECODE_API_KEY"]

    agent_only = not args.standalone_self_eval

    record = run_harbor_task(
        task_id=args.task_id,
        task_package=task_package,
        workspace=workspace,
        hidden_tests=hidden_tests,
        log_dir=log_dir,
        image=args.image,
        eval_mode=args.eval_mode,
        model=args.model,
        endpoint=args.endpoint,
        api_key=api_key,
        max_repairs=args.max_repairs,
        dry_run=args.dry_run,
        agent_only=agent_only,
        agent_mode=args.agent_mode,
    )
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
