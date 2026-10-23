# Controlled scope and agent evolution closeout, 2026-10-23

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. The code commit is `e61a4b6` on `main`. No new hexagram was added: the state space remains the closed 6-bit 64-hexagram space ($Q_6 = \{0..63\}$). `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies remain empty (`dependencies = []`).

This closeout records the nine tasks in [ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md](ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md). The code is `e61a4b6`. The first record of that work is `47cccdf`. This correction replaces the test count and withdraws the four `test_e2e_n100.py` results. That script is not in the repository, and it was not found on n100 under `/tmp` or the home directory.

---

## 1. What changed

### Phase I: Controlled Scope Closure
- **Explicit Sandbox Requirement (Task 1)**: `ONECODE_RUN_COMMAND_SANDBOX=auto` rejects execution on hosts lacking Docker by returning `sandbox_required` without falling back to host execution. Tests in `tests/test_rule_parallel_tasks.py` and `tests/test_rule_action_tasks.py` branch on `host_mode or _docker_daemon_ready()`, enabling gate pass on macOS without Docker and full Docker container rule execution on Linux.
- **Preset Test Anti-Tampering Guard (Task 2)**: Added `src/onecode/kernel/preset_tests.py`. `validate_model_plan` rejects model writes/patches to `tests/`. `verify_shell_write` captures pre-execution SHA-256 snapshots of all test files in `tests/`; if any test file is modified or removed, delivery halts immediately with `reason="verifier_failed"`, `delivery_status="blocked"`, and `preset_tests_changed=True`, refusing to execute compromised tests.
- **Global WAL Test Hash Ledger & Integrity Verification (Task 3)**: Completed task delivery records sorted preset test hashes in the global WAL (`.onecode/global-ledger.jsonl`) under the `th` field (`[{"p": path, "s": sha256}]`). Added `ledger_matches_workspace(workspace)` in `src/onecode/kernel/run_inspection.py` to verify workspace files against WAL entries, distinguishing `preset_test_hash_mismatch`, `asset_hash_mismatch`, and WAL chain hash mismatches.

### Phase II: Perception & Editing Foundation
- **Line-Range Pagination & Line Numbering (Task 4)**: Upgraded `ReadTextTool` in `src/onecode/kernel/execution_tools.py` with optional `start_line`, `end_line` (1-indexed, inclusive) and `line_numbers: bool = False`, returning line count metadata while remaining 100% backward-compatible when omitted.
- **Decoupled Search Misses & Expanded Observation Window (Task 5)**: In `src/onecode/kernel/agent_cycle.py`, decoupled exploratory read misses (`read_miss_streak` capped at configurable `max_read_misses`, default 2, survey reads up to 4) from mutating write stalls (`miss_streak >= 2`). Added configurable `output_limit` (default 1,500 chars, survey reads expanded to 4,000 chars).
- **Whitespace-tolerant unique patch (Task 6)**: A unique match may ignore trailing spaces and tabs, and it may keep a unique first-line indent prefix. Zero matches stay `patch_search_not_found`. More than one match stays `patch_search_ambiguous`.

### Phase III: Repair budget and approval mode
- **Targeted then full verifier (Task 7)**: `run_two_stage_verifier` can run one targeted unittest first, then `python -m unittest discover -s tests`.
- **Configurable repair count (Task 8)**: `run_model_task` defaults `max_repair_attempts` to `0`. The chat path passes `1`. A caller can pass a higher count. A failed check remains `verifier_failed`, Li/Kun (40). `classify_outcome` was not changed, and an in-progress repair is not a Kan/Zhen (17) state.
- **Approval mode (Task 9)**: `model_plan_requires_approval` defaults to `strict`. `scoped_auto` is used only when the caller passes that mode. The chat path does not pass it. `git_commit`, `run_command`, `mcp.*`, and paths outside `src/` still require approval under `scoped_auto`.

---

## 2. n100 verification

On 2026-10-23 the current `src/`, `tests/`, `scripts/`, and `pyproject.toml` were synced to `~/onecode-rule-check` on `yami-n100`. `bash scripts/verify.sh` then used `~/onecode-linux-test/.venv/bin/python`.

- `compileall`: OK
- `source-quality`: OK
- `ruff`: all checks passed
- `mypy`: no issues found in 104 source files
- `unittest`: `Ran 1293 tests` in 375.096s, `OK (skipped=2)`
- skipped tests: `test_four_known_leaks_remain_pytest_rules` because the distilled dataset is not mounted, and `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is unset
- `coverage`: 86% (`13969` statements, `1935` missed)
- `doctor`: status `ok` (`docker_ready: true`, `sandbox_effective: true`, `production_ready: true`, `api_token_set: true`)

`test_e2e_n100.py` is not in this repository and was not found on that host. These four named results are withdrawn:

- `test_1_docker_sandbox_two_stage_verification`
- `test_2_verify_shell_write_and_wal_integrity`
- `test_3_preset_test_tampering_blocked`
- `test_4_patch_repair_context_recovery`

There is no SWE-bench Lite run in this record.

---

## 3. Local Gate (macOS)

`bash scripts/verify.sh` on this Mac, without Docker, against the tree at `47cccdf` before this documentation correction:

- `compileall`: OK
- `source-quality`: OK
- `ruff`: all checks passed
- `mypy`: no issues found in 104 source files
- `unittest`: `Ran 1293 tests`, `OK (skipped=1)`
- skipped test: `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is unset
- `coverage`: 86% (`13969` statements, `1932` missed)
- `doctor`: status `ok` (`docker_ready: false`, `sandbox_effective: false`, `production_ready: false`)

The earlier figure of 1,289 tests passed does not match this run.

---

## 4. Still sealed boundaries

- The 64-hexagram state space remains closed. `src/onecode/kernel/hexagram.py` is not in `e61a4b6`.
- Docker sandbox network default remains `none`.
- Core runtime dependencies remain `dependencies = []`.
- `claims_mainstream_parity` remains `false`.
- The chat path still asks for approval and still passes `max_repair_attempts=1`.
- There is no separate UI report file named `ONECODE_UPDATE_AND_CLOSEOUT_REPORT_2026-10-23` in this repository. This note is the record.
