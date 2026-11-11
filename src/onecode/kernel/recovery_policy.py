from __future__ import annotations

from dataclasses import dataclass, field

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.symbolic_telemetry import compute_damping_factor, symbolic_telemetry_enabled


SCENARIO_ACTIONS = {
    "trace_flush_failure": "repair",
    "verifier_failure": "repair",
    "resume_conflict": "inspect",
    "sandbox_failure": "reconfigure",
    "provider_failure": "retry_once",
    "config_partial_invalid": "inspect",
    "project_context_invalid": "inspect",
}

MAX_ATTEMPTS = 2


@dataclass
class RecoveryContext:
    attempts: dict[str, int] = field(default_factory=dict)

    def record_attempt(self, scenario: str, *, success: bool, status_code: int | None = None) -> dict:
        attempt_count = self.attempts.get(scenario, 0) + 1
        self.attempts[scenario] = attempt_count

        if success:
            state = "succeeded"
            recommended_action = "inspect"
        elif attempt_count >= MAX_ATTEMPTS:
            state = "exhausted"
            recommended_action = "halt"
        else:
            state = "failed"
            recommended_action = None

        return recovery_status(
            scenario,
            attempted=True,
            attempt_count=attempt_count,
            state=state,
            recommended_action=recommended_action,
            status_code=status_code,
        )


def recovery_status(
    scenario: str,
    *,
    attempted: bool = False,
    attempt_count: int = 0,
    state: str = "queued",
    recommended_action: str | None = None,
    turn_number: int = 1,
    status_code: int | None = None,
) -> dict:
    resolved_action = recommended_action or SCENARIO_ACTIONS.get(scenario, "inspect")
    resolved_status_code = status_code if status_code is not None else _iching_status_code(state, resolved_action)
    transition = IchingKernel.transition(resolved_status_code)
    yin_yang = IchingKernel.yin_yang_cross_profile(resolved_status_code)
    damping_factor = compute_damping_factor(attempt_count)

    payload = {
        "scenario": scenario,
        "status": "advisory_only",
        "attempted": attempted,
        "attempt_count": attempt_count,
        "attempts_remaining": max(MAX_ATTEMPTS - attempt_count, 0),
        "retry_limit": MAX_ATTEMPTS,
        "state": state,
        "recommended_action": resolved_action,
        "lyapunov_damping_factor": damping_factor,
        "relief_effective": True,
        "element": "fire",
        "yin_yang_pressure": yin_yang["pressure"],
        "iching_status_code": resolved_status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }
    if symbolic_telemetry_enabled():
        payload["jie_shen_relief"] = IchingKernel.jie_shen_relief_profile(
            turn_number=turn_number,
            status_code=resolved_status_code,
            error_scenario=scenario,
            attempt_count=attempt_count,
        )
        payload["twelve_deities"] = IchingKernel.twelve_deities_profile(
            turn_number=turn_number,
            status_code=resolved_status_code,
        )
    return payload


def _iching_status_code(state: str, recommended_action: str) -> int:
    if state == "exhausted" or recommended_action == "halt":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)
    if state == "succeeded":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.GEN)
    return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KAN)
