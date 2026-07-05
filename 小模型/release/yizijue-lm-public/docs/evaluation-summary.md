# Evaluation Summary

YiZiJue-LM v0.1 was selected from the Qwen3-0.6B LoRA training series as the local closure candidate for OneCode Agent proposal behavior.

## Final Selected Adapter

```text
yizijue-qwen06b-strict-hard-negative-recovery-v5-lora
```

## Current Guarded Gate

Current guarded full-test report is included at:

```text
logs/guarded-full-report.json
```

Current full-test cross-check:

```text
sample_count: 212
missing_prediction_count: 0
json_valid_rate: 0.9858490566037735
action_match_rate: 0.8254716981132075
unknown_action_count: 0
unsafe_allow_count: 0
```

## Test Verification

Local repository verification before v0.1 publication:

```text
Release tests: 86 tests OK
```

## Interpretation

The adapter is suitable for a v0.1 local Agent proposal-model release, with these constraints:

- it is not a human-facing chatbot;
- it is not an execution authority;
- output must be guarded and validated;
- OneCode remains the deterministic control plane;
- production integration should port the same fail-closed guard semantics into OneCode's real execution path.
