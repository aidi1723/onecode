# Controlled scope and agent evolution closeout, 2026-10-23

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. The code commit is `e61a4b6` on `main`. No new hexagram was added: the state space remains the closed 6-bit 64-hexagram space ($Q_6 = \{0..63\}$). `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies remain empty (`dependencies = []`).

This closeout records the completion of all nine tasks outlined in [ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md](ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md) and [ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md](ONECODE_NEXT_DEVELOPMENT_HANDBOOK_2026-10-23.md), covering Phase I (Controlled Scope Closure), Phase II (Agent Perception & Editing Foundation), and Phase III (ReAct Cycle & Targeted Self-Healing), verified both locally on macOS and in live Docker sandbox on host `n100`.

---

## 1. What changed

### Phase I: Controlled Scope Closure
- **Explicit Sandbox Requirement (Task 1)**: `ONECODE_RUN_COMMAND_SANDBOX=auto` rejects execution on hosts lacking Docker by returning `sandbox_required` without falling back to host execution. Tests in `tests/test_rule_parallel_tasks.py` and `tests/test_rule_action_tasks.py` branch on `host_mode or _docker_daemon_ready()`, enabling gate pass on macOS without Docker and full Docker container rule execution on Linux.
- **Preset Test Anti-Tampering Guard (Task 2)**: Added `src/onecode/kernel/preset_tests.py`. `validate_model_plan` rejects model writes/patches to `tests/`. `verify_shell_write` captures pre-execution SHA-256 snapshots of all test files in `tests/`; if any test file is modified or removed, delivery halts immediately with `reason="verifier_failed"`, `delivery_status="blocked"`, and `preset_tests_changed=True`, refusing to execute compromised tests.
- **Global WAL Test Hash Ledger & Integrity Verification (Task 3)**: Completed task delivery records sorted preset test hashes in the global WAL (`.onecode/global-ledger.jsonl`) under the `th` field (`[{"p": path, "s": sha256}]`). Added `ledger_matches_workspace(workspace)` in `src/onecode/kernel/run_inspection.py` to verify workspace files against WAL entries, distinguishing `preset_test_hash_mismatch`, `asset_hash_mismatch`, and WAL chain hash mismatches.

### Phase II: Perception & Editing Foundation
- **Line-Range Pagination & Line Numbering (Task 4)**: Upgraded `ReadTextTool` in `src/onecode/kernel/execution_tools.py` with optional `start_line`, `end_line` (1-indexed, inclusive) and `line_numbers: bool = False`, returning line count metadata while remaining 100% backward-compatible when omitted.
- **Decoupled Search Misses & Expanded Observation Window (Task 5)**: In `src/onecode/kernel/agent_cycle.py`, decoupled exploratory read misses (`read_miss_streak` capped at configurable `max_read_misses`, default 2, survey reads up to 4) from mutating write stalls (`miss_streak >= 2`). Added configurable `output_limit` (default 1,500 chars, survey reads expanded to 4,000 chars).
- **Whitespace-Tolerant Patching & Context Feedback (Task 6)**: In `src/onecode/kernel/patching.py`, removed duplicate return; added `_replace_trailing_whitespace_normalized` for unique match with trailing-whitespace normalization while still rejecting ambiguous occurrences with `patch_search_ambiguous`; implemented `find_closest_patch_context` to return line numbers and best-matching file context when a patch search block fails.

### Phase III: ReAct Cycle & Targeted Self-Healing
- **Targeted Unittest Runner & Two-Stage Verifier (Task 7)**: Whitelisted safe targeted test module/path invocations in `src/onecode/kernel/verifier.py:verifier_command_allowed`. Implemented `run_two_stage_verifier` and `targeted_test_for_path`: modified source files run their targeted test first (`python-unittest-targeted`), short-circuiting on failure to provide focused error traces, then proceed to full discover regression (`python-unittest`). Wired into `verify_shell_write`.
- **Multi-Attempt Patch Repair Loop (Task 8)**: Upgraded `_finish_verified_task` in `src/onecode/kernel/model_loop.py` to support configurable `max_repair_attempts` (default 1 for backward compatibility), allowing multi-round patch repairs. Injected `find_closest_patch_context` and verifier stdout/stderr tails into `repair_prompt`.
- **Strict vs Scoped-Auto Approval (Task 9)**: In `src/onecode/kernel/approval_plans.py`, implemented `model_plan_requires_approval` with `mode="strict"` (default, all mutations require approval) and `mode="scoped_auto"` (auto-allows edits inside `src/` while strictly requiring human approval for `git_commit`, `mcp.*`, `run_command`, and root configuration files).

---

## 2. n100 verification

Host `yami-n100` (`10.0.0.184`), Ubuntu Linux 24.04, Python 3.12.3, Docker version 29.1.3 (`python:3.12-slim`).

1. **Focused Phase I, II, III Test Suite**:
   `PYTHONPATH=src .venv/bin/python -m unittest tests.test_preset_tests tests.test_wal tests.test_execution_tools tests.test_agent_cycle tests.test_patching tests.test_verifier tests.test_model_loop tests.test_approval_plans tests.test_rule_action_tasks tests.test_rule_parallel_tasks`
   - **Result**: `Ran 192 tests in 33.248s, OK` (including real Docker execution of all 64 hexagram rules).

2. **Live Docker E2E Verification Suite**:
   Executed `test_e2e_n100.py` exercising real Docker containers (`--network none`):
   - `test_1_docker_sandbox_two_stage_verification`: Real isolated Docker container spun up and verified code in two stages (`python-unittest-targeted` + `python-unittest`). **Passed**.
   - `test_2_verify_shell_write_and_wal_integrity`: Full pipeline from file write, two-stage Docker verifier execution, achieving hexagram 39, recording `preset_test_hashes` in global WAL (`.onecode/global-ledger.jsonl`), and verifying full chain cryptographic integrity (`ledger_matches_workspace` returns `None`). **Passed**.
   - `test_3_preset_test_tampering_blocked`: Modifying `tests/test_calc.py` halts immediately before running the verifier with `status="halted"`, `delivery_status="blocked"`, `reason="verifier_failed"`. **Passed**.
   - `test_4_patch_repair_context_recovery`: Trailing-whitespace normalized patch commit fixes injected bug, Docker verifier passes, reaching hexagram 39. **Passed**.
   - **Result**: `Ran 4 tests in 9.038s, OK`.

3. **Full Host Gate**:
   `bash scripts/verify.sh` on `n100`:
   - `compileall`: OK
   - `source-quality`: OK (all functions $\le 160$ lines, classes $\le 500$ lines)
   - `ruff`: All checks passed!
   - `mypy`: Success: no issues found in 104 source files
   - `unittest`: **1,289 tests passed**
   - `coverage`: **86%**
   - `doctor`: status `ok` (`api_token_set: true, command_sandbox: "auto", docker_ready: true, production_ready: true, sandbox_effective: true`)

---

## 3. Local Gate (macOS)

`bash scripts/verify.sh` on macOS (without Docker):
- `compileall`: OK
- `source-quality`: OK
- `ruff`: All checks passed!
- `mypy`: Success: no issues found in 104 source files
- `unittest`: **1,289 tests passed**
- `coverage`: **86%**
- `doctor`: status `ok` (`docker_ready: false, sandbox_effective: false`)

---

## 4. Still sealed boundaries

- The 64-hexagram state space ($Q_6$) remains closed; no 65th state or out-of-band control flow.
- Docker sandbox execution remains `--network none`.
- PathGuard boundary remains strictly enforced: path traversal (`..`), symbolic link escapes, `.git`, `.onecode`, `.env*`, and root files are blocked from unapproved mutation.
- Preset test anti-tampering cannot be bypassed by model plans or prompt injection.
- Zero third-party core runtime dependencies (`dependencies = []`).
- `claims_mainstream_parity` remains `false`.
