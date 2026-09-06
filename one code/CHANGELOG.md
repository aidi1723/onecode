# Changelog

## v0.4.0 - 2026-09-06 - I Ching Six-Yao Extension & Complete Repository History Publication

### Added - I Ching Six-Yao System

- **Earthly Branches (Najia) Mapping** (`hexagram_earthly_branches`): Assigns one
  of the 12 earthly branches (子丑寅卯辰巳午未申酉戌亥) to each of the six lines
  in all 64 hexagrams, following traditional Najia attribution rules. Enables
  time analysis, directional analysis, and seasonal weight calculations.
- **Palace Attribution Algorithm** (`palace_attribution`): Implements the
  world-response positioning method (安世应法) to determine palace membership,
  world-line position, response-line position, and hexagram type (pure, first,
  traveling, returning, roaming, error) for each hexagram. Establishes the
  eight-palace hexagram order system.
- **Six Relatives Relationship Network** (`six_relatives_profile`): Based on
  palace five-element, assigns six-relative relationship (兄弟/父母/子孙/妻财/官鬼)
  to each line. Provides semantic-level relationship modeling similar to the
  "useful god/source god/taboo god/enemy god" system.

### Added - Five Elements Modulation

- **Same-Element Transition Reason**: Completed I Ching rule coverage by adding
  explicit reasoning for same-element state transitions (maintain/stabilize).
- **Generation Cycle Modulations**: Added three modulation types in the
  generation cycle—refine (精炼), forge (锻造), temper (淬炼)—to model nuanced
  nurturing relationships beyond simple generation.

### Changed - Repository History

- **Force-pushed complete development history** (288 commits starting from
  2026-05-27) to replace the previous selective open-source release (44 commits
  starting from 2026-06-01) on `origin/main`.
- Unified local and remote history to preserve full project evolution, including
  all I Ching formula updates and core kernel development.

### Documentation

- Added comprehensive I Ching six-yao system research report
  (`docs/易经六爻系统调研_2026-09-03.md`).
- Added implementation plan for six-yao extension Phase 1
  (`docs/易经六爻扩展实施计划_2026-09-03.md`).
- Added feature demonstration with concrete hexagram examples
  (`docs/易经六爻扩展功能演示_2026-09-03.md`).
- Added comprehensive test report covering 99 test cases, all passing
  (`docs/易经六爻扩展测试报告_2026-09-03.md`).

### Verification

- I Ching kernel unit tests: 79 passed (0.031s).
- Mathematical audit: 12 checks passed.
- Core functionality checks: 8 passed.
- All 64 hexagrams verified for earthly branches, palace attribution, and
  six-relatives profiling.
- Pure hexagrams (乾坤震巽坎离艮兑) verified against traditional formulas.

### Publication

- Repository history unified on 2026-09-06.
- Complete development history now available at https://github.com/aidi1723/onecode.
- Feature branch `feature/iching-contrary-inverse-hexagram` pushed and
  subsequently merged into `main`.

---

## Unreleased - 2026-07-16 - LibreChat Execution Reliability

### Changed

- Hardened deterministic task classification with stable reason codes for common
  natural-language project phrases.
- Enforced strict workspace selection for non-chat shell tasks and required
  explicit approval before mutating resume paths.
- Added redacted pending-plan listing and approval decision surfaces on the Web
  API without exposing sensitive plan bodies.
- Published shell projection **v5** with nested `approval_state` (`required`,
  `plan_id`, `status`) while preserving prior control-state fields.
- Aligned shell status semantics and launcher exports for Console consumption.
- Documented the reliability design, implementation plan, closure, and GitHub
  publication record under `docs/`.

### Verification

- Targeted reliability unit tests: 119 passed
  (`task_classification`, `approval_plans`, `web_api`, `shell_projection`).
- Publication-prep source-quality and whitespace checks on a clean worktree.
- Privacy scan of the publication delta: local absolute paths redacted; no real
  secrets found.
- LibreChat Console and proxy work remains in a separate local repository and
  is not part of this GitHub update.

### Publication

- Fast-forward only to `origin/feature/gateway-iching-rule-sync`.
- Does not update unrelated `origin/main`, create a tag, or publish packages.
- See `docs/ONECODE_EXECUTION_RELIABILITY_GITHUB_PUBLICATION_2026-07-16.md`.

## Unreleased - 2026-07-16 - vNext Maintenance Governance

### Changed

- Extracted request-body parsing, JSON response encoding, bearer authentication,
  and workspace-root validation from `src/onecode/web/api.py` into four focused
  stdlib-only modules.
- Preserved the existing `onecode.web.api` import surface, endpoint payloads,
  status codes, loopback authentication policy, constant-time token comparison,
  request-size limits, and workspace path restrictions.
- Reduced the Web API route coordinator from 1,409 to 1,297 lines without
  moving route handlers or changing the local/trusted-loopback deployment model.
- Added a current release-line audit that records the unrelated
  `origin/main` ancestry and the non-destructive sync-branch decision.

### Verification

- TDD module-boundary tests failed on each missing module before implementation
  and passed after the minimal extraction.
- Full Web API suite: 75 tests passed.
- Full project verification: 907 tests passed, 1 environment-only skip;
  source-quality and doctor gates passed.
- Live LibreChat `v0.8.7` shell health passed. A 10-second model boundary
  returned one structured HTTP 504, and a 60-second retry completed with full
  evidence.

### Integration And Publication

- Integrated the four helper-extraction commits and their closure records onto
  `feature/gateway-iching-rule-sync`; the implementation head before final
  publication-document alignment is `1f3d691b175754f5bd8c3677eaf0e3d72cdeb973`.
- Confirmed that `origin/feature/gateway-iching-rule-sync` is an ancestor of
  the integrated line, allowing a normal fast-forward update without force.
- Preserved the unrelated-history boundary with `origin/main`; no merge,
  rebase, force-push, GitHub Release, or package publication is part of this
  update.
- Added the consolidated GitHub closure record at
  `docs/ONECODE_V087_VNEXT_GITHUB_CLOSURE_2026-07-16.md`.

## Unreleased - 2026-07-15 - LibreChat v0.8.7 Shell Hardening

### Changed

- Migrated the OneCode Web shell onto the exact LibreChat `v0.8.7` community
  baseline while preserving a checkpoint of the previous customization.
- Added typed provider timeouts, structured HTTP 504/502 mappings, one terminal
  model-call event, and SHA-256 task correlation for failed planning evidence.
- Forced the OneCode LibreChat endpoint to `maxRetries: 0` so a durable OneCode
  task is not duplicated by LangChain's outer retry policy.
- Replaced temporary authentication and Mongo state with a private persistent
  shell state directory, atomic secret initialization, bounded redacted logs,
  startup preflight, and version provenance.
- Ported the local OneCode API, project selection, Console, workspace metadata,
  model configuration, evidence, verifier, and diagnostics surfaces to current
  LibreChat extension points.
- Aligned static and runtime branding on `OneCode` while preserving community
  PWA assets and recovery behavior.

### Verification

- OneCode focused suite: 163 tests passed.
- Final OneCode full verification: 903 tests passed, 1 environment-only skip;
  source-quality and doctor gates passed.
- LibreChat focused suites: 90 tests passed; data-provider, API, and client
  production builds passed.
- Live desktop/mobile browser checks covered login, project state, Console
  tabs, read execution, approval-required writes, keyboard focus, restart
  persistence, and a visible bounded 504 with complete evidence.
- Full closure details are recorded in
  `docs/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md`.

## 0.8.0 - 2026-07-10 - Canonical I Ching Runtime and Evidence Cutover

### Licensing

- Changed the project license from Apache License 2.0 to GNU General Public
  License Version 3 only (`GPL-3.0-only`).
- Replaced `LICENSE` with the unmodified GNU GPL v3 official text and aligned
  PEP 639 package metadata, README, historical license notes, and release
  records.
- Added a license consistency test and a dedicated relicensing closure record.

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
