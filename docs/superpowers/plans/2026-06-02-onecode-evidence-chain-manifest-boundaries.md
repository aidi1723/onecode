# OneCode Evidence Chain Manifest Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first safe implementation milestone for risk-tiered evidence and manifest boundary controls.

**Architecture:** Keep existing `evidence_mode` compatibility for `full`/`wal` storage durability, and add a separate `capture_mode` plus `risk_tier` for evidence density. Manifest remains an execution index, with optional bounded `domain_projection` and per-run manifest metrics.

**Tech Stack:** Python 3.11 standard library, `unittest`, existing OneCode kernel modules.

---

### Task 1: Evidence Classification Model

**Files:**
- Create: `src/onecode/kernel/evidence_policy.py`
- Test: `tests/test_evidence_policy.py`

- [x] Add tests for default classification:
  - approvals, path guard, physical writes, verifier results, task finalization, and resume classification are `critical/full`.
  - scheduler transitions are `medium/compact`.
  - heartbeat/progress ticks are `low/aggregate`.
  - unknown event families default to `critical/full`.

- [x] Implement `RiskTier`, `CaptureMode`, `EvidenceClassification`, and `classify_event()`.

- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_evidence_policy -v`

### Task 2: Trace Event Classification Fields

**Files:**
- Modify: `src/onecode/kernel/trace.py`
- Modify: `tests/test_trace.py`

- [x] Add tests that `TraceEvent` includes explicit `risk_tier`, `capture_mode`, and `payload_digest`.
- [x] Add tests that unknown trace event types fail closed to `critical/full`.
- [x] Implement classification defaults in `TraceEvent.__post_init__()` and `to_dict()`.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_trace -v`

### Task 3: WAL Classification Fields

**Files:**
- Modify: `src/onecode/kernel/checkpoint.py`
- Modify: `tests/test_wal.py`

- [x] Add tests that `global_wal_entry()` emits `rt` and `cm` fields.
- [x] Add tests that unknown WAL result event families default to `critical/full`.
- [x] Implement WAL classification without changing existing `em` behavior.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_wal -v`

### Task 4: Manifest Domain Projection Boundary And Metrics

**Files:**
- Modify: `src/onecode/kernel/checkpoint.py`
- Modify: `tests/test_checkpoint.py`

- [x] Add tests that a bounded `domain_projection` is persisted when it contains required fields.
- [x] Add tests that branch-heavy domain fields are rejected.
- [x] Add tests that manifest metrics include section sizes and domain projection count.
- [x] Implement `validate_domain_projection()`, `manifest_size_metrics()`, and optional `domain_projection` support in `write_checkpoint()`.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_checkpoint -v`

### Task 5: Focused Regression Suite

**Files:**
- Existing tests only.

- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_evidence_policy tests.test_trace tests.test_wal tests.test_checkpoint -v`
- [x] Run broader evidence/resume tests if focused tests pass: `PYTHONPATH=src python3 -m unittest tests.test_runner_cli tests.test_resumption tests.test_inspect_cli -v`

### Task 6: Low-Risk Trace Aggregation

**Files:**
- Modify: `src/onecode/kernel/trace.py`
- Modify: `tests/test_trace.py`

- [x] Add tests that repeated low-risk `heartbeat` events are written as one aggregate event with count, first timestamp, last timestamp, and rolling digest.
- [x] Add tests that critical/full events are never aggregated by the trace aggregator.
- [x] Implement `TraceAggregator.record()` and `TraceAggregator.flush()`.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_trace -v`

### Task 7: Runner Progress Aggregation

**Files:**
- Modify: `src/onecode/kernel/runner.py`
- Modify: `tests/test_runner_cli.py`

- [x] Add a test that multi-action runs emit one `progress_tick_aggregate` event.
- [x] Route non-deferred runner trace writes through `TraceAggregator`.
- [x] Emit low-risk `progress_tick` after each action and flush aggregates before `run_completed`.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_trace tests.test_runner_cli.RunnerTests.test_run_task_aggregates_progress_tick_trace_events -v`

### Task 8: Evidence Metrics In Runner Results

**Files:**
- Modify: `src/onecode/kernel/trace.py`
- Modify: `src/onecode/kernel/runner.py`
- Modify: `tests/test_trace.py`
- Modify: `tests/test_runner_cli.py`

- [x] Add tests for trace evidence metrics grouped by risk tier and capture mode.
- [x] Implement `trace_evidence_metrics()` for JSONL trace files.
- [x] Add tests that full evidence runner results and ledgers include trace evidence metrics.
- [x] Attach trace metrics to full evidence results after final trace flush and before ledger write.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_trace tests.test_runner_cli.RunnerTests.test_run_task_records_evidence_metrics_in_result_and_ledger -v`

### Task 9: WAL Evidence Metrics In WAL-Only Results

**Files:**
- Modify: `src/onecode/kernel/wal.py`
- Modify: `src/onecode/kernel/runner.py`
- Modify: `tests/test_wal.py`
- Modify: `tests/test_runner_cli.py`

- [x] Add tests for validated global WAL metrics grouped by risk tier and capture mode.
- [x] Implement `global_wal_evidence_metrics()`.
- [x] Add tests that default WAL-only CLI results include global WAL evidence metrics.
- [x] Attach global WAL metrics to WAL-only runner results after WAL append.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_wal tests.test_runner_cli.CliTests.test_cli_run_prints_json_result -v`

### Task 10: Inspect Evidence Metrics

**Files:**
- Modify: `src/onecode/cli.py`
- Modify: `tests/test_inspect_cli.py`

- [x] Add tests that full evidence inspect summaries include ledger `evidence_metrics.trace`.
- [x] Add tests that WAL-only inspect summaries include computed `evidence_metrics.global_wal`.
- [x] Include ledger evidence metrics in full inspect summaries.
- [x] Include validated global WAL evidence metrics in WAL-only inspect summaries.
- [x] Run: `PYTHONPATH=src python3 -m unittest tests.test_inspect_cli.InspectCliTests.test_cli_inspect_prints_existing_run_summary tests.test_inspect_cli.InspectCliTests.test_cli_inspect_prints_wal_only_run_summary -v`
