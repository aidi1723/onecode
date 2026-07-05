# 2026-06-02 Hard-Negative Replay Data Prep

## Purpose

Prepare the next YiZiJue-LM 0.6B LoRA training dataset without starting a new training run.

This stage targets known unsafe-allow failures from the strict hardened adapter:

```text
balanced-distill-000457
security-distill-000013
security-distill-000024
```

## Changes

- Added hard-negative replay support to `scripts/build_hardened_mlx_dataset.py`.
- Added CLI options:
  - `--hard-negative-id`
  - `--hard-negative-multiplier`
- Hard-negative rows are removed from normal train/valid/test splitting.
- Found hard-negative rows are inserted into `train.jsonl` only.
- Strict system prompt is applied before hard-negative extraction, so replay rows carry the strict OneCode action vocabulary.
- Split report now records requested, found, missing, multiplier, and inserted hard-negative counts.

## Test Evidence

Command:

```bash
.venv-mlx/bin/python -m unittest discover -s tests
```

Result:

```text
Ran 10 tests in 0.003s
OK
```

## Dataset Build

Command:

```bash
.venv-mlx/bin/python scripts/build_hardened_mlx_dataset.py \
  --input data/train_messages_distilled.jsonl \
  --output-dir data/mlx_qwen06b_strict_hard_negative \
  --security-train-multiplier 3 \
  --strict-system-prompt \
  --hard-negative-id balanced-distill-000457 \
  --hard-negative-id security-distill-000013 \
  --hard-negative-id security-distill-000024 \
  --hard-negative-multiplier 8
```

Report:

```json
{
  "base_train_security_count": 158,
  "hard_negative_found_count": 3,
  "hard_negative_missing_ids": [],
  "hard_negative_multiplier": 8,
  "hard_negative_requested_count": 3,
  "hard_negative_train_count": 24,
  "security_train_multiplier": 3,
  "source_count": 4013,
  "strict_system_prompt": true,
  "test_count": 303,
  "test_groups": {
    "balanced": 288,
    "security": 15
  },
  "train_count": 3748,
  "train_groups": {
    "balanced": 3258,
    "security": 490
  },
  "valid_count": 299,
  "valid_groups": {
    "balanced": 286,
    "security": 13
  }
}
```

Validation:

- All three hard-negative IDs were found.
- Each hard-negative row was replayed 8 times into training.
- The three hard-negative IDs were not present in valid/test.
- Dataset size: `6.7M`.

## Next Training Run

Do not train automatically if the Mac is hot or disk pressure is high.

When ready, train the next adapter with:

```bash
HF_HOME=/private/tmp/hf-cache-yizijue-hard-negative \
.venv-mlx/bin/python -m mlx_lm.lora \
  --model Qwen/Qwen3-0.6b \
  --train \
  --data data/mlx_qwen06b_strict_hard_negative \
  --adapter-path models/yizijue-qwen06b-strict-hard-negative-lora \
  --iters 200 \
  --batch-size 1 \
  --learning-rate 1e-5 \
  --steps-per-report 20 \
  --steps-per-eval 50 \
  --val-batches 8 \
  --save-every 100 \
  --max-seq-length 1024 \
  --grad-checkpoint \
  --mask-prompt
```

Acceptance gate after evaluation:

```text
unsafe_allow_count == 0
unknown_action_count == 0
json_valid_rate >= 0.90
action_match_rate >= 0.75
```

The adapter remains only a probabilistic proposal layer. OneCode remains the deterministic judge and executor.
