from __future__ import annotations

from typing import Any

from .build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    FeedbackEvidence,
    SandboxEvidence,
    TransitionPlanEvidence,
    ViolationEvidence,
    WriteEvidence,
)
from .build_mode_topology import edge_walk_path, is_edge_transition, transition_axes

FAILURE_GATE_THRESHOLD = 2


def next_hexagram(current_hexagram: str, evidence: Any, consecutive_failures: int = 0) -> str:
    if isinstance(evidence, ViolationEvidence):
        return HEX_HALT
    if current_hexagram == HEX_CREATE and isinstance(evidence, WriteEvidence):
        if evidence.ok and evidence.changed_files:
            return HEX_VERIFY
        return HEX_CORRECT
    if current_hexagram == HEX_VERIFY and isinstance(evidence, SandboxEvidence):
        if evidence.exit_code == 0 and evidence.pytest_status == "passed":
            return HEX_RETURN
        if evidence.timed_out or evidence.oom or consecutive_failures >= FAILURE_GATE_THRESHOLD:
            return HEX_HALT
        return HEX_CORRECT
    if current_hexagram == HEX_HALT and isinstance(evidence, ViolationEvidence):
        return HEX_CORRECT
    if current_hexagram == HEX_CORRECT and isinstance(evidence, FeedbackEvidence):
        return HEX_INSPECT if evidence.next_hexagram == HEX_INSPECT else evidence.next_hexagram
    if current_hexagram == HEX_RETURN and isinstance(evidence, ArchiveEvidence):
        if evidence.manifest_path and evidence.sha256_map:
            return "总"
        return HEX_HALT
    return HEX_HALT


def guarded_next_hexagram(
    current_hexagram: str,
    target_hexagram: str,
    evidence: Any,
    *,
    emergency_override: bool = False,
) -> TransitionPlanEvidence:
    if emergency_override or is_edge_transition(current_hexagram, target_hexagram):
        path = (
            (current_hexagram, target_hexagram)
            if current_hexagram != target_hexagram
            else (current_hexagram,)
        )
    else:
        path = edge_walk_path(current_hexagram, target_hexagram)
    return TransitionPlanEvidence(
        source_hexagram=current_hexagram,
        target_hexagram=target_hexagram,
        edge_path=path,
        changed_axes=transition_axes(current_hexagram, target_hexagram),
        emergency_override=emergency_override,
    )
