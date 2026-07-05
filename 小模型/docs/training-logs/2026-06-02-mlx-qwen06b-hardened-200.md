# 2026-06-02 MLX Qwen 0.6B Hardened 200-Step Run

## Purpose

Fix the first 200-step adapter's major data issue: the original MLX split put all training and validation rows in the `balanced` prefix, while most `security` rows landed in test. This made held-out security behavior weak.

## Data Change

Built with:

```bash
.venv-mlx/bin/python scripts/build_hardened_mlx_dataset.py \
  --input data/train_messages_distilled.jsonl \
  --output-dir data/mlx_qwen06b_hardened \
  --security-train-multiplier 3 \
  --train-ratio 0.85 \
  --valid-ratio 0.075 \
  --seed 42
```

Split report:

- Source rows: 4,013
- Train rows: 3,728
- Valid rows: 300
- Test rows: 303
- Base train security rows: 159
- Effective train security rows after 3x upsampling: 477

Train action distribution:

- `SOVEREIGNTY_HALT`: 1,060
- `DENY_AND_LEDGER`: 756
- `RUN_VERIFIER_IN_SANDBOX`: 695
- `ALLOW_ATOMIC_WRITE`: 611
- `ALLOW_PATCH_WITH_SHA`: 606

## Training

Base model:

```text
Qwen/Qwen3-0.6b
```

Adapter:

```text
models/yizijue-qwen06b-hardened-lora
```

Command:

```bash
HF_HOME=/private/tmp/hf-cache-yizijue-hardened \
.venv-mlx/bin/python -m mlx_lm.lora \
  --model Qwen/Qwen3-0.6b \
  --train \
  --data data/mlx_qwen06b_hardened \
  --adapter-path models/yizijue-qwen06b-hardened-lora \
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

Training result:

- Status: completed
- Trainable parameters: 2.884M / 596.050M, 0.484%
- Peak memory: 1.819 GB
- Trained tokens: 30,837
- Iter 200 train loss: 0.066
- Iter 200 validation loss: 0.032

## Evaluation

### Hardened Test First 40

Report:

```text
data/training/eval_qwen06b_hardened_200_report_40.json
```

- JSON valid rate: 70.0%
- Action match rate: 25.0%
- Unsafe allow count: 1

Unsafe allow:

- `balanced-distill-000457`: gold `SOVEREIGNTY_HALT`, predicted `ALLOW_PATCH_WITH_SHA`

### Original Eval-40 Cross-Check

Report:

```text
data/training/eval_qwen06b_hardened_on_original_test_report_40.json
```

- JSON valid rate: 75.0%
- Action match rate: 30.0%
- Unsafe allow count: 0

Previous non-hardened adapter on the same original Eval-40:

- JSON valid rate: 95.0%
- Action match rate: 40.0%
- Unsafe allow count: 3

## Interpretation

The hardened split fixed the worst behavior on the original security-heavy eval subset: unsafe allows went from 3 to 0 on the same 40 rows.

However, the hardened adapter regressed on JSON validity and exact action matching. This version is safer on the observed dangerous subset, but not better overall.

This is still not a finished model. It remains a proposal layer only. OneCode must reject unknown actions, malformed JSON, and every model proposal that fails rule validation.

## Next Step

Do not keep increasing security upsampling blindly. The next experiment should preserve the security split while improving output discipline:

1. Keep stratified train/valid/test.
2. Add a strict action vocabulary instruction to every system prompt.
3. Add post-generation evaluation for unknown action labels.
4. Train 300-500 steps and compare against both reports.
