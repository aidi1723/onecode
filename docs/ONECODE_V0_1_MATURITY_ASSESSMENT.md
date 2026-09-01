# OneCode v0.1 Maturity Assessment

Date: 2026-05-31
Status: Post-closure assessment for the OneCode Agent Shell v0.1 baseline

## Executive Summary

OneCode v0.1 is best described as a local-first, rule-constrained, recoverable Agent Kernel with a LibreChat Web shell. It has stronger kernel discipline than a typical agent demo, especially around evidence, checkpointing, recovery, path safety, verifier allowlists, and tests.

It is not yet a mature production-grade Agent platform.

Current maturity estimate:

```text
Overall maturity: 2.8 / 5
```

## Positioning

Accurate current positioning:

```text
OneCode v0.1 is a local-first Agent Kernel and shell integration baseline.
It is suitable as a controlled prototype and engineering baseline.
It should not yet be marketed as a mature production Agent platform.
```

The v0.1 shell closure proves that the core can be used through a mature Web shell, but the project still needs sandboxing, benchmarks, observability, human approval, and open-source governance before it reaches community-grade Agent platform expectations.

## Current Strengths

### Kernel Structure

OneCode has clear kernel boundaries:

- checkpoint and ledger persistence
- model planning and execution routing
- path guard
- verifier policy
- inspection and resume classification
- Web API adapter
- LibreChat shell adapter

Score: `4 / 5`

### Evidence And Recovery

Checkpoint, manifest, and ledger design are strong for this stage:

- checkpoint records carry run, turn, state, reason, payload, and resume metadata
- `ledger.json` provides latest user-facing result
- `ledger.jsonl` provides append-only history
- inspect and resume flows can reason about persisted evidence

Score: `4 / 5`

### Safety Guardrails

OneCode is safer than a shell-execution demo:

- path guard rejects absolute paths, workspace escape, `.git`, `.github`, and guarded root files
- verifier policy uses preset allowlists instead of arbitrary command execution
- Web API enforces workspace root constraints

Score: `3 / 5`

The remaining gap is that these are application-level guardrails, not a real process/filesystem/network sandbox.

### Test Density

The project has high test density for its size and stage. The v0.1 closure verification recorded:

- OneCode full verification: `bash scripts/verify.sh`, `Ran 332 tests ... OK`
- OneCode Web API tests: `34 passed`
- LibreChat OneCode bridge tests: `18 passed`
- LibreChat client focused tests: `20 passed`
- data-provider and production frontend builds passed

Score: `4 / 5`

## Major Gaps

### No Real Sandbox

The biggest maturity gap is execution isolation. Current protections rely on path checks and command allowlists. Mature coding agents need sandboxed runtime boundaries:

- isolated filesystem mount
- restricted network
- sanitized environment variables
- process limits
- CPU and memory limits
- timeout enforcement
- cleanup lifecycle

Score: `2 / 5`

### Narrow Tool Surface

The current kernel is strongest around write, patch, verifier, inspect, resume, and shell-facing project workflows. Mature Agent work needs a consistent audited tool model for:

- read/search
- structured edit
- test/package commands
- git state and branch operations
- browser or Web inspection
- artifact export

Score: `2.5 / 5`

### Observability Is Evidence-First, Not Trace-First

Ledger and checkpoints are useful, but the system does not yet expose a complete trace model:

- model call spans
- token/cost accounting
- tool call spans
- verifier spans
- latency and failure classification
- replayable event stream
- OpenTelemetry or SQLite export

Score: `2.5 / 5`

### Missing Standard Benchmark

The test suite validates code behavior, but there is no repeatable Agent benchmark with tasks, scoring, and model/kernel regression baselines.

Missing:

- fixed task corpus
- expected file diffs or assertions
- success/failure scorer
- safety refusal scorer
- resume/recovery scorer
- model comparison reports

Score: `1.5 / 5`

### Human-In-The-Loop Is Early

Execution plans have review/manual concepts, but there is not yet a complete product flow for:

- pending approval
- approve
- reject
- edit
- resume after decision
- human decision evidence

Score: `2 / 5`

### Open-Source Governance Is Incomplete

Before public release, the repository needs:

- LICENSE
- SECURITY.md
- CONTRIBUTING.md
- CODE_OF_CONDUCT.md if public community contribution is expected
- GitHub Actions CI
- release checklist
- versioning policy
- clean worktree and generated artifact rules

Score: `1 / 5`

## Scorecard

| Dimension | Score | Assessment |
| --- | ---: | --- |
| Kernel structure | 4 / 5 | Clear module boundaries and strong evidence chain |
| State recovery | 4 / 5 | Checkpoint/resume design is explicit and tested |
| Safety permissions | 3 / 5 | Strong path/verifier guardrails, but no sandbox |
| Test quality | 4 / 5 | High test density and full verify script |
| Observability | 2.5 / 5 | Ledger exists, trace/metrics/replay missing |
| Model abstraction | 3 / 5 | Multi-provider foundation exists, policy layer is early |
| Human intervention | 2 / 5 | Concepts exist, product flow incomplete |
| Benchmark | 1.5 / 5 | No repeatable Agent benchmark yet |
| Open-source governance | 1 / 5 | CI/license/security/contribution docs missing |
| Production deployment | 2 / 5 | API and shell exist, operations hardening is early |

## Priority Recommendation

### P0: Real Sandbox

Add a Docker-based workspace sandbox before calling the project a mature coding agent. The sandbox should restrict files, network, environment, process limits, and timeouts.

### P1: CI And Open-Source Governance

Add CI, LICENSE, SECURITY.md, CONTRIBUTING.md, release checklist, version policy, and clean worktree rules.

### P1: Agent Benchmark

Create a fixed benchmark with 20-50 tasks:

- file creation
- bug fix
- patch repair
- verifier failure repair
- resume after interruption
- guarded path refusal
- no-op and chat classification

### P2: Trace Observability

Promote ledger/checkpoint into a trace model with model/tool/verifier/human spans, timing, cost, status, and replay.

### P2: Human Approval Flow

High-risk operations should enter `pending_approval`. Human approve/reject/edit decisions should be persisted as evidence and visible in the shell.

## Final Judgment

OneCode v0.1 has a real kernel idea and stronger-than-demo engineering discipline. The next phase should not focus on adding more visible features first. It should harden the Agent substrate: sandbox, benchmark, governance, observability, and human approval.

Recommended next phase name:

```text
OneCode Agent Shell v0.2 - Maturity Hardening
```
