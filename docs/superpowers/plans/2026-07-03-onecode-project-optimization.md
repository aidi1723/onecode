# OneCode Project Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve OneCode diagnostics and maintenance records after the project-wide review fixes.

**Architecture:** Keep changes at existing boundaries. Add run ID validation coverage in tests, improve Web API request-body parsing diagnostics in `onecode.web.api`, and record the work in a closure report.

**Tech Stack:** Python 3.11+, stdlib `unittest`, existing shell verification scripts, Markdown docs.

---

## File Map

- Create: `tests/test_run_id.py`
- Modify: `tests/test_web_api.py`
- Modify: `src/onecode/web/api.py`
- Modify: `README.md`
- Create: `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`

## Task 1: Add Run ID Boundary Coverage

- [x] Write focused tests in `tests/test_run_id.py` covering accepted IDs, rejected path separators, rejected traversal-like strings, rejected non-ASCII strings, empty values, and length limits.
- [x] Run `.venv/bin/python -m unittest tests.test_run_id -v`.
- [x] Keep production code unchanged if the current helper already satisfies the contract.

## Task 2: Improve Request Body Error Diagnostics

- [x] Add focused tests in `tests/test_web_api.py` that exercise HTTP handler behavior for oversized bodies and invalid `Content-Length`.
- [x] Verify the tests fail against the current generic `invalid_json` response.
- [x] Update `src/onecode/web/api.py` so request parsing returns a structured error reason and handlers return clearer error types such as `request_too_large` and `invalid_request_body`.
- [x] Run `.venv/bin/python -m unittest tests.test_web_api -v`.

## Task 3: Update User-Facing Verification Notes

- [x] Update `README.md` to mention that `scripts/verify.sh` skips editable install when `onecode` and `textual` are already importable.
- [x] Keep command examples unchanged.

## Task 4: Write Closure Report

- [x] Create `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`.
- [x] Record selected skill routing, repository map, changes, tests, verification results, and unresolved risks.

## Task 5: Final Verification

- [x] Run focused tests for affected files.
- [x] Run `bash scripts/verify.sh`.
- [x] Run `git diff --check -- src tests scripts docs`.
- [x] Review `git diff --stat -- src tests scripts docs`.
