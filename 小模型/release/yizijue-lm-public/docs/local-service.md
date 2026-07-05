# Local Service

YiZiJue-LM v0.1 includes a small local HTTP service for inspecting model proposals.

The service is intended for local development and validation. It is not a production security boundary.

## Start

Use MLX-LM on Apple Silicon:

```bash
HF_HOME=/path/to/hf-home \
python scripts/serve_yizijue_mlx.py \
  --model Qwen/Qwen3-0.6b \
  --adapter-path /path/to/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora \
  --host 127.0.0.1 \
  --port 8090 \
  --max-tokens 220 \
  --preload
```

Alternatively, provide the adapter through the environment:

```bash
YIZIJUE_ADAPTER_PATH=/path/to/yizijue-qwen06b-strict-hard-negative-recovery-v5-lora \
HF_HOME=/path/to/hf-home \
python scripts/serve_yizijue_mlx.py \
  --model Qwen/Qwen3-0.6b \
  --host 127.0.0.1 \
  --port 8090 \
  --max-tokens 220 \
  --preload
```

Open:

```text
http://127.0.0.1:8090/
```

## Endpoints

```text
GET  /health
POST /predict
```

Example:

```bash
curl -sS http://127.0.0.1:8090/predict \
  -H 'Content-Type: application/json' \
  -d '{"input":"运行 pytest 验证一下","max_tokens":220}'
```

Expected action:

```text
RUN_VERIFIER_IN_SANDBOX
```

## Runtime Behavior

The service uses:

- the strict YiZiJue system prompt;
- greedy decoding;
- fail-closed guard logic;
- stable action JSON wrapping for truncated raw model output;
- threaded HTTP request handling with serialized MLX generation.
- `max_tokens` bounds of `1..512` at startup and request time;
- a 64 KiB request body limit for `/predict`;
- sanitized generation error responses that do not include raw exception details.

## Boundary

The service lets developers inspect proposal output. OneCode or an equivalent deterministic control plane must still perform final validation, authorization, execution, and audit recording.
