# Shell read closeout, 2026-10-21

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. This close is commit `812bab7` on `main`, after `8d6ad91`. No new hexagram was added. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`.

The task rules stay the reading in [ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md](ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md). This note records the chat path that sits on those rules.

## What the chat path does

A change task asks the model for read-only tools before the write plan. The survey uses the existing agent cycle, at most four turns and two tools a turn. A write tool in that survey is dropped and does not create a file. An invalid JSON tool list is asked once more on the same step. If it is still unusable, the survey falls back to the named files and the matching test. A model timeout stops as `model_provider_timeout`, returns HTTP 504, and keeps a single model-call trace. It does not start the write.

The approval message shows the unified diff, and for a patch the search block and the replace block. After a failed sandbox check, that message also shows the verifier tail. The human can reject that plan before the one implementation repair is used.

Approving the next named file accepts an import of a `src` module that is already on disk. The first live pass of the two-file task stopped here: claiming `src/pay.py` reported `imports missing module shift` even though `src/shift.py` had just been written. `812bab7` loads the on-disk module names when the stored plan is claimed. The same task was run again and finished.

An optional `stage` object on an approval writes host bytes only when `approved` is true. The sandbox network stays `none`.

## Live tasks

n100 (`yami-n100`) is the acceptance host. This Mac had no working Docker, so the sandbox tasks ran there. The model was `claude-sonnet-5` through an OpenAI-compatible chat endpoint. Each task went through the chat handler: survey, approval, execute, then `python3 -m unittest discover -s tests` in the sandbox. Preset tests were hashed before and after.

| Task | Approvals | Survey calls | Result | Tests |
| --- | --- | --- | --- | --- |
| Baggage fee, write `src/baggage.py` only | 1 | 3 | completed, code 39, deliverable, verifier passed | `tests/test_baggage.py` unchanged |
| Shift and pay, write `src/shift.py` and `src/pay.py` | 2 | 3 | completed, code 39, deliverable, verifier passed, both files present | `tests/test_shift.py` unchanged |
| Locker, fix the existing `src/lockers.py` | 1 | 3 | completed, code 39, deliverable, verifier passed | `tests/test_lockers.py` unchanged |
| Notes, use the existing `RATE` | 1 | 3 | completed, code 39, deliverable, verifier passed, `RATE = 8` still present | `tests/test_notes.py` unchanged |

The shift task's first attempt is the claim failure described above. The row is the rerun after `812bab7`. The approval text included a diff on every completed task. None of these four needed the post-check repair: the first approved plan already satisfied the tests. That repair path remains covered by the unit tests, including one repair and a blocked second failure.

The survey calls were real model tool choices. Baggage and shift started from the preset test file. Locker read `src/lockers.py` and `tests/test_lockers.py`. Notes read `src/notes.py` and `tests/test_notes.py`.

## Gate

`bash scripts/verify.sh` on this tree passed: 1262 tests, 1 skipped, coverage 86%, doctor status `ok`. The skip is `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is not set. On this Mac, doctor reports `docker_ready` false and `production_ready` false. n100 remains the sandbox acceptance host.

## Shell

LibreChat `v0.8.8` stays the chat shell. OneCode stays the only executor. LibreChat's own agents, code workspaces, programmatic tools, background tools, and scheduled chats stay off. The integrated fork branch `feature/onecode-shell-v088` is on `aidi1723/LibreChat` at `ad9bbe09d`. Start it with `--librechat-dir`. The folder picker remains macOS-only. The full LibreChat client suite was not run.

## What this close does not change

One implementation repair. A patch must match exactly. The sandbox stays `--network none`. Repeated invalid plans halt at Li/Kun (40) and block delivery. A turn still allows two tools, the cycle cap stays 8, and read-only subagents stay at three. This close does not claim mainstream-agent parity. The 30 scripted local tasks remain an oracle record, not a model solve rate.
