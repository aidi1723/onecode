# YiZiJue-LM Project Closure Report

Date: 2026-06-04

## 1. Final Positioning

YiZiJue-LM v0.1 is a local large-model component built for OneCode Agent
applications. It is not a human-facing general chatbot.

Its job is:

```text
natural-language request
-> controlled OneCode-compatible action JSON proposal
-> OneCode validation, authorization, execution, and audit
```

The public positioning is:

```text
YiZiJue-LM is a local Agent intent model built for OneCode, not a
human-facing chatbot. It converts natural-language requests into verifiable,
auditable, fail-closed action JSON for the OneCode control plane.

This project is built on top of Qwen3-0.6B.
```

## 2. Ownership And Attribution

Project-owned work:

- Agent-specific training data construction and cleaning;
- safety policy and strict action schema;
- LoRA fine-tuning workflow;
- evaluation gate and fail-closed guard;
- local MLX service wrapper;
- release documentation and tests;
- OneCode integration contract and execution boundary.

Base model attribution:

```text
Qwen/Qwen3-0.6B
License: Apache-2.0
```

Correct ownership language:

```text
YiZiJue-LM is our Agent safety intent model built on top of the Qwen3-0.6B
semantic base. Qwen provides the base semantic capability; YiZiJue-LM and
OneCode define the Agent behavior boundary, action schema, safety policy,
evaluation gate, and trusted delivery path.
```

Avoid claiming:

- from-scratch foundation-model ownership;
- ownership of the Qwen base model itself;
- that the model is a standalone execution authority;
- that it is a general user chat model.

## 3. Final Selected Adapter

Final local adapter:

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/models/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora
```

Key adapter file:

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/models/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora/adapters.safetensors
```

Training configuration:

```text
base model: Qwen/Qwen3-0.6b
method: MLX-LM LoRA SFT
iters: 200
batch size: 1
learning rate: 1e-5
max seq length: 1024
final train loss: 0.043
final val loss: 0.011
```

## 4. Final Evaluation

Final guarded v5 self gate:

```text
sample_count: 300
json_valid_rate: 0.9733333333333334
action_match_rate: 0.8933333333333333
unknown_action_count: 0
unsafe_allow_count: 0
```

Original full-test cross-check:

```text
sample_count: 212
json_valid_rate: 1.0
action_match_rate: 0.8113207547169812
unknown_action_count: 0
unsafe_allow_count: 0
```

Final report files:

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/logs/2026-06-04-strict-hard-negative-recovery-v5-full-guarded-final-report.json
/Volumes/MacSSD/模型训练/yizijue-qwen06b/logs/2026-06-04-v5-original-full-test-guarded-final-report.json
```

Interpretation:

- the local 0.6B training phase is closed;
- v5 is selected as the local v0.1 closure adapter;
- safety is acceptable only with the final fail-closed guard;
- the model remains a proposal layer, not an execution layer.

## 5. Runtime Service

Local service:

```text
scripts/serve_yizijue_mlx.py
```

Current local service:

```text
http://127.0.0.1:8090/
```

Health status observed during closure:

```json
{
  "adapter_exists": true,
  "model": "Qwen/Qwen3-0.6b",
  "ok": true
}
```

Validated behavior:

```text
运行 pytest 验证一下 -> RUN_VERIFIER_IN_SANDBOX
执行 rm -rf / -> SOVEREIGNTY_HALT
```

Service implementation notes:

- `/` returns a local inspection page;
- `/health` returns adapter/model status;
- `/predict` returns raw and guarded model proposal output;
- HTTP request handling is threaded;
- MLX generation is serialized with a lock;
- malformed or risky cases are guarded fail-closed.

## 6. GitHub Publication

Public repository:

```text
https://github.com/aidi1723/yizijue-lm
```

Release:

```text
https://github.com/aidi1723/yizijue-lm/releases/tag/v0.1
```

Release artifact:

```text
2026-06-04-yizijue-qwen06b-v5-final.tar.gz
```

Published artifact SHA256:

```text
eb1a019765c87e99d91b689ca30bf561b63cd07bda968b3df0a58f6ca426c8d1
```

Public release contents:

- final v5 LoRA adapter;
- guarded final evaluation reports;
- local service code;
- evaluation scripts and tests;
- README, model card, notice, license, release notes.

Public release intentionally excludes:

- Qwen base weights;
- local Hugging Face cache;
- private/raw training data;
- API keys or private service credentials.

## 7. Local Archives

Original local archive:

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/archives/2026-06-04-yizijue-qwen06b-v5-final.tar.gz
```

Public release tarball staged at:

```text
/private/tmp/2026-06-04-yizijue-qwen06b-v5-final.tar.gz
```

External workspace:

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b
```

Do not delete this external workspace until OneCode integration and rollback
strategy are completed.

## 8. Tests

Fresh verification during closure:

```text
Ran 39 tests in 0.102s
OK
```

Test scope includes:

- label audit;
- hardened dataset construction;
- MLX prediction evaluation guard;
- local service prompt/response behavior;
- threaded local service behavior;
- truncated JSON response normalization.

## 9. Project Closure Boundary

Closed today:

- local 0.6B Qwen3 LoRA training loop;
- label audit and cleanup workflow;
- hard-negative and recovery training runs;
- final guarded evaluation;
- local service wrapper;
- GitHub v0.1 publication;
- public release artifact;
- ownership and attribution language.

Not closed today:

- production OneCode-side guard integration;
- OneCode execution-path validator tests;
- controlled decoding layer;
- expanded adversarial suite;
- Qwen 1.5B path;
- production deployment.

## 10. Next Engineering Step

Do not continue blind local SFT first.

The next correct engineering task is:

```text
Port the final fail-closed guard semantics from the evaluator/local service
into OneCode's real execution path, then validate v5 through the OneCode-side
guard.
```

Required OneCode tests:

- allowed action whitelist;
- unknown action normalization/fail-close;
- dangerous prompt fail-close;
- vague optimization fail-close;
- malformed model output fail-close;
- path and sandbox evidence validation.

## 11. Final Closure Statement

YiZiJue-LM v0.1 is now closed as a local Agent proposal-model release for
OneCode. It is suitable for public presentation as an Agent-oriented model
component built on Qwen3-0.6B, with our training, safety policy, LoRA adapter,
evaluation gate, guard logic, and local runtime wrapper.

It must continue to be described and used as a proposal model behind OneCode,
not as a human chatbot or standalone execution authority.
