"""Compatibility import. Implementation lives in onecode.experimental.collapse_decision."""

from onecode.experimental.collapse_decision import (
    collapse_decision,
    collapse_should_defer,
    expected_calibration_error,
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

__all__ = ['collapse_decision', 'collapse_should_defer', 'expected_calibration_error', '_argmax', '_check_distribution', 'OBSERVED_STATES', 'FAIL_STATE', 'INTENT_LABELS', 'PATH_LABELS', 'SANDBOX_LABELS', 'EVIDENCE_LABELS', 'FAIL_FACTS']
