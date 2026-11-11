#!/usr/bin/env python3
"""Count classic and terminal ledger rows on the shared hexagram outcome table."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def normalize_ledger_row(record: dict[str, Any]) -> dict[str, Any]:
    """Map a batch or task record onto the shared outcome fields."""
    code = record.get("iching_status_code")
    if not isinstance(code, int) or isinstance(code, bool):
        legacy = record.get("outcome_status_code")
        if legacy == 0:
            code = 63
        elif legacy == 1:
            code = record.get("iching_status_code") if isinstance(record.get("iching_status_code"), int) else 39
        else:
            code = None
    reward = record.get("host_reward")
    numeric_reward = float(reward) if isinstance(reward, (int, float)) and not isinstance(reward, bool) else None
    return {
        "agent_mode": str(record.get("agent_mode") or "classic"),
        "status": record.get("status"),
        "iching_status_code": code,
        "outcome_status_code": code,
        "host_reward": numeric_reward,
    }


def summarize_ledger_rows(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [normalize_ledger_row(record) for record in records]
    by_mode: dict[str, Counter[str]] = {}
    for row in rows:
        mode = row["agent_mode"]
        bucket = by_mode.setdefault(mode, Counter())
        bucket[str(row["iching_status_code"])] += 1
    return {
        "row_count": len(rows),
        "by_agent_mode": {mode: dict(counter) for mode, counter in sorted(by_mode.items())},
        "modes": sorted(by_mode),
    }


def load_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize classic and terminal ledger rows")
    parser.add_argument("jsonl", nargs="+", type=Path)
    args = parser.parse_args(argv)
    summary = summarize_ledger_rows(load_jsonl(args.jsonl))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
