#!/usr/bin/env python3
"""SWE-bench Evaluation Harness & Agent Adapter for OneCode.

Conforms to standard SWE-bench prediction formats (predictions.jsonl).
Supports multi-turn autonomous terminal execution (agent_mode="terminal")
and classic plan-repair (agent_mode="classic").

Standard library pure: zero third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

# Ensure src/ is on PYTHONPATH
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from onecode.benchmark import evaluate_model_patch, swebench_test_command
from onecode.kernel.model_loop import run_model_task

SWEBENCH_SANDBOX_IMAGE = "onecode-swebench:py312"
SWEBENCH_SYMPY_IMAGE = "onecode-swebench:sympy"


def load_api_key(key_file: Path | None) -> str | None:
    if key_file and key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            os.environ["OPENAI_API_KEY"] = key
            os.environ["ONECODE_API_KEY"] = key
            return key
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("ONECODE_API_KEY")


def load_swebench_instances(
    dataset_path: Path,
    instance_filter: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Loads instances from a SWE-bench json or jsonl dataset."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    instances: list[dict[str, Any]] = []
    text = dataset_path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        raw_list = json.loads(text)
        for item in raw_list:
            if isinstance(item, dict):
                iid = str(item.get("instance_id") or "")
                if not instance_filter or iid in instance_filter:
                    instances.append(item)
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                iid = str(item.get("instance_id") or "")
                if not instance_filter or iid in instance_filter:
                    instances.append(item)
    return instances


def setup_swebench_workspace(
    instance: dict[str, Any],
    workspace_dir: Path,
    repo_cache_dir: Path | None = None,
) -> Path:
    """Sets up a clean workspace repository for the instance at base_commit."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    repo = str(instance.get("repo") or "")
    base_commit = str(instance.get("base_commit") or "")

    # If repo is already a git directory inside workspace, check out base_commit
    git_dir = workspace_dir / ".git"
    if git_dir.is_dir():
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=workspace_dir, capture_output=True, check=False)
        subprocess.run(["git", "clean", "-fdx"], cwd=workspace_dir, capture_output=True, check=False)
        if base_commit:
            subprocess.run(["git", "checkout", base_commit], cwd=workspace_dir, capture_output=True, check=False)
        return workspace_dir

    # Check if a cached clone exists or initialize via blobless clone
    if repo_cache_dir and repo:
        repo_name = repo.split("/")[-1]
        cached_repo = repo_cache_dir / repo_name
        if not (cached_repo / ".git").is_dir():
            cached_repo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--no-checkout",
                    f"https://github.com/{repo}.git",
                    str(cached_repo),
                ],
                capture_output=True,
                check=False,
            )
        if (cached_repo / ".git").is_dir():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    f"https://github.com/{repo}.git",
                    "--reference",
                    str(cached_repo),
                    str(workspace_dir),
                ],
                capture_output=True,
                check=False,
            )
            if base_commit:
                subprocess.run(["git", "checkout", base_commit], cwd=workspace_dir, capture_output=True, check=False)
            return workspace_dir

    # Fallback to local git init if not cloned
    subprocess.run(["git", "init"], cwd=workspace_dir, capture_output=True, check=False)
    subprocess.run(["git", "config", "user.name", "OneCode"], cwd=workspace_dir, capture_output=True, check=False)
    subprocess.run(["git", "config", "user.email", "onecode@swebench"], cwd=workspace_dir, capture_output=True, check=False)
    gitignore = workspace_dir / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(".onecode/\n__pycache__/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=workspace_dir, capture_output=True, check=False)
        subprocess.run(["git", "commit", "-m", "init"], cwd=workspace_dir, capture_output=True, check=False)
    return workspace_dir


def extract_git_patch(workspace_dir: Path) -> str:
    """Extracts git diff patch representing model changes, ignoring .onecode metadata."""
    proc = subprocess.run(
        ["git", "diff", "--no-ext-diff", "HEAD", "--", "."],
        cwd=workspace_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    diff = proc.stdout or ""
    # Filter out .onecode metadata diffs if any
    filtered_lines: list[str] = []
    skipping = False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git a/.onecode") or line.startswith("diff --git a/.gitignore"):
            skipping = True
            continue
        if line.startswith("diff --git "):
            skipping = False
        if not skipping:
            filtered_lines.append(line)
    return "".join(filtered_lines)


def validate_unified_diff(patch: str) -> dict[str, Any]:
    """Validate unified diff format and extract affected files and stats."""
    if not patch or not patch.strip():
        return {
            "valid": True,
            "empty": True,
            "is_safe": True,
            "files": [],
            "additions": 0,
            "deletions": 0,
            "line_count": 0,
        }

    lines = patch.splitlines()
    files: list[str] = []
    additions = 0
    deletions = 0
    has_diff_header = False

    for line in lines:
        if line.startswith("diff --git "):
            has_diff_header = True
            parts = line.strip().split()
            if len(parts) >= 4:
                file_path = parts[3].removeprefix("b/")
                if file_path not in files:
                    files.append(file_path)
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    is_safe = not any(
        f.startswith(".git/") or f.startswith(".onecode/") or ".." in f.split("/")
        for f in files
    )

    return {
        "valid": has_diff_header and is_safe,
        "empty": False,
        "is_safe": is_safe,
        "files": files,
        "additions": additions,
        "deletions": deletions,
        "line_count": len(lines),
    }


def verify_predictions_dataset(
    predictions_path: Path,
    dataset_path: Path,
) -> dict[str, Any]:
    """Verify predictions file against a SWE-bench dataset."""
    if not dataset_path.is_file():
        return {
            "status": "error",
            "reason": f"Dataset file not found: {dataset_path}",
            "predictions_count": 0,
        }
    if not predictions_path.is_file():
        return {
            "status": "error",
            "reason": f"Predictions file not found: {predictions_path}",
            "predictions_count": 0,
        }
    instances = {inst["instance_id"]: inst for inst in load_swebench_instances(dataset_path)}

    records: list[dict[str, Any]] = []
    matched_count = 0
    valid_patch_count = 0
    empty_patch_count = 0

    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        iid = str(rec.get("instance_id") or "")
        patch_str = str(rec.get("model_patch") or "")
        audit = validate_unified_diff(patch_str)
        matched = iid in instances
        if matched:
            matched_count += 1
        if audit.get("empty"):
            empty_patch_count += 1
        elif audit.get("valid"):
            valid_patch_count += 1

        records.append({
            "instance_id": iid,
            "matched_dataset": matched,
            "patch_audit": audit,
            "status": rec.get("status"),
            "duration_s": rec.get("duration_s"),
        })

    return {
        "status": "verified",
        "dataset_total": len(instances),
        "predictions_count": len(records),
        "matched_count": matched_count,
        "valid_patch_count": valid_patch_count,
        "empty_patch_count": empty_patch_count,
        "records": records,
    }


def format_swebench_prompt(instance: dict[str, Any]) -> str:
    """Formats issue problem statement, hints, and target verification checks for the agent."""
    instance_id = instance.get("instance_id", "unknown_instance")
    repo = instance.get("repo", "unknown_repo")
    problem = instance.get("problem_statement", "").strip()
    hints = instance.get("hints_text", "").strip()
    fail_to_pass_raw = instance.get("FAIL_TO_PASS")

    target_checks: list[str] = []
    if isinstance(fail_to_pass_raw, str) and fail_to_pass_raw.strip():
        try:
            parsed = json.loads(fail_to_pass_raw)
            if isinstance(parsed, list):
                target_checks = [str(x) for x in parsed if x]
        except json.JSONDecodeError:
            target_checks = [fail_to_pass_raw.strip()]
    elif isinstance(fail_to_pass_raw, list):
        target_checks = [str(x) for x in fail_to_pass_raw if x]

    prompt_parts = [
        f"You are an expert autonomous software engineer solving SWE-bench issue '{instance_id}' for repo '{repo}'.",
        "",
        "## Issue Description:",
        problem or "No description provided.",
    ]
    if hints:
        prompt_parts.extend(["", "## Additional Hints:", hints])
    if target_checks:
        prompt_parts.extend([
            "",
            "## Expected Verification Targets:",
            "Your solution must resolve all of the following expected verification targets. "
            "Please ensure that all relevant locations, classes, and components mentioned across these checks are addressed "
            "(do not stop after fixing only the first target):",
        ] + [f"- {tc}" for tc in target_checks])
    prompt_parts.extend([
        "",
        "## How to verify",
        "Run the repository tests with this command:",
        swebench_test_command(instance),
        "A zero exit code on tests already present at the base revision only shows those checks still pass. "
        "The issue may describe behavior those checks do not cover. Reproduce that behavior with a Python command "
        "that prints a result and does not create or edit any file.",
        "When the repository command exits 0 and your reproduction shows the issue is fixed, the next action must be "
        '{"action_type":"finish","explanation":"Verification passed."}. '
        "Do not spend the last turn only reading a file.",
        "",
        "Please investigate the codebase, identify root causes, apply minimal surgical patches, "
        "verify via command execution, and finish once verified."
    ])
    return "\n".join(prompt_parts)


def run_swebench_instance(
    instance: dict[str, Any],
    work_dir: Path,
    *,
    model: str,
    endpoint: str,
    agent_mode: str = "terminal",
    repo_cache_dir: Path | None = None,
    timeout_seconds: float = 600.0,
    dry_run: bool = False,
    max_turns: int = 15,
) -> dict[str, Any]:
    """Runs a single SWE-bench instance and returns prediction record."""
    instance_id = str(instance.get("instance_id") or "unknown")
    workspace = work_dir / instance_id / "workspace"
    started_at = time.monotonic()

    setup_swebench_workspace(instance, workspace, repo_cache_dir=repo_cache_dir)
    prompt = format_swebench_prompt(instance)

    if dry_run:
        model_patch = extract_git_patch(workspace)
        record = {
            "instance_id": instance_id,
            "model_patch": model_patch,
            "model_name_or_path": model,
            "agent_mode": agent_mode,
            "status": "dry_run",
            "duration_s": round(time.monotonic() - started_at, 2),
            "workspace": str(workspace),
            "prompt_chars": len(prompt),
        }
        return record

    previous_image = os.environ.get("ONECODE_SANDBOX_IMAGE")
    sandbox_image = (previous_image or "").strip()
    repo = str(instance.get("repo") or "")
    if repo == "django/django":
        if not sandbox_image or sandbox_image == SWEBENCH_SYMPY_IMAGE:
            sandbox_image = SWEBENCH_SANDBOX_IMAGE
    elif repo == "sympy/sympy":
        if not sandbox_image or sandbox_image == SWEBENCH_SANDBOX_IMAGE:
            sandbox_image = SWEBENCH_SYMPY_IMAGE
    elif sandbox_image in {SWEBENCH_SANDBOX_IMAGE, SWEBENCH_SYMPY_IMAGE}:
        sandbox_image = ""
    if sandbox_image:
        os.environ["ONECODE_SANDBOX_IMAGE"] = sandbox_image
    else:
        os.environ.pop("ONECODE_SANDBOX_IMAGE", None)
    try:
        result = run_model_task(
            prompt,
            workspace=workspace,
            run_id=f"swe-{instance_id}",
            model=model,
            agent_mode=agent_mode,
            provider_kind="chat",
            endpoint=endpoint,
            execution_approval=lambda _s: True,
            require_explicit_approval=True,
            http_timeout_seconds=timeout_seconds,
            max_turns=max_turns,
        )
    finally:
        if previous_image is None:
            os.environ.pop("ONECODE_SANDBOX_IMAGE", None)
        else:
            os.environ["ONECODE_SANDBOX_IMAGE"] = previous_image

    duration_s = round(time.monotonic() - started_at, 2)
    model_patch = extract_git_patch(workspace)

    record = {
        "instance_id": instance_id,
        "model_patch": model_patch,
        "model_name_or_path": model,
        "agent_mode": agent_mode,
        "status": result.get("status", "completed"),
        "reason": result.get("reason"),
        "outcome_status_code": result.get("outcome_status_code"),
        "iching_status_code": result.get("iching_status_code"),
        "duration_s": duration_s,
    }
    return record


def official_test_patch(dataset_path: Path, instance: dict[str, Any]) -> dict[str, Any]:
    """Return a copy that includes the official test patch when a sidecar has one."""
    merged = dict(instance)
    current = merged.get("test_patch")
    if isinstance(current, str) and current.strip():
        return merged
    instance_id = str(merged.get("instance_id") or "")
    sidecar = dataset_path.parent / "official" / f"{instance_id}.json"
    if not sidecar.is_file():
        return merged
    try:
        extra = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return merged
    patch = extra.get("test_patch") if isinstance(extra, dict) else None
    if isinstance(patch, str) and patch.strip():
        merged["test_patch"] = patch
    return merged


def score_saved_predictions(
    predictions_path: Path,
    dataset_path: Path,
    work_dir: Path,
    *,
    python: str,
    timeout_seconds: int = 180,
    reference: Path | None = None,
    install: bool = False,
) -> list[dict[str, Any]]:
    """Score saved model diffs with the official test patch. Does not call a model."""
    instances = {str(item.get("instance_id") or ""): item for item in load_swebench_instances(dataset_path)}
    scored: list[dict[str, Any]] = []
    for index, line in enumerate(predictions_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        instance_id = str(record.get("instance_id") or "")
        source = instances.get(instance_id)
        if source is None:
            scored.append({
                "instance_id": instance_id,
                "prediction_row": index,
                "status": "blocked",
                "reason": "instance_not_in_dataset",
                "claims_mainstream_parity": False,
            })
            continue
        instance = official_test_patch(dataset_path, source)
        row_dir = work_dir / f"{index}-{instance_id}"
        repo = str(instance.get("repo") or "")
        sandbox_image = None
        if repo == "django/django":
            sandbox_image = SWEBENCH_SANDBOX_IMAGE
        elif repo == "sympy/sympy":
            sandbox_image = SWEBENCH_SYMPY_IMAGE
        outcome = evaluate_model_patch(
            instance,
            str(record.get("model_patch") or ""),
            row_dir,
            python=python,
            install=install,
            timeout_seconds=timeout_seconds,
            reference=reference,
            sandbox_image=sandbox_image,
        )
        outcome["prediction_row"] = index
        outcome["model_status"] = record.get("status")
        outcome["model_reason"] = record.get("reason")
        scored.append(outcome)
    return scored


def main() -> int:
    parser = argparse.ArgumentParser(description="OneCode SWE-bench Adapter & Evaluation Harness")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_REPO_ROOT / "benchmarks" / "swebench-lite" / "subset.jsonl",
        help="Path to SWE-bench json or jsonl dataset",
    )
    parser.add_argument("--instances", type=str, default="", help="Comma-separated instance IDs to run")
    parser.add_argument("--work-dir", type=Path, default=Path("/tmp/onecode_swebench_eval"))
    parser.add_argument("--output", type=Path, default=Path("predictions.jsonl"))
    parser.add_argument(
        "--repo-cache-dir",
        type=Path,
        default=Path.home() / ".onecode" / "swebench_repo_cache",
        help="Directory containing cached git clones",
    )
    parser.add_argument("--model", type=str, default="deepseek-v4.1-flash")
    parser.add_argument("--endpoint", type=str, default="https://happycoding.xyz/v1")
    parser.add_argument("--key-file", type=Path, default=Path("/tmp/onecode_happycoding_key"))
    parser.add_argument(
        "--agent-mode",
        choices=["classic", "terminal"],
        default="terminal",
        help="Agent mode: terminal (open-ended terminal session) or classic",
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--dry-run", action="store_true", help="Prepare workspace and print plan without model execution")
    parser.add_argument(
        "--verify-predictions",
        type=Path,
        default=None,
        help="Path to predictions.jsonl to audit and verify against dataset without running model",
    )
    parser.add_argument(
        "--score-predictions",
        type=Path,
        default=None,
        help="Score a predictions.jsonl with the official test patch. Does not call a model.",
    )
    parser.add_argument("--score-work-dir", type=Path, default=Path("/tmp/onecode_swebench_score"))
    parser.add_argument("--python", type=str, default=sys.executable)
    parser.add_argument("--score-timeout", type=int, default=180)
    parser.add_argument("--reference", type=Path, default=None, help="Local git clone used as a clone reference")
    parser.add_argument("--max-turns", type=int, default=15)
    args = parser.parse_args()

    if args.score_predictions:
        scored = score_saved_predictions(
            args.score_predictions,
            args.dataset,
            args.score_work_dir,
            python=args.python,
            timeout_seconds=args.score_timeout,
            reference=args.reference,
            install=False,
        )
        for item in scored:
            print(
                f"row {item.get('prediction_row')} {item.get('instance_id')} "
                f"status={item.get('status')} reason={item.get('reason')} "
                f"before={item.get('before_returncode')} after={item.get('after_returncode')}"
            )
        resolved = sum(1 for item in scored if item.get("status") == "resolved")
        print(f"Scored {len(scored)} prediction row(s); resolved {resolved}")
        print("claims_mainstream_parity false")
        return 0 if scored and all(item.get("status") != "blocked" for item in scored) else 1

    if args.verify_predictions:
        report = verify_predictions_dataset(args.verify_predictions, args.dataset)
        print(f"Predictions Audit Status: {report.get('status')}")
        print(f"Dataset Total: {report.get('dataset_total')}")
        print(f"Predictions Count: {report.get('predictions_count')}")
        print(f"Matched Instances: {report.get('matched_count')}")
        print(f"Valid Patches: {report.get('valid_patch_count')}")
        print(f"Empty Patches: {report.get('empty_patch_count')}")
        if report.get("status") != "verified":
            print(f"Error: {report.get('reason')}")
            return 1
        return 0

    if not args.dry_run:
        load_api_key(args.key_file)
    selected_instances = {item.strip() for item in args.instances.split(",") if item.strip()} if args.instances else None
    instances = load_swebench_instances(args.dataset, selected_instances)

    print(f"Loaded {len(instances)} SWE-bench instance(s) from {args.dataset}")
    print(f"Agent Mode: {args.agent_mode} | Model: {args.model}")
    print(f"Output: {args.output}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for inst in instances:
        iid = inst.get("instance_id")
        print(f"\n[SWE-BENCH START] Instance: {iid} | Repo: {inst.get('repo')}", flush=True)
        rec = run_swebench_instance(
            inst,
            args.work_dir,
            model=args.model,
            endpoint=args.endpoint,
            agent_mode=args.agent_mode,
            repo_cache_dir=args.repo_cache_dir,
            timeout_seconds=args.timeout,
            dry_run=args.dry_run,
            max_turns=args.max_turns,
        )
        results.append(rec)
        patch_len = len(rec.get("model_patch", ""))
        print(
            f"[SWE-BENCH DONE] Instance: {iid} | Status: {rec.get('status')} | "
            f"Patch: {patch_len} chars | Time: {rec.get('duration_s')}s",
            flush=True,
        )
        with open(args.output, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nCompleted {len(results)} instance(s). Predictions saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
