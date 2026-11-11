# Audit remediation closeout, 2026-10-23

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. No new hexagram was added. `IchingKernel.classify_outcome` was not edited. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies stay `dependencies = []`.

This note records the security fixes from the 2026-10-23 review. Those fixes are in `efb4447` and travel with the 2026-10-28 exam closeout. The chat path still passes `max_repair_attempts=1` and does not pass `approval_mode`, so approval stays `strict`.

## What changed

- A unique patch match may keep a leading indent only when every character of that prefix is a space or a tab. A search block of `x = 1` no longer rewrites `max = 1`. Matching is line-oriented after trailing whitespace is stripped. Several matches stay `patch_search_ambiguous`. No match stays `patch_search_not_found`.
- `is_preset_test_path` normalizes with `posixpath.normpath` before the `tests/` check. Asset paths, patch paths, `write_text` and `patch_text` execution steps, and `git_commit` paths are all checked. `.//tests/`, `/tests/`, and `tests/../tests/` are rejected.
- A new Python asset may not import `unittest` or `pytest`, including through `__import__` or `importlib.import_module`. It may not call `_exit`.
- Root names `unittest.py`, `unittest`, `pytest.py`, `pytest`, `conftest.py`, `sitecustomize.py`, and `usercustomize.py` are denied by `PathGuard`.
- The sandbox sets `PYTHONSAFEPATH=1`. Unittest commands run under `python -I` with a guard that refuses a workspace `unittest.py` or `pytest.py`, loads the suite, restores the standard `TestCase` assertion methods, and then runs. A zero exit code is a pass only when the output contains `Ran N tests` with N at least 1 and `OK`. Anything else is `verifier_empty_or_aborted`.
- `git_status` and `git_diff` force `--no-textconv`, an empty attributes file, and empty external diff, tool, and LFS filter settings. A repo-local textconv does not run.
- Every global-ledger line must have a `hash` and a matching `prev`. The hash is an HMAC-SHA256 using `ONECODE_HOME/approval-plan.key`, not a bare SHA-256 of the line. A chain rewritten with plain SHA-256 is `global_wal_chain_hash_mismatch`.
- `handle_onecode_plan_approval` and `run_model_task` call `ledger_matches_workspace` before execution. A mismatch stops the run. A blocked preset-test change is written to the ledger. The next approval uses `authoritative_preset_test_hashes`, which prefers the last ledger `th` entry.
- MCP commands are read from `ONECODE_HOME/mcp_servers.json`. A workspace `.onecode/mcp_servers.json` does not supply the command. In `auto` mode, with Docker unavailable, the call returns `sandbox_required` and does not start a host process. Explicit `host` mode still runs on the host. The approval text names the command and says whether it runs on the host or in the sandbox.
- When `.git`, `.github`, `.onecode`, or `tests` exists, the sandbox bind-mounts that directory a second time as read-only. The rest of the workspace stays writable so an approved write can land.

## Gate

`bash scripts/verify.sh` on this Mac, without Docker:

- `compileall`: OK
- `source-quality`: OK
- `ruff`: all checks passed
- `mypy`: no issues found in 104 source files
- `unittest`: `Ran 1306 tests`, `OK (skipped=1)`
- skipped test: `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is unset
- `coverage`: 86% (14121 statements, 1949 missed)
- `doctor`: status `ok` (`docker_ready: false`)

n100 has not been re-run for this tree.

## What this close does not claim

- The ledger key lives in `ONECODE_HOME`. A person who has that key can still produce a valid chain. The workspace ledger alone is not enough to do so.
- Explicit `ONECODE_RUN_COMMAND_SANDBOX=host` still runs MCP on the host, and the approval text says so.
- The workspace mount stays writable outside the four read-only overlays.
- This is not a SOX, 等保, functional-safety, or military certification. `production_ready` still means Docker is up, unauthenticated access is off, and an API token is set.
- `claims_mainstream_parity` stays false.
