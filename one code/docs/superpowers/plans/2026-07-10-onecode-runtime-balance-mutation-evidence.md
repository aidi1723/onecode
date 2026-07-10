# OneCode Runtime Balance Mutation Evidence Implementation Plan

**Goal:** Persist descriptive evidence for existing raw-to-balanced state
changes while preserving the authoritative I Ching formulas and static profile
identity.

**Architecture:** Build mutation evidence from existing kernel profile methods,
attach full evidence to assets, aggregate it at result level, and persist only
bounded summaries in checkpoint, manifest, and WAL records.

### Task 1: Define Runtime Mutation Evidence

- [x] Write failing kernel tests for before/after lines, trigrams, elements,
  pressure, balance, transition, and dispatch facts.
- [x] Verify RED.
- [x] Add a pure descriptive evidence helper.
- [x] Verify the static profile mutation field remains null.

### Task 2: Attach Asset and Result Evidence

- [x] Write failing single- and multi-asset runner tests.
- [x] Verify RED.
- [x] Attach full evidence to assets and bounded aggregate to results.
- [x] Verify no status or action changes.

### Task 3: Persist Compact Evidence

- [x] Write failing checkpoint, manifest, ledger, and WAL tests.
- [x] Verify RED.
- [x] Add optional compact mutation summaries and WAL aliases.
- [x] Preserve legacy evidence reads.

### Task 4: Close and Verify

- [x] Update changelog and closure records.
- [x] Run focused kernel, runner, checkpoint, WAL, and integration tests.
- [x] Run 64-state safety equivalence.
- [x] Run full verification and release audit.
- [x] Review diff for forbidden formula changes.
