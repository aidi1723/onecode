from __future__ import annotations

from dataclasses import dataclass, field

from onecode.kernel.hexagram import IchingKernel


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

    def record_attempt(self, scenario: str, *, success: bool) -> dict:
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
        )


def recovery_status(
    scenario: str,
    *,
    attempted: bool = False,
    attempt_count: int = 0,
    state: str = "queued",
    recommended_action: str | None = None,
) -> dict:
    resolved_action = recommended_action or SCENARIO_ACTIONS.get(scenario, "inspect")
    status_code = _iching_status_code(state, resolved_action)
    transition = IchingKernel.transition(status_code)
    yin_yang = IchingKernel.yin_yang_cross_profile(status_code)

    return {
        "scenario": scenario,
        "status": "advisory_only",
        "attempted": attempted,
        "attempt_count": attempt_count,
        "attempts_remaining": max(MAX_ATTEMPTS - attempt_count, 0),
        "retry_limit": MAX_ATTEMPTS,
        "state": state,
        "recommended_action": resolved_action,
        "element": "fire",
        "yin_yang_pressure": yin_yang["pressure"],
        "iching_status_code": status_code,
        "iching_transition_action": transition.action,
        "iching_transition_reason": transition.reason,
        "dispatch_decision": IchingKernel.dispatch_decision(transition),
    }


def _iching_status_code(state: str, recommended_action: str) -> int:
    if state == "exhausted" or recommended_action == "halt":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)
    if state == "succeeded":
        return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.GEN)
    return IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KAN)
