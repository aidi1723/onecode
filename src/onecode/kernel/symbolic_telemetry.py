"""Deterministic state-bit governance helpers and opt-in symbolic telemetry switch."""
from __future__ import annotations

import os
from typing import Any

from onecode.kernel.hexagram import IchingKernel

SYMBOLIC_TELEMETRY_ENV = "ONECODE_SYMBOLIC_TELEMETRY"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def symbolic_telemetry_enabled() -> bool:
    """Return True only when opt-in symbolic/Ziwei observability skin is enabled."""
    return os.environ.get(SYMBOLIC_TELEMETRY_ENV, "").strip().lower() in _TRUTHY_VALUES


def is_degraded_status(status_code: int) -> bool:
    """Determine degraded mode purely from the 6-bit state and Lyapunov energy."""
    normalized = int(status_code) & 0b111111
    if normalized in {0, 32} or (normalized & 0b000111) != 0:
        return True
    return IchingKernel.lyapunov_energy(normalized) > 1.60


def resolve_state_governance_mode(status_code: int) -> str:
    """Resolve deterministic governance mode ('autonomous', 'guarded', or 'degraded')."""
    normalized = int(status_code) & 0b111111
    if is_degraded_status(normalized):
        return "degraded"
    energy = IchingKernel.lyapunov_energy(normalized)
    if energy <= 0.60:
        return "autonomous"
    return "guarded"


def compute_damping_factor(attempt_count: int) -> float:
    """Compute exponential-decay bounded damping factor for retry backoff."""
    return round(max(0.40, 0.75 - 0.15 * max(0, int(attempt_count) - 1)), 2)


def compute_systemic_intervention(status_code: int) -> dict[str, Any]:
    """Compute bounded execution throttling and WAL checkpoint interventions from Hamming weight."""
    normalized = int(status_code) & 0x3F
    yang_count = bin(normalized).count("1")
    yin_count = 6 - yang_count
    if yang_count >= 5:
        return {
            "turn_budget_damping_factor": 0.85,
            "adaptive_cooldown_ms": 50,
            "force_wal_checkpoint_sync": False,
            "execution_mode": "degraded",
        }
    if yin_count >= 5:
        return {
            "turn_budget_damping_factor": 1.0,
            "adaptive_cooldown_ms": 0,
            "force_wal_checkpoint_sync": True,
            "execution_mode": "degraded",
        }
    return {
        "turn_budget_damping_factor": 1.0,
        "adaptive_cooldown_ms": 0,
        "force_wal_checkpoint_sync": False,
        "execution_mode": "autonomous",
    }


def compute_cycle_gain_multiplier(
    bureau: int = 2,
    ming_branch: int = 2,
    year_branch: int = 0,
    *,
    age: int = 30,
    gender: str = "male",
    calendar_year_branch: int = 6,
) -> float:
    """Compute deterministic Z_12 modular phase-alignment multiplier (1.0, 1.5, or 2.0)."""
    b = bureau if bureau in (2, 3, 4, 5, 6) else 2
    cur_age = max(1, age)
    y_branch = year_branch % 12
    m_branch = ming_branch % 12
    cal_branch = calendar_year_branch % 12

    is_yang_year = (y_branch % 2) == 0
    is_male = gender.casefold() == "male"
    clockwise = (is_yang_year and is_male) or (not is_yang_year and not is_male)
    if cur_age < b:
        macro_phase = m_branch
    else:
        step = (cur_age - b) // 10
        macro_phase = (m_branch + (step if clockwise else -step)) % 12

    origin = (10 - 3 * (y_branch % 4)) % 12
    minor_phase = (origin + (cur_age - 1) if is_male else origin - (cur_age - 1)) % 12

    def _dist(a: int, c: int) -> int:
        diff = abs(a - c)
        return min(diff, 12 - diff)

    if macro_phase == minor_phase == cal_branch:
        return 2.0
    if (
        _dist(macro_phase, minor_phase) in (0, 4)
        and _dist(minor_phase, cal_branch) in (0, 4)
        and _dist(macro_phase, cal_branch) in (0, 4)
    ):
        return 1.5
    return 1.0
