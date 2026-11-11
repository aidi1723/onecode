#!/usr/bin/env python3
"""Run multi-model comparative benchmark on WorkBuddy tasks on n100."""

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

# Add onecode source to path
sys.path.insert(0, str(Path.home() / "onecode-linux-test/src"))

TASKS = (
    "bug_fix-easy-a_crash_in_local",
    "feature-medium-envless_file_load",
    "feature-medium-validation_to_eliminate_uriref",
)

MODELS = (
    "kimi-k2.7-code",
    "deepseek-v4.1-flash",
)

API_KEY = os.environ.get("ONECODE_API_KEY", "")
ENDPOINT = os.environ.get("ONECODE_API_ENDPOINT", "https://api.openai.com/v1")
TASKS_ROOT = Path.home() / "workbuddy-exam/wb-bench-code-v1.0/tasks"
RUNS_BASE = Path.home() / "workbuddy-exam/runs-multi-model"
VENV_PYTHON = str(Path.home() / "onecode-linux-test/.venv/bin/python3")


def extract_workspace(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="data")


def overlay_injected(workspace: Path, injected: Path) -> None:
    for source in injected.rglob("*"):
        if not source.is_file():
            continue
        target = workspace / source.relative_to(injected)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def pytest_targets(toml_text: str) -> list[str]:
    match = re.search(r"command = '''(.*?)'''", toml_text, re.S)
    if match is None:
        return []
    command = match.group(1)
    inner = re.search(r"bash -lc '([^']*)'", command)
    if inner:
        command = inner.group(1)
    if "runtests.py" in command:
        labels = [
            token
            for token in command.split()
            if "." in token and not token.startswith("-") and "runtests" not in token and "settings" not in token
        ]
        return ["DJANGO", *labels]
    command = re.sub(r">\s*\S+", " ", command)
    command = re.sub(r"2>&1", " ", command)
    command = re.sub(r"-m\s+\"[^\"]*\"", " ", command)
    command = re.sub(r"-m\s+'[^']*'", " ", command)
    command = re.sub(r"-o\s+\S+", " ", command)
    command = re.sub(r"--junitxml=\S+", " ", command)
    targets: list[str] = []
    for raw in command.replace("\\\n", " ").split():
        token = raw.strip("'\"")
        if not token or token in {"env", "python", "python3", "-m", "pytest", "cd", "tests", "&&"}:
            continue
        if token.startswith("-") or "=" in token and "::" not in token:
            continue
        if "/" in token or "::" in token or token.endswith(".py"):
            targets.append(token)
    return targets


def run_injected_grade(task_id: str, workspace: Path) -> dict:
    from onecode.kernel.injected_test_runner import parse_pytest_summary

    task_dir = TASKS_ROOT / task_id
    toml_path = task_dir / "tests" / "verifier.toml"
    if not toml_path.is_file():
        return {"reward": "ungraded", "detail": "missing verifier.toml"}
    toml_text = toml_path.read_text(encoding="utf-8")
    targets = pytest_targets(toml_text)
    if not targets or targets[0] == "DJANGO":
        return {"reward": "ungraded", "detail": "no pytest targets or django"}

    # Copy workspace to isolated grading directory
    grade_dir = Path(tempfile.mkdtemp(prefix=f"grade-{task_id}-"))
    try:
        shutil.copytree(workspace, grade_dir / "ws", symlinks=True, ignore_dangling_symlinks=True)
        dest = grade_dir / "ws"
        injected = task_dir / "tests" / "injected"
        if injected.is_dir():
            overlay_injected(dest, injected)
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([str(dest / "src"), str(dest), env.get("PYTHONPATH", "")])

        proc = subprocess.run(
            [VENV_PYTHON, "-m", "pytest", "-q", "--tb=line", "-p", "no:cacheprovider", "-o", "addopts=", *targets],
            cwd=dest,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        combined = (proc.stdout + "\n" + proc.stderr).strip()
        summary = parse_pytest_summary(combined)
        return {
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
            "total": summary.total,
            "pass_rate": summary.pass_rate,
            "exit_code": proc.returncode,
            "raw_summary": summary.raw_summary,
            "tail": combined[-400:],
        }
    finally:
        shutil.rmtree(grade_dir, ignore_errors=True)


def call_onecode(workspace: Path, content: str, run_id: str, model: str, max_repair_attempts: Any = "auto") -> tuple[dict, int]:
    from onecode.web.api import handle_chat_completion

    payload, status = handle_chat_completion(
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "metadata": {
                "workspace": str(workspace),
                "onecode_mode": "change_task",
                "run_id": run_id,
                "max_repair_attempts": max_repair_attempts,
            },
        }
    )
    if not isinstance(payload, dict):
        return {"message": str(payload)}, status
    return payload, status


def summarize_call(payload: dict, status: int) -> dict:
    onecode = payload.get("onecode")
    result = onecode.get("result") if isinstance(onecode, dict) else None
    if not isinstance(result, dict):
        result = {}
    error = payload.get("error")
    message = str(error.get("message") or "") if isinstance(error, dict) else ""
    detail = result.get("detail") or message
    return {
        "http_status": status,
        "status": result.get("status") or ("http_error" if status != 200 else None),
        "reason": result.get("reason"),
        "iching_status_code": result.get("iching_status_code"),
        "delivery_status": result.get("delivery_status"),
        "plan_id": result.get("plan_id"),
        "detail": str(detail)[:500],
    }


def run_task_for_model(task_id: str, model: str) -> dict:
    from onecode.kernel.model_loop import resolve_task_bureau
    from onecode.kernel.recovery_policy import recovery_status

    task_dir = TASKS_ROOT / task_id
    archive = task_dir / "environment" / "workspace.tar.gz"
    instruction = (task_dir / "instruction.md").read_text(encoding="utf-8").strip()

    run_dir = RUNS_BASE / model / task_id
    extract_workspace(archive, run_dir)

    bureau = resolve_task_bureau(run_dir)
    bureau_name = bureau.get("bureau_name", "水二局")
    turn_budget = bureau.get("turn_budget", 3)

    run_id = f"eval-{model}-{task_id}"
    payload, status = call_onecode(run_dir, instruction, f"{run_id}-init", model, max_repair_attempts=turn_budget)
    info = summarize_call(payload, status)

    approvals = 0
    while info.get("reason") == "approval_required" and approvals < 4 and info.get("plan_id"):
        approvals += 1
        payload, status = call_onecode(run_dir, f"批准计划 {info['plan_id']}", f"{run_id}-a{approvals}", model, max_repair_attempts=turn_budget)
        info = summarize_call(payload, status)

    grade_res = run_injected_grade(task_id, run_dir)
    repair_attempts = 0
    total_cooldown_ms = 0
    governance_mode = "autonomous"

    # If injected tests failed, return failures to OneCode repair loop governed by Five Elements bureau budget & Jie Shen damping
    while (grade_res.get("failed", 0) > 0 or grade_res.get("exit_code") != 0) and repair_attempts < turn_budget:
        repair_attempts += 1
        governance_mode = "degraded"
        rec = recovery_status("verifier_failure", turn_number=repair_attempts, attempted=True, attempt_count=repair_attempts - 1, status_code=47)
        damping = float(rec.get("jie_shen_relief", {}).get("damping_factor", 0.75))
        base_ms = 50 * repair_attempts
        cooldown_ms = int(base_ms / damping) if damping > 0 else base_ms
        total_cooldown_ms += cooldown_ms
        time.sleep(cooldown_ms / 1000.0)

        fail_tail = str(grade_res.get("tail", ""))[-400:]
        repair_msg = (
            f"Existing tests failed during verification. Please fix the implementation so tests pass.\n"
            f"Verifier tail:\n{fail_tail}"
        )
        payload, status = call_onecode(run_dir, repair_msg, f"{run_id}-repair-{repair_attempts}", model, max_repair_attempts=1)
        info = summarize_call(payload, status)

        rep_approvals = 0
        while info.get("reason") == "approval_required" and rep_approvals < 3 and info.get("plan_id"):
            rep_approvals += 1
            payload, status = call_onecode(run_dir, f"批准计划 {info['plan_id']}", f"{run_id}-rep-{repair_attempts}-a{rep_approvals}", model, max_repair_attempts=1)
            info = summarize_call(payload, status)

        grade_res = run_injected_grade(task_id, run_dir)
        if grade_res.get("failed", 0) == 0 and grade_res.get("exit_code") == 0:
            break

    return {
        "task_id": task_id,
        "model": model,
        "run_status": info.get("status"),
        "run_reason": info.get("reason"),
        "iching_code": info.get("iching_status_code"),
        "bureau_name": bureau_name,
        "turn_budget": turn_budget,
        "repair_attempts": repair_attempts,
        "total_cooldown_ms": total_cooldown_ms,
        "governance_mode": governance_mode,
        "approvals": approvals,
        "injected_grade": grade_res,
    }


def main():
    os.environ["OPENAI_API_KEY"] = API_KEY
    os.environ["ONECODE_MODEL_PROVIDER"] = "chat"
    os.environ["ONECODE_MODEL_ENDPOINT"] = ENDPOINT
    os.environ["ONECODE_MODEL_TIMEOUT_SECONDS"] = "240"
    os.environ["ONECODE_ALLOWED_WORKSPACE_ROOTS"] = str(RUNS_BASE.resolve())

    RUNS_BASE.mkdir(parents=True, exist_ok=True)
    all_results = {}

    for model in MODELS:
        print("\n=======================================================")
        print(f"RUNNING BENCHMARK WITH MODEL: {model}")
        print("=======================================================")
        os.environ["ONECODE_MODEL"] = model
        os.environ["ONECODE_HOME"] = str(Path.home() / f"workbuddy-exam/spot-{model}-home")

        model_results = []
        out_file = Path.home() / f"workbuddy-exam/results-{model}.jsonl"
        out_file.write_text("", encoding="utf-8")

        for task_id in TASKS:
            print(f"\n--> Running task [{task_id}] with {model}...")
            try:
                res = run_task_for_model(task_id, model)
            except Exception as e:
                res = {
                    "task_id": task_id,
                    "model": model,
                    "run_status": "exception",
                    "detail": str(e),
                    "trace": traceback.format_exc()[-400:],
                    "injected_grade": {"reward": "exception"},
                }
            model_results.append(res)
            with out_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")

            grade = res.get("injected_grade", {})
            pass_rate = grade.get("pass_rate")
            passed = grade.get("passed")
            total = grade.get("total")
            score_str = f"{passed}/{total} ({pass_rate})" if total else str(grade.get("detail", "no-score"))
            print(f"    Status: {res.get('run_status')} | Reason: {res.get('run_reason')} | Injected: {score_str}")

        all_results[model] = model_results

    # Summary table
    print("\n" + "=" * 80)
    print("MULTI-MODEL COMPARATIVE INJECTED TEST SUMMARY")
    print("=" * 80)
    header = f"{'Task ID':<45} | " + " | ".join(f"{m:<15}" for m in MODELS)
    print(header)
    print("-" * 80)
    for task_id in TASKS:
        row_str = f"{task_id:<45} | "
        scores = []
        for model in MODELS:
            r = next((x for x in all_results[model] if x["task_id"] == task_id), {})
            g = r.get("injected_grade", {})
            rate = g.get("pass_rate")
            if rate is not None:
                scores.append(f"{g.get('passed')}/{g.get('total')} ({rate:.3f})")
            else:
                scores.append("ungraded")
        row_str += " | ".join(f"{s:<15}" for s in scores)
        print(row_str)
    print("=" * 80)


if __name__ == "__main__":
    main()
