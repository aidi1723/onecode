# Evidence-Based Repair Card Fix

Date: 2026-05-27

## Change

The failed verification path now preserves compact repair evidence instead of only storing stdout/stderr hashes.

- Added `agent_skill_dictionary/build_mode_repair.py`.
- Added `SandboxEvidence.failure_summary` with a backward-compatible default.
- `sandbox_evidence_from_result()` now extracts compact pytest failure lines.
- Failed `run_pytest` tool calls now attach `repair_card`.
- Build Mode state persistence now stores `repair_card` and compact `failure_summary`.
- Next-turn Build Mode context injects `Repair Card:` before the repo card.

## Verification

Local:

```text
python3 -m unittest tests.test_build_mode_repair_card tests.test_build_mode_sandbox tests.test_build_mode_tool_executor tests.test_gateway_server_import tests.test_build_mode_permissions
Ran 92 tests in 0.289s
OK

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

N100:

```text
python3 -m unittest tests.test_build_mode_repair_card tests.test_build_mode_sandbox tests.test_build_mode_tool_executor tests.test_gateway_server_import tests.test_build_mode_permissions
Ran 92 tests in 1.727s
OK

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

## Known Unrelated Local Regression

Full local `python3 -m unittest discover` still has one pre-existing contract drift:

```text
tests.test_trigram_contract.TrigramContractTest.test_root_tool_allowlists_match_final_runtime_contract (code='查')
expected: ['read_file', 'list_directory', 'grep_code', 'git_diff']
actual:   ['native_inspect_card', 'read_file', 'list_directory', 'grep_code', 'git_diff']
```

This is not introduced by the repair-card patch. It reflects an existing mismatch between the root dictionary allowlist and `kernel_policy.py`, where runtime `查` now includes `native_inspect_card`.
