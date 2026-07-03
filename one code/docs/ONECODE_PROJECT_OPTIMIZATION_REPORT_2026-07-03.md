# OneCode Project Optimization Report

Date: 2026-07-03
Status: Optimization pass implemented
Scope: Current `one code` Python project

## 1. Objective

Continue the project-wide review and repair work with a small, verifiable optimization pass. The goal was to improve diagnostics, regression coverage, and project records without expanding into large structural refactors.

## 2. Skill Routing

The task was routed through the OneCode verified skill pack with these selected method guides:

- `codebase-explore-map`
- `code-review-risk`
- `code-simplify-refactor-plan`
- `code-test-regression`
- `code-python-debug`
- `code-ast-refactor-safety`
- `code-dead-path-cleanup-review`
- `code-dependency-cycle-review`

Additional local workflow skills used:

- `superpowers:brainstorming`
- `superpowers:writing-plans`
- `superpowers:test-driven-development`
- `superpowers:verification-before-completion`

## 3. Repository Map

Key project entry points:

- CLI: `src/onecode/cli.py`
- Web API: `src/onecode/web/api.py`
- Kernel context and evidence paths: `src/onecode/kernel/context.py`
- Run ID validation: `src/onecode/kernel/run_id.py`
- Verification scripts: `scripts/verify-core.sh`, `scripts/verify.sh`
- Tests: `tests/test_*.py`

The parent worktree contains unrelated modified and untracked files. This pass only changed files under the current project scope.

## 4. Implemented Optimizations

### 4.1 Web API Request Body Diagnostics

`src/onecode/web/api.py` now has a structured `JsonRequestBody` result and `read_json_request_body()` helper. POST handlers use this result to return clearer local API errors:

- oversized request body: `413` with `request_too_large`
- invalid `Content-Length`: `400` with `invalid_request_body`
- invalid JSON or non-object JSON: `400` with `invalid_json`

The existing `_read_json()` compatibility method remains available and still returns `dict | None`.

### 4.2 Run ID Validation Regression Coverage

Added `tests/test_run_id.py` to pin the run ID validation contract:

- accepts single-segment ASCII IDs
- rejects path separators and traversal-like values
- rejects empty, non-ASCII, and oversized IDs
- verifies optional run ID validation keeps `None` and reports field-specific errors

### 4.3 Verification Documentation

Updated `README.md` to document that `scripts/verify.sh` skips editable install when `onecode` and `textual` are already importable for the selected interpreter.

### 4.4 Planning Records

Added:

- `docs/superpowers/specs/2026-07-03-onecode-project-optimization-design.md`
- `docs/superpowers/plans/2026-07-03-onecode-project-optimization.md`
- `docs/superpowers/specs/2026-07-03-onecode-skill-rule-kernel-integration-design.md`
- `docs/superpowers/plans/2026-07-03-onecode-skill-rule-kernel-integration.md`

These records describe the optimization scope, non-goals, test strategy, and closure criteria.

### 4.5 Read-Only Skill Context

Added a Phase 1 skill-evidence layer:

- `src/onecode/kernel/skill_context.py` discovers project-local `.onecode/skills/*.json` manifests as read-only evidence.
- `IchingKernel.classify_skill_context()` maps skill registry states into the existing 6-bit kernel surface.
- CLI doctor and Web project status expose only `public_skill_context()` summaries, not raw manifest bodies.
- Symlink escapes, invalid JSON, duplicate names, oversized manifests, excessive capability counts, and overlong capability strings are reported as bounded evidence.
- `select_skill_evidence()` records deterministic, read-only capability matches for each run.
- Skill token routing now handles punctuation-separated task text, conservative plural/verb aliases, and phrase capabilities when all component tokens are present.
- `skill_selection` evidence is persisted in result, ledger, manifest, checkpoint records, and compact global WAL hash/reason/count fields when a skill is actually selected.
- Runner, checkpoint, ledger, and global WAL boundaries now validate `skill_selection` schema before writing, rejecting forbidden fields, count mismatches, invalid hashes, and oversized evidence.
- Shell projection schema is now version 2 and exposes only compact skill state in `control_state`: skill-context status, selection reason, selected count, and selection hash.
- WAL-only inspect summaries now carry compact skill-selection aliases into shell projection, so inspect/list consumers get the same bounded reason/count/hash without raw skill details.
- Project review found and closed a schema bypass where direct writers could place raw fields inside `skill_context_summary` or use arbitrary skill selection status/reason/mode/risk strings.
- Follow-up review found and closed a read-side drift where full-evidence inspect summaries did not project compact skill-selection aliases and did not reject tampered full `skill_selection` documents. Full inspect now validates ledger/manifest selection evidence and exposes only bounded status/reason/count/hash aliases to shell projection.
- Further hardening now recomputes `selection_sha256` from the selection document and rejects hash/content mismatches at checkpoint, ledger, WAL, runner, and full-inspect boundaries. Rule metadata inside `skill_selection` is also typed and character-bounded.
- Schema type-boundary review found and closed a Python `bool`/`int` ambiguity where `selected_count=True` could match a single selected skill. `selected_count` now rejects booleans explicitly.
- WAL segment discovery now ignores non-numeric `global-ledger.*.jsonl` scratch or backup files and reports invalid WAL JSON through the stable `invalid_global_wal_json` reason.
- Skill discovery and selection do not add execution authority; executable skill adapters remain a separate future design.

### 4.6 Strict Numeric Evidence Contracts

Hardened remaining Python `bool`/`int` ambiguity in external and evidence-facing numeric fields:

- verifier policy `timeout_ms=True` is rejected instead of becoming a 1ms timeout.
- task-resume verifier evidence with boolean `timeout_ms` is treated as unmapped evidence.
- YiZiJue generation `max_new_tokens=True` is rejected.
- YiZiJue token-id policies and tokenizer output reject boolean token ids.
- inspect ledger count validation rejects boolean counts.
- task-status aggregation ignores boolean asset `raw_status_code` instead of feeding it into the 6-bit status formula.
- sandbox runtime limits reject boolean timeout and PID limits.
- DeepSeek distillation rejects boolean sample counts, request timeouts, and max-token limits.
- OneCode context and LogosGate reject boolean runtime timeout and executor-pool limits.
- runner resource-budget helpers reject boolean task/write/action/trace/deadline limits.
- `IchingKernel.delivery_decision()` treats boolean counts as unknown, so booleans do not produce derived resolved/remaining count evidence.
- model-loop runtime timeout and repair-attempt limits reject booleans before provider calls.
- execution guardrail limits reject boolean max steps, tool calls, duration, and consecutive-failure counts.
- Web query numeric parsers reject boolean list limits and metrics window sizes.

## 5. Test Evidence

Focused red/green evidence:

```text
.venv/bin/python -m unittest \
  tests.test_web_api.OneCodeWebApiTests.test_read_json_result_reports_oversized_request_body \
  tests.test_web_api.OneCodeWebApiTests.test_read_json_result_reports_invalid_content_length -v

Initial result: FAILED with ImportError for read_json_request_body.
After implementation: OK, 2 tests passed.
```

Focused affected tests:

```text
.venv/bin/python -m unittest tests.test_run_id tests.test_web_api -v
Result: OK, 61 tests passed, 9 skipped due to local socket bind permission.
```

Full verification:

```text
bash scripts/verify.sh
Result: OK, 729 tests passed, 1 skipped, doctor status ok.
```

Skill context focused verification:

```text
.venv/bin/python -m unittest tests.test_skill_context tests.test_iching_kernel tests.test_doctor_cli tests.test_web_api -v
Result: OK, 138 tests passed, 9 skipped due to local socket bind permission.
```

Skill selection focused verification:

```text
.venv/bin/python -m unittest tests.test_skill_context tests.test_runner_cli tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 90 tests passed.
```

Skill routing quality verification:

```text
.venv/bin/python -m unittest tests.test_skill_context -v
Result: OK, 16 tests passed.
```

Skill selection schema verification:

```text
.venv/bin/python -m unittest tests.test_checkpoint -v
Result: OK, 21 tests passed.
```

Skill selection persistence-boundary verification:

```text
.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_wal tests.test_runner_cli tests.test_iching_kernel_integration -v
Result: OK, 98 tests passed.
```

Shell projection skill-state verification:

```text
.venv/bin/python -m unittest tests.test_shell_projection -v
Result: OK, 12 tests passed.

.venv/bin/python -m unittest tests.test_runner_cli.CliTests.test_cli_run_projects_compact_skill_selection_for_shell -v
Result: OK, 1 test passed.

.venv/bin/python -m unittest \
  tests.test_shell_projection tests.test_runner_cli \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_shell_schema_endpoint_returns_projection_contract \
  tests.test_web_api.OneCodeWebApiTests.test_http_server_serves_shell_schema \
  tests.test_inspect_cli tests.test_checkpoint tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 150 tests passed, 1 skipped due to local socket bind permission.
```

WAL inspect skill-state alias verification:

```text
.venv/bin/python -m unittest \
  tests.test_shell_projection tests.test_inspect_cli tests.test_runner_cli \
  tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 127 tests passed.
```

Full inspect skill-state validation and alias verification:

```text
.venv/bin/python -m unittest \
  tests.test_inspect_cli.InspectCliTests.test_cli_inspect_full_run_projects_compact_skill_selection_for_shell \
  tests.test_inspect_cli.InspectCliTests.test_cli_inspect_rejects_invalid_full_skill_selection_evidence -v
Result: OK, 2 tests passed.

.venv/bin/python -m unittest tests.test_inspect_cli tests.test_shell_projection tests.test_wal tests.test_checkpoint tests.test_web_api -v
Result: OK, 143 tests passed, 9 skipped due to local socket bind permission.
```

Skill selection hash and metadata hardening verification:

```text
.venv/bin/python -m unittest \
  tests.test_checkpoint.ManifestBoundaryTests.test_write_checkpoint_rejects_skill_selection_hash_mismatch \
  tests.test_inspect_cli.InspectCliTests.test_cli_inspect_rejects_full_skill_selection_hash_mismatch -v
Initial result: FAILED, 2 failures.
After implementation: OK, 2 tests passed.

.venv/bin/python -m unittest \
  tests.test_checkpoint.ManifestBoundaryTests.test_write_checkpoint_rejects_invalid_skill_selection_rule_metadata -v
Initial result: FAILED, 1 failure.
After implementation: OK, 1 test passed.

.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_wal tests.test_skill_context tests.test_runner_cli \
  tests.test_inspect_cli tests.test_iching_kernel_integration -v
Result: OK, 161 tests passed.
```

WAL segment filtering and stable corrupt-reason verification:

```text
.venv/bin/python -m unittest tests.test_wal.GlobalWalTests.test_global_wal_paths_ignore_non_numeric_archive_files -v
Initial result: FAILED with JSONDecodeError from non-numeric backup file.
After implementation: OK, 1 test passed.

.venv/bin/python -m unittest \
  tests.test_wal.GlobalWalTests.test_read_validated_global_wal_entries_rejects_invalid_json_with_stable_reason -v
Initial result: FAILED because raw JSONDecodeError message was exposed.
After implementation: OK, 1 test passed.

.venv/bin/python -m unittest tests.test_wal \
  tests.test_inspect_cli.InspectCliTests.test_cli_inspect_and_list_runs_read_rotated_global_wal_segments \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_run_evidence_returns_rotated_wal_segment_path -v
Result: OK, 12 tests passed.
```

Skill selection boolean-count hardening verification:

```text
.venv/bin/python -m unittest \
  tests.test_checkpoint.ManifestBoundaryTests.test_write_checkpoint_rejects_boolean_skill_selection_count -v
Initial result: FAILED, 1 failure.
After implementation: OK, 1 test passed.

.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_wal tests.test_skill_context tests.test_runner_cli \
  tests.test_inspect_cli tests.test_iching_kernel_integration -v
Result: OK, 164 tests passed.
```

Strict numeric evidence-contract verification:

```text
PYTHONPATH=src python3 -m unittest \
  tests.test_verifier.VerifierPolicyTests.test_load_verifier_policy_rejects_boolean_timeout \
  tests.test_task_resume.TaskResumeClassificationTests.test_boolean_verifier_timeout_evidence_is_unmapped
Initial result: FAILED, 2 failures.
After implementation: OK, 2 tests passed.

PYTHONPATH=src python3 -m unittest \
  tests.test_yizijue_transformers.YiZiJueTransformersTests.test_generate_with_yizijue_logits_rejects_boolean_max_new_tokens \
  tests.test_yizijue_logits.YiZiJueLogitsPolicyTests.test_validate_state_token_id_policy_rejects_boolean_ids \
  tests.test_yizijue_logits.YiZiJueLogitsPolicyTests.test_text_policy_to_token_id_policy_rejects_boolean_tokenizer_ids
Initial result: FAILED, 3 failures.
After implementation: OK, 3 tests passed.

PYTHONPATH=src python3 -m unittest \
  tests.test_inspection.InspectionKernelTests.test_validate_ledger_counts_rejects_negative_and_impossible_totals \
  tests.test_verifier.VerifierExecutionTests.test_task_status_ignores_boolean_asset_status_codes
Initial result: FAILED, 2 failures.
After implementation: OK, 2 tests passed.

PYTHONPATH=src python3 -m unittest \
  tests.test_verifier tests.test_task_resume tests.test_yizijue_logits \
  tests.test_yizijue_transformers tests.test_inspection tests.test_inspect_cli
Result: OK, 93 tests passed.

PYTHONPATH=src python3 -m unittest \
  tests.test_sandbox tests.test_deepseek_distillation tests.test_context \
  tests.test_logos_gate tests.test_runner_cli tests.test_iching_kernel
Result: OK, 160 tests passed.

PYTHONPATH=src python3 -m unittest \
  tests.test_model_loop tests.test_execution_engine tests.test_web_api
Result: OK, 95 tests passed.
```

Project review schema-tightening verification:

```text
.venv/bin/python -m unittest tests.test_checkpoint -v
Result: OK, 25 tests passed.

.venv/bin/python -m unittest \
  tests.test_checkpoint tests.test_skill_context tests.test_runner_cli \
  tests.test_wal tests.test_iching_kernel_integration -v
Result: OK, 118 tests passed.
```

Diff hygiene:

```text
git diff --check -- src tests docs README.md scripts
Result: OK, no whitespace errors reported.
```

## 6. Residual Risks

- The Web API remains a local/trusted-loopback stdlib HTTP server, not a production gateway.
- Skill integration is intentionally read-only; execution-capable skill adapters are deferred.
- Large file decomposition for `web/api.py` and `cli.py` is still deferred to avoid mixing structural refactor with hardening work.
- Parent worktree cleanup remains outside this pass.

## 7. Closure Criteria

This optimization pass is closed when:

- focused tests pass: done
- `bash scripts/verify.sh` passes: done
- whitespace checks pass: done
- final handoff records verification evidence and unresolved risks: done in assistant response
- closure report and maintenance log are committed to project docs: done
- GitHub update path is prepared from branch `feature/gateway-iching-rule-sync`: done

## 8. Publication Handoff

Publish target:

- repository: `https://github.com/aidi1723/onecode.git`
- branch: `feature/gateway-iching-rule-sync`
- scope: project-local source, tests, scripts, README, and docs under `/Users/aidi/大字典/one code`
- excluded scope: unrelated parent-directory files and generated material outside this project root

Pre-publication checklist:

- source and test changes are intentional project hardening work
- no new runtime third-party dependency was introduced
- license remains Apache-2.0 as recorded in `LICENSE` and `README.md`
- release docs record the read-only skill boundary and residual risks
- final verification evidence is captured in this report and in `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`

Publication decision:

- ready to commit and push this branch after final `git diff --check` and `bash scripts/verify.sh`
