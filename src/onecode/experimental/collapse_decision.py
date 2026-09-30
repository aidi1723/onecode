"""Experimental collapse helper. Not called by the runner or web API.

Turn a 64-way state distribution and closed fact scores into one gateway action.

The hexagram distribution is the judgment base. Line probabilities are marginals
of that distribution. ``project_gateway`` still projects a committed hexagram
and the closed facts. It does not read confidence.

When ``entropy_gate`` is set, a normalized entropy above that gate is ``observe``:
the argmax hexagram is kept, and any non-halt projection is withheld. When it is
omitted, the earlier four-code confidence rule remains for already trained heads.
"""

import math

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_gateway import project_gateway

ENTROPY_GATE = IchingKernel.ENTROPY_THRESHOLD


OBSERVED_STATES = (0b000000, 0b010010, 0b100001, 0b111111)
FAIL_STATE = 0b000000
INTENT_LABELS = (
    "write_text",
    "patch_text",
    "execute_pytest",
    "bash_execution",
    "invalid_intent",
)
PATH_LABELS = ("workspace_relative", "outside_workspace", "no_path")
SANDBOX_LABELS = ("required", "not_required", "missing")
EVIDENCE_LABELS = ("required", "present", "failed")
FAIL_FACTS = {
    "intent_type": "invalid_intent",
    "path_scope": "no_path",
    "sandbox_state": "not_required",
    "evidence_state": "required",
}


def normalized_entropy(state_probs: list[float]) -> float:
    """Shannon entropy of a 64-way cast, divided by log2(64)."""
    _check_distribution(state_probs, 64, "state_probs")
    entropy = 0.0
    for probability in state_probs:
        if probability > 0.0:
            entropy -= probability * math.log2(probability)
    return entropy / 6.0


def line_marginals(state_probs: list[float]) -> list[float]:
    """Yang probability of each line, bottom to top, from the hexagram distribution."""
    _check_distribution(state_probs, 64, "state_probs")
    marginals = []
    for bit_index in range(6):
        marginals.append(
            sum(probability for code, probability in enumerate(state_probs) if (code >> bit_index) & 1)
        )
    return marginals


def collapse_decision(
    state_probs: list[float],
    intent_probs: list[float],
    path_probs: list[float],
    sandbox_probs: list[float],
    evidence_probs: list[float],
    *,
    threshold: float,
    entropy_gate: float | None = None,
) -> dict[str, object]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if entropy_gate is not None and not 0.0 <= entropy_gate <= 1.0:
        raise ValueError("entropy_gate must be between 0 and 1")
    _check_distribution(state_probs, 64, "state_probs")
    _check_distribution(intent_probs, len(INTENT_LABELS), "intent_probs")
    _check_distribution(path_probs, len(PATH_LABELS), "path_probs")
    _check_distribution(sandbox_probs, len(SANDBOX_LABELS), "sandbox_probs")
    _check_distribution(evidence_probs, len(EVIDENCE_LABELS), "evidence_probs")

    state_index, state_confidence = _argmax(state_probs)
    entropy = normalized_entropy(state_probs)
    marginals = line_marginals(state_probs)
    if entropy_gate is None:
        observed = state_index in OBSERVED_STATES
        abstained = (not observed) or state_confidence < threshold
        status_code = FAIL_STATE if abstained else state_index
        facts = dict(FAIL_FACTS) if abstained else _fact_choice(intent_probs, path_probs, sandbox_probs, evidence_probs)
        projected = project_gateway(status_code, facts)
        action = projected
        observe = False
    else:
        facts = _fact_choice(intent_probs, path_probs, sandbox_probs, evidence_probs)
        status_code = state_index
        projected = project_gateway(status_code, facts)
        observe = entropy > entropy_gate
        abstained = observe
        if observe and projected != "SOVEREIGNTY_HALT":
            action = "DENY_AND_LEDGER"
        else:
            action = projected
    return {
        "status_code": status_code,
        "yizijue_state": format(status_code, "06b"),
        "facts": facts,
        "action": action,
        "projected_action": projected,
        "abstained": abstained,
        "observe": observe,
        "state_confidence": state_confidence,
        "normalized_entropy": entropy,
        "line_marginals": marginals,
        "raw_state": state_index,
    }


def _fact_choice(
    intent_probs: list[float],
    path_probs: list[float],
    sandbox_probs: list[float],
    evidence_probs: list[float],
) -> dict[str, str]:
    return {
        "intent_type": INTENT_LABELS[_argmax(intent_probs)[0]],
        "path_scope": PATH_LABELS[_argmax(path_probs)[0]],
        "sandbox_state": SANDBOX_LABELS[_argmax(sandbox_probs)[0]],
        "evidence_state": EVIDENCE_LABELS[_argmax(evidence_probs)[0]],
    }


def collapse_should_defer(decision: dict[str, object]) -> bool:
    """A named gateway action is final. Evidence completion accepts or denies ALLOW afterward."""
    action = decision.get("action")
    return not isinstance(action, str) or not action


def expected_calibration_error(confidences: list[float], correct: list[bool], *, bins: int = 10) -> float:
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("confidences and correct must be the same non-empty length")
    if bins < 1:
        raise ValueError("bins must be positive")
    total = len(confidences)
    error = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        chosen = [
            pair
            for pair in zip(confidences, correct)
            if (lower <= pair[0] < upper) or (index == bins - 1 and pair[0] == 1.0)
        ]
        if not chosen:
            continue
        mean_confidence = sum(item[0] for item in chosen) / len(chosen)
        accuracy = sum(1 for item in chosen if item[1]) / len(chosen)
        error += abs(accuracy - mean_confidence) * (len(chosen) / total)
    return error


def _argmax(values: list[float]) -> tuple[int, float]:
    best_index = 0
    best_value = values[0]
    for index, value in enumerate(values):
        if value > best_value:
            best_index = index
            best_value = value
    return best_index, float(best_value)


def _check_distribution(values: list[float], size: int, name: str) -> None:
    if len(values) != size:
        raise ValueError(f"{name} must have length {size}")
    if any((not isinstance(value, (int, float))) or isinstance(value, bool) for value in values):
        raise ValueError(f"{name} must be numeric")
    total = float(sum(values))
    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"{name} must sum to 1")
