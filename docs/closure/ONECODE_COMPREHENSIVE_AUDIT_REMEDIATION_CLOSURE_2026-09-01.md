# OneCode Comprehensive Audit Remediation Closure

Date: 2026-09-01
Status: Verified and committed locally; no remote publication
Branch: `main`
Implementation head: `75aea0d`
Source audit: `docs/closure/ONECODE_COMPREHENSIVE_AUDIT_2026-09-01.md`

## Outcome

All six high- and medium-priority items from the 2026-09-01 comprehensive audit
are closed. One low-priority item (#7, CI configuration) was verified rather
than changed. No runtime behavior changed: each item is a security guard, a
structural move, or documentation.

| Priority | Item | Resolution |
| --- | --- | --- |
| High #1 | Git history references invalid | Repository re-initialized; `docs/GIT_HISTORY_NOTE.md` records the cited commits and branches |
| High #2 | Web API binding not enforced | Startup guard in `run_server` plus five tests |
| High #3 | Documentation discoverability | 37 closure reports relocated to `docs/closure/`; `docs/INDEX.md` updated |
| Medium #4 | `training_data.py` too large | Split into a four-module package; original file removed |
| Medium #5 | No architecture diagrams | `docs/ARCHITECTURE.md`, 11 Mermaid diagrams |
| Medium #6 | I Ching learning curve | `docs/ICHING_QUICKREF.md`, all 64 hexagrams |
| Low #7 | CI configuration unverified | `.github/workflows/verify.yml` reviewed; Python 3.11/3.12/3.13 matrix plus wheel-asset check |

## Training Package Refactoring

`src/onecode/kernel/training_data.py` (2,441 lines) became
`src/onecode/kernel/training/`:

| Module | Lines | Responsibility |
| --- | --- | --- |
| `core.py` | 360 | `TrainingSample`, constants, validation |
| `samples.py` | 959 | Sample generation |
| `corpus.py` | 516 | Corpus building, export, I/O |
| `evaluation.py` | 713 | Prediction evaluation, quality gates, benchmarks |
| `__init__.py` | 178 | Re-exports 74 public names |

No module exceeds 1,000 lines. The dependency graph is acyclic and flows in one
direction: `core` ← `samples`, `core` ← `evaluation`, and all three ← `corpus`.

The plan anticipated a cycle, because `corpus` needs `evaluate_training_quality`
and `evaluation` was expected to need `build_training_corpus`. The second
dependency does not exist, so the cycle never formed and
`evaluate_training_quality` stayed in `evaluation.py` instead of being moved into
`core.py` as the plan had recommended.

Two deliberate adjustments, both behavior-preserving:

1. `sanitize_reason` moved into `core.py`, since `samples.py` and `evaluation.py`
   both depend on it.
2. In `generate_pretraining_readiness_report`, the locals `llamafactory_config`
   and `axolotl_config` shadowed the module-level functions of the same name once
   those functions shared the module; renamed to `..._path`.

Everything else is a verbatim move.

## Import Migration

`onecode.kernel.training_data` → `onecode.kernel.training`:

- `src/onecode/cli.py`
- `src/onecode/kernel/deepseek_distillation.py`
- `src/onecode/kernel/yizijue_transformers.py`
- `tests/test_training_data.py`
- `tests/test_cli_read_only_commands.py` (forbidden-import prefix list)
- `scripts/check_source_quality.py` (long-function allowlist)

Two call sites reached `assistant_payload` and `adjudicate_gateway_prediction`
through the old module's namespace rather than from their defining module. They
now import from `onecode.kernel.gateway_engine` directly
(`tests/test_training_data.py`, `tests/test_web_api.py`).

## Verification

| Gate | Result |
| --- | --- |
| Full suite | 912 passed, 1 environment-only skip |
| `compileall src tests` | clean |
| `scripts/check_source_quality.py src` | clean |
| `onecode doctor` | `ok` |
| Wheel build | `training/` package present, `training_data.py` absent |

Behavior parity for the split was established per module against the original
implementation by sorted-key JSON comparison covering the sample generators, the
coverage report, `deterministic_eval_ids`, both trainer configs, corpus counts,
and the readiness report. Generated `train.jsonl` and `eval.jsonl` are
byte-identical to the pre-refactor output.

CLI smoke checks passed for `generate-training-data`, `validate-training-data`,
`build-training-corpus`, `training-coverage`, `pretraining-readiness`, and
`run-yizijue-lm-eval`.

## Incidental Fix

`tests/test_rule_closure.py` asserted on `docs/V0_6_MATH_CLOSURE_REPORT.md`,
stale since commit `6566c11` moved closure reports into `docs/closure/`. The
path was corrected. This failure predates the refactoring and is unrelated to
it.

## Open Items

These were identified during remediation and deliberately left for the
maintainer, because each changes environment or repository identity rather than
project code.

1. **The `.venv` editable install resolves `onecode` to a different copy of the
   project** at `/Users/aidi/大字典/one code`, so `scripts/verify.sh` exercises
   that tree rather than this one. All verification above was run with
   `PYTHONPATH=src` to bypass it. Re-running `pip install -e .` from this
   directory would realign the install. Until then, `verify.sh` results should
   not be treated as evidence about this working tree.

2. **No git remote is configured and CI has never executed.**
   `.github/workflows/verify.yml` is well-formed but has never run, so the
   three-version matrix is an untested intention rather than a passing gate.

3. **Commit identity is auto-derived** (`aidi@aidideMac-mini.lan`). Setting
   `user.name` and `user.email` before the history grows is cheaper than
   rewriting it later.

4. **Version remains `0.8.0` with no tags.** History begins at `c563552`, a
   re-initialization, so the commits cited across the closure reports
   (`1f3d691b`, `9e74cc0e`, `4878c18`) are recoverable only through
   `docs/GIT_HISTORY_NOTE.md`.

## Maturity Assessment

Engineering quality is mature: a zero-dependency core, 912 tests in roughly 19
seconds, frozen dataclasses with predominantly pure functions, path-guard and
sandbox isolation, custom source-quality gates, and a documented mathematical
closure for the I Ching state machine.

Release engineering is not. The primary verification script tests the wrong
directory tree, CI has never run, history is reconstructed rather than
original, and there is no tagged baseline. The accurate description of the
project today is solid code with an unclosed delivery chain. Closing it means,
in order: configure a remote and get one green CI run, repair the editable
install so `verify.sh` is trustworthy again, then tag a traceable baseline.

## Changed Files

```
CHANGELOG.md                                  (+76)
docs/closure/IMPROVEMENTS_COMPLETED_2026-09-01.md  (new)
docs/TRAINING_DATA_REFACTORING_STATUS.md      (rewritten)
scripts/check_source_quality.py               (allowlist path)
src/onecode/cli.py                            (import)
src/onecode/kernel/deepseek_distillation.py   (import)
src/onecode/kernel/yizijue_transformers.py    (import)
src/onecode/kernel/training/__init__.py       (full re-exports)
src/onecode/kernel/training/core.py           (+sanitize_reason)
src/onecode/kernel/training/samples.py        (new)
src/onecode/kernel/training/corpus.py         (new)
src/onecode/kernel/training/evaluation.py     (new)
src/onecode/kernel/training_data.py           (removed)
tests/test_cli_read_only_commands.py          (prefix list)
tests/test_rule_closure.py                    (stale path)
tests/test_training_data.py                   (imports)
tests/test_web_api.py                         (import)
```

17 files, +2956 / -2610.
