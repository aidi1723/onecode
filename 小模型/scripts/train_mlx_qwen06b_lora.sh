#!/usr/bin/env bash
set -euo pipefail

MODEL=${MODEL:-Qwen/Qwen3-0.6b}
DATA_DIR=${DATA_DIR:-data/mlx_qwen06b_full}
ADAPTER_PATH=${ADAPTER_PATH:-models/yizijue-qwen06b-full-lora}
HF_HOME=${HF_HOME:-/private/tmp/hf-cache-yizijue-qwen06b}
ITERS=${ITERS:-200}
BATCH_SIZE=${BATCH_SIZE:-1}
LEARNING_RATE=${LEARNING_RATE:-1e-5}
MAX_SEQ_LENGTH=${MAX_SEQ_LENGTH:-1024}
VAL_BATCHES=${VAL_BATCHES:-8}

exec .venv-mlx/bin/python -m mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data "$DATA_DIR" \
  --adapter-path "$ADAPTER_PATH" \
  --iters "$ITERS" \
  --batch-size "$BATCH_SIZE" \
  --learning-rate "$LEARNING_RATE" \
  --steps-per-report "${STEPS_PER_REPORT:-20}" \
  --steps-per-eval "${STEPS_PER_EVAL:-50}" \
  --val-batches "$VAL_BATCHES" \
  --save-every "${SAVE_EVERY:-100}" \
  --max-seq-length "$MAX_SEQ_LENGTH" \
  --grad-checkpoint \
  --mask-prompt
