"""Training data package for OneCode.

This package provides training data generation, corpus building, and evaluation
functionality for the YiZiJue safety gateway model.

Re-exports all public APIs from submodules for backward compatibility.
Legacy imports like `from onecode.kernel.training_data import X` continue to work
by importing from `onecode.kernel.training` instead.
"""

# Core exports
from onecode.kernel.training.core import (
    ACTIVE_RULE_SCHEMA,
    MODEL_BASE,
    MODEL_REPOSITORY,
    REQUIRED_ACTION_COVERAGE,
    REQUIRED_DIMENSION_COVERAGE,
    SYSTEM_PROMPT,
    YIZIJUE_LM_BASIS_FIELDS,
    YIZIJUE_LM_OPTIONAL_BASIS_FIELDS,
    YIZIJUE_LM_OUTPUT_TYPES,
    YIZIJUE_LM_REQUIRED_BASIS_FIELDS,
    YIZIJUE_LM_SYSTEM_PROMPT,
    TrainingSample,
    build_adjudicated_feedback_samples,
    enrich_basis_with_kernel_profile,
    state_basis_for_lm_row,
    validate_training_sample,
    validate_yizijue_lm_sample,
    validate_yizijue_lm_state_sample,
    write_jsonl,
    yizijue_lm_state_rows_from_lm_rows,
)

__all__ = [
    # Constants
    "ACTIVE_RULE_SCHEMA",
    "MODEL_BASE",
    "MODEL_REPOSITORY",
    "REQUIRED_ACTION_COVERAGE",
    "REQUIRED_DIMENSION_COVERAGE",
    "SYSTEM_PROMPT",
    "YIZIJUE_LM_BASIS_FIELDS",
    "YIZIJUE_LM_OPTIONAL_BASIS_FIELDS",
    "YIZIJUE_LM_OUTPUT_TYPES",
    "YIZIJUE_LM_REQUIRED_BASIS_FIELDS",
    "YIZIJUE_LM_SYSTEM_PROMPT",
    # Core classes and functions
    "TrainingSample",
    "build_adjudicated_feedback_samples",
    "enrich_basis_with_kernel_profile",
    "state_basis_for_lm_row",
    "validate_training_sample",
    "validate_yizijue_lm_sample",
    "validate_yizijue_lm_state_sample",
    "write_jsonl",
    "yizijue_lm_state_rows_from_lm_rows",
]

# Note: Additional exports will be added as samples.py, corpus.py, and evaluation.py are created
# For now, functions not yet refactored will be imported from the legacy training_data.py
# This allows incremental migration
