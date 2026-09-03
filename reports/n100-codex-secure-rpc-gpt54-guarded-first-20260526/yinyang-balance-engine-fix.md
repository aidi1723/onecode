# Yin-Yang Balance Engine Fix

Context: the guarded-first A/B run exposed a no-tool dead end. After artifact completion, the gateway moved to `001` verify state, but the Codex CLI request only provided `apply_patch`. Filtering for `run_pytest` produced `tools=[]`, so the model could only emit text and no `SandboxEvidence` was generated.

Implemented fix:

- Added `canonical_tool_schema()` in `agent_skill_dictionary/build_mode_permissions.py`.
- When Verify Gate is active and filtering leaves no tools, `gateway_server.py` now injects a canonical `run_pytest(command)` schema.
- The gateway also sets protocol-appropriate `tool_choice`:
  - Chat Completions: `{"type": "function", "function": {"name": "run_pytest"}}`
  - Responses: `{"type": "function", "name": "run_pytest"}`

This implements the first concrete slice of the Yin-Yang balance meta-rule: a strong `001` verification gate must never collapse into `tools=[]`; it must expose exactly one constrained evidence-producing outlet.

Verification:

```text
Local:  101 tests OK; compileall OK
N100:   101 tests OK; compileall OK
```

Scope note: this fix does not change the previous A/B outcome retroactively. It removes the observed dead end so the next guarded run can produce `SandboxEvidence` at the artifact-complete boundary.
