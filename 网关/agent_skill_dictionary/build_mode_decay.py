from __future__ import annotations

import difflib
import hashlib

from .build_mode_types import EntropyDecayEvidence


def compute_decay_gate(
    previous_failure_summary: str,
    current_failure_summary: str,
    *,
    base_threshold: int = 3,
    deadlock_similarity: float = 0.95,
) -> EntropyDecayEvidence:
    ratio = difflib.SequenceMatcher(None, previous_failure_summary, current_failure_summary).ratio()
    deadlock = bool(previous_failure_summary and current_failure_summary and ratio >= deadlock_similarity)
    return EntropyDecayEvidence(
        previous_sha256=_sha256(previous_failure_summary),
        current_sha256=_sha256(current_failure_summary),
        similarity_ratio=ratio,
        base_threshold=base_threshold,
        dynamic_threshold=1 if deadlock else base_threshold,
        deadlock_suspected=deadlock,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
