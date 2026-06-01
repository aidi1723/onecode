# OneCode Phase 2 Rule Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 2 rule and execution hardening for OneCode.

**Architecture:** Keep runtime safety boundaries intact while expanding pure rule transitions, resumable patch evidence, execution-plan layer scheduling, and LogosGate executor lifecycle. All behavior is covered through unittest red-green cycles.

**Tech Stack:** Python standard library, unittest, concurrent.futures, existing OneCode kernel modules.

---

### Task 1: Rule Surface Expansion

**Files:**
- Modify: `src/onecode/kernel/hexagram.py`
- Test: `tests/test_iching_kernel.py`

- [ ] Add failing tests for `quench`, `prune`, `fuel`, `dam`, `activate`, and differentiated 64-state transition coverage.
- [ ] Implement expanded `element_dynamics()` modulation.
- [ ] Implement transition actions derived from yin-yang pressure and element relation.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_iching_kernel -v`.

### Task 2: Patch Resume

**Files:**
- Modify: `src/onecode/kernel/resumption.py`
- Modify: `src/onecode/kernel/runner.py`
- Test: `tests/test_resumption.py`
- Test: `tests/test_runner_cli.py`

- [ ] Add failing tests proving completed patch checkpoints can be skipped when replacement content is already present.
- [ ] Add conflict audit detail for SHA mismatch.
- [ ] Extend ready-asset lookup to `patch_text`.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_resumption tests.test_runner_cli -v`.

### Task 3: Dependency-Layered Parallel Execution

**Files:**
- Modify: `src/onecode/kernel/execution_engine.py`
- Test: `tests/test_execution_engine.py`

- [ ] Add failing tests for parallel independent steps and stable ordered results.
- [ ] Implement topological ready-layer scheduling with `ThreadPoolExecutor`.
- [ ] Preserve immediate safety break semantics.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_execution_engine -v`.

### Task 4: LogosGate Executor Lifecycle

**Files:**
- Modify: `src/onecode/kernel/logos_gate.py`
- Modify: `src/onecode/kernel/runner.py`
- Test: `tests/test_logos_gate.py`

- [ ] Add failing tests proving bounded actions reuse one executor and `close()` shuts it down.
- [ ] Implement reusable executor plus context-manager methods.
- [ ] Close the gate from `run_task()`.
- [ ] Run `PYTHONPATH=src python -m unittest tests.test_logos_gate tests.test_runner_cli -v`.

### Task 5: Verification

**Files:**
- Modify: `docs/PHASE1_CLOSURE_REPORT.md` or add Phase 2 note if needed.

- [ ] Run `env -u PYTHONPATH "PATH=$PWD/.venv/bin:$PATH" bash scripts/verify.sh`.
- [ ] Run `env "PATH=$PWD/.venv/bin:$PATH" onecode audit-self`.
- [ ] Commit Phase 2 implementation.
