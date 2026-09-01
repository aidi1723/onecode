# OneCode Project Optimization Design

Date: 2026-07-03
Status: Approved for implementation

## Objective

Continue hardening the current OneCode Python project after the project-wide review fixes, with small changes that improve maintainability, diagnostics, and release records without expanding the current blast radius.

## Scope

This optimization is limited to the current `one code` project files:

- preserve the run evidence and shell projection contracts
- improve local API request-body diagnostics for invalid or oversized JSON bodies
- add focused regression coverage for the new run ID validation boundary
- keep verification scripts usable in an already-prepared virtual environment
- write a closure report that records changes, verification, and remaining risks

## Non-Goals

- no large `cli.py` or `web/api.py` file split
- no cleanup of the parent workspace or unrelated untracked files
- no production deployment changes
- no public API migration beyond clearer local Web API error types for malformed request bodies

## Architecture

The project remains a Python stdlib-first local agent kernel. New behavior should stay near the affected boundary:

- `onecode.kernel.run_id` remains the single run ID validation helper
- `onecode.web.api` owns HTTP request-body parsing and API error payload selection
- docs under `docs/` record the optimization and verification evidence

## Testing

Use focused `unittest` coverage before production edits, then run:

```bash
.venv/bin/python -m unittest tests.test_run_id tests.test_web_api -v
bash scripts/verify.sh
git diff --check -- src tests scripts docs
```

## Closure Criteria

The optimization is closed when:

- focused tests cover the new or clarified behavior
- the full verification script passes
- the closure report lists selected skills, changes, verification commands, and unresolved risks
- the diff is reviewable and confined to the current project
