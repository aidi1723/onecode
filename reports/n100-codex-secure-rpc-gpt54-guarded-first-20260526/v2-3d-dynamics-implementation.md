# Build Mode V2 3D Dynamics Implementation

Date: 2026-05-27

## Implemented

- Added cube topology helpers in `build_mode_topology.py`.
  - Hamming distance.
  - Edge-only transition detection.
  - Diagonal transition decomposition via `edge_walk_path`.
- Added `TransitionPlanEvidence` and `guarded_next_hexagram()` without changing legacy `next_hexagram()`.
- Added behavioral fingerprint audit in `build_mode_audit.py`.
  - Detects destructive hidden text intent and path escape arguments.
- Added entropy decay gate in `build_mode_decay.py`.
  - Repeated failure summaries reduce retry threshold from 3 to 1.
- Added signed evidence envelopes in `build_mode_consensus.py`.
  - HMAC-signed evidence DTO envelope.
  - Local append-only JSONL node event store.
- Wired decay metadata into `execute_build_mode_tool()` and `build_tool_payload()`.
  - Repeated failed verification now persists `decay` metadata into Build Mode state.
- Updated docs:
  - `docs/build-mode-v2-3d-dynamics.md`
  - `docs/hexagram-rules.md`
  - `docs/superpowers/plans/2026-05-27-build-mode-v2-3d-dynamics.md`

## Verification

Local:

```text
python3 -m unittest tests.test_build_mode_topology tests.test_build_mode_audit tests.test_build_mode_decay tests.test_build_mode_consensus tests.test_build_mode_fsm tests.test_build_mode_tool_executor tests.test_gateway_server_import
Ran 94 tests in 0.225s
OK

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

N100:

```text
python3 -m unittest tests.test_build_mode_topology tests.test_build_mode_audit tests.test_build_mode_decay tests.test_build_mode_consensus tests.test_build_mode_fsm tests.test_build_mode_tool_executor tests.test_gateway_server_import
Ran 94 tests in 1.340s
OK

python3 -m compileall -q agent_skill_dictionary scripts tests
OK
```

## Known Unrelated Full-Suite Failure

Full local `python3 -m unittest discover` still has one pre-existing contract drift:

```text
tests.test_trigram_contract.TrigramContractTest.test_root_tool_allowlists_match_final_runtime_contract (code='查')
expected: ['read_file', 'list_directory', 'grep_code', 'git_diff']
actual:   ['native_inspect_card', 'read_file', 'list_directory', 'grep_code', 'git_diff']
```

This V2 patch does not change `kernel_policy.py` or `oneword_dict.json`. The drift should be resolved as a separate root-contract decision.
