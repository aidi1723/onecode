# 2026-06-02 MLX Qwen 0.6B Smoke Training

## Purpose

Verify that the Mac can run a small local LoRA fine-tuning job on the existing YiZiJue distilled `messages` dataset before attempting a longer run.

## Environment

- Machine: Apple Silicon Mac (`arm64`)
- macOS: 26.2
- Python env: `.venv-mlx`
- Python: 3.12.12
- Package: `mlx-lm==0.31.3`
- Metal access: available when run with elevated/local execution

## Model And Data

- Base model: `Qwen/Qwen3-0.6b`
- Data source: `data/train_messages_distilled.jsonl`
- Smoke split:
  - `data/mlx_smoke_0_5b/train.jsonl`: 96 samples
  - `data/mlx_smoke_0_5b/valid.jsonl`: 16 samples
  - `data/mlx_smoke_0_5b/test.jsonl`: 16 samples

## Command

```bash
HF_HOME=/private/tmp/hf-cache-yizijue-smoke \
.venv-mlx/bin/python -m mlx_lm.lora \
  --model Qwen/Qwen3-0.6b \
  --train \
  --data data/mlx_smoke_0_5b \
  --adapter-path models/yizijue-qwen06b-smoke-lora \
  --iters 16 \
  --batch-size 1 \
  --learning-rate 1e-5 \
  --steps-per-report 4 \
  --steps-per-eval 8 \
  --val-batches 2 \
  --save-every 16 \
  --max-seq-length 1024 \
  --grad-checkpoint \
  --mask-prompt
```

## Result

- Status: completed
- Trainable parameters: 2.884M / 596.050M, 0.484%
- Peak memory: 1.771 GB
- Final train loss at iter 16: 1.184
- Final validation loss at iter 16: 0.881
- Trained tokens: 2,562
- Adapter output:
  - `models/yizijue-qwen06b-smoke-lora/adapters.safetensors`
  - `models/yizijue-qwen06b-smoke-lora/0000016_adapters.safetensors`
  - `models/yizijue-qwen06b-smoke-lora/adapter_config.json`

## Storage Notes

- Local project size after smoke run: about 410 MB.
- MLX virtualenv size: about 310 MB.
- Smoke adapter size: about 22 MB.
- Temporary Hugging Face cache: `/private/tmp/hf-cache-yizijue-smoke`, about 1.4 GB.
- Mac free space after run: about 39 GiB.
- Remote archive candidate: `ssh n100`, host `yami-n100`, root filesystem had about 58 GB available during this check.

For longer runs, keep model/cache data out of the default home cache by setting `HF_HOME` explicitly. Move completed adapters, old caches, or full generated corpora to `n100` and leave a record in this directory.
