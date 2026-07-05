# YiZiJue-LM v0.1 Project Closure

Date: 2026-07-05

## Status

YiZiJue-LM v0.1 remains closed as a local Agent proposal-model release for
OneCode. The source release package has received the 2026-07-05 hardening pass
for evaluation, dataset building, prediction generation, service request
handling, and checksum validation.

It is not a human-facing chatbot and not a standalone execution authority.

## Public Release Directory

Repository:

```text
https://github.com/aidi1723/yizijue-lm
```

This source directory contains runtime code, evaluation code, tests, documentation, and the guarded full-test report. The LoRA adapter is distributed separately and must be supplied through `--adapter-path` or `YIZIJUE_ADAPTER_PATH`.

```text
logs/guarded-full-report.json
```

SHA256:

```text
1fa3fad5891835c0e281abd1325b7b652d26e1b0cddd217bc48c4dc29bd6e853
```

## Positioning

YiZiJue-LM is a local Agent intent model built for OneCode. It converts
natural-language requests into verifiable, auditable, fail-closed action JSON
for the OneCode control plane.

This project is built on top of Qwen3-0.6B.

## Current Metrics

Original full-test cross-check:

```text
sample_count: 212
missing_prediction_count: 0
json_valid_rate: 0.9858490566037735
action_match_rate: 0.8254716981132075
unknown_action_count: 0
unsafe_allow_count: 0
```

Current verification:

```text
Release tests: 86 tests OK
Release checksum validation: OK
```

## Release Contents

Included:

- guarded final evaluation reports;
- local service code;
- evaluation scripts and tests;
- README, model card, notice, license, release notes.
- release-local self-check and checksum manifest.

Excluded:

- final v5 LoRA adapter from this source directory;
- Qwen base weights;
- local Hugging Face cache;
- private/raw training data;
- API keys or private service credentials.

## Boundary

The model proposes action JSON. OneCode must remain responsible for final
validation, authorization, execution, and audit.

Next engineering step:

```text
Port the final fail-closed guard semantics into OneCode's real execution path.
```
