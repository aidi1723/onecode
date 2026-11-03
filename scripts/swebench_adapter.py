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

from onecode.kernel.model_loop import run_model_task


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

    # Check if a cached clone exists
    if repo_cache_dir and repo:
        repo_name = repo.split("/")[-1]
        cached_repo = repo_cache_dir / repo_name
        if (cached_repo / ".git").is_dir():
            subprocess.run(
                ["git", "clone", "--no-checkout", str(cached_repo), str(workspace_dir)],
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


def format_swebench_prompt(instance: dict[str, Any]) -> str:
    """Formats issue problem statement and hints for the agent."""
    instance_id = instance.get("instance_id", "unknown_instance")
    repo = instance.get("repo", "unknown_repo")
    problem = instance.get("problem_statement", "").strip()
    hints = instance.get("hints_text", "").strip()

    prompt_parts = [
        f"You are an expert autonomous software engineer solving SWE-bench issue '{instance_id}' for repo '{repo}'.",
        "",
        "## Issue Description:",
        problem or "No description provided.",
    ]
    if hints:
        prompt_parts.extend(["", "## Additional Hints:", hints])
    prompt_parts.extend([
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
) -> dict[str, Any]:
    """Runs a single SWE-bench instance and returns prediction record."""
    instance_id = str(instance.get("instance_id") or "unknown")
    workspace = work_dir / instance_id / "workspace"
    started_at = time.monotonic()

    if dry_run:
        workspace.mkdir(parents=True, exist_ok=True)
        record = {
            "instance_id": instance_id,
            "model_patch": "",
            "model_name_or_path": model,
            "agent_mode": agent_mode,
            "status": "dry_run",
            "duration_s": round(time.monotonic() - started_at, 2),
            "workspace": str(workspace),
        }
        return record

    setup_swebench_workspace(instance, workspace, repo_cache_dir=repo_cache_dir)
    prompt = format_swebench_prompt(instance)

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
    )

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
    parser.add_argument("--repo-cache-dir", type=Path, default=None, help="Directory containing git clones")
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
    args = parser.parse_args()

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
