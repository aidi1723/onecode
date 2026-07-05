# Model Card: YiZiJue-LM v0.1

## Summary

YiZiJue-LM v0.1 is a local Agent intent proposal model for OneCode. It is trained to convert natural-language requests into controlled action JSON that can be validated, audited, and fail-closed by OneCode.

It is not a human-facing chatbot.

## Base Model

```text
Qwen/Qwen3-0.6B
License: Apache-2.0
```

YiZiJue-LM v0.1 is distributed as a LoRA adapter and associated runtime/evaluation code. The full base model weights are not included in this repository.

## Intended Use

Intended use:

- proposal layer for OneCode Agent runtime;
- local intent classification into controlled action JSON;
- safety-oriented fail-closed action proposal;
- evaluation and research on deterministic Agent control surfaces.

Not intended for:

- general chat;
- direct execution;
- final authorization;
- unsupervised production deployment;
- replacing OneCode validation, sandboxing, or audit logic.

## Action Vocabulary

```text
ALLOW_ATOMIC_WRITE
ALLOW_PATCH_WITH_SHA
RUN_VERIFIER_IN_SANDBOX
DENY_AND_LEDGER
SOVEREIGNTY_HALT
```

Unknown, vague, dangerous, outside-workspace, privileged, or malformed requests must be denied or halted by the runtime guard.

## Architecture Boundary

```text
user request
-> YiZiJue-LM proposes controlled action JSON
-> OneCode validates risk, evidence, schema, path, and authority
-> OneCode accepts, rejects, rewrites, executes, and records ledger evidence
```

The model is only a proposal layer. OneCode remains the deterministic control plane.

## Training And Engineering Contribution

The Agent-specific data construction, safety policy, LoRA fine-tuning, strict action schema, evaluation guard, local service wrapper, tests, and OneCode integration contract are self-developed by the project team.

Qwen3-0.6B provides the base semantic foundation.

## Release Artifact

The v0.1 release artifact contains:

- final v5 LoRA adapter;
- guarded evaluation reports;
- local MLX service;
- evaluation scripts;
- tests and documentation.

It excludes:

- Qwen base weights;
- Hugging Face cache;
- private/raw training data;
- API keys or private service credentials.

## Safety Notes

This model must not be treated as an execution authority. Any production use must put OneCode or an equivalent deterministic control plane after model output.

Recommended production rules:

- whitelist action names;
- reject unknown action names;
- validate paths and sandbox boundaries;
- fail-close on malformed JSON;
- fail-close on dangerous or vague prompts;
- preserve ledger evidence for accepted and rejected actions.
