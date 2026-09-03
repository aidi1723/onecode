# Native Inspect Contract Alignment

Date: 2026-05-27

## Change

Aligned the root `查` tool contract with the runtime policy.

`native_inspect_card` is already the formal read-only inspect tool in:

- `agent_skill_dictionary/kernel_policy.py`
- `agent_skill_dictionary/tool_guard.py`
- `agent_skill_dictionary/build_mode_permissions.py`
- gateway native inspect injection paths
- live smoke tests and Build Mode post-failure flow

The dictionary contract was behind the runtime behavior, so `agent_skill_dictionary/oneword_dict.json` now includes:

```json
["native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"]
```

Updated old assertions/docs in:

- `tests/test_trigram_contract.py`
- `tests/test_agent_cli.py`
- `tests/test_minimal_gateway_mvp.py`
- `docs/yizijue-gateway-quickstart.md`

## Verification

Local:

```text
python3 -m unittest discover
Ran 451 tests in 13.069s
OK (skipped=10)

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

N100:

```text
python3 -m unittest discover
Ran 542 tests in 25.756s
OK (skipped=10)

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```
