# Changelog

## 0.8.0 - 2026-07-10 - Canonical I Ching Runtime and Evidence Cutover

### Added

- Added immutable `onecode-iching-v1` and `onecode-iching-v2` trigram schemas.
- Added canonical bottom-to-top trigram line invariants with `LI = 101` and
  `XUN = 110` in the v2 schema.
- Added pure trigram and 64-state conversion helpers so historical v1 evidence
  can be interpreted without rewriting checkpoint, ledger, WAL, or training
  artifacts.
- Added a canonical encoding certificate covering all eight line patterns and
  the qian/kun, zhen/xun, kan/li, and dui/gen complement pairs.
- Added read-only evidence migration audits that preserve source files and
  hashes while reporting v1-to-v2 status interpretations and affected trigrams.
- Added auditable line-position, centrality, correspondence, adjacency,
  trigram-virtue, opposite-hexagram, and inverse-hexagram profiles.

### Compatibility

- Activated `onecode-iching-v2` for all new runtime classifications and newly
  written checkpoint, manifest, ledger, WAL, profile, and shell evidence.
- Preserved deterministic legacy reads: evidence without `rule_schema` is
  interpreted as `onecode-iching-v1` and is never rewritten in place.
- Added `rule_schema` to profile identity and compact evidence. Global WAL uses
  the compact alias `rsv`; shell projections expose the full field.
- Bumped the shell projection schema from version 2 to version 3.
- Kept LogosGate, PathGuard, approvals, verifier, sandbox, and physical evidence
  dominant. New I Ching profiles are descriptive and do not alter `transition()`
  or dispatch authority.

### Verification

- Added exhaustive v1/v2 trigram and 64-state round-trip regression coverage.
- Compared all 64 states by trigram name and found no semantic action changes
  and no `stop`-to-`continue` relaxation after the canonical cutover.
- Updated canonical runtime examples: sovereignty breach `40`, valid project
  context `49`, provider failure `42`, timeout `17`, and cooldown `39`.

### CLI Configuration Command Split Follow-Up

- Added `onecode.cli_commands.configuration` for
  `list-verifier-presets`, `init-verifier-policy`, and the nested `config`
  command family.
- Preserved the exact top-level and nested argparse contracts, JSON output,
  parser-error conversion, service exceptions, and exit codes.
- Kept verifier-policy path validation and writing in the verifier service and
  model configuration, permissions, secret masking, and discovery networking
  in the model-config service.
- Added direct mocked dispatch tests, temporary-home integration coverage,
  dependency boundaries, reverse-dependency checks, secret-output checks, and
  structural reduction assertions.
- Kept the I Ching transition, dispatch, yin-yang, and five-element authority
  unchanged.

### Training and Benchmark Projection Follow-Up

- Added record-level `rule_schema` to gateway training JSONL, YiZiJue-LM
  corpus/evaluation/state rows, prediction files, LLaMA-Factory exports,
  Axolotl exports, benchmark reports, and A/B reports.
- Preserved the strict Action JSON fields unchanged; schema metadata remains in
  the persisted record envelope and does not become a model decision variable.
- Kept missing historical schema metadata as v1 and made current generators
  emit v2 explicitly.
- Added name-preserving v1-to-v2 profile interpretation before deriving
  trigram, five-element, yin/yang pressure, and balance facts. Historical v1 Li
  states therefore remain fire and historical v1 Xun states remain wood.
- Added tests proving exported yin/yang, five-element, balance, transition, and
  dispatch facts remain equal to the existing kernel profile.
- Added the phase closure record at
  `docs/ONECODE_TRAINING_BENCHMARK_RULE_SCHEMA_CLOSURE_2026-07-10.md`.

### Runtime Balance Mutation Evidence Follow-Up

- Added pure runtime `balance_mutation` evidence describing the existing
  `raw_status_code -> balanced_status_code` result through changed yin/yang
  lines and earth/human/heaven bands.
- Added before/after yin-yang balance, pressure, elements, five-element
  relation/modulation, transition, and dispatch facts sourced from the existing
  kernel profiles.
- Kept static `cross_cutting_profile()["mutation"]` as `null`, preserving profile
  hashes and registry identity.
- Added bounded result, checkpoint, manifest, ledger, and WAL summaries. WAL
  uses the fixed four-scalar `bm` tuple to remain within size budgets.
- Did not add mutation evidence to paths that never computed a raw-to-balanced
  state pair; no evidence is fabricated.

### Mutation Evidence Integrity and Shell v4 Follow-Up

- Added full read-side validation that recomputes each persisted
  `balance_mutation` certificate with the existing kernel and rejects tampered
  line, element, transition, dispatch, or summary facts.
- Added checkpoint/manifest summary consistency checks and stable corruption
  reasons without rewriting historical evidence.
- Added strict decoding for the compact global WAL `bm` tuple and restored its
  named mutation summary during WAL-only inspection.
- Bumped the shell projection schema from version 3 to version 4 and added the
  read-only `balance_state` section for full and WAL-backed evidence.
- Kept `balance_state` outside severity, next-action, control, delivery, resume,
  transition, and dispatch decisions.
- Added the phase closure record at
  `docs/ONECODE_MUTATION_EVIDENCE_INTEGRITY_SHELL_V4_CLOSURE_2026-07-10.md`.

### Shell v4 Public Contract Follow-Up

- Added versioned, wheel-distributed Shell v4 schema and six projection-case
  fixtures under `onecode.contracts`.
- Added fresh-decoding public loaders using `importlib.resources` without
  importing fixtures into production shell decision paths.
- Changed Python, CLI, direct Web, and HTTP schema tests from partial assertions
  to exact equality against one public fixture.
- Covered completed, denied, halted/resumable, corrupt, WAL-only, and legacy
  missing-field projections with exact-output fixtures.
- Proved legacy missing schema remains v1, WAL aliases remain bounded, and
  descriptive balance/evidence/skill fields do not alter shell authority.
- Added the phase closure record at
  `docs/ONECODE_SHELL_V4_PUBLIC_CONTRACT_CLOSURE_2026-07-10.md`.

### CLI Read-Only Command Split Follow-Up

- Extracted parser registration and dispatch for `inspect`, `list-runs`,
  `doctor`, `math-audit`, and `shell-schema` into
  `onecode.cli_commands.read_only`.
- Preserved `onecode.cli.build_parser()` and `onecode.cli.main()` as public
  compatibility entry points.
- Added structural parser-contract, exact Shell v4 output, unknown-command,
  import-boundary, and `main()` reduction tests.
- Reduced `cli.main()` from 581 to 500 lines without expanding into write,
  model, training, verifier, sandbox, Web, or TUI command paths.
- Kept read-only output construction and exit-code rules unchanged and added
  the phase closure record at
  `docs/ONECODE_CLI_READ_ONLY_COMMAND_SPLIT_CLOSURE_2026-07-10.md`.

### CLI Local Interface Command Split Follow-Up

- Extracted parser registration and lazy dispatch for `serve`, `shell`,
  `shell-status`, and `tui` into `onecode.cli_commands.local_interfaces`.
- Preserved all local host/port, workspace, credential, browser, provider, and
  unauthenticated-loopback parser contracts.
- Added fake-module dispatch tests that verify calls, environment mutation,
  JSON, errors, and exit codes without starting Web, TUI, MongoDB, LibreChat, or
  a browser.
- Added lazy-import, reverse-dependency, and structural reduction tests.
- Reduced `cli.main()` from 500 to 472 lines and `build_parser()` to 214 lines
  without entering runner, model, training, verifier, or sandbox paths.
- Added the phase closure record at
  `docs/ONECODE_CLI_LOCAL_INTERFACE_COMMAND_SPLIT_CLOSURE_2026-07-10.md`.

## 2026-07-05 - Run Inspection Hotspot Split

This update completes the focused follow-up from the CLI service decoupling
phase. It keeps the public run-inspection behavior stable while removing
`src/onecode/kernel/run_inspection.py:inspect_run` from the source-quality
hotspot allowlist.

### Updated and Optimized

- Split `inspect_run` into smaller kernel-owned helpers for corrupt payloads,
  run document validation, trace metrics, workspace-root resolution, and final
  inspection summary projection.
- Removed `src/onecode/kernel/run_inspection.py:inspect_run` from
  `scripts/check_source_quality.py`'s explicit long-function allowlist.
- Kept CLI/Web/list-runs behavior unchanged through the existing
  `onecode.kernel.run_inspection` public service surface.

### Regression Coverage

- Added a source-quality regression test that prevents
  `src/onecode/kernel/run_inspection.py:inspect_run` from being re-added to the
  hotspot allowlist.
- Re-ran focused source-quality, inspect CLI, list-runs CLI, and Web API
  regression coverage for the shared inspection surface.

### Documentation Added

- `docs/ONECODE_MAINTENANCE_LOG_2026-07-05.md`
- `docs/ONECODE_RUN_INSPECTION_HOTSPOT_CLOSURE_2026-07-05.md`

### Verification

Latest local verification for this update:

```text
.venv/bin/python -m unittest tests.test_source_quality.SourceQualityTests.test_run_inspection_inspect_run_is_not_allowlisted_as_hotspot -v
Result: OK, 1 test passed

.venv/bin/python scripts/check_source_quality.py src
Result: source quality ok

.venv/bin/python -m unittest tests.test_source_quality tests.test_inspect_cli tests.test_list_runs_cli tests.test_web_api -v
Result: OK, 99 tests passed, 9 skipped

git diff --check -- .
Result: passed

bash scripts/verify.sh
Result: OK, 743 tests passed, 1 skipped, doctor status ok
```

### Remaining Follow-Up

- Split `src/onecode/cli.py` parser construction and command handlers by
  command family.
- Split `src/onecode/web/api.py` request parsing, auth, workspace, route
  handlers, and HTML console responsibilities.
- Add stable public shell projection fixtures for downstream adapters.

## 2026-07-04 - CLI Service Decoupling Phase

This update starts the next maintenance phase after release-readiness closure.
It reduces `onecode.cli` coupling by moving shared doctor and run-inspection
behavior into kernel-owned service modules while preserving existing CLI, Web,
and TUI behavior.

### Updated and Optimized

- Added `onecode.kernel.diagnostics` for shared `run_doctor` behavior.
- Added `onecode.kernel.run_inspection` for shared `inspect_run`,
  `list_runs`, delivery summary, verifier evidence, task-resume evidence, and
  WAL-backed run inspection helpers.
- Kept compatibility exports in `onecode.cli` so existing callers can continue
  importing `run_doctor`, `inspect_run`, `list_runs`, and `delivery_summary`.
- Updated Web API and TUI worker imports so non-CLI surfaces no longer depend
  on `onecode.cli` for shared runtime services.
- Migrated the source-quality allowlist entry for `inspect_run` from
  `src/onecode/cli.py` to `src/onecode/kernel/run_inspection.py`.

### Regression Coverage

- Added an import-boundary test that blocks `src/onecode/web/api.py` and
  `src/onecode/tui/app.py` from importing shared services from `onecode.cli`.
- Added a compatibility-export test that verifies CLI-level names still point
  to the new kernel service implementations.
- Added design and implementation planning records for this phase:
  `docs/superpowers/specs/2026-07-04-onecode-cli-service-decoupling-design.md`
  and `docs/superpowers/plans/2026-07-04-onecode-cli-service-decoupling.md`.
- Follow-up completed on 2026-07-05: `inspect_run` is now split below the
  source-quality threshold and is no longer allowlisted as a hotspot.

### Verification

Latest local verification for this phase:

```text
.venv/bin/python scripts/check_source_quality.py src
Result: source quality ok

.venv/bin/python -m unittest tests.test_source_quality tests.test_doctor_cli tests.test_inspect_cli tests.test_list_runs_cli tests.test_run_plan_cli tests.test_web_api tests.test_tui_model_closure -v
Result: OK, 143 tests passed, 9 skipped

bash scripts/verify.sh
Result: OK, 742 tests passed, 1 skipped, doctor status ok
```

### Remaining Follow-Up

- Split `src/onecode/cli.py` parser construction and command handlers by
  command family.
- Split `src/onecode/web/api.py` request parsing, auth, workspace, route
  handlers, and HTML console responsibilities.

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
