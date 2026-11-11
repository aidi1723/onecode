# Task rule follow-up, 2026-10-20

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Commit `654ddb2` is the first follow-up on `main`. This note is the current task-rule reading, including the 2026-10-21 close. No new hexagram was added. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`.

The formal release record remains [ONECODE_V1_0_RELEASE_2026-10-20.md](ONECODE_V1_0_RELEASE_2026-10-20.md).

## Rules

When `max_repair_attempts` is greater than zero, a task that names Python paths under `src/` or `tests/` receives one write slot for each path it asks to create or fix, and at least as many slots as the repair count. A path introduced by "do not modify" or left outside an "only" path is protected: it is not a missing file, and a plan does not write it. Once the required files are written, the sequence closes into the sandbox check. A later unusable plan does not replace that cooled write. If the task names no files, using up the slots without `no_action` still halts as `resource_budget_exceeded`, Li/Kun (40), and keeps the files.

An invalid JSON plan, a plan that mixes `no_action` with actions, or a plan whose task string is empty retries once on the same step. The retry span ends in `-retry`. A second invalid plan halts as `invalid_model_plan`, Li/Kun (40). Empty asset content and a truncated plan do not get that retry. Truncation stays `resource_budget_exceeded`. An import of a `src` module that is already on disk counts as present.

A completed write with a sandbox config and a `tests/` directory runs `python3 -m unittest discover -s tests` in the sandbox. A pass stays deliverable at the cooled write, Gen/Qian (39). A failure with repair attempts remaining gets one patch of the implementation. A patch under `tests/` is `repair_plan_must_use_patches_only`, Li/Kun (40), and the tests stay as they were. The check then runs again. A second failure is `verifier_failed`, Li/Kun (40), delivery blocked, files kept. With `max_repair_attempts` at 0, the first failure halts the same way.

Gateway statuses 408, 429, 502, 503, and 504 are `model_provider_timeout`, Kan/Zhen (17), checkpoint. Statuses 401 and 403 stay `model_provider_error`, Li/Kun (40).

## Live tasks

n100 is the acceptance host. The model was `claude-sonnet-5` through an OpenAI-compatible endpoint. The sandbox image name was `python:3.12-slim`, which resolves to the local native sibling.

On 2026-10-20, three tasks in `/tmp/onecode-complex-4` finished deliverable at code 39, action `cooldown`:

| Task | Calls | Check |
| --- | --- | --- |
| `page-fix` | 1 write of `src/pages.py` | `tests/test_pages.py` unchanged, unittest passed |
| `ballot` | first call was invalid JSON; the same-step retry wrote 4 files | unittest passed |
| `shift` | 1 call wrote 4 files | unittest passed |

An earlier ledger repair in `/tmp/onecode-complex-2/ledger-repair` used the one implementation patch: `repaired` true, one repair attempt, the public balance API kept, unittest passed, code 39.

The model did not exhaust the named-file slots, fail the second sandbox check, or return 502 during these tasks. Those three paths are covered by `tests/test_model_loop.py`.

On 2026-10-21, after the protected-path rules were on n100, these tasks finished deliverable at code 39, action `cooldown`:

| Task | Result |
| --- | --- |
| `fare` | preset `tests/test_fares.py` unchanged, sandbox unittest passed |
| `loans` | 4 files, sandbox unittest passed |
| `grades` | one implementation repair, preset tests unchanged, sandbox unittest passed |
| `seats` | 4 files, sandbox unittest passed |
| `meter` | preset `tests/test_meters.py` unchanged, sandbox unittest passed. 250 kWh is 3100 cents at the stated rates |
| `postage` | the first plan did not complete; one repair left the preset tests unchanged and the sandbox unittest passed |
| `warehouse` | 4 files, sandbox unittest passed |

`clinic` halted at Li/Kun (40), `invalid_model_plan`, delivery blocked. The same-step retry still returned invalid JSON or mixed `no_action` with actions. One round kept only `src/slots.py`. The named files were not all written, so the sequence did not close into the check.

## Close

Tag `v1.0.0` stays on `dd51424`. Tag `v0.8.0` stays on `e1adb3c`. The first follow-up commit is `654ddb2`. The protected-path close is `e4a6eb4` on `main`. The 1.0.0 gate of 1219 tests and 1 skipped remains the count recorded for that tag.
