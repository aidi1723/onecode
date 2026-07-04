# OneCode CLI Service Decoupling Design

Date: 2026-07-04
Scope: First maintenance phase after release-readiness closure

## Goal

Reduce the long-term maintenance risk in `src/onecode/cli.py` by moving shared
runtime inspection and diagnostic behavior into kernel-owned service modules.
The first phase preserves every public CLI, Web API, and TUI behavior while
removing the current Web/TUI dependency on `onecode.cli` for `run_doctor`,
`inspect_run`, and `list_runs`.

## Current Problem

`src/onecode/cli.py` is both a command-line entrypoint and a shared service
module. `src/onecode/web/api.py` imports `inspect_run`, `list_runs`, and
`run_doctor` from `onecode.cli`; `src/onecode/tui/app.py` imports the same CLI
functions inside workers. This makes CLI parsing code part of the dependency
path for non-CLI surfaces and makes future CLI decomposition riskier.

The source quality gate currently records the large CLI hotspots explicitly.
This phase should shrink the CLI responsibility without attempting a broad
parser or command-family rewrite.

## Design

Add two kernel-owned modules:

- `src/onecode/kernel/diagnostics.py`
  - owns `doctor_check`, `doctor_result_detail`, `doctor_rule_passed`, and
    `run_doctor`
  - depends on kernel services only
  - is the shared implementation used by CLI, Web API, TUI, and self-audit

- `src/onecode/kernel/run_inspection.py`
  - owns run inspection helpers and public `inspect_run` / `list_runs`
  - keeps the existing result payload contract unchanged
  - depends on kernel inspection, checkpoint, trace, WAL, run-id, shell
    projection, and Iching kernel helpers

`src/onecode/cli.py` will keep compatibility wrappers or re-exports for
existing imports used by tests and downstream callers. CLI command handling
will keep calling the same names so behavior remains unchanged.

`src/onecode/web/api.py` and `src/onecode/tui/app.py` will import shared
services from the kernel modules instead of importing from `onecode.cli`.

## Compatibility Contract

This phase must preserve:

- `onecode.cli.run_doctor()`
- `onecode.cli.inspect_run(workspace, run_id)`
- `onecode.cli.list_runs(workspace)`
- `onecode.cli.delivery_summary(ledger)`
- CLI JSON output for `doctor`, `inspect`, and `list-runs`
- Web handler payloads for project status, run inspect, run list, run resume,
  doctor, and evidence endpoints
- TUI worker behavior for doctor, inspect, and list-runs

No new runtime dependency is allowed.

## Test Strategy

Use test-first extraction guards:

1. Add import-boundary tests that assert `onecode.web.api` and
   `onecode.tui.app` source no longer import `onecode.cli`.
2. Add compatibility tests that assert the CLI-level exported functions are
   the same callable implementations as the new kernel services.
3. Run focused tests for CLI inspection, runner CLI, Web API, TUI closure, and
   source quality.
4. Run `bash scripts/verify.sh` before closure.

## Out Of Scope

- Splitting `build_parser`
- Splitting `main`
- Splitting training/model command families
- Refactoring Web routes or HTML console
- Changing public JSON schemas
- Removing the existing source-quality allowlist entries in this phase

## Follow-Up

After this phase, the next safe steps are:

1. Extract CLI parser construction by command family.
2. Split Web API request parsing/auth/workspace helpers from route handlers.
3. Remove source-quality allowlist entries only after specific long functions
   are actually below threshold.
