# N100 Secure RPC Mesh A/B Closeout Index

Date: 2026-05-27

This directory records the guarded-first `gpt-5.4` A/B run and the engineering fixes that followed.

## Primary Reports

1. [`summary.md`](summary.md)
   - Original guarded-first A/B report.
   - Corrected aggregate: guarded 一字诀 used 6 turns, 156s, 46,590 reported tokens; bare Codex used 1 turn, 387s, 262,557 reported tokens.
   - Main finding: 一字诀 reduced wall time and token load, but strict external pytest still failed before the later repair-loop fixes.

2. [`yinyang-balance-engine-fix.md`](yinyang-balance-engine-fix.md)
   - Fix for the Verify Gate no-tool dead end.
   - `001` verify state can now inject canonical `run_pytest`.

3. [`repair-card-fix.md`](repair-card-fix.md)
   - Evidence-Based Repair Card implementation.
   - Failed verification now carries compact `failure_summary`, interface signatures, and next-turn repair context.

4. [`v2-3d-dynamics-implementation.md`](v2-3d-dynamics-implementation.md)
   - V2 additive control layer.
   - Includes cube topology, guarded transition plans, behavior audit, entropy decay, and signed evidence envelopes.

5. [`native-inspect-contract-alignment.md`](native-inspect-contract-alignment.md)
   - Aligns `native_inspect_card` across runtime policy, root dictionary contract, tests, and docs.

6. [`behavior-audit-tool-entry.md`](behavior-audit-tool-entry.md)
   - Wires V2 behavior fingerprint auditing into the real Build Mode tool execution path.
   - Suspicious assistant text now blocks before scoped writes or command execution.

7. [`final-closeout.md`](final-closeout.md)
   - Final engineering closeout.
   - Local and N100 full-suite verification records.

## Raw Artifacts

- [`secure-rpc-hard-ab.json`](secure-rpc-hard-ab.json): structured benchmark/evaluation artifact.
- [`build-mode-debug.jsonl`](build-mode-debug.jsonl): Build Mode gateway debug stream.
- [`guarded-unified-pytest.stdout.txt`](guarded-unified-pytest.stdout.txt): guarded unified pytest output.
- [`bare-codex-stderr.txt`](bare-codex-stderr.txt): bare Codex stderr capture.

## Final Verification Snapshot

Local:

```text
python3 -m unittest discover
Ran 451 tests in 13.087s
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
