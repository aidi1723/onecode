#!/usr/bin/env python3
"""Score WorkBuddy tasks that were outside the tuned 36-task hard set.

The in-sample cohort is every task id containing ``-hard-`` that ships
``tests/verifier.py``. That is the cohort behind the published mean 0.8474.
Held-out tasks are the other packages that ship the same verifier protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from onecode.kernel.model_loop import data_contract_guidance  # noqa: E402

INSAMPLE_REFERENCE_MEAN = 0.8474


def classify_task(task_dir: Path) -> str:
    if not (task_dir / "tests" / "verifier.py").is_file():
        return "excluded"
    if "-hard-" in task_dir.name:
        return "in_sample"
    return "held_out"


def split_tasks(tasks_dir: Path) -> dict[str, list[str]]:
    groups = {"in_sample": [], "held_out": [], "excluded": []}
    for task_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
        groups[classify_task(task_dir)].append(task_dir.name)
    return groups


def prompt_sha256() -> str:
    """Hash the tuned guidance function. Task instructions are not part of the prompt bundle."""
    source = inspect.getsource(data_contract_guidance).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def numeric_reward(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * fraction)))
    return sorted_values[index]


def summarize_rewards(records: list[dict[str, Any]], *, reference_mean: float = INSAMPLE_REFERENCE_MEAN) -> dict[str, Any]:
    scored: list[float] = []
    ungraded: list[str] = []
    for record in records:
        reward = numeric_reward(record.get("host_reward"))
        if reward is None:
            ungraded.append(str(record.get("task_id") or ""))
            scored.append(0.0)
            continue
        scored.append(reward)
    ordered = sorted(scored)
    mean = statistics.fmean(scored) if scored else 0.0
    return {
        "task_count": len(records),
        "ungraded_count": len(ungraded),
        "ungraded_task_ids": ungraded,
        "mean": round(mean, 4),
        "min": round(ordered[0], 4) if ordered else None,
        "max": round(ordered[-1], 4) if ordered else None,
        "p25": round(_percentile(ordered, 0.25), 4) if ordered else None,
        "p75": round(_percentile(ordered, 0.75), 4) if ordered else None,
        "in_sample_reference_mean": reference_mean,
        "delta_vs_in_sample": round(mean - reference_mean, 4) if scored else None,
    }


def git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def run_held_out(
    *,
    tasks_dir: Path,
    runs_dir: Path,
    task_ids: list[str],
    model: str,
    endpoint: str,
    max_repairs: int,
    timeout_seconds: float,
    split: str = "held_out",
    output: Path | None = None,
) -> list[dict[str, Any]]:
    import bench_workbuddy

    os.environ.setdefault("ONECODE_STREAM_CHAT", "1")
    prompt_hash = prompt_sha256()
    revision = git_revision()
    records: list[dict[str, Any]] = []
    for task_id in task_ids:
        instruction = tasks_dir / task_id / "instruction.md"
        task_text = instruction.read_text(encoding="utf-8") if instruction.is_file() else task_id
        record = bench_workbuddy.run_benchmark_task(
            task_id,
            tasks_dir,
            runs_dir,
            model=model,
            endpoint=endpoint,
            max_repairs=max_repairs,
            timeout_seconds=timeout_seconds,
            agent_mode="classic",
        )
        record["split"] = split
        record["prompt_sha256"] = prompt_hash
        record["git_revision"] = revision
        record["guidance_applied"] = bool(data_contract_guidance(f"{task_id}\n{task_text}").strip())
        records.append(record)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the prompt hash and score the held-out WorkBuddy split")
    parser.add_argument("--tasks-dir", type=Path, default=Path.home() / "workbuddy-exam/wb-bench-code-v1.0/tasks")
    parser.add_argument("--runs-dir", type=Path, default=Path.home() / "workbuddy-exam/runs-heldout")
    parser.add_argument("--output", type=Path, default=Path.home() / "workbuddy-exam/results-heldout.jsonl")
    parser.add_argument("--summary", type=Path, default=Path.home() / "workbuddy-exam/results-heldout-summary.json")
    parser.add_argument("--model", default="deepseek-v4.1-flash")
    parser.add_argument("--endpoint", default="https://api.kunyou.asia/v1")
    parser.add_argument("--key-file", type=Path, default=Path("/tmp/onecode_happycoding_key"))
    parser.add_argument("--max-repairs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--cohort", choices=("held_out", "in_sample"), default="held_out")
    parser.add_argument("--run", action="store_true", help="Execute the selected cohort")
    args = parser.parse_args(argv)

    if not args.tasks_dir.is_dir():
        print(f"Tasks directory does not exist: {args.tasks_dir}", file=sys.stderr)
        return 1
    groups = split_tasks(args.tasks_dir)
    manifest = {
        "prompt_sha256": prompt_sha256(),
        "git_revision": git_revision(),
        "in_sample_reference_mean": INSAMPLE_REFERENCE_MEAN,
        "in_sample_count": len(groups["in_sample"]),
        "held_out_count": len(groups["held_out"]),
        "excluded_count": len(groups["excluded"]),
        "cohort": args.cohort,
        "held_out_task_ids": groups["held_out"],
        "selected_task_ids": groups[args.cohort],
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if not args.run:
        return 0

    import bench_workbuddy

    if bench_workbuddy.load_api_key(args.key_file) is None:
        print("API key file is missing or empty", file=sys.stderr)
        return 1
    os.environ.setdefault("ONECODE_SURVEY_MAX_TURNS", "0")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("", encoding="utf-8")
    records = run_held_out(
        tasks_dir=args.tasks_dir,
        runs_dir=args.runs_dir,
        task_ids=groups[args.cohort],
        model=args.model,
        endpoint=args.endpoint,
        max_repairs=args.max_repairs,
        timeout_seconds=args.timeout,
        split=args.cohort,
        output=args.output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    from batch_report import batch_run_report

    summary = {
        "manifest": manifest,
        "summary": summarize_rewards(records),
        "batch_report": batch_run_report(
            records,
            model=args.model,
            endpoint=args.endpoint,
            prompt_sha256=manifest["prompt_sha256"],
            git_revision_value=manifest["git_revision"],
        ),
        "model": args.model,
        "endpoint": args.endpoint,
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.cohort.upper()} SUMMARY")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
