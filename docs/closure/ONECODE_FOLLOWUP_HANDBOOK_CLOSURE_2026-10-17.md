# OneCode Follow-up Handbook Closure

**Date**: 2026-10-17

Record for `docs/superpowers/plans/2026-10-16-onecode-followup-development-handbook.md`. This file lists the contracts that changed, the gates that were run, and the items that remain unfinished.

## Contracts changed

- `execute_plan` defaults to explicit approval.
- CLI and TUI require `--approve`.
- `granted_approval_ids` runs a matching pending tool once, and a denying callback still wins.
- The approval secret is under `ONECODE_HOME` and is created with mode `0600`.
- A missing `read_text` target is `path_not_found`. A non-file target stays `read_target_not_file`. Both reasons are in `SOFT_MISS_REASONS` and map to Kun/Kun.
- A same-host HTTPS to HTTP redirect drops `Authorization`.
- 承/乘 documentation matches the `cheng` and `sheng` fields.

## Gates

- `bash scripts/verify.sh` at `fd34441d58392318cd7a158eae5ad9e73b00ba6a` was 1175 tests, 86% coverage, doctor ok. It was not re-run for this record.
- `bash scripts/verify-core.sh`: 249 OK, doctor ok.
- `PYTHONPATH=src python -m unittest tests.test_web_api -v`: 81 OK.
- `git diff --check`: clean.
- The Task 15 `rg` checks are clean, including `rg -n 'AssertionError" in script_content' tests`, which prints nothing. The previous match was the harness meta-assertion in `tests/test_sandbox_test_harness.py`. That assertion was removed. The behavioral harness tests remain: real unittest discovery and `python -c`.
- After that edit, `PYTHONPATH=src .venv/bin/python3 -m unittest tests.test_sandbox_test_harness tests.test_run_plan_cli -v` ran 35 tests, OK.

## Not done

- OpenAI key revocation.
- n100 sync.
- 4-hour soak.
- ARM64 re-proof.
- Third-party pentest.
- `claims_mainstream_parity` stays false.
- No tag, no push, no version bump.
