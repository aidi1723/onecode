# Controlled-scope plan, 2026-10-22

> **For agentic workers:** Implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. Commit only when the operator asks for that slice. Do not push unless the operator asks.

**Goal:** Deepen the current product around a named file, one approval per write, preset tests that stay unchanged, and a local hash ledger that can be checked again.

**Architecture:** The shell stays the conductor. Each write is still one kernel entry and one human approval. This plan does not lengthen the in-run loop. Slice 1 closes the audit edits already in the working tree and stops the command-rule test from needing a host fallback. Slice 2 refuses a plan that writes under `tests/` and blocks delivery when those files change. Slice 3 records the preset-test hashes on the global ledger and checks them against the workspace.

**Tech Stack:** Python 3.11+, standard library, existing unittest gate `bash scripts/verify.sh`. Acceptance host remains n100 with Docker. This Mac has no Docker.

This plan is not a permission to change sealed rules. It sits on [ONECODE_LONG_TASK_PLAN_2026-10-21.md](ONECODE_LONG_TASK_PLAN_2026-10-21.md) and [ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md](ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md). `claims_mainstream_parity` stays false. Version stays 1.0.0. Tags `v1.0.0` and `v0.8.0` stay where they are. No new hexagram. `IchingKernel.classify_outcome` is not edited.

The ledger stays a local `prev` plus SHA-256 chain in `.onecode/global-ledger.jsonl`. A passing check is a local reproduction. It is not an external witness.

## Positioning this plan implements

- **定点受控.** The task names the file. The preset test is already there. A protected path is not written.
- **一次批准.** Each write waits for `approved: true`. Several files are several approvals.
- **测试防篡改.** A plan that touches `tests/` is rejected. A delivery whose preset tests changed is halted.
- **哈希账本可复现.** The delivery entry stores the asset sha256 values it already stores, plus the preset-test hashes. A later read compares those hashes to the files on disk.

## What stays sealed

- No new hexagram. `classify_outcome` is unchanged.
- One implementation repair inside a single run. A second failed check is `verifier_failed`, Li/Kun (40), delivery blocked.
- A patch that does not match stays `patch_search_not_found`. There is no fuzzy apply.
- One later complete-file rewrite is a new approval. A second miss stays halted.
- The sandbox stays `--network none`.
- The agent cycle default stays 8 turns and 2 tools a turn. Read-only subagents stay at 3.
- LibreChat's own agents, code workspaces, programmatic tools, background tools, and scheduled chats stay off.
- User-Agent stays `onecode/0.8`.
- `ONECODE_RUN_COMMAND_SANDBOX=host` is not the default and is not added to `scripts/verify.sh`.

## Already in the working tree

These edits are written and covered by their own tests. Slice 1 does not rewrite them.

- `tests/test_verify_script.py` accepts a passed verifier as `completed / deliverable`, and a failed verifier as `halted / blocked`.
- `src/onecode/tui/app.py` sets `APP_VERSION = __version__`. `tests/test_version.py` does not import `onecode.tui.app`.
- `src/onecode/self_audit.py` treats a missing `textual` import as a passed check with `skipped_reason: textual_not_installed`.
- `src/onecode/kernel/execution_tools.py` returns `sandbox_required` when mode `auto` has no Docker. Explicit `host` still runs on the host. `tests/test_execution_tools_fallback.py` expects that refusal.

## Slice 1: Close the command-rule test

`tests/test_rule_parallel_tasks.py` `test_every_hexagram_patches_and_commands` runs 64 `run_command` steps. `GuardrailConfig.max_consecutive_failures` stays 3. On this Mac, `auto` now refuses the host, three allowed commands fail, and the trace stops at 37 results. The assertion `len(command_by_id) == 64` fails. Setting `ONECODE_RUN_COMMAND_SANDBOX=host` makes that one test pass and also runs the commands on the host. The gate must pass without that variable.

**Files:**

- Modify: `tests/test_rule_parallel_tasks.py`
- Modify: `tests/test_rule_action_tasks.py`
- Test command: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_rule_parallel_tasks tests.test_rule_action_tasks tests.test_execution_tools_fallback tests.test_verify_script.VerifyScriptTests.test_demo_v07_script_runs_with_current_interpreter tests.test_self_audit_cli tests.test_version -q`

- [x] **Step 1: Change the command half of the test**

Keep the patch half as it is. Replace the command assertions with this environment split. `host_mode` is only true for `host`, `off`, `false`, and `0`.

```python
host_mode = os.environ.get("ONECODE_RUN_COMMAND_SANDBOX", "auto").strip().lower() in {
    "host",
    "off",
    "false",
    "0",
}
self.assertEqual(len(patch_by_id), 64)
if host_mode:
    self.assertEqual(len(command_by_id), 64)
else:
    self.assertGreater(len(command_by_id), 0)
    self.assertLess(len(command_by_id), 64)
for code in range(64):
    ruling = IchingKernel.action_ruling(code, "patch_text")
    command_ruling = IchingKernel.action_ruling(code, "run_command")
    patched = (workspace / "src" / f"p{code}.py").read_text(encoding="utf-8")
    marker = workspace / f"c{code}.txt"
    with self.subTest(code=code):
        if ruling["outcome"] == "write":
            self.assertEqual(patched, "VALUE = 2\n")
            self.assertEqual(patch_by_id[f"patch-{code}"].status, "completed")
        else:
            self.assertEqual(patched, "VALUE = 1\n")
            self.assertEqual(patch_by_id[f"patch-{code}"].reason, ruling["reason"])
        recorded = command_by_id.get(f"command-{code}")
        if command_ruling["outcome"] != "write":
            self.assertFalse(marker.exists())
            if recorded is not None:
                self.assertEqual(recorded.reason, command_ruling["reason"])
            continue
        if host_mode:
            self.assertEqual(marker.read_text(encoding="utf-8"), "ran")
            self.assertEqual(recorded.status, "completed")
            continue
        self.assertFalse(marker.exists())
        if recorded is not None:
            self.assertNotEqual(recorded.status, "completed")
```

Add `import os` to that test file.

`tests/test_rule_action_tasks.py` `test_command_and_patch_follow_generation_and_control` also runs an allowed command. On this Mac, line 79 fails with `False is not true` while `ONECODE_RUN_COMMAND_SANDBOX` is unset. The tool payload has `returncode == 1` and `stderr == "sandbox_required"`. `execute_step` currently records the step reason as `action_exception`, because `RunCommandTool.execute` only promotes `image_platform_mismatch` from stderr into `reason`. The dam command and both patch calls stay as they are. Split only the nourishing command:

```python
host_mode = os.environ.get("ONECODE_RUN_COMMAND_SANDBOX", "auto").strip().lower() in {
    "host",
    "off",
    "false",
    "0",
}
if host_mode:
    self.assertTrue(allowed.success)
    self.assertEqual((workspace / "ran.txt").read_text(encoding="utf-8"), "ran")
else:
    self.assertFalse(allowed.success)
    self.assertFalse((workspace / "ran.txt").exists())
    self.assertEqual(allowed.step_results[0].reason, "action_exception")
    payload = allowed.step_results[0].tool_results[0].output["payload"]
    self.assertEqual(payload["returncode"], 1)
    self.assertEqual(payload["stderr"], "sandbox_required")
```

- [x] **Step 2: Run the focused tests**

Run the command in the slice header. Expected: the parallel test passes with `ONECODE_RUN_COMMAND_SANDBOX` unset. The fallback tests still expect `sandbox_required` under `auto`.

- [x] **Step 3: Run one explicit-host check**

```bash
ONECODE_RUN_COMMAND_SANDBOX=host PYTHONPATH=src .venv/bin/python -m unittest tests.test_rule_parallel_tasks.ParallelRuleTaskTests.test_every_hexagram_patches_and_commands tests.test_rule_action_tasks.RuleActionTaskTests.test_command_and_patch_follow_generation_and_control -q
```

Expected: OK, and this variable is not written into `scripts/verify.sh`.

- [x] **Step 4: Run the full gate**

```bash
bash scripts/verify.sh
```

`verify.sh` needs to run outside the Cursor sandbox because it creates a git repo and a `.cursor` directory. Result: passed with 1271 tests, 1 skipped (`test_global_onecode_command_points_to_project_entrypoint` when `ONECODE_GLOBAL_COMMAND` is unset), coverage 86%, and doctor status is `ok`.

- [ ] **Step 5: Commit only if the operator asks**

Suggested message: `fix: refuse host commands unless the sandbox mode is explicit`. Include the audit files listed above, `tests/test_rule_parallel_tasks.py`, and `tests/test_rule_action_tasks.py`. Leave this plan in the same commit only if the operator wants the document with the code.

## Slice 2: Preset tests cannot be rewritten into a pass

A repair prompt already says not to patch `tests/`. Plan validation does not yet reject a `tests/` asset. The live runner hashes tests outside the kernel. The kernel still needs its own check.

**Files:**

- Create: `src/onecode/kernel/preset_tests.py`
- Modify: `src/onecode/kernel/model_provider.py` `validate_model_plan`
- Modify: `src/onecode/web/api.py` `verify_shell_write` and the approval handler that calls it
- Test: `tests/test_preset_tests.py`
- Test: the existing model-plan tests that build a one-file asset

Keep each new function at or under 160 lines. Do not edit `IchingKernel.classify_outcome`.

- [x] **Step 1: Write the failing hash and rejection tests**

```python
def test_preset_test_hash_changes_when_the_file_changes(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "tests" / "test_fee.py"
        target.parent.mkdir()
        target.write_text("VALUE = 1\n", encoding="utf-8")
        before = preset_test_hashes(root)
        target.write_text("VALUE = 2\n", encoding="utf-8")
        self.assertNotEqual(before, preset_test_hashes(root))
        self.assertEqual(before["tests/test_fee.py"], hashlib.sha256(b"VALUE = 1\n").hexdigest())


def test_a_plan_that_writes_under_tests_is_invalid(self):
    for path in ("tests/test_fee.py", "Tests/test_pay.py"):
        with self.subTest(path=path):
            with self.assertRaises(ValueError) as caught:
                validate_model_plan(
                    {
                        "task": "keep the preset test",
                        "assets": [{"path": path, "content": "VALUE = 2\n"}],
                    }
                )
            self.assertIn("tests/", str(caught.exception))
```

`validate_model_plan` lives in `src/onecode/kernel/model_provider.py`. An asset object accepts `path` and `content` only. The `task` field is required.

- [x] **Step 2: Run the new tests and confirm they fail**

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_preset_tests -q
```

Expected: FAIL because `preset_test_hashes` and the `tests/` rejection are absent.

- [x] **Step 3: Implement the guard**

`preset_test_hashes(root)` walks `tests/**/*.py`, skips `__pycache__`, and returns a dict of workspace-relative path to SHA-256. Each key comes from `Path.relative_to(root).as_posix()`, so the separator is `/` on every system. An empty or missing `tests/` directory returns `{}`. The ledger field `th` sorts those posix keys.

In `validate_model_plan`, normalize a path with `path.replace("\\", "/").casefold()` before the check. Reject it when the normalized path is `tests` or starts with `tests/`. That includes `Tests/test_pay.py`. Raise `ValueError` with a message that contains `tests/`. Add that `Tests/` path to the rejection test beside `tests/test_fee.py`. The existing invalid-plan path already becomes `invalid_model_plan`, Li/Kun (40).

In the chat approval handler, call `preset_test_hashes(workspace)` after the plan is approved and before `verify_shell_write`. Pass that snapshot into `verify_shell_write`. If the snapshot differs from a fresh hash:

```python
if preset_test_hashes(workspace) != before:
    blocked = dict(result)
    blocked["status"] = "halted"
    blocked["reason"] = "verifier_failed"
    blocked["delivery_status"] = "blocked"
    blocked["preset_tests_changed"] = True
    return blocked
```

Use `verifier_failed` so the control reason stays inside the current set. `preset_tests_changed` is evidence on the result, not a new branch in `classify_outcome`. Do not run the sandbox unittest on the changed tests.

- [x] **Step 4: Lock the existing hexagram mapping**

```python
def test_preset_test_mismatch_uses_the_existing_verifier_halt(self):
    code = IchingKernel.classify_outcome("halted", "verifier_failed")
    self.assertEqual(code, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
```

- [x] **Step 5: Run the new tests and the chat approval tests**

Expected: PASS. A plan whose only change is `src/...` still validates. A plan that includes `tests/test_fee.py` does not.

- [ ] **Step 6: Full gate, then commit only if the operator asks**

Suggested message: `fix: block delivery when a preset test changes`.

## Slice 3: The ledger can be checked against the workspace

`global_wal_entry` already stores completed `write_text` and `patch_text` assets as `as`, with path `p` and sha256 `s`, when `evidence_mode` is `wal`. It does not store preset-test hashes. `read_validated_global_wal_segment` already rejects `global_wal_chain_prev_mismatch` and `global_wal_chain_hash_mismatch`.

**Files:**

- Modify: `src/onecode/kernel/checkpoint.py` `global_wal_entry`
- Modify: `src/onecode/kernel/run_inspection.py` where a segment is read
- Test: `tests/test_wal.py`
- Test: the inspection test that already reads a segment

- [x] **Step 1: Write the failing ledger test**

```python
def test_global_wal_entry_records_preset_test_hashes(self):
    with tempfile.TemporaryDirectory() as tmp:
        context = create_context(Path(tmp), run_id="wal-preset-tests")
        entry = global_wal_entry(
            context,
            {
                "run_id": "wal-preset-tests",
                "status": "completed",
                "partial": False,
                "reason": None,
                "intent_type": "write_text",
                "evidence_mode": "wal",
                "preset_test_hashes": {"tests/test_fee.py": "abc"},
            },
        )
        self.assertEqual(entry["th"], [{"p": "tests/test_fee.py", "s": "abc"}])
```

- [x] **Step 2: Run it and confirm it fails**

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_wal.GlobalWalTests.test_global_wal_entry_records_preset_test_hashes -q
```

Expected: FAIL because `th` is absent.

- [x] **Step 3: Store and check the hashes**

When `result["preset_test_hashes"]` is a dict of relative path to sha256, set `entry["th"]` to `[{"p": path, "s": digest}]` sorted by path. Ignore any path that is not under `tests/` or does not end in `.py`. Leave entries without the field valid, so old ledger lines still verify.

Add `ledger_matches_workspace(workspace)` in `run_inspection.py`. It reads the last validated global entry that has `th` or `as`. For each item, compare `s` with the SHA-256 of `workspace / p`. A missing file or a different digest returns `preset_test_hash_mismatch` or `asset_hash_mismatch`. A chain failure still returns `global_wal_chain_prev_mismatch` or `global_wal_chain_hash_mismatch`. A match returns `None`.

Wire the chat completion path so a deliverable result passes `preset_test_hashes` into the result object that `write_global_wal` already compacts. If the compactor drops unknown keys, add `preset_test_hashes` to the compact allowlist in the same function that builds the wal entry. Do not drop `as`.

- [x] **Step 4: Tests for a mismatch and an intact chain**

Write one test that appends an entry, changes `tests/test_fee.py`, and expects `preset_test_hash_mismatch`. Write one test that leaves the file untouched and expects `None`. Write one test that flips a stored `hash` and still expects `global_wal_chain_hash_mismatch`.

- [ ] **Step 5: Full gate, then n100**

Run `bash scripts/verify.sh` on the Mac (passed: 1279 tests, 1 skipped, coverage 86%, doctor status `ok`). Sync `src/` to `~/onecode-rule-check` on n100. Run the new unit tests there with `~/onecode-linux-test/.venv/bin/python`. Then run one live chat task with a preset test, on n100, with Docker ready. Expected: code 39, deliverable, verifier passed, preset test unchanged, and `ledger_matches_workspace` returns `None` for that workspace. Do not record the model key.

- [ ] **Step 6: Commit only if the operator asks**

Suggested message: `fix: record preset-test hashes on the delivery ledger`.

## Acceptance for the whole plan

The plan is done when all three slices have passed `bash scripts/verify.sh` on the Mac and the slice 3 live task has passed on n100. GitHub `verify` is a separate check: it stays red until slice 1 is pushed, because the demo assertion fix is what lets the Docker runners accept `completed / deliverable`.

## Out of scope

| Change | Why it waits |
| --- | --- |
| More than one repair inside one run | The second failure stays Li/Kun (40) |
| Fuzzy apply after `patch_search_not_found` | Exact patch match stays |
| Network inside the sandbox | `--network none` stays |
| A default turn cap above 8 | The cycle budget stays |
| LibreChat's own agent loop | Execution stays in the kernel |
| Setting `claims_mainstream_parity` true | No public task set is named here |
| An external timestamp or a legal-evidence claim | The ledger remains local |
| `ONECODE_RUN_COMMAND_SANDBOX=host` as the daily gate | Host execution stays explicit |
