# OneCode Maintenance Log - 2026-07-06

## Test Run Summary

- Initial command: `python3 -m unittest discover -s tests -v`
  - Result: failed.
  - Evidence: `Ran 216 tests ... FAILED (errors=183, skipped=1)`.
  - Root cause: system Python did not have the `src/` package path or editable install active, so tests failed with `ModuleNotFoundError: No module named 'onecode'`.

- Package-path check:
  - `python3 -c "import onecode"` failed with `ModuleNotFoundError`.
  - `python3 -c "import sys; sys.path.insert(0, 'src'); import onecode; print(onecode.__file__)"` resolved `src/onecode/__init__.py`.

- Second command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  - Result: failed.
  - Evidence: `Ran 728 tests ... FAILED (errors=4, skipped=1)`.
  - Root cause: system Python lacked the optional TUI dependency `textual`.
  - Failing surfaces:
    - `tests.test_tui_layout`: `ModuleNotFoundError: No module named 'textual'`.
    - `tests.test_tui_model_closure`: `ModuleNotFoundError: No module named 'textual'`.
    - `tests.test_self_audit_cli`: `audit-self` failed because `tui_bootstrap` could not import `textual`.
    - `tests.test_verify_script`: `scripts/verify.sh --skip-tests` tried `pip install -e .[tui]`, but Homebrew Python 3.14 rejected system package installation with PEP 668 `externally-managed-environment`.

- Project virtualenv check:
  - `.venv/bin/python -c "import sys, onecode, textual; print(sys.executable); print(textual.__version__)"` passed.
  - Confirmed interpreter: `.venv/bin/python`.
  - Confirmed `textual` version: `8.2.7`.

- Final unittest command: `.venv/bin/python -m unittest discover -s tests -v`
  - Result: passed.
  - Evidence: `Ran 743 tests ... OK (skipped=1)`.
  - Skipped test: `test_global_onecode_command_points_to_project_entrypoint`, reason `ONECODE_GLOBAL_COMMAND is not configured`.

- Final verification command: `env -u PYTHON -u VIRTUAL_ENV bash scripts/verify.sh`
  - Result: passed.
  - Evidence:
    - install skipped because `onecode` and `textual` were available.
    - `source quality ok`.
    - `Ran 743 tests ... OK (skipped=1)`.
    - `doctor` returned `"status": "ok"`.

## Recorded Issues

1. Running the suite with bare system Python is not valid in this workspace unless the package is installed or `PYTHONPATH=src` is set.
2. Running TUI-related tests with system Python 3.14 fails because `textual` is not installed there.
3. Forcing `PYTHON=/opt/homebrew/opt/python@3.14/bin/python3.14` makes `scripts/verify.sh` attempt a system-level editable install and fail under PEP 668. The project `.venv` avoids this.

## Current Passing Path

Use the project virtualenv:

```bash
env -u PYTHON -u VIRTUAL_ENV bash scripts/verify.sh
```

or directly:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Continued Test Pass

- Command: `PYTHON=.venv/bin/python bash scripts/verify-core.sh`
  - Result: passed.
  - Evidence:
    - `compileall` completed.
    - `source quality ok`.
    - `Ran 215 tests ... OK`.
    - `doctor` returned `"status": "ok"`.

- Command: `PYTHON=.venv/bin/python bash scripts/demo_v07.sh`
  - Result: passed.
  - Evidence:
    - verifier presets listed: `python-compileall`, `python-unittest`.
    - policy initialization returned `completed`.
    - run-plan returned `completed / deliverable`.
    - verifier returned `python-unittest passed`.
    - inspect returned `completed / deliverable`.
    - list-runs found `demo-plan-verified`.

- Command: `PYTHON=.venv/bin/python bash scripts/release-audit.sh`
  - Result: passed.
  - Evidence:
    - `git diff --check` completed.
    - `source quality ok`.
    - wheel built: `onecode-0.1.0-py3-none-any.whl`.
    - `wheel assets ok`.
    - publish action was not performed.

- Command: `PYTHONPATH=src ONECODE_AUDIT_SELF_DEPTH=1 .venv/bin/python -m onecode audit-self`
  - Result: passed.
  - Evidence:
    - `cli_entrypoint`, `tui_bootstrap`, `model_provider_matrix`, `compileall`, `unittest`, and `doctor` checks passed.
    - final status returned `"ok"`.

- Command: `PYTHONPATH=src .venv/bin/python -m onecode benchmark --run --workspace-root /private/tmp/onecode-benchmark-20260706 --report /private/tmp/onecode-benchmark-20260706-report.json`
  - Result: passed.
  - Evidence:
    - status `completed`.
    - `task_count`: 20.
    - `passed_count`: 20.
    - `failed_count`: 0.
    - metrics: `pass_at_1=1.0`, `hallucination_rate=0.0`, `asset_completeness=1.0`, `evidence_completeness=1.0`.

- Command: `PYTHONPATH=src .venv/bin/python -m onecode shell-schema`
  - Result: passed.
  - Evidence:
    - returned schema name `onecode.shell_projection`.
    - returned schema `version`: 2.

## Continued Test Issues

1. Initial continued-test command wrapper failed before executing tests because a temporary `PATH=...` assignment included the workspace path with a space and was not shell-quoted. Re-run used the scripts' supported `PYTHON=.venv/bin/python` override.
2. Initial sandbox smoke command failed before Docker execution because the target workspace did not exist:
   - `sandbox workspace does not exist: /private/tmp/onecode-sandbox-smoke-20260706`.
3. After creating the workspace, sandbox smoke reached Docker but failed because the local Docker/Colima daemon is not running:
   - Command: `PYTHONPATH=src .venv/bin/python -m onecode sandbox-smoke --workspace /private/tmp/onecode-sandbox-smoke-20260706 --report /private/tmp/onecode-sandbox-smoke-20260706-report/report.json`.
   - Result: failed.
   - Evidence: Docker daemon connection failed at the local Colima socket.
   - Report status: `failed`, reason `sandbox_smoke_failed`.

## Fixes Applied

- `sandbox-smoke` CLI now creates a missing workspace directory before constructing `SandboxConfig`.
- `run_sandbox_smoke()` now classifies Docker daemon connection failures as `blocked` with reason `docker_daemon_unavailable` instead of generic `failed/sandbox_smoke_failed`.
- Added regression coverage:
  - CLI sandbox smoke creates a missing workspace and reports Docker absence as blocked.
  - Docker daemon unavailable stderr is classified as `blocked/docker_daemon_unavailable`.

## Post-Fix Verification

- Red test check before implementation:
  - Command: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_sandbox.SandboxTests.test_sandbox_smoke_returns_blocked_when_docker_daemon_unavailable tests.test_sandbox.SandboxTests.test_cli_sandbox_smoke_creates_missing_workspace -v`.
  - Result before fix: failed as expected.
  - Evidence:
    - daemon unavailable case returned `failed` instead of expected `blocked`.
    - missing workspace case raised `sandbox workspace does not exist`.

- Focused sandbox tests:
  - Command: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_sandbox -v`.
  - Result: passed.
  - Evidence: `Ran 11 tests ... OK`.

- Reproduced CLI sandbox smoke after fix:
  - Command: `PYTHONPATH=src .venv/bin/python -m onecode sandbox-smoke --workspace /private/tmp/onecode-sandbox-smoke-fixed-20260706 --report /private/tmp/onecode-sandbox-smoke-fixed-20260706-report/report.json`.
  - Result: blocked, exit code 2.
  - Evidence: JSON output had `"status": "blocked"` and `"reason": "docker_daemon_unavailable"`.
  - This is the expected local result while Docker/Colima is not running.

- Full verification:
  - Command: `env -u PYTHON -u VIRTUAL_ENV bash scripts/verify.sh`.
  - Result: passed.
  - Evidence:
    - `source quality ok`.
    - `Ran 745 tests ... OK (skipped=1)`.
    - skipped test: `ONECODE_GLOBAL_COMMAND is not configured`.
    - `doctor` returned `"status": "ok"`.

- Release audit:
  - Command: `PYTHON=.venv/bin/python bash scripts/release-audit.sh`.
  - Result: passed.
  - Evidence:
    - `git diff --check` completed.
    - `source quality ok`.
    - wheel built successfully.
    - `wheel assets ok`.
    - publish action was not performed.

## Stability Retest

- Repeated full verification:
  - Command shape: `env -u PYTHON -u VIRTUAL_ENV bash scripts/verify.sh`.
  - Pass 1 evidence: `Ran 745 tests ... OK (skipped=1)`, `doctor` returned `"status": "ok"`.
  - Pass 2 evidence: `Ran 745 tests ... OK (skipped=1)`, `doctor` returned `"status": "ok"`.
  - Harness note: one wrapper attempt used zsh variable name `status`, which is read-only; the verification command itself completed successfully. Later wrappers used non-conflicting variable names.

- End-to-end chain retest before the second sandbox classification fix:
  - Chain: `audit-self -> demo_v07 -> benchmark -> sandbox-smoke`.
  - `audit-self`: `ok / continue`.
  - `demo_v07`: policy `completed`, run-plan `completed / deliverable`, verifier `python-unittest passed`, inspect `completed / deliverable`, list-runs found `demo-plan-verified`.
  - `benchmark`: `completed`, `task_count=20`, `passed_count=20`, `failed_count=0`, `pass_at_1=1.0`.
  - `sandbox-smoke`: exposed a new Docker boundary variant: permission denied while trying to connect to the local Docker API socket.

## Additional Fix Applied

- `run_sandbox_smoke()` now also classifies Docker socket permission errors as `blocked/docker_daemon_unavailable`.
- Added regression coverage for Docker API socket permission denial.

## Final Stability Evidence

- Focused sandbox verification:
  - Command: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_sandbox -v`.
  - Result: passed.
  - Evidence: `Ran 12 tests ... OK`.

- Repeated end-to-end chain after the permission-denied fix:
  - Pass 1:
    - `audit ok continue`.
    - demo policy/run-plan/verifier/inspect/list-runs all completed.
    - `benchmark completed 20 20 0 1.0`.
    - `sandbox blocked docker_daemon_unavailable exit 2`.
  - Pass 2:
    - `audit ok continue`.
    - demo policy/run-plan/verifier/inspect/list-runs all completed.
    - `benchmark completed 20 20 0 1.0`.
    - `sandbox blocked docker_daemon_unavailable exit 2`.

- Final full verification:
  - Command: `env -u PYTHON -u VIRTUAL_ENV bash scripts/verify.sh`.
  - Result: passed.
  - Evidence:
    - `source quality ok`.
    - `Ran 746 tests ... OK (skipped=1)`.
    - skipped test: `ONECODE_GLOBAL_COMMAND is not configured`.
    - `doctor` returned `"status": "ok"`.

- Final release audit:
  - Command: `PYTHON=.venv/bin/python bash scripts/release-audit.sh`.
  - Result: passed.
  - Evidence:
    - `git diff --check` completed.
    - `source quality ok`.
    - wheel built successfully.
    - `wheel assets ok`.
    - publish action was not performed.

## Additional Continuation Checks

- Global command entrypoint:
  - Command: `ONECODE_GLOBAL_COMMAND=.venv/bin/onecode .venv/bin/python -m unittest tests.test_venv_entrypoint -v`.
  - Result: passed.
  - Evidence: `Ran 2 tests ... OK`.
  - This covers the test that is skipped in normal local verification when `ONECODE_GLOBAL_COMMAND` is not configured.

- Tests covering currently modified local files:
  - Command: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_model_config tests.test_shell_launcher -v`.
  - Result: passed.
  - Evidence: `Ran 29 tests ... OK`.

- Core verification gate:
  - Command: `PYTHON=.venv/bin/python bash scripts/verify-core.sh`.
  - Result: passed.
  - Evidence:
    - `source quality ok`.
    - `Ran 215 tests ... OK`.
    - `doctor` returned `"status": "ok"`.

- Local HTTP API smoke:
  - First attempt without `ONECODE_API_TOKEN` correctly returned unauthorized for `/v1/models`.
  - First attempt also used incorrect `/onecode/...` paths; the documented routes are under `/v1/onecode/...`.
  - Restarted server with:
    - `PYTHONPATH=src`.
    - `ONECODE_API_TOKEN=<local-test-token>`.
    - `ONECODE_ALLOWED_WORKSPACE_ROOTS="$PWD"`.
    - `onecode serve --host 127.0.0.1 --port 19180`.
  - Result: passed for read-only smoke requests.
  - Evidence:
    - `GET /health` returned `{"status": "ok", "service": "onecode"}`.
    - `GET /v1/models` with bearer token returned `onecode-agent`.
    - `GET /v1/onecode/shell/schema` with bearer token returned `onecode.shell_projection`, version `2`.
    - `GET /v1/onecode/project/status?workspace=<repo workspace>` with bearer token returned `exists=true`, `allowed=true`, and project/runtime/skill summaries.
  - Observation: project status reports `git.present=false` for this workspace because the actual git root is above `one code/`; current API semantics check only `workspace/.git`.

## n100 Shell System Test

- Host and paths:
  - SSH target: remote Intel N100 test host, Ubuntu, Python `3.12.3`.
  - OneCode path: `<remote-onecode-repo>`.
  - LibreChat shell path: `<remote-librechat-shell>`.

- Remote shell launcher unit tests:
  - Command: `cd <remote-onecode-repo> && PYTHONPATH=src python3 -m unittest tests.test_shell_launcher -v`.
  - Result: passed.
  - Evidence: `Ran 20 tests ... OK`.

- Initial remote shell status:
  - Command: `PYTHONPATH=src python3 -m onecode shell-status --onecode-port 19080 --librechat-port 14080`.
  - Result before launch: `status=down`.
  - Checks: OneCode API down, LibreChat shell down, Mongo down.

- CLI command-intent safety smoke:
  - Command input: `touch /tmp/onecode-n100-command-deny-ran`.
  - Result: denied with `reason=permission_denied`, `severity=blocked`, exit code `1`.
  - Sentinel result: `/tmp/onecode-n100-command-deny-ran` was not created.
  - Observation: `inspect` on the denied run reported `status=missing` even though evidence files existed under `.onecode/runs/command-intent/`; this looks like a denied-run inspection/reporting bug.

- OneCode API smoke on n100:
  - Started `python3 -m onecode serve` on `127.0.0.1:19181` with a `/tmp` workspace and local token.
  - `/health` returned ok.
  - `/v1/models` returned `onecode-agent`.
  - Chat input `你好，回答 2+2` completed through `chat_fallback`.
  - Task input `查：n100 shell command input smoke` completed through `rule_fallback`.
  - Command-like text `执行：touch /tmp/onecode-n100-api-command-ran` completed through `rule_fallback`, and the sentinel file was not created.
  - Risk: command-like plain chat text is not executed, but it reports as completed rather than explicitly blocked/unsupported.

- Full shell launch on n100:
  - Command: `PYTHONPATH=src python3 -m onecode shell --no-browser --show-credentials --workspace /tmp/onecode-n100-live-shell-test --onecode-port 19080 --librechat-port 14080 --mongo-port 39017`.
  - Result: launched successfully.
  - `shell-status` after launch returned `status=ok`.
  - Checks:
    - Mongo TCP `127.0.0.1:39017`: ok.
    - OneCode API `http://127.0.0.1:19080/health`: ok.
    - LibreChat `http://127.0.0.1:14080/c/new`: ok.
  - LibreChat login succeeded with the configured local preview account.
  - Shell-side OneCode project status for `/tmp/onecode-n100-live-shell-test`: `exists=true`, `allowed=true`.
  - Shell-side model config was readable and returned provider `openai-compatible`, model `gpt-5.5`.
  - Cleanup: stopped the test shell parent and remaining Mongo/OneCode API/LibreChat child processes; final `shell-status` returned `status=down`.

- Browser/UI command input test through SSH port forwarding:
  - Local tunnel: `127.0.0.1:24080 -> n100:127.0.0.1:14080`.
  - Opened real shell page with Playwright and logged in.
  - UI showed model `onecode-agent` and message input was usable.
  - Test input: `执行：touch /tmp/onecode-n100-ui-command-ran`.
  - Result:
    - User message was saved in LibreChat conversation `2d7a84d1-0010-4694-9d1f-52131743b874`.
    - Assistant response: `我收到了这条消息，但模型没有生成文件变更或执行计划。这次已记录为普通 OneCode 对话运行；如果你要我改代码或写文件，请明确说明目标文件和期望内容。`
    - Sentinel `/tmp/onecode-n100-ui-command-ran` was not created.
  - Conclusion: shell UI accepts command-shaped text as chat input, but it does not execute it as a host shell command.

- Browser/UI stability retest:
  - Follow-up input: `你好，回答 2+2`.
  - Result: response completed and displayed as `2+2 = 4`.
  - Message API confirmed four saved messages: command-shaped user text, assistant explanation, `2+2` user text, and `2+2 = 4` assistant response.

- n100 shell issues recorded:
  1. `/api/balance` returns repeated 404s in the browser console after login. It did not block chat, but it is noisy and should be hidden or disabled when balance is not configured.
  2. `/api/agents/chat/status/<conversationId>` returned an SSE-style `event: error` / `Illegal request` response during manual HTTP probing, instead of a normal JSON status payload.
  3. `onecode list-runs` for the live shell workspace showed completed WAL-backed runs plus two `missing` projection entries (`52c2246e...`, `cfcbaf...`) where only `trace.jsonl` and `.write.lock` existed, but projected `ledger.json` and `manifest.json` paths were absent.
  4. Plain command-like chat input is safely not executed, but the UX reports it as a normal completed conversation rather than an explicit "command execution is unsupported/blocked" state.

## n100 Concrete Programming Task Tests

- Sandbox boundary:
  - Workspace: `/tmp/onecode-n100-programming-task-test`.
  - Remote project used to run OneCode: `<remote-onecode-repo>`.
  - The workspace was isolated from the OneCode source tree and contained only small test files plus `.onecode` evidence.

- Baseline failing project:
  - Created `calculator.py` with a deliberate bug: `add(a, b)` returned `a - b`.
  - Created `test_calculator.py` with two unittest cases.
  - Baseline command: `python3 -m unittest -v`.
  - Result before OneCode fix: failed.
  - Evidence: both `test_add_positive_numbers` and `test_add_negative_number` failed.

- Programming task 1: fix a failing implementation.
  - Command shape: `PYTHONPATH=src python3 -m onecode run-model ... --workspace /tmp/onecode-n100-programming-task-test --run-id fix-calculator --provider openai-compatible --endpoint <local-model-endpoint> --model gpt-5.5`.
  - Task: fix `calculator.py` so `python3 -m unittest -v` passes.
  - Result: completed.
  - Model plan: one patch, `calculator.py`, replacing `return a - b` with `return a + b`.
  - Evidence mode: full.
  - Inspect result: `status=completed`, `requested_count=1`, `completed_count=1`, `delivery_status=deliverable`.
  - Verification: `python3 -m unittest -v` passed for both calculator tests.

- Programming task 2: create new code and tests.
  - Task: create dependency-free `string_utils.py` with `slugify(text)` and `test_string_utils.py` unittest coverage.
  - Result: completed.
  - Model plan: two assets, `string_utils.py` and `test_string_utils.py`.
  - Evidence mode: full.
  - Inspect result: `status=completed`, `requested_count=2`, `completed_count=2`, `delivery_status=deliverable`.
  - Verification: `python3 -m unittest -v` passed 10 tests total.
  - Additional verification: `python3 -m compileall -q .` passed.

- Programming boundary test:
  - Command attempted to write `../onecode-n100-escape.py` from the test workspace.
  - Result: halted with `reason=sovereignty_breach`, shell projection `severity=blocked`, exit code `1`.
  - Verification: `/tmp/onecode-n100-escape.py` was absent after the run.
  - Inspect/list-runs showed the blocked run as `delivery_status=blocked`, `status=halted`, `failed_count=1`.

- Programming task issues and risks:
  1. `run-model` marks a programming task `completed` when the generated patch/write actions apply successfully; it does not automatically run the task's requested tests. Manual `python3 -m unittest -v` was required to prove the code actually worked.
  2. `run-model` CLI output is extremely verbose because each asset includes the full rule profile. This is useful for forensic evidence but noisy for ordinary programming task feedback.
  3. Evidence for the successful programming runs was consistent in this workspace; unlike the earlier full shell UI test, `list-runs` did not show missing ledger/manifest entries for `fix-calculator`, `create-string-utils`, or `path-escape-programming`.

## run-model Verifier Gate Fix

- Issue fixed:
  - `run-model` now supports `--verifier-policy` and repeated `--verifier` flags.
  - When a selected verifier fails after the model task completes, delivery is blocked:
    - final status: `halted`.
    - reason: `verifier_failed`.
    - delivery status: `blocked`.
    - verifier evidence is persisted in the result ledger.

- Regression coverage added:
  - `test_cli_run_model_blocks_delivery_when_selected_verifier_fails`.
  - `test_model_verifier_failure_keeps_inspection_evidence_consistent`.

- Evidence consistency fix:
  - Root cause: verifier failure rewrote `ledger.json` to `halted`, but `manifest.json` still said `completed`, so `inspect` returned `corrupt/status_mismatch`.
  - Fix: final result writes now synchronize manifest top-level status fields and append a final `run_completed` trace event.
  - Trace validation now treats the last `run_completed` event as the final run state, which supports post-run verifier gates and repair loops.

- Local verification:
  - `PYTHONPATH=src .venv/bin/python -m unittest tests.test_model_loop tests.test_inspect_cli tests.test_run_plan_cli -v`
    - Result: passed.
    - Evidence: `Ran 94 tests ... OK`.
  - `bash scripts/verify.sh`
    - Result: passed.
    - Evidence: `Ran 748 tests ... OK (skipped=1)`, `doctor` returned `status=ok`.

## n100 Post-Fix Verification

- Synced updated `src/onecode/` and focused tests to `<remote-onecode-repo>` on the remote Intel N100 test host.

- Focused n100 regression tests:
  - Command shape: `PYTHONPATH=src python3 -m unittest tests.test_model_loop.ModelLoopTests.test_model_verifier_failure_keeps_inspection_evidence_consistent tests.test_inspect_cli.InspectCliTests.test_cli_inspect_reports_repair_evidence -v`.
  - Result: passed.
  - Evidence: `Ran 2 tests ... OK`.

- n100 related suite:
  - Command shape: `PYTHONPATH=src python3 -m unittest tests.test_model_loop tests.test_inspect_cli tests.test_run_plan_cli -v`.
  - Result: passed.
  - Evidence: `Ran 94 tests ... OK`.

- n100 real `run-model --verifier` smoke:
  - Failing verifier workspace: `/tmp/onecode-n100-runmodel-verifier-fail-20260706-final`.
    - Run result: `halted verifier_failed blocked failed halted`.
    - Inspect result: `halted verifier_failed blocked failed halted`, `corrupt_reason=None`.
  - Passing verifier workspace: `/tmp/onecode-n100-runmodel-verifier-pass-20260706-final`.
    - Run result: `completed None deliverable passed completed`.
    - Inspect result: `completed None deliverable passed completed`, `corrupt_reason=None`.

- n100 command-intent smoke:
  - Command shape: `run --intent-type bash_execution --command ...`.
  - Result: `denied permission_denied blocked`.
  - Inspect result: exit `0`, `status=denied`, `reason=permission_denied`, `corrupt_reason=None`.
  - Interpretation: command-shaped input is recorded and blocked by policy; it is not executed as a host shell command.

- n100 concrete programming smoke:
  - Workspace: `/tmp/onecode-n100-programming-task-20260706`.
  - Task: create `src/calc.py` plus `tests/test_calc.py`.
  - Run-plan result: `completed None deliverable passed completed`.
  - Manual verifier: `python3 -m unittest discover -s tests -v` passed, `Ran 2 tests ... OK`.
  - Inspect result: `completed None deliverable passed`, `corrupt_reason=None`.

- n100 live shell smoke:
  - Started `PYTHONPATH=src python3 -m onecode.cli shell --workspace /tmp/onecode-n100-live-shell-20260706 --no-browser --show-credentials`.
  - `shell-status` during run returned `status=ok`.
  - Health checks:
    - OneCode API `/health`: `200`.
    - LibreChat `/api/config`: `200`.
    - LibreChat `/c/new`: `200`.
    - shell schema `/v1/onecode/shell/schema`: `200`.
  - Authenticated `/v1/chat/completions` with the shell runtime token.
    - Result: `chat.completion stop`.
    - Generated file: `/tmp/onecode-n100-live-shell-20260706/src/shell_api_smoke.py`.
    - File content: `VALUE = 42`.
    - Inspect result: `completed None ok`, `corrupt_reason=None`.
  - Cleanup:
    - Sent SIGINT to the shell launcher parent and cleaned a remaining LibreChat process.
    - Final `shell-status`: `status=down`.
    - Final port checks for `19080`, `14080`, and `39017`: connection refused.

- Remaining known shell/UI issue:
  - Direct unauthenticated calls to `/v1/models` and `/v1/chat/completions` correctly return 401 while the shell is running. LibreChat uses the generated runtime token, and direct tests must include it.
  - Previously recorded UI-only issues such as `/api/balance` console noise and plain command UX were not changed in this fix.

## Temporary Closure Decision

- Pressure testing was discussed and intentionally not run in this pass.
- n100 resource check showed it is an Intel N100 host with 4 CPU cores, 7.5 GiB RAM, about 68 GiB free disk, healthy temperature around 45-47 C, and multiple existing Docker/local services already running.
- Conclusion:
  - Suitable for small to medium smoke and stability tests.
  - Not suitable as a heavy pressure-test machine while it is also running unrelated services.
- Temporary closure report:
  - `docs/ONECODE_TEMPORARY_CLOSURE_HANDOFF_2026-07-06.md`.
- Pressure testing is deferred to a later scoped pass with explicit concurrency, duration, cleanup, and resource-monitoring limits.
