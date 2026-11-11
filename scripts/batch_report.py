#!/usr/bin/env python3
"""Archive one batch run: revision, model, prompt hash, tokens, cost, and duration."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def _usage(record: dict[str, Any]) -> dict[str, Any]:
    usage = record.get("model_usage")
    return usage if isinstance(usage, dict) else {}


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def batch_run_report(
    records: list[dict[str, Any]],
    *,
    model: str,
    endpoint: str,
    prompt_sha256: str,
    git_revision_value: str | None = None,
) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    call_count = 0
    cost_usd: float | None = None
    duration_s = 0.0
    for record in records:
        usage = _usage(record)
        prompt_tokens += _int(usage.get("prompt_tokens"))
        completion_tokens += _int(usage.get("completion_tokens"))
        total_tokens += _int(usage.get("total_tokens"))
        call_count += _int(usage.get("call_count"))
        cost = usage.get("cost_usd")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            cost_usd = float(cost_usd or 0.0) + float(cost)
        duration = record.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            duration_s += float(duration)
    return {
        "git_revision": git_revision_value or git_revision(),
        "model": model,
        "endpoint": endpoint,
        "prompt_sha256": prompt_sha256,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "call_count": call_count,
        "cost_usd": None if cost_usd is None else round(cost_usd, 6),
        "duration_s": round(duration_s, 2),
        "task_count": len(records),
        "claims_mainstream_parity": False,
    }
