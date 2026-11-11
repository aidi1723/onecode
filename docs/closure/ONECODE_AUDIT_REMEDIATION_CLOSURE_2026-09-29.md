# OneCode Audit Remediation Closure

Date: 2026-09-29
Status: Verified locally and published to `origin/main`
Branch: `main`
Base before this closeout: `8d4d6e1`
Source review: working-tree audit on 2026-09-29

## Outcome

The 2026-09-29 audit findings that could be closed without changing the I Ching
runtime are closed in this commit. The kernel remains v0.8.0 and local-first.
`onecode doctor` now reports whether a checkout is production-ready. On a
machine without a Docker daemon and without `ONECODE_API_TOKEN`, that field is
false. This closeout does not declare a production release.

## Verification

Recorded against this tree before publication:

| Check | Result |
| --- | --- |
| `PYTHONPATH=src python -m unittest discover -s tests` | 958 passed, 1 skipped |
| `scripts/check_source_quality.py src` | passed, with an empty length exemption list |
| `ruff check src tests` | passed (`E9`, `F`) |
| scoped `mypy` on the boundary modules | passed |
| coverage | 85% total; `verify.sh` fails under 75% |

The scoped type check covers `deployment_boundary`, `outcome_policy`,
`evidence_io`, `path_guard`, and `web/auth`. The rest of the kernel is still
dictionary-shaped and is not under a whole-tree type check.

## What changed for operators

| Area | Behavior |
| --- | --- |
| Resume API | Model-planned writes and commands require explicit approval |
| Local HTTP | Non-JSON content types are rejected. Host must be the loopback listener. A foreign `Origin` is rejected |
| Model config | Changing the endpoint host does not keep the stored API key |
| Shell | `dev-local-token` and `OneCode123!` are rejected and replaced with random persisted credentials. Open registration is off |
| Commands | `ONECODE_RUN_COMMAND_SANDBOX` defaults to `auto`: Docker when the daemon is ready, otherwise the host allowlist |
| Verifier | A path such as `tools/python` cannot impersonate Python. The child process does not inherit API keys |
| Approval plans | Integrity is an HMAC under `ONECODE_HOME/approval-plan.key` |
| Evidence | Reads and resume checkpoints must stay inside the run directory. New JSONL files are mode `0600` |
| TUI | Default workspace is the current directory, or `ONECODE_TUI_WORKSPACE` |
| Doctor | Adds `deployment_boundary` with `production_ready` |
| Verify | `scripts/verify.sh` runs length checks, Ruff, scoped mypy, coverage, tests, and doctor |
| Install | This checkout's virtualenv imports `src/onecode` from this repository |

## Structure

- I Ching analysis methods moved into `hexagram_profile.py`, `hexagram_dynamics.py`, and `hexagram_certificates.py`. `IchingKernel` keeps the same methods.
- Runner decisions go through `outcome_policy.py`. The skip decision still calls `IchingKernel.should_skip`.
- CLI `main` dispatches to command functions. Training parsers live in `register_training_parsers`.
- Evidence locks, hashes, and atomic writes live in `evidence_io.py`.
- Gateway HTML lives in `src/onecode/web/gateway_console.html`.
- Self-audit lives in `onecode.self_audit`.
- `allow_evidence`, `collapse_decision`, `prompt_rules`, and `iching_migration` live in `onecode.experimental`, with the old import paths kept.
- `tmp/` and `output/` are no longer tracked.

## Still open

- `production_ready` stays false until Docker is available, unauthenticated local access is off, and `ONECODE_API_TOKEN` is set.
- Whole-tree mypy is not enabled.
- `docs/closure/` and `docs/superpowers/` remain as historical records. `docs/INDEX.md` says so.
- This is not a public production release.
