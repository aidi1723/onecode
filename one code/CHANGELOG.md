# Changelog

## 2026-07-04 - Release Readiness and Source Quality Gates

This update continues the project optimization pass with release packaging,
CI, design-contract, and source-maintainability hardening. It preserves the
core runtime dependency boundary while adding stronger local and CI checks.

### Updated and Optimized

- Added package data for `onecode.tui` so `styles.tcss` is included in built
  wheels.
- Added `scripts/check_wheel_assets.py` to verify required wheel assets without
  hard-coding the package version.
- Expanded GitHub Actions verification to Python 3.11, 3.12, and 3.13.
- Added a CI wheel-build step that checks packaged TUI assets.
- Extended `DESIGN.md` from TUI-only scope to cover the local Web Gateway and
  shared terminal-style interface rules.
- Added `scripts/check_source_quality.py`, a no-third-party AST quality gate
  that blocks new unlisted long functions/classes while explicitly recording
  current large-module hotspots.
- Wired the source quality gate into `scripts/verify-core.sh` and
  `scripts/verify.sh`.
- Upgraded `scripts/release-audit.sh` from a passive file listing to a local
  release readiness checklist that runs whitespace, source-quality, wheel-build,
  and wheel-asset checks without publishing.
- Tightened release-audit cleanup so temporary wheel build directories are
  removed along with generated `build/` output before release candidate review.

### Regression Coverage

- Added packaging tests for TUI package data and wheel asset checker behavior.
- Added CI contract tests for the supported Python version matrix.
- Added design contract tests for TUI and Web Gateway coverage.
- Added source quality tests that accept the current hotspot allowlist and
  reject a synthetic new oversized function.
- Added release-audit script contract tests for non-publishing behavior and
  required readiness checks.
- Added a release-audit behavior test that executes the script with a fake
  Python build backend and verifies generated audit artifacts are cleaned.

### Documentation Added

- `docs/ONECODE_MAINTENANCE_LOG_2026-07-04.md`
- `docs/ONECODE_RELEASE_READINESS_CLOSURE_2026-07-04.md`

### Verification

Latest local verification for this update:

```text
bash scripts/verify-core.sh
Result: OK, 215 tests passed, doctor status ok

bash scripts/verify.sh
Result: OK, 740 tests passed, 1 skipped, doctor status ok

python3 -m pip wheel . -w /tmp/onecode-wheelhouse-check-2 --no-deps
python3 scripts/check_wheel_assets.py /tmp/onecode-wheelhouse-check-2
Result: wheel assets ok

bash scripts/release-audit.sh
Result: passed; publish action not performed
```

### Remaining Follow-Up

- Split `src/onecode/cli.py` by command family.
- Split `src/onecode/web/api.py` into request parsing, auth, routing, and
  response/projection responsibilities.
- Decide whether to add a dedicated release artifact directory for retained
  local wheels, separate from temporary audit builds.

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
