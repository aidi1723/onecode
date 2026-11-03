#!/usr/bin/env python3
"""OneCode Harbor Benchmark Scheduler & Evaluation Harness.

Conforms to ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02.
Orchestrates Harbor evaluation by:
1. Setting up the directory topology (task_package, workspace, hidden_tests, log_dir);
2. Injecting HARBOR_* environment variables and invoking the Agent Adapter (scripts/harbor_adapter.py --agent-only);
3. Verifying that log_dir contains no pre-existing reward/container artifacts before grading;
4. Executing containerized verifier.py via official `docker run --cidfile`;
5. Reading the host staging directory mounted at /log_dir, then writing reward.txt and reward.json into the official log directory after the exit code and assertion counts agree;
6. Outputting the reconciliation report and audit JSON.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

CID_PATTERN = re.compile(r"^[0-9a-f]{64}$")

from onecode.kernel.verifier import (  # noqa: E402
    assertion_counts,
    audit_workspace_for_sys_path_hijacking,
    full_score_problem,
)


def snapshot_test_hashes(hidden_tests: Path, workspace_tests: Path | None = None) -> dict[str, str]:
    """Takes a SHA-256 snapshot of all test files and verifier scripts."""
    hashes: dict[str, str] = {}
    if hidden_tests.is_dir():
        for p in hidden_tests.rglob("*"):
            if p.is_file():
                try:
                    rel = f"hidden_tests/{p.relative_to(hidden_tests).as_posix()}"
                    hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
                except OSError:
                    pass
    if workspace_tests and workspace_tests.is_dir():
        for p in workspace_tests.rglob("*"):
            if p.is_file():
                try:
                    rel = f"workspace_tests/{p.relative_to(workspace_tests).as_posix()}"
                    hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
                except OSError:
                    pass
    return hashes


def verify_test_hashes(baseline: dict[str, str], hidden_tests: Path, workspace_tests: Path | None = None) -> tuple[bool, str]:
    """Verifies that no test files have been modified or deleted."""
    current = snapshot_test_hashes(hidden_tests, workspace_tests)
    for rel, orig_hash in baseline.items():
        if rel not in current:
            return False, f"Test asset '{rel}' was deleted"
        if current[rel] != orig_hash:
            return False, f"Test asset '{rel}' was tampered with (SHA-256 mismatch)"
    for rel in current:
        if rel not in baseline:
            return False, f"Unexpected test asset '{rel}' was created"
    return True, ""


def build_stage2_docker_command(
    *,
    workspace: Path,
    verifier_script: Path,
    staging_dir: Path,
    image: str,
    cidfile: Path | None,
    workspace_tests: Path | None,
) -> list[str]:
    """Mount a host staging directory at /log_dir. The official log directory stays outside the container."""
    command = [
        "docker", "run", "--rm",
        *(["--cidfile", str(cidfile)] if cidfile else []),
        "--network", "none",
        "--memory", "512m",
        "--cpus", "1",
        "--pids-limit", "256",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--security-opt", "no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--mount", f"type=bind,src={workspace},dst=/workspace",
        "--mount", f"type=bind,src={staging_dir},dst=/log_dir",
        "--mount", f"type=bind,src={verifier_script},dst=/verifier/verifier.py,readonly",
        "--mount", f"type=bind,src={workspace / '.onecode'},dst=/workspace/.onecode,readonly",
    ]
    if workspace_tests is not None:
        command.extend(["--mount", f"type=bind,src={workspace_tests},dst=/workspace/tests,readonly"])
    for name in (".git", ".github"):
        source = workspace / name
        if source.exists():
            command.extend(["--mount", f"type=bind,src={source},dst=/workspace/{name},readonly"])
    command.extend([
        "--env", "WORKSPACE=/workspace",
        "--env", "LOG_DIR=/log_dir",
        "--env", "PYTHONSAFEPATH=1",
        "--workdir", "/workspace",
        image,
        "python3", "/verifier/verifier.py",
    ])
    return command


def publish_official_reward(log_dir: Path, reward: float, detail: dict[str, Any]) -> None:
    """The host process is the only writer of the official reward files."""
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (log_dir / "reward.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")


def _zero_reward(reason: str, detail_text: str) -> dict[str, Any]:
    detail = {
        "overall": 0.0,
        "test_pass_rate": 0.0,
        "tests_passed": 0,
        "tests_total": 1,
        "test_status": "fail",
        "security_violation": reason,
        "detail": detail_text,
    }
    return {
        "status": "failed",
        "reason": reason,
        "security_violation": reason,
        "detail": detail_text,
        "host_reward": 0.0,
        "passed": False,
        "verifier_exit_code": 1,
        "verifier_duration_s": 0.0,
        "tests_passed": 0,
        "tests_total": 1,
        "reward_detail": detail,
    }


def _read_staged_reward(staging: Path) -> tuple[float | None, dict[str, Any]]:
    reward_txt = staging / "reward.txt"
    if not reward_txt.is_file():
        return None, {}
    try:
        reward = float(reward_txt.read_text(encoding="utf-8").strip())
    except ValueError:
        reward = 0.0
    detail: dict[str, Any] = {}
    reward_json = staging / "reward.json"
    if reward_json.is_file():
        try:
            parsed = json.loads(reward_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            detail = parsed
    return reward, detail


def assess_staged_reward(staging: Path, returncode: int) -> dict[str, Any]:
    """Accept a full score only when the exit code and assertion counts agree."""
    reward, detail = _read_staged_reward(staging)
    if reward is None:
        outcome = _zero_reward("missing_reward_txt", "verifier did not write reward.txt")
        outcome["security_violation"] = ""
        outcome["reward_detail"].pop("security_violation", None)
        outcome["verifier_exit_code"] = returncode
        return outcome

    forgery = full_score_problem(returncode, reward, detail)
    counts = assertion_counts(detail)
    if forgery:
        outcome = _zero_reward("reward_forgery_detected", forgery)
        outcome["verifier_exit_code"] = returncode
        return outcome

    tests_passed, tests_total = counts if counts is not None else (0, 0)
    passed = returncode == 0 and is_full_pass(reward)
    return {
        "status": "completed" if passed else "failed",
        "reason": "full_pass" if passed else "tests_failed",
        "security_violation": "",
        "detail": "",
        "host_reward": reward,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "passed": passed,
        "verifier_exit_code": returncode,
        "verifier_duration_s": 0.0,
        "reward_detail": detail,
    }


def _run_verifier_process(
    *,
    workspace: Path,
    verifier_script: Path,
    workspace_tests: Path | None,
    image: str,
    timeout_seconds: float,
    cidfile: Path | None,
    use_docker: bool,
    staging: Path,
) -> int:
    if not use_docker:
        env = {**os.environ, "WORKSPACE": str(workspace), "LOG_DIR": str(staging), "PYTHONSAFEPATH": "1"}
        try:
            completed = subprocess.run(
                [sys.executable, str(verifier_script)],
                cwd=str(workspace),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 124
        return completed.returncode

    if cidfile and cidfile.exists():
        cidfile.unlink()
    command = build_stage2_docker_command(
        workspace=workspace,
        verifier_script=verifier_script,
        staging_dir=staging,
        image=image,
        cidfile=cidfile,
        workspace_tests=workspace_tests,
    )
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        return 124
    return completed.returncode


def run_stage2_evaluation(
    *,
    task_id: str,
    workspace: Path,
    hidden_tests: Path,
    log_dir: Path,
    image: str = "python:3.12-slim-amd64",
    timeout_seconds: float = 300.0,
    cidfile: Path | None = None,
    use_docker: bool = True,
) -> dict[str, Any]:
    """Executes containerized or sandboxed Stage 2 grading with strict anti-tamper and sys.path isolation."""
    verifier_script = hidden_tests / "verifier.py"
    if not verifier_script.is_file():
        raise FileNotFoundError(f"Verifier script missing: {verifier_script}")

    log_dir.mkdir(parents=True, exist_ok=True)
    sys_path_violations = audit_workspace_for_sys_path_hijacking(workspace)
    if sys_path_violations:
        outcome = _zero_reward("sys_path_hijack_detected", "; ".join(sys_path_violations))
        publish_official_reward(log_dir, 0.0, outcome["reward_detail"])
        return outcome

    ws_tests = workspace / "tests" if (workspace / "tests").is_dir() else None
    baseline_hashes = snapshot_test_hashes(hidden_tests, ws_tests)
    (workspace / ".onecode").mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="onecode-grade-", dir=log_dir.parent))
    t0_verifier = time.monotonic()
    try:
        returncode = _run_verifier_process(
            workspace=workspace,
            verifier_script=verifier_script,
            workspace_tests=ws_tests,
            image=image,
            timeout_seconds=timeout_seconds,
            cidfile=cidfile,
            use_docker=use_docker,
            staging=staging,
        )
        verifier_duration = round(time.monotonic() - t0_verifier, 2)
        intact, tamper_msg = verify_test_hashes(baseline_hashes, hidden_tests, ws_tests)
        if not intact:
            outcome = _zero_reward("test_tampering_detected", tamper_msg)
        else:
            outcome = assess_staged_reward(staging, returncode)
        outcome["verifier_exit_code"] = returncode
        outcome["verifier_duration_s"] = verifier_duration
        publish_official_reward(log_dir, float(outcome["host_reward"]), outcome["reward_detail"])
        return outcome
    finally:
        shutil.rmtree(staging, ignore_errors=True)


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
    print("[HARBOR SCHEDULER] Stage 2: Executing isolated verifier container...", flush=True)
    stage2 = run_stage2_evaluation(
        task_id=task_id,
        workspace=workspace,
        hidden_tests=hidden_tests,
        log_dir=log_dir,
        image=image,
        timeout_seconds=timeout_seconds,
        cidfile=cidfile,
        use_docker=True,
    )

    verifier_duration = stage2.get("verifier_duration_s", 0.0)
    verifier_exit_code = stage2.get("verifier_exit_code", 1)
    passed = stage2.get("passed", False)
    reward = stage2.get("host_reward", 0.0)
    tests_passed = stage2.get("tests_passed", 0)
    tests_total = stage2.get("tests_total", 0)

    # Stage 3: Reconcile and inspect artifacts
    cid = ""
    if cidfile.is_file():
        cid_candidate = cidfile.read_text(encoding="utf-8").strip()
        if CID_PATTERN.match(cid_candidate):
            cid = cid_candidate

    print(f"[HARBOR SCHEDULER VERIFIED] {task_id}:", flush=True)
    print(f"  Container CID:       {cid}", flush=True)
    print(f"  Reward (reward.txt): {reward} ({tests_passed}/{tests_total})", flush=True)
    print(f"  Verifier Exit Code:  {verifier_exit_code}", flush=True)
    print(f"  Adapter Time:        {adapter_duration}s", flush=True)
    print(f"  Verifier Time:       {verifier_duration}s", flush=True)
    print(f"  Full Pass:           {passed}", flush=True)
    if stage2.get("security_violation"):
        print(f"  Security Violation:  {stage2.get('security_violation')}: {stage2.get('detail')}", flush=True)

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
        "verifier_exit_code": verifier_exit_code,
        "security_violation": stage2.get("security_violation"),
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
