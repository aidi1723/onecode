# OneCode Skill Selection Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record deterministic, read-only skill selection evidence in OneCode run artifacts without enabling skill execution.

**Architecture:** Extend `skill_context` with `select_skill_evidence()`. Thread the compact selection dictionary through `run_task()` into checkpoint, manifest, ledger, and result evidence. Keep execution decisions in existing runner, gate, path, verifier, and Iching control paths.

**Tech Stack:** Python 3.11+, stdlib `json`, `hashlib`, `pathlib`, `unittest`, existing OneCode kernel modules.

---

## File Map

- Modify: `src/onecode/kernel/skill_context.py`
- Modify: `src/onecode/kernel/checkpoint.py`
- Modify: `src/onecode/kernel/runner.py`
- Modify: `tests/test_skill_context.py`
- Modify: `tests/test_iching_kernel_integration.py`
- Modify: `README.md`
- Modify: `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`

## Task 1: Skill Selection Contract

- [x] Write failing tests for deterministic selection, no-match selection, and raw-field redaction.
- [x] Implement `select_skill_evidence(workspace, task)`.
- [x] Run `tests.test_skill_context -v`.

## Task 2: Run Evidence Integration

- [x] Write failing integration test that `run_task()` persists `skill_selection` in result, ledger, manifest, and checkpoint records.
- [x] Add optional `skill_selection` evidence to `write_checkpoint()`.
- [x] Call `select_skill_evidence()` from `run_task()` and pass it through evidence writes.
- [x] Run `tests.test_iching_kernel_integration -v`.

## Task 3: Documentation and Verification

- [x] Document Phase 1.5 in README and optimization report.
- [x] Run focused tests.
- [x] Run `bash scripts/verify.sh`.
- [x] Run `git diff --check -- src tests docs README.md scripts`.

## Task 4: Skill Routing Quality

- [x] Write failing tests for plural/punctuated task tokens and phrase capabilities.
- [x] Split task text on non-alphanumeric separators.
- [x] Add conservative aliases for common test/review/audit/verification variants.
- [x] Match normalized phrase capabilities when all component tokens are present.
- [x] Run `tests.test_skill_context -v`.

Observed routing verification:

```text
.venv/bin/python -m unittest tests.test_skill_context -v
Result: OK, 16 tests passed.
```

Observed focused verification:

```text
.venv/bin/python -m unittest tests.test_skill_context tests.test_runner_cli tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 90 tests passed.
```

Observed full verification:

```text
bash scripts/verify.sh
Result: OK, 692 tests passed, 1 skipped, doctor status ok.
```

Observed diff hygiene:

```text
git diff --check -- src tests docs README.md scripts
Result: no output.
```

## Safety Boundary

Selection evidence is not execution authority. It must not include priority,
confidence, score, raw skill body, allowed tools, or verifier expectation text.
