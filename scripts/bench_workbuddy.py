#!/usr/bin/env python3
"""Standardized WorkBuddy benchmark execution harness for OneCode.

Runs benchmark tasks directly through OneCode's native host verifier protocol
and records structured telemetry without requiring external monkey patching.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path
from typing import Any

# Ensure src/ is on PYTHONPATH
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from onecode.kernel.model_loop import resolve_task_bureau, run_model_task
from onecode.web.api import prepare_shell_model_call


def extract_workspace(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="data")


def load_api_key(key_file: Path | None) -> str | None:
    if key_file and key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            os.environ["OPENAI_API_KEY"] = key
            return key
    return os.environ.get("OPENAI_API_KEY")


def run_benchmark_task(
    task_id: str,
    tasks_dir: Path,
    runs_dir: Path,
    *,
    model: str,
    endpoint: str,
    max_repairs: int = 8,
    timeout_seconds: float = 300.0,
    docker_image: str | None = None,
) -> dict[str, Any]:
    task_dir = tasks_dir / task_id
    if not task_dir.is_dir():
        raise FileNotFoundError(f"Task directory not found: {task_dir}")

    workspace = runs_dir / task_id
    archive = task_dir / "environment" / "workspace.tar.gz"
    if not archive.is_file():
        raise FileNotFoundError(f"Workspace archive not found: {archive}")

    extract_workspace(archive, workspace)

    verifier = task_dir / "tests" / "verifier.py"
    if verifier.is_file():
        (workspace / ".onecode_host_verifier").write_text(str(verifier), encoding="utf-8")
        os.environ["ONECODE_HOST_VERIFIER"] = str(verifier)
    else:
        (workspace / ".onecode_host_verifier").unlink(missing_ok=True)
        os.environ.pop("ONECODE_HOST_VERIFIER", None)

    os.environ["ONECODE_SURVEY_MAX_TURNS"] = "0"

    bureau = resolve_task_bureau(workspace)
    print(
        f"[BENCH START] {task_id} | bureau={bureau.get('bureau_name')} "
        f"budget={bureau.get('turn_budget')}",
        flush=True,
    )

    instruction_file = task_dir / "instruction.md"
    instruction = instruction_file.read_text(encoding="utf-8") if instruction_file.is_file() else task_id

    started_at = time.monotonic()
    prepared = prepare_shell_model_call(instruction, workspace, run_id=f"bench-{task_id}")
    if "stop" in prepared:
        stop = prepared["stop"]
        duration_s = round(time.monotonic() - started_at, 2)
        record = {
            "task_id": task_id,
            "model": model,
            "status": stop.get("status") or "halted",
            "reason": stop.get("reason"),
            "outcome_status_code": None,
            "iching_status_code": None,
            "repair_attempt_count": 0,
            "bureau_name": bureau.get("bureau_name"),
            "bureau_turn_budget": bureau.get("turn_budget"),
            "host_reward": "ungraded",
            "harbor": False,
            "duration_s": duration_s,
            "detail": str(stop.get("detail") or stop.get("reason") or "")[:300],
        }
        print(f"[BENCH HALT] {task_id} halted during preface survey: {record['reason']}", flush=True)
        return record

    extras = dict(prepared["extras"])
    extras["max_repair_attempts"] = max_repairs
    extras["provider_kind"] = "chat"
    extras["endpoint"] = endpoint

    if docker_image:
        from onecode.kernel.sandbox import SandboxConfig
        extras["sandbox_config"] = SandboxConfig(workspace=workspace, image=docker_image)

    effective_timeout = timeout_seconds
    task_toml = task_dir / "task.toml"
    if task_toml.is_file():
        try:
            import tomllib
            with open(task_toml, "rb") as f:
                toml_data = tomllib.load(f)
                v_timeout = float(toml_data.get("verifier", {}).get("timeout_sec", 0.0))
                if v_timeout > 0:
                    effective_timeout = max(effective_timeout, v_timeout)
        except Exception:
            pass

    result = run_model_task(
        prepared["task"],
        workspace=workspace,
        run_id=f"bench-{task_id}",
        model=model,
        execution_approval=lambda _step: True,
        require_explicit_approval=True,
        http_timeout_seconds=effective_timeout,
        **extras,
    )

    duration_s = round(time.monotonic() - started_at, 2)
    host_reward = result.get("host_reward")
    if (host_reward is None or host_reward == "ungraded") and verifier.is_file():
        from onecode.kernel.verifier import run_host_verifier
        _checked, graded_reward = run_host_verifier(
            workspace,
            verifier,
            sandbox_config=extras.get("sandbox_config"),
        )
        host_reward = graded_reward
        if _checked.container_id:
            result["container_id"] = _checked.container_id
            result["container_image"] = _checked.container_image
            result["container_arch"] = _checked.container_arch
    if host_reward is None:
        host_reward = "ungraded"
    outcome_code = result.get("outcome_status_code") or result.get("global_status_code")
    iching_code = result.get("iching_status_code")

    record = {
        "task_id": task_id,
        "model": model,
        "status": result.get("status"),
        "reason": result.get("reason"),
        "outcome_status_code": outcome_code,
        "iching_status_code": iching_code,
        "repair_attempt_count": result.get("repair_attempt_count", 0),
        "bureau_name": bureau.get("bureau_name"),
        "bureau_turn_budget": bureau.get("turn_budget"),
        "host_reward": host_reward,
        "harbor": False,
        "duration_s": duration_s,
        "detail": str(result.get("detail") or result.get("reason") or "")[:300],
    }
    if result.get("container_id"):
        record["container_id"] = result["container_id"]
        record["container_image"] = result.get("container_image")
        record["container_arch"] = result.get("container_arch")

    print(
        f"[BENCH DONE] {task_id} | status={record['status']} | reward={host_reward} | "
        f"repairs={record['repair_attempt_count']} | hex={outcome_code}/{iching_code} | "
        f"time={duration_s}s",
        flush=True,
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="OneCode WorkBuddy Benchmark Runner")
    parser.add_argument("--tasks-dir", type=Path, default=Path.home() / "workbuddy-exam/wb-bench-code-v1.0/tasks")
    parser.add_argument("--runs-dir", type=Path, default=Path.home() / "workbuddy-exam/runs-bench")
    parser.add_argument("--output", type=Path, default=Path.home() / "workbuddy-exam/results-bench.jsonl")
    parser.add_argument("--tasks", type=str, default="", help="Comma-separated task IDs")
    parser.add_argument("--category", type=str, default="", help="Filter tasks by category prefix")
    parser.add_argument("--model", type=str, default="agnes-3.0-flash")
    parser.add_argument("--endpoint", type=str, default="https://plan.pmcat.top/v1/chat/completions")
    parser.add_argument("--key-file", type=Path, default=Path("/tmp/onecode_key_once"))
    parser.add_argument("--max-repairs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--docker", type=str, default=None, help="Docker sandbox image (e.g. python:3.12-slim-amd64)")
    parser.add_argument("--concurrency", "-j", type=int, default=1, help="Max concurrent tasks (capped by CPU cores)")
    args = parser.parse_args()

    load_api_key(args.key_file)

    if not args.tasks_dir.is_dir():
        print(f"Error: Tasks directory does not exist: {args.tasks_dir}", file=sys.stderr)
        return 1

    if args.tasks:
        selected_tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    elif args.category:
        selected_tasks = [
            p.name for p in sorted(args.tasks_dir.iterdir())
            if p.is_dir() and p.name.startswith(args.category)
        ]
    else:
        # Default to the 4 Hard expansion tasks
        selected_tasks = [
            "api_contract-hard-openapi_params",
            "security_hardening-hard-archive_path_traversal",
            "feature_pipeline-hard-cross_categorical",
            "refactor-hard-sync_async_bridge",
        ]

    args.runs_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    cpu_limit = os.cpu_count() or 1
    concurrency = max(1, min(args.concurrency, cpu_limit, 8))
    if args.concurrency > concurrency:
        print(f"Notice: Concurrency {args.concurrency} capped to {concurrency} (CPU cores / safety limit)")

    print(f"Starting WorkBuddy Benchmark | Tasks: {len(selected_tasks)} | Model: {args.model} | Concurrency: {concurrency}")
    print(f"Output JSONL: {args.output}")

    import concurrent.futures
    import threading

    results: list[dict[str, Any]] = []
    output_lock = threading.Lock()

    def _execute(task_id: str) -> dict[str, Any] | None:
        try:
            res = run_benchmark_task(
                task_id,
                args.tasks_dir,
                args.runs_dir,
                model=args.model,
                endpoint=args.endpoint,
                max_repairs=args.max_repairs,
                timeout_seconds=args.timeout,
                docker_image=args.docker,
            )
            with output_lock:
                results.append(res)
                with open(args.output, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
            return res
        except Exception as exc:
            print(f"[BENCH ERROR] {task_id}: {exc}", file=sys.stderr, flush=True)
            return None

    if concurrency == 1:
        for tid in selected_tasks:
            _execute(tid)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_execute, tid) for tid in selected_tasks]
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception as exc:
                    print(f"[POOL ERROR] Worker raised: {exc}", file=sys.stderr, flush=True)

    passed_count = sum(1 for r in results if r.get("host_reward") == 1.0)
    total_count = len(results)
    avg_score = (
        sum(r["host_reward"] for r in results if isinstance(r.get("host_reward"), (int, float))) / total_count
        if total_count > 0 else 0.0
    )
    print("\n" + "=" * 60)
    print(f"Benchmark Complete | Passed: {passed_count}/{total_count} | Avg Reward: {avg_score:.4f}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
