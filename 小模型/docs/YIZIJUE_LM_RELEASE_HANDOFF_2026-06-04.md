# YiZiJue-LM Release Handoff

Date: 2026-06-04

## Public Links

Repository:

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

SHA256:

```text
eb1a019765c87e99d91b689ca30bf561b63cd07bda968b3df0a58f6ca426c8d1
```

## One-Sentence Description

```text
YiZiJue-LM is a local Agent intent model built for OneCode, not a
human-facing chatbot. It converts natural-language requests into verifiable,
auditable, fail-closed action JSON. Built on top of Qwen3-0.6B.
```

## Recommended Social Copy

```text
YiZiJue-LM v0.1 发布。

这是我们面向 OneCode Agent 应用开发的本地安全意图模型，不是通用聊天机器人。它将自然语言请求转换为可验证、可审计、可 fail-closed 的 OneCode action JSON。

底层语义能力基于 Qwen3-0.6B；Agent 行为边界、安全策略、LoRA 微调、评估体系和运行守卫由我们自主构建。

GitHub:
https://github.com/aidi1723/yizijue-lm
```

## Local Service Command

```bash
HF_HOME=/Volumes/MacSSD/模型训练/yizijue-qwen06b/hf-home \
.venv-mlx/bin/python scripts/serve_yizijue_mlx.py \
  --model Qwen/Qwen3-0.6b \
  --adapter-path /Volumes/MacSSD/模型训练/yizijue-qwen06b/models/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora \
  --host 127.0.0.1 \
  --port 8090 \
  --max-tokens 220 \
  --preload
```

Open:

```text
http://127.0.0.1:8090/
```

## Final Metrics

Recovery v5 self gate:

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

## Communication Boundary

Use:

```text
Agent intent model
OneCode proposal layer
local safety intent model
controlled action JSON
fail-closed guard
built on Qwen3-0.6B
```

Avoid:

```text
general chatbot
fully from-scratch foundation model
standalone execution model
production authorization engine
complete replacement for OneCode
```

## Handoff Checklist

- [x] Final v5 adapter selected.
- [x] Final guarded reports generated.
- [x] Local service runs on port 8090.
- [x] Public GitHub repository created.
- [x] v0.1 Release uploaded.
- [x] Public release excludes base weights, HF cache, private/raw training data, and secrets.
- [x] Tests pass.

## Next Owner Task

The next owner should start from OneCode integration:

```text
Port evaluator/local-service fail-closed guard semantics into the OneCode
execution path and add OneCode-side validator tests.
```
