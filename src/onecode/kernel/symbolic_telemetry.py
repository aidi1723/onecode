"""Deterministic state-bit governance helpers and opt-in symbolic telemetry / extension loader."""
from __future__ import annotations

import importlib
import math
import os
import sys
from typing import Any

SYMBOLIC_TELEMETRY_ENV = "ONECODE_SYMBOLIC_TELEMETRY"
SYMBOLIC_EXTENSION_PACKAGE = "onecode-symbolic-audit"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
_EXTENSION_ATTACHED = False


def symbolic_telemetry_enabled() -> bool:
    """Return True only when opt-in symbolic/observability telemetry skin is enabled."""
    return os.environ.get(SYMBOLIC_TELEMETRY_ENV, "").strip().lower() in _TRUTHY_VALUES


def symbolic_extension_loaded() -> bool:
    """Return True if the optional companion package `onecode-symbolic-audit` is loaded."""
    return _EXTENSION_ATTACHED


def _safe_import_symbolic_extension() -> Any | None:
    """Import `onecode_symbolic_audit` avoiding current working directory / workspace hijacking."""
    cwd = os.path.abspath(os.getcwd())
    ws_env = os.environ.get("ONECODE_WORKSPACE")
    workspace = os.path.abspath(ws_env) if ws_env else ""
    safe_sys_path = [
        p for p in sys.path
        if p and p != "." and os.path.abspath(p) != cwd and (not workspace or os.path.abspath(p) != workspace)
    ]
    saved_path = sys.path[:]
    try:
        sys.path = safe_sys_path
        return importlib.import_module("onecode_symbolic_audit")
    except ImportError:
        return None
    finally:
        sys.path = saved_path


def attach_symbolic_extension(kernel_cls: type[Any], *, force: bool = False) -> bool:
    """Attach optional mixins from `onecode_symbolic_audit` onto `kernel_cls` when enabled."""
    global _EXTENSION_ATTACHED
    if not force and not symbolic_telemetry_enabled():
        _EXTENSION_ATTACHED = False
        return False

    mod = _safe_import_symbolic_extension()
    if mod is None:
        _EXTENSION_ATTACHED = False
        return False

    mixins = getattr(mod, "SYMBOLIC_MIXINS", ())
    attached_any = False
    for mixin in mixins:
        for base in reversed(mixin.__mro__):
            if base is object:
                continue
            for name, attr in base.__dict__.items():
                if name.startswith("__"):
                    continue
                if name not in kernel_cls.__dict__:
                    setattr(kernel_cls, name, attr)
                    attached_any = True
    _EXTENSION_ATTACHED = attached_any or hasattr(kernel_cls, "ziwei_mathematical_audit")
    return _EXTENSION_ATTACHED


def call_symbolic_profile(
    kernel_cls: type[Any],
    method_name: str,
    *args: Any,
    force: bool = False,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Invoke an optional symbolic audit method on `kernel_cls` if the companion extension is installed."""
    if not _EXTENSION_ATTACHED and (force or symbolic_telemetry_enabled()):
        attach_symbolic_extension(kernel_cls, force=force)
    fn = getattr(kernel_cls, method_name, None)
    if fn is None or not callable(fn):
        return None
    result = fn(*args, **kwargs)
    return result if isinstance(result, dict) else None


def compute_workspace_envelope(file_count: int, total_loc: int) -> dict[str, Any]:
    """Compute bounded workspace complexity tier and scheduling envelope from code metrics."""
    scale = math.log(max(1, total_loc) + 1) * math.sqrt(max(1, file_count))
    if scale < 4.0:
        tier = 2
        turn_budget = 3
        timeout_sec = 45
        patch_strategy = "surgical_diff_only"
        preview_limit_chars = 4000
        repair_file_limit = 6
    elif scale < 8.0:
        tier = 3
        turn_budget = 4
        timeout_sec = 60
        patch_strategy = "incremental_feature_growth"
        preview_limit_chars = 6000
        repair_file_limit = 8
    elif scale < 14.0:
        tier = 4
        turn_budget = 5
        timeout_sec = 90
        patch_strategy = "strict_contract_refactoring"
        preview_limit_chars = 8000
        repair_file_limit = 10
    elif scale < 22.0:
        tier = 5
        turn_budget = 6
        timeout_sec = 120
        patch_strategy = "foundational_stability_migration"
        preview_limit_chars = 10000
        repair_file_limit = 12
    else:
        tier = 6
        turn_budget = 8
        timeout_sec = 180
        patch_strategy = "distributed_orchestration"
        preview_limit_chars = 14000
        repair_file_limit = 16

    return {
        "scale": round(scale, 2),
        "bureau": tier,
        "bureau_name": f"tier_{tier}",
        "turn_budget": turn_budget,
        "timeout_sec": timeout_sec,
        "patch_strategy": patch_strategy,
        "preview_limit_chars": preview_limit_chars,
        "repair_file_limit": repair_file_limit,
    }


def trace_causal_origin_file(
    error_traceback: str | None,
    history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Locate the most recent modified file referenced in an error traceback."""
    if not error_traceback or not history:
        return None

    for past_turn in reversed(history):
        modified = past_turn.get("modified_files")
        files = list(modified) if isinstance(modified, (list, set)) else []
        for file_path in files:
            if str(file_path) in error_traceback:
                turn_id = int(past_turn.get("turn_id", past_turn.get("turn_index", 0)))
                return {
                    "incoming_turn_id": turn_id,
                    "culprit_file": str(file_path),
                    "target_rollback_point": max(0, turn_id - 1),
                    "reason": f"Defect originated in Turn {turn_id} modifying {file_path}",
                }
    return None


def is_degraded_status(status_code: int) -> bool:
    """Determine degraded mode purely from the 6-bit state and Lyapunov energy."""
    from onecode.kernel.hexagram import IchingKernel

    normalized = int(status_code) & 0b111111
    if normalized in {0, 32} or (normalized & 0b000111) != 0:
        return True
    return IchingKernel.lyapunov_energy(normalized) > 1.60


def resolve_state_governance_mode(status_code: int) -> str:
    """Resolve deterministic governance mode ('autonomous', 'guarded', or 'degraded')."""
    from onecode.kernel.hexagram import IchingKernel

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
