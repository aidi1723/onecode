# OneCode v0.2 Six-Direction Review Correction

Date: 2026-05-31

This document corrects the six-direction application review against the current
OneCode repository state. It supersedes review notes that still describe older
v0.1 or early v0.2 gaps as current defects.

## Verification Baseline

- Full verification: `bash scripts/verify.sh`
- Result: `384 tests OK`
- Doctor: `status: ok`
- Core posture: local-first, rule-constrained, evidence-first Agent kernel
- License posture: Apache License 2.0, copyright `aidi`

## Corrections To Earlier Review Claims

### Verifier

Earlier claim: verifier can execute arbitrary commands.

Current corrected status: verifier is a real command execution channel, but it
is controlled by policy allowlists. `load_verifier_policy()` rejects commands
outside `VERIFIER_POLICY_PRESETS` or equivalent Python executable forms.

Residual risk: verifier still executes local processes when enabled. It should
be treated as a privileged controlled verifier path, not as a general shell.

### Sandbox

Earlier claim: no real sandbox.

Current corrected status: a Docker sandbox adapter exists. It supports
workspace mounting, network mode control, memory limits, CPU limits, and
timeout enforcement. It is reachable through `sandbox-smoke` and optional
verifier execution.

Residual risk: sandboxing is not mandatory for the main `run_task` write path.
The main path still relies primarily on `LogosGate`, `PathGuard`, verifier
policy, and resource budgets.

### run_task Exception Handling

Earlier claim: `run_task()` has no exception handling.

Current corrected status: `run_task()` now catches unexpected exceptions and
converts them to a halted `run_exception` result where possible. It writes
terminal `run_completed` trace evidence and ledger evidence when the evidence
path remains writable.

Residual risk: catastrophic filesystem failure can still prevent all evidence
from being persisted. The in-memory result carries `ledger_write_error` or
`trace_write_error` when those writes fail.

### Evidence Locks

Earlier claim: evidence locking is process-local only.

Current corrected status: evidence writes use a process-local lock plus Unix
`fcntl.flock()` on `.write.lock`, so concurrent processes on Unix/macOS share a
file-level lock for one run evidence directory.

Residual risk: this is not Windows portable and is not a distributed lock for
multi-host deployments.

### Web API Authentication

Earlier claim: token comparison uses normal string equality.

Current corrected status: bearer token comparison uses
`secrets.compare_digest()`. Missing-token behavior is explicit: unauthenticated
mode is allowed only when configured and bound to loopback hosts.

Residual risk: the built-in stdlib HTTP server remains a local/development
server, not a public production gateway.

### Resource Budgets

Earlier claim: no resource budgets.

Current corrected status: `run_task` supports positive `max_task_chars`,
`max_write_bytes`, and `max_actions`, exposed by the CLI. Budget breaches halt
as `resource_budget_exceeded` before target files are written, while still
recording manifest, checkpoint, ledger, and terminal trace evidence.

Residual risk: total run deadline, ledger/trace size limits, stdout/stderr
aggregate limits, and per-run disk budgets are still future work.

## Six-Direction Assessment

| Direction | Fit | Directly usable now | Corrected assessment |
| --- | ---: | --- | --- |
| Math / research | 4.5 / 5 | Yes | Strongest direction. The deterministic 6-bit control model is real and test-covered. |
| Enterprise internal tooling | 3.5 / 5 | Yes, with boundaries | Useful as an embedded controlled file-change engine or internal Agent kernel. |
| Production platform | 2.5 / 5 | No | Hardened beyond prototype, but not a public/multi-tenant production platform. |
| Financial systems | 2 / 5 | PoC only | Audit evidence is relevant, but compliance, HA, signing, and governance are missing. |
| Energy vertical | 1 / 5 | No | Not a direct OT/SCADA or real-time industrial control product. |
| Education / engineering baseline | 4 / 5 | Yes | Good teaching and benchmark baseline for deterministic Agent control. |

## Correct Current Positioning

OneCode v0.2 is a local-first, rule-constrained, evidence-first Agent kernel
with a usable Web shell integration. It is strongest as:

- a deterministic Agent control research target
- a controlled internal file-change engine
- a local/offline code and asset generation kernel
- a benchmark substrate for hallucination, evidence, resume, and guarded write
  behavior

It should not yet be described as:

- a public multi-tenant Agent platform
- a financial-grade or compliance-certified system
- an energy/OT control product
- a general unrestricted shell-execution Agent

## Adopted Improvement Plan

### P0: Evidence Tamper Resistance

Status: partially closed.

`evidence-chain.jsonl` now records a tamper-evident SHA256 chain over ledger
writes. `inspect` validates sequence continuity, previous hash continuity,
record hash integrity, and ledger artifact hash matches.

Remaining work: extend the chain to checkpoint and trace artifacts, or add an
optional signing layer for compliance environments.

### P0: Stronger Sandbox Defaults

Status: closed for current local sandbox adapter.

Sandbox execution now includes stricter Docker flags:

- `--pids-limit`
- `--cap-drop ALL`
- read-only root filesystem where compatible
- bounded `/tmp` tmpfs
- configurable network policy

Remaining work: make verifier sandboxing default in internal deployment
profiles if the operator has Docker available.

### P1: Run-Level Resource Budgets

Status: partially closed.

The runner now covers task text, write payloads, action count, trace size, and
total run deadline:

- total run deadline
- total trace size

Remaining work:

- total ledger history size
- verifier stdout/stderr aggregate limits
- per-run disk usage budget

### P1: Cross-Platform Lock Strategy

Keep Unix `fcntl.flock()` as the current local production path, but document the
platform boundary and add a portable lock abstraction before claiming Windows
support.

### P1: Public Deployment Boundary

Keep the stdlib HTTP server positioned as local-first. Public deployments should
place OneCode behind a hardened service layer with request size limits,
rate-limiting, TLS, audit logging, and operator-managed auth.

### P2: Math-Layer Publication

Extract the deterministic control model into a research-facing document or
small library. Present it as discrete state projection, entropy gating, and
finite-state control rather than relying on cultural terminology alone.

## Final Judgment

The six-direction review is directionally useful, but several high-severity
defects in that review are outdated. Current OneCode has already closed the
exception convergence, cross-process local evidence lock, Web auth compare, and
basic resource budget gaps.

The honest v0.2 claim is:

```text
OneCode is a local-first, deterministic, evidence-first Agent kernel suitable
for research and controlled internal tooling. It is not yet a public
multi-tenant production Agent platform.
```
