#!/usr/bin/env python3
"""OneCode Harbor Benchmark Scheduler & Evaluation Harness.

Conforms to ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.
Orchestrates Harbor evaluation by:
1. Setting up the directory topology (task_package, workspace, hidden_tests, log_dir);
2. Injecting HARBOR_* environment variables and invoking the Agent Adapter (scripts/harbor_adapter.py --agent-only);
3. Verifying that log_dir contains no pre-existing reward/container artifacts before grading;
4. Executing containerized verifier.py via official `docker run --cidfile`;
5. Verifying that container.cid, reward.txt, and reward.json are genuinely produced by Docker and the container verifier;
6. Outputting the reconciliation report and audit JSON.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

CID_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def run_scheduler_task(
    *,
    task_id: str,
    tasks_dir: Path,
    eval_dir: Path,
    model: str,
    endpoint: str,
    api_key: str | None,
    image: str = "python:3.12-slim-amd64",
    timeout_seconds: float = 300.0,
    max_repairs: int = 4,
    agent_mode: str = "classic",
) -> dict[str, Any]:
    task_package = (tasks_dir / task_id).resolve()
    if not task_package.is_dir():
        raise FileNotFoundError(f"Task package directory not found: {task_package}")

    task_eval_dir = (eval_dir / task_id).resolve()
    workspace = task_eval_dir / "workspace"
    log_dir = task_eval_dir / "log_dir"
    hidden_tests = (task_package / "tests").resolve()

    task_eval_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Ensure pre-grading cleanliness in log_dir
    cidfile = log_dir / "container.cid"
    reward_txt_file = log_dir / "reward.txt"
    reward_json_file = log_dir / "reward.json"
    for f in (cidfile, reward_txt_file, reward_json_file):
        if f.exists():
            f.unlink()

    print("\n============================================================", flush=True)
    print(f"[HARBOR SCHEDULER] Task: {task_id}", flush=True)
    print(f"  Package:   {task_package}", flush=True)
    print(f"  Workspace: {workspace}", flush=True)
    print(f"  Log Dir:   {log_dir}", flush=True)
    print(f"  Image:     {image}", flush=True)
    print("============================================================", flush=True)

    # Stage 1: Invoke Agent Adapter
    print("[HARBOR SCHEDULER] Stage 1: Invoking Agent Adapter (--agent-only)...", flush=True)
    env = os.environ.copy()
    env["HARBOR_TASK_ID"] = task_id
    env["HARBOR_TASK_PACKAGE"] = str(task_package)
    env["HARBOR_WORKSPACE"] = str(workspace)
    env["HARBOR_HIDDEN_TESTS"] = str(hidden_tests)
    env["HARBOR_LOG_DIR"] = str(log_dir)
    env["HARBOR_IMAGE"] = image
    env["HARBOR_EVAL_MODE"] = "container"
    env["HARBOR_AGENT_ONLY"] = "1"
    env["HARBOR_AGENT_MODE"] = agent_mode
    env["ONECODE_STREAM_CHAT"] = "1"
    env["ONECODE_MODEL"] = model
    env["ONECODE_ENDPOINT"] = endpoint
    if api_key:
        env["ONECODE_API_KEY"] = api_key
        env["OPENAI_API_KEY"] = api_key

    adapter_script = ROOT / "scripts" / "harbor_adapter.py"
    adapter_cmd = [
        sys.executable,
        str(adapter_script),
        "--task-id", task_id,
        "--task-package", str(task_package),
        "--workspace", str(workspace),
        "--hidden-tests", str(hidden_tests),
        "--log-dir", str(log_dir),
        "--image", image,
        "--model", model,
        "--endpoint", endpoint,
        "--max-repairs", str(max_repairs),
        "--agent-mode", agent_mode,
    ]

    t0_agent = time.monotonic()
    adapter_proc = subprocess.run(adapter_cmd, env=env, capture_output=True, text=True)
    adapter_duration = round(time.monotonic() - t0_agent, 2)

    if adapter_proc.returncode != 0:
        print(f"[HARBOR SCHEDULER ERROR] Agent adapter failed (exit code {adapter_proc.returncode})", flush=True)
        print(f"  STDERR: {adapter_proc.stderr[:400]}", flush=True)
        return {
            "task_id": task_id,
            "harbor": True,
            "status": "adapter_failed",
            "host_reward": 0.0,
            "adapter_exit_code": adapter_proc.returncode,
            "adapter_duration_s": adapter_duration,
        }

    print(f"[HARBOR SCHEDULER] Stage 1 complete in {adapter_duration}s.", flush=True)

    # Verification of independent origin: Adapter MUST NOT have created evaluation artifacts
    if cidfile.exists() or reward_txt_file.exists() or reward_json_file.exists():
        raise RuntimeError(
            "Protocol violation: evaluation artifacts (container.cid/reward.txt/reward.json) "
            "were written during Stage 1 by the adapter!"
        )

    # Stage 2: Harbor Container Grading
    print("[HARBOR SCHEDULER] Stage 2: Executing Docker verifier container...", flush=True)
    verifier_script = hidden_tests / "verifier.py"
    if not verifier_script.is_file():
        raise FileNotFoundError(f"Verifier script missing: {verifier_script}")

    # Ensure .onecode exists in workspace so Docker bind mount succeeds
    (workspace / ".onecode").mkdir(parents=True, exist_ok=True)

    docker_cmd = [
        "docker", "run", "--rm",
        "--cidfile", str(cidfile),
        "--network", "none",
        "--memory", "512m",
        "--cpus", "1",
        "--pids-limit", "256",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--security-opt", "no-new-privileges",
        "--mount", f"type=bind,src={workspace},dst=/workspace",
        "--mount", f"type=bind,src={log_dir},dst=/log_dir",
        "--mount", f"type=bind,src={verifier_script},dst=/verifier/verifier.py,readonly",
        "--mount", f"type=bind,src={workspace / '.onecode'},dst=/workspace/.onecode,readonly",
        "--env", "WORKSPACE=/workspace",
        "--env", "LOG_DIR=/log_dir",
        "--env", "PYTHONSAFEPATH=1",
        "--workdir", "/workspace",
        image,
        "python3", "/verifier/verifier.py",
    ]

    t0_verifier = time.monotonic()
    verifier_proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout_seconds)
    verifier_duration = round(time.monotonic() - t0_verifier, 2)

    # Stage 3: Reconcile and inspect artifacts
    if not cidfile.is_file():
        raise FileNotFoundError(f"Docker failed to write --cidfile at {cidfile}")
    cid = cidfile.read_text(encoding="utf-8").strip()
    if not CID_PATTERN.match(cid):
        raise ValueError(f"Invalid container CID written by docker: {cid!r}")

    if not reward_txt_file.is_file():
        raise FileNotFoundError(f"Container verifier failed to write reward.txt at {reward_txt_file}")
    reward_raw = reward_txt_file.read_text(encoding="utf-8").strip()
    try:
        reward = float(reward_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid reward.txt content: {reward_raw!r}") from exc

    if not reward_json_file.is_file():
        raise FileNotFoundError(f"Container verifier failed to write reward.json at {reward_json_file}")
    try:
        reward_detail = json.loads(reward_json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"reward.json is not valid JSON at {reward_json_file}") from exc

    tests_passed = reward_detail.get("tests_passed", 0)
    tests_total = reward_detail.get("tests_total", 0)
    passed = is_full_pass(reward)

    print(f"[HARBOR SCHEDULER VERIFIED] {task_id}:", flush=True)
    print(f"  Container CID:       {cid}", flush=True)
    print(f"  Reward (reward.txt): {reward} ({tests_passed}/{tests_total})", flush=True)
    print(f"  Verifier Exit Code:  {verifier_proc.returncode}", flush=True)
    print(f"  Adapter Time:        {adapter_duration}s", flush=True)
    print(f"  Verifier Time:       {verifier_duration}s", flush=True)
    print(f"  Full Pass:           {passed}", flush=True)

    report: dict[str, Any] = {
        "harbor": True,
        "task_id": task_id,
        "agent_mode": agent_mode,
        "model": model,
        "scheduler": "onecode_harbor_scheduler_v1",
        "eval_mode": "container",
        "container_image": image,
        "container_id": cid,
        "container_arch": "amd64",
        "host_reward": reward,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "passed": passed,
        "adapter_duration_s": adapter_duration,
        "verifier_duration_s": verifier_duration,
        "total_duration_s": round(adapter_duration + verifier_duration, 2),
        "adapter_exit_code": adapter_proc.returncode,
        "verifier_exit_code": verifier_proc.returncode,
        "artifacts": {
            "container_cid": str(cidfile),
            "reward_txt": str(reward_txt_file),
            "reward_json": str(reward_json_file),
        },
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    scheduler_report_file = task_eval_dir / "harbor_scheduler_report.json"
    scheduler_report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def is_full_pass(reward: float) -> bool:
    return abs(reward - 1.0) < 1e-6


def main() -> int:
    parser = argparse.ArgumentParser(description="OneCode Harbor Scheduler & Evaluation Harness")
    parser.add_argument(
        "--tasks",
        type=str,
        default="data_reporting-hard-support_sla,feature_pipeline-hard-cross_categorical",
        help="Comma-separated task IDs",
    )
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=Path.home() / "workbuddy-exam/wb-bench-code-v1.0/tasks",
        help="Directory containing task packages",
    )
    parser.add_argument(
        "--eval-dir",
        type=Path,
        default=Path.home() / "workbuddy-exam/harbor-scheduler-eval",
        help="Root directory for scheduler evaluations",
    )
    parser.add_argument("--model", type=str, default="deepseek-v4.1-flash")
    parser.add_argument("--endpoint", type=str, default="https://happycoding.xyz/v1")
    parser.add_argument("--key-file", type=Path, default=Path("/tmp/onecode_happycoding_key"))
    parser.add_argument("--image", type=str, default="python:3.12-slim-amd64")
    parser.add_argument(
        "--agent-mode",
        choices=["classic", "terminal"],
        default=os.environ.get("HARBOR_AGENT_MODE", "classic"),
        help="Agent loop architecture: classic (plan-repair) or terminal (interactive bash/read/patch)",
    )
    parser.add_argument("--max-repairs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=300.0)

    args = parser.parse_args()
    task_ids = [t.strip() for t in args.tasks.split(",") if t.strip()]
    if not task_ids:
        parser.error("No task IDs provided")

    api_key = None
    if args.key_file and args.key_file.is_file():
        api_key = args.key_file.read_text(encoding="utf-8").strip()
    elif "ONECODE_API_KEY" in os.environ:
        api_key = os.environ["ONECODE_API_KEY"]

    args.eval_dir.mkdir(parents=True, exist_ok=True)
    summary_jsonl = args.eval_dir / "results-harbor-scheduler.jsonl"

    all_reports: list[dict[str, Any]] = []
    print(f"Starting Harbor Scheduler Evaluation | Tasks: {len(task_ids)} | Model: {args.model}", flush=True)
    print(f"Scheduler Output Directory: {args.eval_dir}", flush=True)

    for task_id in task_ids:
        report = run_scheduler_task(
            task_id=task_id,
            tasks_dir=args.tasks_dir,
            eval_dir=args.eval_dir,
            model=args.model,
            endpoint=args.endpoint,
            api_key=api_key,
            image=args.image,
            timeout_seconds=args.timeout,
            max_repairs=args.max_repairs,
            agent_mode=args.agent_mode,
        )
        all_reports.append(report)
        with open(summary_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False) + "\n")

    passed_count = sum(1 for r in all_reports if r.get("passed"))
    avg_reward = sum(float(r.get("host_reward", 0.0)) for r in all_reports) / len(all_reports)

    print("\n============================================================", flush=True)
    print("Harbor Scheduler Evaluation Complete", flush=True)
    print(f"  Tasks Evaluated: {len(all_reports)}")
    print(f"  Passed:          {passed_count}/{len(all_reports)}")
    print(f"  Average Reward:  {avg_reward:.4f}")
    print(f"  Summary JSONL:   {summary_jsonl}")
    print("============================================================\n", flush=True)

    return 0 if passed_count == len(all_reports) else 1


if __name__ == "__main__":
    sys.exit(main())
