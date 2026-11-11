from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskTier(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaptureMode(StrEnum):
    FULL = "full"
    COMPACT = "compact"
    AGGREGATE = "aggregate"
    SAMPLED = "sampled"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class EvidenceClassification:
    risk_tier: RiskTier
    capture_mode: CaptureMode
    commit_coupled: bool
    reason: str


_CRITICAL_FULL_EVENTS = {
    "approval_decision",
    "path_guard_decision",
    "permission_matrix_decision",
    "sandbox_decision",
    "sovereignty_decision",
    "physical_write",
    "patch_application",
    "write_text",
    "patch_text",
    "verifier_result",
    "task_finalization",
    "resume_classification",
    "resume_conflict",
    "final_delivery_state",
    "run_completed",
}

_HIGH_COMPACT_EVENTS = {
    "node_ownership_transfer",
    "retry_exhaustion",
    "repair_attempt",
    "model_tool_boundary_decision",
}

_MEDIUM_COMPACT_EVENTS = {
    "scheduler_state_transition",
    "internal_api_orchestration",
    "cache_decision",
    "non_mutating_inspection",
    "run_started",
    "tool_call_started",
    "tool_call_completed",
    "checkpoint_written",
}

_LOW_AGGREGATE_EVENTS = {
    "heartbeat",
    "progress_tick",
    "stable_poll",
    "idempotent_noop",
    "queue_visibility_update",
}


def classify_event(event_type: str | None) -> EvidenceClassification:
    normalized = (event_type or "").strip()
    if normalized in _CRITICAL_FULL_EVENTS:
        return EvidenceClassification(
            risk_tier=RiskTier.CRITICAL,
            capture_mode=CaptureMode.FULL,
            commit_coupled=True,
            reason="critical_trust_event",
        )
    if normalized in _HIGH_COMPACT_EVENTS:
        return EvidenceClassification(
            risk_tier=RiskTier.HIGH,
            capture_mode=CaptureMode.COMPACT,
            commit_coupled=True,
            reason="high_risk_decision_event",
        )
    if normalized in _MEDIUM_COMPACT_EVENTS:
        return EvidenceClassification(
            risk_tier=RiskTier.MEDIUM,
            capture_mode=CaptureMode.COMPACT,
            commit_coupled=False,
            reason="medium_risk_runtime_event",
        )
    if normalized in _LOW_AGGREGATE_EVENTS:
        return EvidenceClassification(
            risk_tier=RiskTier.LOW,
            capture_mode=CaptureMode.AGGREGATE,
            commit_coupled=False,
            reason="low_risk_liveness_event",
        )
    return EvidenceClassification(
        risk_tier=RiskTier.CRITICAL,
        capture_mode=CaptureMode.FULL,
        commit_coupled=True,
        reason="unknown_event_family_fail_closed",
    )
