# Changelog

## 2026-07-03 - vNext Maintenance Governance

This update starts the next maintenance milestone after the project-wide
closure pass. It focuses on making the GitHub release path reviewable and
beginning conservative Web API decomposition without changing public behavior.

### Updated and Optimized

- Added a release-line audit for `feature/gateway-iching-rule-sync`, including
  local and remote merge-base evidence, current branch tracking state, and the
  non-destructive GitHub review path.
- Documented that the GitHub PR limitation is caused by remote release-line
  divergence between `origin/main` and the milestone branch, not by a code or
  verification failure.
- Extracted Web API request-body parsing into `onecode.web.request_body`.
- Extracted Web API JSON response helpers into `onecode.web.responses`.
- Extracted loopback and token authorization checks into `onecode.web.auth`.
- Extracted workspace-root parsing and path validation into
  `onecode.web.workspace`.
- Preserved compatibility imports from `onecode.web.api` so existing callers
  can continue importing the helper names from the original module.
- Added focused regression coverage for the extracted helper modules while
  keeping `src/onecode/web/api.py` as the route coordinator.

### Documentation Added

- `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-03.md`
- `docs/superpowers/specs/2026-07-03-onecode-vnext-maintenance-governance-design.md`
- `docs/superpowers/plans/2026-07-03-onecode-vnext-maintenance-governance.md`

### Verification

Final local verification for this update:

```text
git diff --check -- src tests docs README.md scripts CHANGELOG.md
Result: passed

PYTHONPATH=src python3 -m unittest tests.test_web_api -v
Result: OK, 62 tests passed

PYTHONPATH=src bash scripts/verify.sh
Result: OK, 733 tests passed, 1 skipped, doctor status ok
```

### Remaining Follow-Up

- Create a non-destructive sync branch from `origin/main` if GitHub still
  rejects a PR directly from `feature/gateway-iching-rule-sync`.
- Continue decomposing `src/onecode/web/api.py` only at stable helper or route
  boundaries with focused regression coverage.
- Decompose `src/onecode/cli.py` by command family in a separate milestone.
- Keep skill integration read-only until executable skill adapters have an
  explicit permission model, provenance contract, and approval boundary.

## 2026-07-03 - Evidence Boundary Hardening and Closure

This update closes the current OneCode project-wide review and optimization
cycle. It focuses on evidence integrity, read-only skill integration, safer
runtime inputs, stronger regression coverage, and clearer maintenance records.

### Updated and Optimized

- Added read-only skill context discovery with bounded public summaries.
- Added deterministic skill-selection evidence for run results, ledgers,
  manifests, checkpoints, global WAL records, and shell projections.
- Hardened `skill_selection` schema validation against forbidden fields,
  count mismatches, hash mismatches, invalid metadata, and oversized evidence.
- Added centralized run ID validation to reject traversal, separators, empty
  IDs, non-ASCII IDs, and oversized IDs.
- Hardened global WAL discovery and validation, including stable
  `invalid_global_wal_json` reporting and filtering for non-numeric archive
  scratch files.
- Rejected Python boolean values in integer-only runtime and evidence
  contracts across verifier, context, sandbox, runner, model loop, execution
  guardrails, DeepSeek distillation, YiZiJue policies, and Web query parsing.
- Improved local Web API JSON request diagnostics for oversized bodies,
  invalid `Content-Length`, invalid JSON, and non-object JSON payloads.
- Updated shell projection schema to version 2 with compact skill-state aliases
  for shell and adapter consumers.
- Expanded regression coverage for skill context, run IDs, checkpoint/WAL
  validation, runner behavior, inspect flows, Web API handling, shell
  projection, model-loop limits, and numeric contract boundaries.
- Added closure and maintenance documentation for future review and handoff.

### Documentation Added

- `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`
- `docs/ONECODE_PROJECT_CLOSURE_HANDOFF_2026-07-03.md`
- `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`
- `docs/superpowers/plans/2026-07-03-*.md`
- `docs/superpowers/specs/2026-07-03-*.md`

### Verification

Final local verification for this update:

```text
git diff --check -- src tests docs README.md scripts
Result: passed

bash scripts/verify.sh
Result: OK, 729 tests passed, 1 skipped, doctor status ok
```

### Remaining Follow-Up

- Split `src/onecode/cli.py` by command family in a focused refactor.
- Split `src/onecode/web/api.py` by request parsing, auth, routes, and
  projection responsibilities.
- Keep the Web API scoped as a local/trusted-loopback bridge unless a separate
  production gateway is designed.
- Keep skill integration read-only until executable skill adapters have a
  separate permission model and approval boundary.

## 2026-07-02

### Fixed

- Prevented trace write-latency patching from mutating payload values that
  happen to equal the latency placeholder.
- Fixed aggregate trace gap metrics so cross-type aggregate windows are
  evaluated in timestamp order instead of file flush order.

### Tests

- Added regression coverage for payload placeholder collisions in
  `write_trace_event`.
- Added regression coverage for cross-type aggregate gap detection in
  `trace_evidence_metrics`.
