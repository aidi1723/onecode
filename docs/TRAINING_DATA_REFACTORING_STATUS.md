# Training Data Refactoring Progress

## Status: Complete

Date: 2026-09-01
Task: Split `src/onecode/kernel/training_data.py` (2,441 lines) into a modular package

## Result

```
src/onecode/kernel/training/
├── __init__.py      178 lines  # public API re-exports (74 names)
├── core.py          360 lines  # TrainingSample, constants, validation
├── samples.py       959 lines  # sample generation
├── corpus.py        516 lines  # corpus building, export, I/O
└── evaluation.py    713 lines  # prediction evaluation, quality gates, benchmarks
```

`src/onecode/kernel/training_data.py` has been removed. No module exceeds 1,000 lines.

## Module Contents

### core.py
`TrainingSample`, constants (`MODEL_BASE`, `MODEL_REPOSITORY`, `SYSTEM_PROMPT`,
`YIZIJUE_LM_*`, `REQUIRED_ACTION_COVERAGE`, `REQUIRED_DIMENSION_COVERAGE`),
`validate_training_sample`, `validate_yizijue_lm_sample`,
`validate_yizijue_lm_state_sample`, `write_jsonl`, `sanitize_reason`,
`build_adjudicated_feedback_samples`, `enrich_basis_with_kernel_profile`,
`state_basis_for_lm_row`, `yizijue_lm_state_rows_from_lm_rows`.

### samples.py
`seed_training_samples`, `expanded_training_samples`,
`schema_correction_training_samples`, `yizijue_lm_base_samples`,
`natural_language_rule_lm_samples`, `yizijue_lm_eval_samples`,
`iching_rule_lm_samples`, `yizijue_lm_action_row`, action payload helpers,
and the private helpers `_samples_from_spec`, `_sample_from_prompt`, `_dedupe_samples`.

### corpus.py
`build_training_corpus`, `build_yizijue_lm_corpus`, `build_yizijue_lm_state_corpus`,
`build_yizijue_lm_evalset`, `export_llamafactory_bundle`, `export_axolotl_jsonl`,
`write_training_configs`, `generate_pretraining_readiness_report`,
`generate_coverage_report`, `read_jsonl`, `validate_jsonl`, `deterministic_eval_ids`,
`llamafactory_config`, `axolotl_config`, and dimension/ranking helpers.

### evaluation.py
`evaluate_training_predictions`, `evaluate_yizijue_lm_predictions`,
`evaluate_yizijue_lm_state_predictions`, `evaluate_training_quality`,
normalization and prediction-reading functions, `run_yizijue_lm_eval_predictions`,
and the benchmark functions (`generate_training_benchmark_tasks`,
`training_benchmark_task_payloads`, `benchmark_task_to_training_sample`,
`replay_benchmark_training_samples`, and their helpers).

## Dependency Graph

Acyclic, one direction only:

```
core  ←  samples
core  ←  evaluation
{core, samples, evaluation}  ←  corpus
```

The plan anticipated a cycle (corpus needs `evaluate_training_quality`) and suggested
moving that function into core. It turned out evaluation.py needs nothing from
corpus.py, so the cycle never existed and `evaluate_training_quality` stayed in
evaluation.py where it belongs.

## Deliberate Changes

Two, both behavior-preserving:

1. `sanitize_reason` moved into core.py because both samples.py and evaluation.py use it.
2. In `generate_pretraining_readiness_report`, the local variables `llamafactory_config`
   and `axolotl_config` shadowed the module-level functions of the same name once those
   functions lived in the same module; the locals were renamed to
   `llamafactory_config_path` / `axolotl_config_path`.

Everything else is a verbatim move.

## Import Migration

`onecode.kernel.training_data` → `onecode.kernel.training`:

- `src/onecode/cli.py`
- `src/onecode/kernel/deepseek_distillation.py`
- `src/onecode/kernel/yizijue_transformers.py`
- `tests/test_training_data.py`
- `tests/test_cli_read_only_commands.py` (forbidden-import prefix list)
- `scripts/check_source_quality.py` (long-function allowlist entry)

Two call sites imported `assistant_payload` / `adjudicate_gateway_prediction` through
`training_data`'s namespace rather than from their defining module; they now import from
`onecode.kernel.gateway_engine` directly (`tests/test_training_data.py`,
`tests/test_web_api.py`).

## Verification

- 912 tests pass (`unittest discover -s tests`), 1 skipped, 0 failures
- `compileall` clean, `scripts/check_source_quality.py src` clean
- `onecode doctor` status `ok`
- Behavior parity checked per module against the original by JSON round-trip comparison
  (sorted keys): sample generators, coverage report, `deterministic_eval_ids`, both
  trainer configs, corpus counts, readiness report, and byte-identical `train.jsonl` /
  `eval.jsonl` output
- CLI smoke tested: `generate-training-data`, `validate-training-data`,
  `build-training-corpus`, `training-coverage`, `pretraining-readiness`,
  `run-yizijue-lm-eval`

Two unrelated pre-existing failures surfaced during the run:

- `tests/test_rule_closure.py` referenced `docs/V0_6_MATH_CLOSURE_REPORT.md`, stale since
  commit 6566c11 moved closure reports into `docs/closure/`. Path corrected.
- `.venv` holds an editable install pointing at a different copy of the project
  (`/Users/aidi/大字典/one code`), so `scripts/verify.sh` tests that tree instead of this
  one. Worked around with `PYTHONPATH=src`; the install itself was left alone.

## Verification Commands

```bash
cd "/Volumes/MacSSD/项目开发/one code"
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m onecode doctor
```

## Audit Items

All 6 high/medium priority items from the 2026-09-01 audit are now complete:

1. Git history fixes (High #1)
2. Web API binding validation (High #2)
3. Documentation reorganization (High #3)
4. training_data.py split (Medium #4)
5. Architecture diagrams (Medium #5)
6. I Ching quick reference (Medium #6)
