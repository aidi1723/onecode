from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    run_id: str
    span_id: str
    parent_span_id: str | None
    event_type: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        for field_name in ("trace_id", "run_id", "span_id", "event_type", "status"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "event_type": self.event_type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


def write_trace_event(path: Path, event: TraceEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
