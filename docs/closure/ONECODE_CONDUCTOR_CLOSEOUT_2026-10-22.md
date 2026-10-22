# Conductor closeout, 2026-10-22

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. The code commit is `d6e00ce` on `main`, after `33e5d29`. No new hexagram was added. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`.

This close records the shell conductor added on top of [ONECODE_ASSET_WRITE_CLOSEOUT_2026-10-21.md](ONECODE_ASSET_WRITE_CLOSEOUT_2026-10-21.md). The long-task scheme remains [ONECODE_LONG_TASK_PLAN_2026-10-21.md](ONECODE_LONG_TASK_PLAN_2026-10-21.md). Unattended multi-step editing, a second repair inside one run, fuzzy patches, and sandbox network are not in this close.

## What changed

- A patch that does not match, or a patch-only sandbox check that still fails, opens one new approval for a complete file. If that later plan also misses, the run stays halted. It does not open a third plan. The single in-run repair is unchanged.
- Confirmed memory is loaded into the next preface. It is stored only when the caller sets `confirm_memory` and the turn status is `completed`. A halted turn is not stored.
- Names from `.onecode/mcp_servers.json` are listed in that preface. Calling an MCP tool still requires an approval plan.

## n100 verification

Host `yami-n100`, tree `~/onecode-rule-check`, synced from `85eefbe`. Docker was ready. The model for the live tasks was `claude-sonnet-5`.

Five focused tests passed on that host:

- a missed patch opens one complete-file approval
- a second miss does not open another rewrite
- a completed turn with `confirm_memory` is stored, and a halted turn is not
- confirmed memory and the MCP server name appear in the next preface
- a `glob_files` call without `pattern` does not end the survey

Live tasks, chat path, sandbox `python3 -m unittest discover -s tests`. Preset tests were unchanged.

| Task | Plans | Result |
| --- | --- | --- |
| Scale, fix existing `src/scale.py` | 1 approval, 1 asset, 0 patches | completed, code 39, deliverable, verifier passed |
| Wharf, write `src/tide.py` and `src/berth.py` | 2 approvals, each 1 asset and 0 patches | completed, code 39, deliverable, verifier passed, both files present |

Neither live task needed the missed-patch rewrite. That path is the unit test above, not a live model miss.

## Gate

`bash scripts/verify.sh` on the Mac passed: 1270 tests, 1 skipped, doctor status `ok`. This Mac reports `docker_ready` false. n100 remains the sandbox host.

GitHub Actions `verify` is still red on Python 3.11, 3.12, and 3.13. The only failure is `test_demo_v07_script_runs_with_current_interpreter`. The demo plan completes and the unittest passes; the test still expects `halted / blocked`. That mismatch dates from the `v1.0.0` push. It is outside this slice.

## Still sealed

One implementation repair inside a run. Exact patch match. Sandbox `--network none`. Eight turns, two tools a turn, three read-only subagents. LibreChat's own agent loop stays off. This close does not claim mainstream-agent parity.
