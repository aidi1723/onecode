# Training Data Refactoring Progress

## Status: Partial Complete (Core Module + Package Structure)

Date: 2026-09-01  
Task: Split `src/onecode/kernel/training_data.py` (2,441 lines) into modular package

## What Was Completed

### ✅ Package Structure Created
```
src/onecode/kernel/training/
├── __init__.py              # Backward-compatible re-exports
└── core.py                  # Core definitions and validation (~350 lines)
```

### ✅ core.py Module (Lines 1-345 extracted)
**Contains:**
- `TrainingSample` dataclass
- All constants: MODEL_BASE, SYSTEM_PROMPT, YIZIJUE_LM_*, REQUIRED_*
- `validate_training_sample()`
- `validate_yizijue_lm_sample()`
- `validate_yizijue_lm_state_sample()`
- `write_jsonl()`
- `build_adjudicated_feedback_samples()`
- `enrich_basis_with_kernel_profile()`
- `state_basis_for_lm_row()`
- `yizijue_lm_state_rows_from_lm_rows()`

### ✅ Backward Compatibility
- `__init__.py` re-exports all core functions
- Existing imports continue to work: `from onecode.kernel.training.core import TrainingSample`
- Legacy path compatible once full migration complete

## What Remains

### ⏳ samples.py (~900 lines)
**Lines to extract: 346-400, 401-828, 1997-2441**
- `seed_training_samples()`
- `expanded_training_samples()`
- `schema_correction_training_samples()`
- `yizijue_lm_base_samples()`
- `natural_language_rule_lm_samples()`
- `yizijue_lm_eval_samples()`
- `iching_rule_lm_samples()`
- `yizijue_lm_action_row()`
- Action payload functions
- Helper functions: `_samples_from_spec`, `_sample_from_prompt`, `_dedupe_samples`

### ⏳ corpus.py (~700 lines)
**Lines to extract: 700-708, 830-1050, 1442-1681**
- `build_training_corpus()`
- `build_yizijue_lm_corpus()`
- `build_yizijue_lm_state_corpus()`
- `build_yizijue_lm_evalset()`
- `export_llamafactory_bundle()`
- `export_axolotl_jsonl()`
- `write_training_configs()`
- `generate_pretraining_readiness_report()`
- `generate_coverage_report()`
- `read_jsonl()`, `validate_jsonl()`
- Config templates and helpers

### ⏳ evaluation.py (~500 lines)
**Lines to extract: 1053-1440, 1544-1994**
- `evaluate_training_predictions()`
- `evaluate_yizijue_lm_predictions()`
- `evaluate_yizijue_lm_state_predictions()`
- `evaluate_training_quality()`
- Normalization functions
- Prediction reading functions
- `run_yizijue_lm_eval_predictions()`
- Benchmark functions
- Helper functions for facts/actions/sanitization

## Why Partial?

The full refactoring requires:
1. **Careful extraction** of 2,096 remaining lines (2,441 - 345 done)
2. **Dependency analysis** between modules to avoid circular imports
3. **Function-by-function verification** to ensure no logic changes
4. **Import updates** in 4+ dependent files
5. **Full test suite run** (907 tests) to verify behavior unchanged

**Time estimate**: 2-3 hours for complete refactoring + testing

**Completed today**: 5 audit improvements including:
- Git history fixes
- Documentation reorganization (37 closure reports moved)
- Architecture diagrams (ARCHITECTURE.md)
- I Ching quick reference (ICHING_QUICKREF.md)
- Web API security validation

## Next Steps (For Future Session)

1. **Create samples.py**: Extract all sample generation functions
2. **Create corpus.py**: Extract corpus building and export functions
3. **Create evaluation.py**: Extract evaluation and benchmark functions
4. **Update __init__.py**: Add all new exports
5. **Update imports**: Modify cli.py and other dependent files
6. **Run tests**: Verify all 907 tests pass
7. **Remove old file**: Delete training_data.py after verification
8. **Commit**: Final commit with refactored structure

## Current State

**Training package is functional** but incomplete:
- ✅ Core module works independently
- ✅ Can import: `from onecode.kernel.training.core import TrainingSample`
- ❌ Legacy `training_data.py` still exists and is used by CLI
- ❌ Sample/corpus/evaluation functions not yet extracted

**No breaking changes** - all existing code continues to work with original `training_data.py`

## Files Modified Today

```
src/onecode/kernel/training/
├── __init__.py              (new, 60 lines)
└── core.py                  (new, 350 lines)

src/onecode/web/api.py       (modified, +13 lines security check)
tests/test_web_api_binding_security.py  (new, 80 lines)
docs/ARCHITECTURE.md          (new, 450 lines)
docs/ICHING_QUICKREF.md       (new, 530 lines)
docs/INDEX.md                 (modified)
docs/closure/                 (37 files moved from docs/)
docs/GIT_HISTORY_NOTE.md      (new)
README.md                     (modified, git history note)
```

## Verification Commands

```bash
# Verify core module works
cd "/Volumes/MacSSD/项目开发/one code"
PYTHONPATH=src python3 -c "from onecode.kernel.training.core import TrainingSample; print('OK')"

# Verify original still works
PYTHONPATH=src python3 -c "from onecode.kernel.training_data import TrainingSample; print('OK')"

# Run tests
bash scripts/verify-core.sh
```

## Conclusion

**Today's accomplishments**: 5 out of 6 high/medium priority audit items completed:
1. ✅ Git history fixes (High Priority #1)
2. ✅ Web API binding validation (High Priority #2)  
3. ✅ Documentation reorganization (High Priority #3)
4. ⏳ **training_data.py split** (Medium Priority #4) - **Partial (core module done)**
5. ✅ Architecture diagrams (Medium Priority #5)
6. ✅ I Ching quick reference (Medium Priority #6)

The training_data refactoring foundation is laid with core.py complete. The remaining work (samples/corpus/evaluation modules) can be completed in a dedicated session when time permits.
