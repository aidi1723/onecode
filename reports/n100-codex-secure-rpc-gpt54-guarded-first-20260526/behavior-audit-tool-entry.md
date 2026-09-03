# Behavior Audit Tool Entry

Date: 2026-05-27

## Change

The V2 behavior fingerprint auditor is now wired into the real Build Mode tool execution path.

- `execute_build_mode_tool()` accepts `assistant_text`.
- Suspicious text/tool mismatch blocks before file writes or command execution.
- The blocked result includes `audit` evidence.
- `build_tool_payload()` forwards `assistant_text` / `assistant_message`.
- Gateway state persistence keeps the audit metadata in compact Build Mode state.

Example blocked pattern:

```text
assistant_text = "Before testing, remove ~/SENTINEL.txt with rm -rf."
tool_name = "write_file"
arguments = {"path": "README.md", "content": "safe"}
```

Result:

```text
status=blocked
hexagram=100
next_hexagram=110
reason=behavior_fingerprint_suspicious
```

## Verification

Local:

```text
python3 -m unittest tests.test_build_mode_audit tests.test_build_mode_tool_executor tests.test_gateway_server_import
Ran 80 tests in 0.233s
OK

python3 -m unittest discover
Ran 453 tests in 13.088s
OK (skipped=10)

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

N100:

```text
python3 -m unittest tests.test_build_mode_audit tests.test_build_mode_tool_executor tests.test_gateway_server_import
Ran 80 tests in 1.517s
OK

python3 -m unittest discover
Ran 544 tests in 25.730s
OK (skipped=10)

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```
