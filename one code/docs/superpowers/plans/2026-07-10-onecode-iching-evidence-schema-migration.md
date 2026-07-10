# OneCode I Ching Evidence Schema Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every newly written I Ching status self-describing, preserve legacy reads as v1, provide a read-only v1-to-v2 migration audit, and cut new runtime writes to v2 only after exhaustive safety comparison.

**Architecture:** Add `rule_schema` at the result, asset, profile, checkpoint, manifest, WAL, ledger, and shell projection boundaries. Readers normalize a missing schema to v1 without rewriting artifacts. A separate pure migration audit reports canonical v2 interpretations and affected trigrams while preserving original hashes and files. New writes use `ACTIVE_RULE_SCHEMA`, which became v2 after the 64-state comparison found no semantic action changes or safety relaxation.

**Tech Stack:** Python 3.11+, `unittest`, JSON checkpoint/ledger/WAL evidence.

---

### Task 1: Add Rule Schema to Runtime Results

**Files:**
- Modify: `src/onecode/kernel/runner.py`
- Modify: `src/onecode/kernel/finalization.py`
- Modify: `src/onecode/kernel/model_loop.py`
- Test: `tests/test_runner_cli.py`
- Test: `tests/test_checkpoint.py`

- [x] Write failing tests asserting every result and asset carrying an
  `iching_status_code` also carries the active `rule_schema`.
- [x] Run focused tests and verify the missing-field failure.
- [x] Add the active schema at result construction and checkpoint calls.
- [x] Run focused tests and verify pass.

### Task 2: Persist Rule Schema in Evidence

**Files:**
- Modify: `src/onecode/kernel/checkpoint.py`
- Test: `tests/test_checkpoint.py`
- Test: `tests/test_wal.py`

- [x] Write failing tests for checkpoint, manifest, ledger, compact profile, and
  global WAL schema fields.
- [x] Run tests and verify RED.
- [x] Extend `write_checkpoint()` and compact evidence projections with
  `rule_schema`, defaulting new writes to the active schema.
- [x] Keep validators backward-compatible when legacy evidence omits the field.
- [x] Run tests and verify GREEN.

### Task 3: Project Schema to Shell Consumers

**Files:**
- Modify: `src/onecode/kernel/shell_projection.py`
- Test: `tests/test_shell_projection.py`

- [x] Write failing tests requiring `rule_state.rule_schema`.
- [x] Verify legacy input without a schema projects v1.
- [x] Add the field to shell projection schema version 3.
- [x] Run focused tests and verify pass.

### Task 4: Add Read-Only Migration Audit

**Files:**
- Create: `src/onecode/kernel/iching_migration.py`
- Create: `tests/test_iching_migration.py`

- [x] Write failing tests for v1 evidence normalization, v2 interpretation,
  affected inner/outer trigram reporting, and no file mutation.
- [x] Implement pure payload audit helpers using `convert_status()`.
- [x] Reject unknown schemas and invalid status values.
- [x] Run exhaustive migration tests.

### Task 5: Evaluate Runtime Cutover

**Files:**
- Modify only after Tasks 1-4 pass.

- [x] Generate a 64-state v1/v2 action comparison report.
- [x] Identify action or safety-dominance differences caused by canonical li/xun
  correction.
- [x] Verify persisted labels remain interpretable through explicit or legacy
  v1 schema normalization.
- [x] Cut over only if no unsafe allow is introduced and legacy reads remain
  deterministic; otherwise retain v1 runtime and record blockers.

### Task 6: Full Verification

- [x] Run focused checkpoint, WAL, shell, encoding, migration, kernel, and
  integration tests.
- [x] Run source quality.
- [x] Run `bash scripts/verify.sh`.
- [x] Run wheel asset and release audit after documentation closure.
