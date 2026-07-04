# OneCode Release Sync and Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the release-sync maintenance stage on a branch based on `origin/main` while reducing Web/API and CLI module size with behavior-preserving helper extraction.

**Architecture:** Keep `api.py` and `cli.py` as coordinators. Extract stable helper families into focused modules and import them back for compatibility. Add fixture-backed contract tests before relying on the new boundaries.

**Tech Stack:** Python stdlib, `unittest`, existing OneCode CLI/Web modules, Git worktree branch `feature/vnext-release-sync-2026-07-04`.

---

## File Structure

- Create: `src/onecode/web/chat.py`
- Create: `src/onecode/web/gateway_console.py`
- Create: `src/onecode/cli_inspect.py`
- Create: `tests/test_contract_fixtures.py`
- Create: `tests/fixtures/contracts/shell_projection_schema_v1.json`
- Create: `tests/fixtures/contracts/chat_completion_response.json`
- Create: `docs/ONECODE_EXECUTABLE_SKILL_ADAPTER_PERMISSION_MODEL_2026-07-04.md`
- Modify: `src/onecode/web/api.py`
- Modify: `src/onecode/cli.py`
- Modify: `tests/test_web_api.py`
- Modify: `tests/test_inspect_cli.py`
- Modify: `CHANGELOG.md`
- Modify: `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`

## Task 1: Web Chat and Console Extraction

- [x] Add failing import tests for `onecode.web.chat` and `onecode.web.gateway_console`.
- [x] Run the focused tests and confirm they fail because the modules do not exist.
- [x] Move chat helper functions and gateway console HTML into the new modules.
- [x] Import moved names back into `onecode.web.api` for compatibility.
- [x] Run focused Web API verification.
- [x] Commit with message `refactor: extract web chat and console helpers`.

## Task 2: CLI Inspect Extraction

- [x] Add failing import tests for `onecode.cli_inspect.inspect_run`, `list_runs`,
  `read_global_wal_segment`, and `delivery_summary`.
- [x] Run focused inspect/list-runs tests and confirm the new module import fails.
- [x] Move inspect/list-runs/WAL helper functions into `src/onecode/cli_inspect.py`.
- [x] Import moved names back into `onecode.cli` for compatibility.
- [x] Run focused inspect/list-runs verification.
- [x] Commit with message `refactor: extract cli inspect helpers`.

## Task 3: Public Contract Fixtures

- [x] Add `tests/test_contract_fixtures.py` with tests that load contract fixtures
  and compare them to generated runtime payloads.
- [x] Run the new test and confirm it fails because fixture files do not exist.
- [x] Add shell projection schema and chat completion response fixtures.
- [x] Run contract fixture verification.
- [x] Commit with message `test: add public contract fixtures`.

## Task 4: Executable Skill Adapter Permission Model

- [x] Create `docs/ONECODE_EXECUTABLE_SKILL_ADAPTER_PERMISSION_MODEL_2026-07-04.md`.
- [x] Include adapter identity, approval gates, path scope, network scope,
  provenance, audit evidence, rollback, and denial behavior.
- [x] Run `rg -n "adapter identity|approval|path scope|network scope|provenance|rollback|denial" docs/ONECODE_EXECUTABLE_SKILL_ADAPTER_PERMISSION_MODEL_2026-07-04.md`.
- [x] Commit with message `docs: close release sync decomposition stage`.

## Task 5: Release Records and Verification

- [x] Update `CHANGELOG.md` with this release-sync/decomposition stage.
- [x] Update `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md` with 2026-07-04 notes.
- [x] Run `git diff --check -- src tests docs README.md scripts CHANGELOG.md`.
- [x] Run focused TUI, Web API, inspect/list-runs, and contract fixture verification.
- [x] Run `PYTHON=/Users/aidi/大字典/one\ code/.venv/bin/python PYTHONPATH=src bash scripts/verify.sh --skip-install`.
- [x] Commit with message `docs: close release sync decomposition stage`.
- [x] Push `feature/vnext-release-sync-2026-07-04`.

## Closure Status

This stage is closed on branch `feature/vnext-release-sync-2026-07-04`.
Final verification passed with 658 tests and doctor status `ok`. Remaining
items are recorded as next-stage follow-up work in `CHANGELOG.md` and
`docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`.
