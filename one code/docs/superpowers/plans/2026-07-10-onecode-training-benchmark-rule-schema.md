# OneCode Training and Benchmark Rule Schema Implementation Plan

**Goal:** Add explicit versioned I Ching schema metadata to persisted training
and benchmark projections while preserving legacy reads and the strict Action
JSON contract.

**Architecture:** Normalize record-level schema through the existing immutable
encoding module. Builders emit the active v2 schema; validators interpret
missing metadata as v1 and reject unknown identifiers. Benchmark reports carry
one top-level schema covering embedded runtime results. No exporter may
recalculate or override yin/yang lines, five-element generation/control,
dynamic balance, transition, or dispatch facts.

### Task 1: Version Gateway Training Rows

- [x] Write failing tests for v2 emission, v1 legacy normalization, and unknown
  schema rejection.
- [x] Verify focused tests fail for the missing contract.
- [x] Add record-level schema to `TrainingSample` and its validator.
- [x] Verify focused tests pass.

### Task 2: Version YiZiJue-LM Rows

- [x] Write failing corpus, evaluation, and state-row schema tests.
- [x] Verify RED without changing Action JSON.
- [x] Add normalized schema handling to row builders and validators.
- [x] Verify Action JSON fields remain unchanged.
- [x] Verify exported state profiles equal the kernel's yin/yang, five-element,
  balance, transition, and dispatch projections.

### Task 3: Version Benchmark Reports

- [x] Write failing run and A/B report schema tests.
- [x] Verify RED.
- [x] Add active schema to report roots.
- [x] Verify focused benchmark tests pass.

### Task 4: Documentation and Verification

- [x] Update changelog and canonical closure follow-up.
- [x] Run training, transformer, benchmark, encoding, and migration tests.
- [x] Run full verification and release audit.
- [x] Review final diff and compatibility risks.
