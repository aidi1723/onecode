#!/usr/bin/env python3
"""Evaluate and analyze injected test results from external benchmark runs.

Reads jsonl records (such as ~/workbuddy-exam/results-r13-injected.jsonl),
applies robust multi-strategy parsing to capture missing scores, and
classifies task failures into clear diagnostic categories.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from onecode.kernel.injected_test_runner import (
    classify_injected_test_failure,
    parse_junit_xml,
    parse_pytest_summary,
)


def analyze_injected_record(record: dict[str, Any]) -> dict[str, Any]:
    task_id = str(record.get("task_id", "unknown"))
    stdout = str(record.get("stdout") or "")
    stderr = str(record.get("stderr") or "")
    exit_code = int(record.get("exit_code", 0))
    xml_report = str(record.get("junit_xml") or "")

    # 1. Parse score / summary
    summary = None
    if xml_report:
        summary = parse_junit_xml(xml_report)
    if summary is None or summary.total == 0:
        summary = parse_pytest_summary(stdout + "\n" + stderr)

    # 2. If score already recorded in record, check if our parser recovers a missing score
    prior_score = record.get("score")
    if prior_score is None and summary.total > 0:
        recovered_score = summary.pass_rate
    else:
        recovered_score = prior_score

    # 3. Classify failure category
    classification = classify_injected_test_failure(stdout, stderr, exit_code)

    return {
        "task_id": task_id,
        "passed": summary.passed,
        "failed": summary.failed,
        "errors": summary.errors,
        "total": summary.total,
        "pass_rate": recovered_score,
        "status": "graded" if summary.total > 0 else "ungraded",
        "category": classification["category"],
        "detail": classification["detail"],
        "summary_mode": summary.raw_summary,
    }


def evaluate_injected_jsonl(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Result file not found: {path}")

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    analyzed = [analyze_injected_record(r) for r in records]
    graded = [a for a in analyzed if a["status"] == "graded" and a["pass_rate"] is not None]
    category_counts = Counter(a["category"] for a in analyzed)

    mean_pass_rate = (
        round(sum(float(g["pass_rate"]) for g in graded) / len(graded), 3)
        if graded
        else 0.0
    )

    return {
        "total_tasks": len(analyzed),
        "graded_tasks": len(graded),
        "ungraded_tasks": len(analyzed) - len(graded),
        "mean_pass_rate": mean_pass_rate,
        "category_counts": dict(category_counts),
        "tasks": analyzed,
    }


def print_evaluation_report(report: dict[str, Any]) -> None:
    print("=" * 80)
    print("INJECTED TEST RUNNER EVALUATION REPORT")
    print("=" * 80)
    print(f"Total Tasks:     {report['total_tasks']}")
    print(f"Graded Tasks:    {report['graded_tasks']}")
    print(f"Ungraded Tasks:  {report['ungraded_tasks']}")
    print(f"Mean Pass Rate:  {report['mean_pass_rate']}")
    print("\nFailure / Status Categories:")
    for cat, count in report["category_counts"].items():
        print(f"  - {cat:28s}: {count:2d}")
    print("-" * 80)
    print(f"{'Task ID':<45} | {'Passed/Total':<14} | {'Pass Rate':<10} | {'Category'}")
    print("-" * 80)
    for t in report["tasks"]:
        score_str = f"{t['passed']}/{t['total']}" if t["total"] > 0 else "-"
        rate_str = f"{t['pass_rate']:.3f}" if t["pass_rate"] is not None else "-"
        print(f"{t['task_id']:<45} | {score_str:<14} | {rate_str:<10} | {t['category']}")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze injected test results")
    parser.add_argument("results_file", type=Path, help="Path to results jsonl file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    try:
        report = evaluate_injected_jsonl(args.results_file)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_evaluation_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
