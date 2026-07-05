#!/usr/bin/env bash
set -euo pipefail
TRAIN_DATA=${TRAIN_DATA:-data/train_data.jsonl}
MODEL=${MODEL:-Qwen/Qwen2.5-Coder-1.5B-Instruct}
OUTPUT_DIR=${OUTPUT_DIR:-models/yizijue-controlled-1.5b-lora}
test -f "$TRAIN_DATA"
python -m mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data "$TRAIN_DATA" \
  --adapter-path "$OUTPUT_DIR" \
  --iters "${ITERS:-800}" \
  --batch-size "${BATCH_SIZE:-2}" \
  --learning-rate "${LEARNING_RATE:-1e-5}"
