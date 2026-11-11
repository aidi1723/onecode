"""Compatibility import. Implementation lives in onecode.experimental.collapse_decision."""

from onecode.experimental.collapse_decision import (
    ENTROPY_GATE,
    collapse_decision,
    collapse_should_defer,
    expected_calibration_error,
    line_marginals,
    normalized_entropy,
    _argmax,
    _check_distribution,
    OBSERVED_STATES,
    FAIL_STATE,
    INTENT_LABELS,
    PATH_LABELS,
    SANDBOX_LABELS,
    EVIDENCE_LABELS,
    FAIL_FACTS,
)

__all__ = ['ENTROPY_GATE', 'collapse_decision', 'collapse_should_defer', 'expected_calibration_error', 'line_marginals', 'normalized_entropy', '_argmax', '_check_distribution', 'OBSERVED_STATES', 'FAIL_STATE', 'INTENT_LABELS', 'PATH_LABELS', 'SANDBOX_LABELS', 'EVIDENCE_LABELS', 'FAIL_FACTS']
