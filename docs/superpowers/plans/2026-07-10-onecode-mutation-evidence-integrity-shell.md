# OneCode Mutation Evidence Integrity and Shell Implementation Plan

**Goal:** Validate persisted balance mutation evidence and expose a bounded
read-only inspect/shell projection while preserving all bottom-theory formulas
and execution authority.

**Architecture:** Recompute full evidence with existing kernel helpers, compare
summaries to asset evidence, decode the fixed WAL tuple, and project one new
shell section that is never consulted by control logic.

### Task 1: Validate Full Mutation Evidence

- [x] Write failing tests for tampered lines, elements, transition, and summary.
- [x] Verify RED.
- [x] Add pure full-evidence and summary validators.
- [x] Integrate validators into full run inspection.

### Task 2: Validate and Recover WAL Summary

- [x] Write failing WAL tuple type/range tests.
- [x] Write failing WAL-only inspect recovery test.
- [x] Add fixed-tuple validation and named summary decoding.
- [x] Preserve WAL size and hash-chain budgets.

### Task 3: Add Shell v4 Balance State

- [x] Write failing schema and full/WAL projection tests.
- [x] Verify RED.
- [x] Add `balance_state` without changing severity or next action.
- [x] Update Web/CLI projection contracts.

### Task 4: Close and Verify

- [x] Update changelog and closure reports.
- [x] Run focused inspection, WAL, shell, Web, and runner tests.
- [x] Run safety-equivalence certificates.
- [x] Run full verification and release audit.
- [x] Review diff for forbidden authority changes.
