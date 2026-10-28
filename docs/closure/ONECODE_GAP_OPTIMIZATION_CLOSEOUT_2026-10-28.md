# Gap optimization closeout, 2026-10-28

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. No new hexagram was added. `IchingKernel.classify_outcome` was not edited. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies stay `dependencies = []`.

This note closes the phase in [ONECODE_GAP_OPTIMIZATION_HANDBOOK_2026-10-28.md](ONECODE_GAP_OPTIMIZATION_HANDBOOK_2026-10-28.md). The exam it answers is [ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md](ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md). n100 was offline for this closeout. The 31 `no_actionable_plan` tasks were not re-run.

## What the exam showed

On n100, 80 WorkBuddy code tasks, chat path, `gpt-6.1-sol`, `https://anyrouter.top/v1/responses`:

| Result | Count |
| --- | --- |
| `completed`, hexagram 39 | 12 |
| `no_actionable_plan` | 31 |
| `model_provider_error` (HTTP 520, `Origin Error`) | 36 |
| empty `replace_block` raised `ValueError` | 1 |
| numeric host rewards | 16, mean 0.190, none at 1.0 |
| `ungraded` | 64 |

Hidden tests stayed out of the model workspace. The host grader is not a Harbor score.

## What this phase changed

- A Python path named in the task is the write target, and up to four named files are copied into the preface.
- A file already read into the preface outranks the first eight alphabetical paths.
- Identifiers in the task select up to four implementation files. The default survey reads those files first and still includes the matching `tests/test_*.py` when it exists.
- A task that names one JSON file and says not to change business code targets that JSON file.
- A task that asks only for tests may add one new `tests/*.py` file and may import `unittest`. An existing preset test whose hash changes still blocks delivery. Patches under `tests/` stay rejected. `conftest.py`, `unittest.py`, and `pytest.py` cannot be added.
- An empty `replace_block` is an invalid plan. Building that patch returns `invalid_intent` and does not raise.
- Preset-test hashes are captured before host staging. An existing test file cannot be staged over.
- MCP names in the preface come from `ONECODE_HOME/mcp_servers.json`.
- A shadow module such as `src/unittest.py` cannot be written.
- HTTP 520 is retried twice. A third failure stays `model_provider_error`.

## What stays outside this phase

- Three HTTP 520 failures in a row are still a channel failure.
- The host grader is still not the official Harbor score. `gold.patch` stays out of the model workspace.
- Existing preset tests stay immutable.
- Someone who holds `ONECODE_HOME/approval-plan.key` can still rewrite the local ledger.
- `claims_mainstream_parity` stays false.

## Gate

`bash scripts/verify.sh` on this Mac, without Docker:

- `unittest`: `Ran 1327 tests`, `OK (skipped=1)`
- skipped test: `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is unset
- `coverage`: 86% (14355 statements, 1964 missed)
- `doctor`: status `ok` (`docker_ready: false`, `production_ready: false`)

n100 was not asked to re-run this gate. n100 remains the sandbox acceptance host.
