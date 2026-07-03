# OneCode Release Sync and Decomposition Design

Date: 2026-07-04
Branch: `feature/vnext-release-sync-2026-07-04`

## Goal

Complete the next maintenance stage on a branch based on `origin/main`, preserve
the prior vNext maintenance governance work, and reduce the largest Web/API and
CLI maintenance hotspots without changing public behavior.

## Release-Line Strategy

The previous milestone branch is preserved as historical evidence. This stage
uses a new sync branch from `origin/main` and replays only reviewed project
changes. No force-push, history rewrite, or broad parent-directory sync is part
of this design.

## Web API Decomposition

`src/onecode/web/api.py` remains the HTTP route coordinator. Stable helper
logic moves into focused modules:

- `onecode.web.chat`: chat request classification, direct provider fallback,
  chat payload construction, run-result formatting, and light task execution.
- `onecode.web.gateway_console`: static gateway console HTML.

The existing `onecode.web.api` import surface remains compatible by re-exporting
the moved helper names at module top level.

## CLI Decomposition

`src/onecode/cli.py` remains the argparse command coordinator. Inspect,
list-runs, global WAL reading, checkpoint asset projection, and delivery
summary helpers move into `src/onecode/cli_inspect.py`.

The existing `onecode.cli` import surface remains compatible by importing the
moved helper names back into `cli.py`.

## Public Contract Fixtures

Stable JSON fixtures are added under `tests/fixtures/contracts/` for:

- shell projection schema
- chat completion response envelope

Tests compare generated runtime payloads to these fixtures so future refactors
cannot silently change public contracts.

## Executable Skill Adapter Boundary

Skill integration remains read-only in runtime. A new permission model document
defines the requirements that must exist before any executable skill adapter is
implemented: explicit adapter identity, approval gates, path/network scope,
provenance, audit evidence, rollback notes, and denial behavior.

## Verification

Required verification for this stage:

- focused Web API tests
- focused CLI inspect/list-runs tests
- contract fixture tests
- `git diff --check`
- full `scripts/verify.sh`

## Risks

- The sync branch starts from a newer `origin/main`; conflicts must be resolved
  by preserving current main behavior unless the vNext tests prove a regression.
- Decomposition is intentionally conservative. Route reshaping or CLI command
  UX changes are out of scope.
- Executable skill adapters remain documentation-only until a future stage adds
  implementation and approval-backed tests.
