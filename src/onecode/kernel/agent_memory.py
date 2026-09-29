"""Bounded agent history and confirmed cross-task memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from onecode.kernel.evidence_io import ensure_private_file


def compact_agent_history(task: str, history: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    full = [{"role": "task", "text": task}, *history]
    if _encoded_length(full) <= max_chars or len(history) <= 2:
        return full
    omitted = history[:-2]
    return [
        {"role": "task", "text": task},
        {"role": "summary", "omitted_turns": len(omitted)},
        *history[-2:],
    ]


def remember_turn(workspace: Path, record: dict[str, Any], *, confirmed: bool, cycle: str) -> bool:
    if not confirmed or cycle == "stop":
        return False
    path = _memory_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_private_file(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def load_agent_memory(workspace: Path) -> list[dict[str, Any]]:
    path = _memory_path(workspace)
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            records.append(value)
    return records


def _memory_path(workspace: Path) -> Path:
    return workspace.resolve() / ".onecode" / "memory.jsonl"


def _encoded_length(items: list[dict[str, Any]]) -> int:
    return len(json.dumps(items, ensure_ascii=False, sort_keys=True))
