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
