# OneCode Maintenance Log

Date: 2026-07-03
Maintainer: Codex session
Branch: `feature/gateway-iching-rule-sync`

## Session Goal

Close the current project optimization cycle, document the completed hardening
work, record verification evidence, and prepare the GitHub repository update.

## Change Record

### Evidence and Skill Boundaries

- Added read-only skill context discovery and bounded public summaries.
- Added deterministic skill-selection evidence and compact shell/WAL aliases.
- Validated skill-selection schema at checkpoint, ledger, WAL, runner, and inspect boundaries.
- Recomputed and checked selection hashes to prevent content/hash drift.
- Preserved the rule that skills are reference evidence only, not execution authority.

### Runtime and Evidence Safety

- Centralized run ID validation for run/resume inputs.
- Rejected path traversal and separator-bearing run identifiers.
- Hardened WAL segment discovery to ignore non-numeric archive scratch files.
- Normalized invalid WAL JSON reporting to stable `invalid_global_wal_json`.
- Rejected raw or oversized skill context fields from bounded summaries.

### Numeric Contract Hardening

- Rejected Python booleans in integer-only fields across verifier, context,
  sandbox, model loop, execution guardrails, Web query parsing, DeepSeek
  distillation, YiZiJue token policies, runner budgets, task status, and
  delivery-decision formulas.
- Added regression tests to ensure booleans no longer enter integer formulas
  as `0` or `1`.

### Web API and Shell Contracts

- Added structured JSON request body parsing diagnostics.
- Preserved `_read_json()` compatibility while adding result-based error handling.
- Exposed compact skill state in shell projection schema version 2.
- Ensured inspect/list consumers receive bounded aliases instead of raw skill detail.

### Documentation

- Updated `README.md` verification notes and shell projection contract.
- Added `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`.
- Added this maintenance log.
- Added `docs/ONECODE_PROJECT_CLOSURE_HANDOFF_2026-07-03.md`.
- Added supporting implementation specs and plans under `docs/superpowers/`.

## Verification Log

Final verification gate:

```text
git diff --check -- src tests docs README.md scripts
Result: passed

bash scripts/verify.sh
Result: OK, 729 tests passed, 1 skipped, doctor status ok
```

Focused verification was also performed during the session for:

- skill context and selection evidence
- checkpoint, WAL, runner, inspect, and shell projection boundaries
- strict numeric contract rejection
- Web API JSON diagnostics
- run ID validation

## Publish Checklist

- [x] source changes scoped to project root
- [x] parent-directory unrelated files excluded from release scope
- [x] no new runtime third-party dependency introduced
- [x] Apache-2.0 license record preserved
- [x] tests and doctor gate passed
- [x] residual risks recorded
- [x] GitHub branch update requested by owner

## Follow-Up Queue

1. Decompose `src/onecode/web/api.py` into smaller modules.
2. Decompose `src/onecode/cli.py` by command family.
3. Define a separate executable skill-adapter design before adding runtime skill execution.
4. Add stable public shell projection fixtures for downstream adapters.

## Open Risks

- Current Web API is still local/trusted-loopback only.
- Large module decomposition remains future maintenance work.
- The branch should be reviewed before merging to `main` if the repository uses pull requests.

---

## vNext Maintenance Governance Update

Date: 2026-07-03
Maintainer: Codex session
Branch: `feature/vnext-maintenance-governance`
Parent milestone branch: `feature/gateway-iching-rule-sync`

### Session Goal

Begin the next maintenance milestone by making the GitHub release path
reviewable and reducing `src/onecode/web/api.py` responsibility in a
conservative, behavior-preserving way.

### Change Record

#### Release-Line Governance

- Added `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md`.
- Recorded the local merge base between `main` and
  `feature/gateway-iching-rule-sync`.
- Recorded that `origin/main` and `feature/gateway-iching-rule-sync` do not
  share a merge base in the current remote topology.
- Recorded the selected non-destructive path: keep the milestone branch as the
  historical record and create a sync branch from `origin/main` only if a PR is
  required.
- Avoided force-push, history rewrite, and unrelated parent-directory changes.

#### Web API Decomposition

- Added `src/onecode/web/request_body.py` for JSON body parsing, request size
  limits, and structured body parse results.
- Added `src/onecode/web/responses.py` for JSON error and response encoding
  helpers.
- Added `src/onecode/web/auth.py` for loopback and optional bearer-token
  authorization checks.
- Added `src/onecode/web/workspace.py` for workspace root parsing and path
  validation.
- Updated `src/onecode/web/api.py` to import the extracted helpers while
  preserving top-level compatibility names.
- Expanded `tests/test_web_api.py` with focused import and behavior checks for
  the extracted helper modules.

### Verification Log

Verification performed for this vNext update:

```text
git diff --check -- src tests docs README.md scripts CHANGELOG.md
Result: passed

PYTHONPATH=src python3 -m unittest tests.test_web_api -v
Result: OK, 62 tests passed

PYTHONPATH=src bash scripts/verify.sh
Result: OK, 733 tests passed, 1 skipped, doctor status ok
```

The worktree uses the existing shared virtual environment through a local
`.venv` symlink. In this worktree, `PYTHONPATH=src` is required for the full
verification command so tests import the checked-out source tree instead of any
stale editable install in that shared environment.

### Publish Checklist

- [x] release-line audit documented
- [x] helper extraction scoped to Web API internals
- [x] `onecode.web.api` compatibility imports preserved
- [x] focused Web API tests passed
- [x] full verification and doctor gate passed
- [x] no runtime third-party dependency introduced
- [x] no destructive Git operation used

### Follow-Up Queue

1. If GitHub PR creation still rejects the milestone branch, create a
   non-destructive sync branch from `origin/main` and replay only project-root
   changes.
2. Continue route-level `web/api.py` decomposition after the helper boundary is
   stable.
3. Split `src/onecode/cli.py` by command family in a separate milestone.
4. Define the executable skill-adapter permission model before changing skills
   from read-only evidence into runtime execution.

### Open Risks

- Remote `origin/main` is still divergent from the local milestone line.
- Web API remains intentionally scoped to local/trusted-loopback usage.
- Additional decomposition should remain test-first because `web/api.py` still
  coordinates routes, projections, and local process behavior.

---

## Release Sync Decomposition Update

Date: 2026-07-04
Maintainer: Codex session
Branch: `feature/vnext-release-sync-2026-07-04`
Base: `origin/main`

### Session Goal

Complete the next stage by moving vNext maintenance work onto a GitHub-friendly
sync branch, continuing conservative decomposition, adding public contract
fixtures, and documenting the executable skill-adapter permission boundary.

### Change Record

#### Release-Line Sync

- Created `feature/vnext-release-sync-2026-07-04` from `origin/main`.
- Replayed the prior vNext maintenance governance commits onto the sync branch.
- Resolved the root-layout difference by applying path-stripped patch commits.
- Preserved Web request-body error behavior after sync conflict resolution.

#### Web API Decomposition

- Added `src/onecode/web/chat.py`.
- Added `src/onecode/web/gateway_console.py`.
- Kept `src/onecode/web/api.py` as the HTTP route coordinator.
- Preserved compatibility imports for chat helpers from `onecode.web.api`.

#### CLI Decomposition

- Added `src/onecode/cli_inspect.py`.
- Moved inspect/list-runs/global-WAL projection helpers out of `src/onecode/cli.py`.
- Preserved compatibility imports for `inspect_run`, `list_runs`, and
  `delivery_summary` from `onecode.cli`.

#### Public Contract Fixtures

- Added `tests/fixtures/contracts/shell_projection_schema_v1.json`.
- Added `tests/fixtures/contracts/chat_completion_response.json`.
- Added `tests/test_contract_fixtures.py` to compare runtime payloads against
  the public fixtures.

#### Skill Adapter Boundary

- Added `docs/ONECODE_EXECUTABLE_SKILL_ADAPTER_PERMISSION_MODEL_2026-07-04.md`.
- Recorded adapter identity, approval gates, path scope, network scope,
  provenance, denial behavior, and rollback requirements.
- Reconfirmed that skills remain read-only evidence until a future
  implementation adds tested runtime gates.

#### TUI Repair Evidence Preservation

- Restored repaired-run details in TUI task output when shell projection compact
  messages are preferred.
- Kept shell projection as the primary one-line summary while appending the
  existing `repair: attempts=... initial=...` evidence line.
- Avoided changing the public shell projection schema or fixtures for a
  presentation-layer regression.

### Verification Log

Focused verification performed during the stage:

```text
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
Result: OK, 58 tests passed

PYTHONPATH=src python3 -m unittest tests.test_inspect_cli tests.test_list_runs_cli -v
Result: OK, 39 tests passed

PYTHONPATH=src python3 -m unittest tests.test_contract_fixtures -v
Result: OK, 2 tests passed
```

During final full verification, the first install-enabled gate was blocked by
the host Python environment:

```text
PYTHONPATH=src bash scripts/verify.sh
Result: blocked by Homebrew PEP 668 externally managed environment

PYTHONPATH=src bash scripts/verify.sh --skip-install
Result: blocked because system Python lacked textual
```

Final verification used the existing project virtual environment while keeping
imports pointed at the sync worktree:

```text
git diff --check -- src tests docs README.md scripts CHANGELOG.md
Result: passed

PYTHON=/Users/aidi/大字典/one\ code/.venv/bin/python PYTHONPATH=src python -m unittest tests.test_tui_model_closure -v
Result: OK, 7 tests passed

PYTHON=/Users/aidi/大字典/one\ code/.venv/bin/python PYTHONPATH=src python -m unittest tests.test_web_api tests.test_inspect_cli tests.test_list_runs_cli tests.test_contract_fixtures -v
Result: OK, 99 tests passed

PYTHON=/Users/aidi/大字典/one\ code/.venv/bin/python PYTHONPATH=src bash scripts/verify.sh --skip-install
Result: OK, 658 tests passed, doctor status ok
```

### Publish Checklist

- [x] sync branch based on `origin/main`
- [x] prior vNext maintenance work replayed without force-push
- [x] Web API decomposition continued at helper boundaries
- [x] CLI inspect/list-runs decomposition completed for this stage
- [x] public contract fixtures added and verified
- [x] executable skill adapter permission model documented
- [x] TUI repair evidence regression fixed
- [x] focused and full verification gates passed
- [x] GitHub update notes recorded in `CHANGELOG.md`

### Follow-Up Queue

1. Continue Web route-family extraction after this sync branch is reviewed.
2. Continue CLI command-family extraction for run-plan repair and training-data
   commands.
3. Convert the executable skill adapter permission model into tests before
   adding runtime execution.

### Open Risks

- The sync branch is intentionally review-focused and should be merged through
  GitHub review rather than force-pushed into an existing milestone branch.
- Executable skill adapters are still design-only.
