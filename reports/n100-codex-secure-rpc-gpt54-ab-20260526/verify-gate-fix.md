# Verify Gate Fix

Context: the GPT-5.4 A/B run showed that artifact orchestration could produce the four required files, but the gateway did not force a physical pytest evidence turn when the artifact gap reached zero.

Implemented fix:

- Added `build_verify_gate_instruction()` in `agent_skill_dictionary/build_mode_orchestrator.py`.
- Updated `gateway_server.py` so a complete `secure-rpc-mesh` artifact plan switches request state to `001` and exposes only `run_pytest`.
- The Verify Gate instruction tells the model to call `run_pytest(command="pytest -q")` and forbids additional writes in that turn.
- The existing `/v1/yizijue/build-tool` path still executes pytest and persists `SandboxEvidence`, so failures continue through the existing `110 -> 101 -> 111` repair chain.

Verification:

```text
Local:  97 tests OK; compileall OK
N100:   97 tests OK; compileall OK
```

Scope note: this fix does not claim that the previous A/B output now passes. It closes the missing transition so future runs cannot stop after artifact completion without entering the verification evidence gate.
