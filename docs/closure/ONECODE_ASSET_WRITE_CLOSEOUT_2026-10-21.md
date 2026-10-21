# Asset-write closeout, 2026-10-21

Version stays 1.0.0. Tags `v1.0.0` and `v0.8.0` stay at `dd51424` and `e1adb3c`. No new hexagram was added. `claims_mainstream_parity` stays false. This close sits on [ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md](ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md). The long-task scheme is [ONECODE_LONG_TASK_PLAN_2026-10-21.md](ONECODE_LONG_TASK_PLAN_2026-10-21.md). It is not implemented here.

## What changed

- A chat write asks for one complete Python asset. A task with several missing files still asks for one new file at a time. Patches stay on the single post-check repair.
- The repair prompt omits paths under `tests/` and says not to patch them.
- The write prompt says not to install packages or use the network.
- A survey tool that raises `ValueError` is a search miss, so the read cycle can continue. `action_exception` and `search_miss` from the survey do not block the later write. A path escape still stops as `sovereignty_breach`.

## Live tasks

n100, model `claude-sonnet-5`, chat path, sandbox unittest. Preset tests were hashed before and after.

| Task | Plan shape | Result |
| --- | --- | --- |
| Parking fee, write `src/parking.py` | survey read the preset test | completed, code 39, verifier passed, test unchanged |
| Scale, fix existing `src/scale.py` | 1 asset, 0 patches | completed, code 39, verifier passed, test unchanged |
| Library late fee, write `src/library.py` | 1 asset, 0 patches | completed, code 39, verifier passed, test unchanged |
| Wharf, write `src/tide.py` and `src/berth.py` | first survey called `glob_files` without `pattern` and halted as `action_exception` | no source written, test unchanged |
| Wharf rerun after the search-miss change | 2 approvals, each 1 asset and 0 patches | completed, code 39, both files present, verifier passed, test unchanged |

None of these runs used the post-check repair. That path stays covered by the unit tests.

## Gate

`bash scripts/verify.sh` passed: 1266 tests, 1 skipped, doctor status `ok`. This Mac still reports `docker_ready` false. n100 remains the sandbox host.

GitHub Actions `verify` is still red on Python 3.11, 3.12, and 3.13. The only failure is `test_demo_v07_script_runs_with_current_interpreter`: the demo plan is `completed / deliverable` with `python-unittest passed`, and the test still expects `halted / blocked`. That mismatch has been present since the `v1.0.0` push. It is not a failure of these live tasks.
