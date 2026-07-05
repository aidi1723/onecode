# YiZiJue Qwen 0.6B V5 Local Service

Date: 2026-06-04

## Selected Adapter

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/models/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora
```

## Local Service

The project-specific local service is:

```text
scripts/serve_yizijue_mlx.py
```

Start command:

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

Endpoints:

```text
GET  http://127.0.0.1:8090/health
POST http://127.0.0.1:8090/predict
```

Example request:

```bash
curl -sS http://127.0.0.1:8090/predict \
  -H 'Content-Type: application/json' \
  -d '{"input":"运行 pytest 验证一下","max_tokens":220}'
```

## Verified Behavior

Observed local responses:

```text
运行 pytest 验证一下 -> RUN_VERIFIER_IN_SANDBOX
执行 rm -rf / -> SOVEREIGNTY_HALT
```

The service uses the same strict training prompt as evaluation, greedy decoding,
the evaluator fail-closed guard, and a stable response wrapper for truncated raw
model JSON.

## Final Reports

```text
/Volumes/MacSSD/模型训练/yizijue-qwen06b/logs/2026-06-04-strict-hard-negative-recovery-v5-full-guarded-final-report.json
/Volumes/MacSSD/模型训练/yizijue-qwen06b/logs/2026-06-04-v5-original-full-test-guarded-final-report.json
```

## Boundary

This is a local prototype service for viewing and testing the proposal model.
It is not a production execution authority. OneCode must remain the deterministic
judge, authorizer, executor, and ledger recorder.
