# OneCode vNext Maintenance Governance Design

Date: 2026-07-03
Status: Approved next-stage scope

## Objective

Create the next maintenance milestone after the July 3 hardening closure. The
milestone must first make the GitHub update path reviewable, then reduce the
largest Web API maintenance risk without changing external behavior.

## Scope

This milestone has two execution tracks.

### P0: GitHub Release-Line Governance

Goal: make future updates reviewable through a normal GitHub branch or pull
request workflow.

The current branch `feature/gateway-iching-rule-sync` has been pushed to
`origin`, but GitHub rejected PR creation to `main` with:

```text
The feature/gateway-iching-rule-sync branch has no history in common with main
```

The next stage must:

- verify local `main`, `origin/main`, and current branch ancestry
- identify whether the mismatch is caused by remote branch history, repository
  layout, or a previously rewritten synchronization path
- create a reviewable update path without force-pushing
- preserve the July 3 hardening commits and documentation
- leave unrelated parent-directory files untouched

Acceptable outcomes:

- a new branch based on `origin/main` containing the project changes and ready
  for PR, or
- a documented owner decision that the current branch is the new review line
  and `main` will be handled separately

### P1a: Web API Module Decomposition

Goal: reduce `src/onecode/web/api.py` complexity while preserving the local API
contract and all tests.

Current size:

- `src/onecode/web/api.py`: 1289 lines

The first decomposition must be conservative. It should move stable helper
responsibilities out of `api.py` before changing route structure.

Target modules:

- `src/onecode/web/request_body.py`
  - `JsonRequestBody`
  - request body size and JSON parsing helpers
  - compatibility wrappers needed by existing handlers
- `src/onecode/web/responses.py`
  - OpenAI-style JSON error payload helpers
  - JSON response serialization helpers where practical
- `src/onecode/web/auth.py`
  - bearer-token parsing and constant-time comparison helpers
  - loopback-only unauthenticated-mode checks
- `src/onecode/web/workspace.py`
  - workspace extraction and allowed-root validation helpers

The first pass should avoid moving all route handlers. Route extraction belongs
to a separate follow-up milestone after helper seams are stable and covered.

## Non-Goals

- Do not introduce a production gateway.
- Do not broaden Web API exposure beyond local/trusted loopback assumptions.
- Do not add executable skill adapters.
- Do not rewrite the HTTP server framework.
- Do not force-push or rewrite GitHub history.
- Do not include unrelated parent-directory files.
- Do not split `src/onecode/cli.py` in this milestone; it is the next
  maintenance track after Web API decomposition stabilizes.

## Design Constraints

- Preserve all current endpoint behavior, status codes, JSON fields, and
  OpenAI-compatible response shapes.
- Preserve `OneCodeRequestHandler._read_json()` compatibility for tests and
  existing callers.
- Keep all new modules stdlib-only.
- Use TDD for each extracted boundary:
  - write/import-level or behavior test first
  - verify red where the helper/module does not exist or is not wired
  - move minimal code
  - run targeted tests
  - run broader Web API tests
- Keep P0 Git operations reversible:
  - prefer new branches/worktrees
  - no destructive reset
  - no force-push

## P0 Design

P0 should start with a read-only ancestry audit:

```bash
git fetch origin
git branch -vv
git log --oneline --decorate --graph --max-count=20 --all
git merge-base main feature/gateway-iching-rule-sync
git merge-base origin/main feature/gateway-iching-rule-sync
```

If `origin/main` and the feature branch truly have unrelated histories, create
a clean sync branch from `origin/main` in an isolated worktree. Then copy only
project-root changes from the feature branch into that branch using Git-aware
commands such as `git checkout feature/gateway-iching-rule-sync -- "one code"`.

The sync branch must pass the same verification gate before PR creation:

```bash
git diff --check -- src tests docs README.md scripts CHANGELOG.md
bash scripts/verify.sh
```

If GitHub still rejects PR creation, document the exact reason in a maintenance
note and stop before any history rewrite.

## P1a Design

P1a should be implemented as helper extraction with behavior-preserving tests.

Extraction order:

1. `request_body.py`
2. `responses.py`
3. `auth.py`
4. `workspace.py`

This order starts with the most recently hardened helper surface and proceeds
to increasingly cross-cutting concerns.

Each extraction should:

- add a focused import/behavior test
- move code without changing signatures where possible
- keep `api.py` as the public route coordinator
- run the relevant `tests.test_web_api` focused tests
- commit after the extraction stays green

## Acceptance Criteria

P0 is accepted when:

- the GitHub review path decision is documented
- current branch status and remote status are clear
- no unrelated parent-directory files are included
- no destructive Git operation was used

P1a is accepted when:

- `api.py` is smaller and route behavior is unchanged
- extracted modules have focused tests or are covered through existing Web API
  tests
- `tests.test_web_api` passes
- `bash scripts/verify.sh` passes
- `CHANGELOG.md` or maintenance docs record the milestone update

## Verification Plan

Targeted checks:

```bash
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_read_json_result_reports_oversized_request_body -v
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_bearer_auth_uses_constant_time_compare -v
PYTHONPATH=src python3 -m unittest tests.test_web_api.OneCodeWebApiTests.test_workspace_from_request_rejects_workspace_outside_allowed_roots -v
```

Full checks:

```bash
git diff --check -- src tests docs README.md scripts CHANGELOG.md
bash scripts/verify.sh
```

## Rollback Plan

- If P0 sync work produces a bad branch, delete only that new branch/worktree.
- If P1a breaks Web API behavior, revert the latest extraction commit and keep
  the previous extracted modules intact only if tests prove they are safe.
- If final verification fails late, stop and fix the first failing behavior
  before continuing.

## Risks

- GitHub PR rejection may come from remote repository history rather than local
  branch ancestry; that needs remote-based verification before any workaround.
- `web/api.py` route methods are coupled to handler instance state, so moving
  route handlers too early could create behavior drift.
- Tests currently exercise many handler methods directly; compatibility
  wrappers should remain until route extraction is designed separately.
