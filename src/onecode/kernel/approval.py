from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ApprovalAction = Literal["approve", "reject", "edit"]
APPROVAL_ACTIONS = {"approve", "reject", "edit"}


@dataclass(frozen=True)
class ApprovalDecision:
    run_id: str
    decision_id: str
    action: ApprovalAction
    reason: str
    edited_payload: dict[str, Any] | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if self.action not in APPROVAL_ACTIONS:
            raise ValueError(f"unknown approval action: {self.action}")
        if not self.run_id.strip():
            raise ValueError("run_id must not be empty")
        if not self.decision_id.strip():
            raise ValueError("decision_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "decision_id": self.decision_id,
            "action": self.action,
            "reason": self.reason,
            "edited_payload": self.edited_payload,
            "timestamp": self.timestamp,
        }


def write_approval_decision(path: Path, decision: ApprovalDecision) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
        )
