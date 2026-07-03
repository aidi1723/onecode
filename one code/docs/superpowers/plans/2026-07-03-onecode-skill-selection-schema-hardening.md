# OneCode Skill Selection Schema Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate `skill_selection` evidence before it is persisted in checkpoint, manifest, ledger, or WAL records.

**Architecture:** Add a compact validator in `src/onecode/kernel/checkpoint.py` near existing domain projection and manifest-size validators. `run_task()` validates `select_skill_evidence()` output before trace/result persistence. `write_checkpoint()`, `write_ledger()`, and global WAL projection validate optional `skill_selection` and persist only validated copies or compact hash/reason/count fields.

**Tech Stack:** Python 3.11+, stdlib `json`, `re`, `unittest`, existing OneCode checkpoint and runner modules.

---

## File Map

- Modify: `src/onecode/kernel/checkpoint.py`
- Modify: `src/onecode/kernel/runner.py`
- Modify: `tests/test_checkpoint.py`
- Modify: `tests/test_runner_cli.py`
- Modify: `tests/test_wal.py`
- Modify: `README.md`
- Modify: `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`

## Task 1: Schema Regression Tests

- [x] Write failing tests for forbidden fields and selected count mismatch.
- [x] Write failing tests for oversized selection evidence.
- [x] Write passing test for valid compact `skill_selection` persistence.

## Task 2: Validator Implementation

- [x] Add skill-selection allowed key constants and size limits.
- [x] Add `validate_skill_selection()` helper.
- [x] Call the helper from `write_checkpoint()`.
- [x] Run `tests.test_checkpoint -v`.

## Task 3: Documentation and Verification

- [x] Update README and optimization report.
- [x] Run focused tests.
- [x] Run `bash scripts/verify.sh`.
- [x] Run `git diff --check -- src tests docs README.md scripts`.

Observed focused verification:

```text
.venv/bin/python -m unittest tests.test_checkpoint -v
Result: OK, 21 tests passed.

.venv/bin/python -m unittest tests.test_skill_context tests.test_runner_cli tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 90 tests passed.

bash scripts/verify.sh
Result: OK, 696 tests passed, 1 skipped, doctor status ok.

git diff --check -- src tests docs README.md scripts
Result: OK, no whitespace errors reported.
```

## Task 4: Runner, Ledger, and WAL Boundary Deepening

- [x] Add failing runner test for invalid selected-skill fields before persistence.
- [x] Add failing direct ledger and WAL projection tests for invalid selection evidence.
- [x] Validate selection output immediately after `select_skill_evidence()`.
- [x] Validate direct `write_ledger()` and `global_wal_entry()` inputs.
- [x] Run affected checkpoint, WAL, runner, and integration tests.

Observed deepening verification:

```text
.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_wal tests.test_runner_cli tests.test_iching_kernel_integration -v
Result: OK, 98 tests passed.

bash scripts/verify.sh
Result: OK, 699 tests passed, 1 skipped, doctor status ok.

git diff --check -- src tests docs README.md scripts
Result: OK, no whitespace errors reported.
```

## Task 5: Shell Projection Compact Skill State

- [x] Add failing shell projection schema test for compact skill state fields.
- [x] Add projection test that exposes reason/count/hash without raw selected skills.
- [x] Bump shell projection schema version to 2.
- [x] Add CLI run regression test for shell-projected skill selection.
- [x] Update README shell projection contract.

Observed shell projection verification:

```text
.venv/bin/python -m unittest tests.test_shell_projection -v
Result: OK, 12 tests passed.

.venv/bin/python -m unittest tests.test_runner_cli.CliTests.test_cli_run_projects_compact_skill_selection_for_shell -v
Result: OK, 1 test passed.

.venv/bin/python -m unittest \
  tests.test_shell_projection tests.test_runner_cli \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_shell_schema_endpoint_returns_projection_contract \
  tests.test_web_api.OneCodeWebApiTests.test_http_server_serves_shell_schema \
  tests.test_inspect_cli tests.test_checkpoint tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 150 tests passed, 1 skipped due to local socket bind permission.

bash scripts/verify.sh
Result: OK, 701 tests passed, 1 skipped, doctor status ok.

git diff --check -- src tests docs README.md scripts
Result: OK, no whitespace errors reported.
```

## Task 6: WAL Inspect Skill-State Alias Closure

- [x] Add failing shell projection test for compact WAL aliases `ssh`, `ssr`, and `ssc`.
- [x] Add failing CLI inspect test for WAL-only skill selection visibility.
- [x] Project WAL compact aliases into shell `control_state`.
- [x] Carry compact WAL skill-selection fields through `inspect_global_wal_run()`.
- [x] Verify shell, inspect, runner, WAL, and Iching integration tests.

Observed WAL inspect verification:

```text
.venv/bin/python -m unittest \
  tests.test_shell_projection tests.test_inspect_cli tests.test_runner_cli \
  tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 127 tests passed.

bash scripts/verify.sh
Result: OK, 702 tests passed, 1 skipped, doctor status ok.

git diff --check -- src tests docs README.md scripts
Result: OK, no whitespace errors reported.
```

## Task 7: Project Review Schema Tightening

- [x] Review current skill evidence persistence and shell projection paths for schema bypasses.
- [x] Add failing tests for raw fields inside `skill_context_summary`.
- [x] Add failing tests for invalid top-level selection status/reason.
- [x] Add failing tests for invalid selected skill mode/risk.
- [x] Restrict `skill_context_summary` to explicit compact summary keys.
- [x] Restrict `status`, `selection_reason`, selected skill `mode`, and selected skill `risk` to read-only evidence enums.
- [x] Verify checkpoint, skill context, runner, WAL, and Iching integration tests.

Observed project-review verification:

```text
.venv/bin/python -m unittest tests.test_checkpoint -v
Result: OK, 25 tests passed.

.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_skill_context tests.test_runner_cli \
  tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 118 tests passed.
```

## Safety Boundary

This plan validates evidence only. It must not enable skill execution or add
runtime authority fields such as priority, confidence, or score.
