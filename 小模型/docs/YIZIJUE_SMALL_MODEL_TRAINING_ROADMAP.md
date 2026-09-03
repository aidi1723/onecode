# YiZiJue-LM Small Model Training Roadmap

Date: 2026-06-02
Workspace: `.`

## Core Principle

Do not train a 0.5B-class model from scratch.

Use an existing small open-source base model, then apply narrow-domain supervised fine-tuning and later, only if needed, reward-based alignment.

Current local base used in experiments:

```text
Qwen/Qwen3-0.6b
```

YiZiJue-LM is not the execution authority. It is only a proposal model:

```text
natural language -> OneCode-compatible JSON proposal
```

OneCode remains the deterministic judge, authorizer, executor, and evidence recorder.

## Target Task

The first production target is narrow:

```text
User intent -> strict OneCode-compatible action JSON
```

Allowed action vocabulary:

```text
ALLOW_ATOMIC_WRITE
ALLOW_PATCH_WITH_SHA
RUN_VERIFIER_IN_SANDBOX
DENY_AND_LEDGER
SOVEREIGNTY_HALT
```

The model should learn:

- intent extraction;
- facts extraction;
- action proposal;
- JSON shape;
- safe default behavior for vague, dangerous, missing-evidence, or outside-workspace requests.

The model should not learn:

- direct execution;
- final authorization;
- long multi-turn agent memory;
- large knowledge storage inside parameters.

## Training Order

### Stage 0: Data And Evaluation First

Before any new training run, verify that the evaluation harness is working.

Required artifacts:

```text
scripts/generate_mlx_predictions.py
scripts/eval_mlx_predictions.py
tests/test_eval_mlx_predictions.py
tests/test_build_hardened_mlx_dataset.py
```

Required metrics:

```text
json_valid_rate
action_match_rate
unknown_action_count
unsafe_allow_count
```

Primary gate:

```text
unsafe_allow_count == 0
```

If the evaluator is not trusted, do not train.

### Stage 1: High-Quality SFT Baseline

Start with supervised fine-tuning on distilled data.

Use:

```text
data/train_messages_distilled.jsonl
```

Keep runs small and comparable:

```text
base model: Qwen/Qwen3-0.6b or similar 0.5B/0.6B model
method: MLX LoRA SFT
steps: 200 first
batch size: 1
max sequence length: 1024
mask prompt: true
```

Purpose:

- prove training path works;
- learn JSON structure;
- identify split and data-quality failures.

Do not jump to full fine-tuning or GRPO here.

### Stage 2: Stratified Security Split

Never allow all security samples to land only in test.

Use the hardened dataset builder:

```bash
.venv-mlx/bin/python scripts/build_hardened_mlx_dataset.py \
  --input data/train_messages_distilled.jsonl \
  --output-dir data/mlx_qwen06b_hardened \
  --security-train-multiplier 3 \
  --train-ratio 0.85 \
  --valid-ratio 0.075 \
  --seed 42
```

Goal:

- security rows appear in train, valid, and test;
- `SOVEREIGNTY_HALT` is strongly represented;
- dangerous cases are not only seen after training.

### Stage 3: Strict Output Discipline

Use strict system prompts and action vocabulary before trying stronger optimization.

Build strict hardened data:

```bash
.venv-mlx/bin/python scripts/build_hardened_mlx_dataset.py \
  --input data/train_messages_distilled.jsonl \
  --output-dir data/mlx_qwen06b_strict_hardened \
  --security-train-multiplier 3 \
  --train-ratio 0.85 \
  --valid-ratio 0.075 \
  --seed 42 \
  --strict-system-prompt
```

Strict prompt rules:

- output one JSON object;
- use only the allowed action vocabulary;
- never invent action names;
- unknown/vague/risky/outside-workspace/missing-evidence requests should become `DENY_AND_LEDGER` or `SOVEREIGNTY_HALT`;
- never claim execution authority.

Use deterministic evaluation:

```text
greedy decoding
strict system prompt for strict models
```

### Stage 4: Hard-Negative Replay

Do this before increasing training scale.

Collect unsafe allow failures from evaluation reports.

Known failures from 2026-06-02:

```text
balanced-distill-000457
security-distill-000013
security-distill-000024
```

For each failure:

1. preserve the original user prompt;
2. use the OneCode gold action;
3. add the corrected row to a hard-negative augmentation set;
4. upsample these rows more heavily than the general security set.

Goal:

```text
unsafe_allow_count == 0
```

Do not broadly upsample all security rows if the issue is concentrated in a few hard negatives.

### Stage 5: Controlled Decoding

After strict SFT and hard negatives, add runtime decoding control.

Use OneCode-side rule documentation:

```text
<onecode-repo>/docs/YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md
```

Target formula:

```text
P_model = softmax(logits_model(context) + lambda * rule_bias(state))
P_controlled = softmax(mask_forbidden(P_model, allowed_tokens(state)))
execute = OneCode.verify(output, context)
```

Use existing OneCode implementation entry points:

```text
src/onecode/kernel/yizijue_logits.py
src/onecode/kernel/yizijue_transformers.py
```

Important boundary:

```text
YiZiJue-LM output != authorization
OneCode verification == authorization
```

### Stage 6: Higher-Rank LoRA

Only after the data/eval/controlled decoding loop is stable, try stronger LoRA.

Candidates:

```text
LoRA rank 64
LoRA rank 128
```

Purpose:

- give the 0.5B/0.6B model more adaptation capacity;
- improve action matching without losing safety.

Do not use high-rank LoRA to compensate for bad data or weak evaluation.

### Stage 7: Full Fine-Tuning

Full fine-tuning may be reasonable for 0.5B-class models, but only after:

- SFT baseline is stable;
- strict prompt works;
- hard-negative replay works;
- controlled decoding works;
- evaluation is repeatable.

Full fine-tuning is not the first step because it makes failures harder to attribute.

### Stage 8: GRPO Or Reward-Based Alignment

Use GRPO only when reward functions are reliable.

Potential rewards:

- JSON parses successfully;
- action is in allowed vocabulary;
- action matches OneCode gold action;
- unsafe allow gets zero or negative reward;
- unknown action gets zero or negative reward;
- OneCode validation passes.

GRPO should be treated as an alignment refinement, not as a replacement for:

- clean SFT data;
- hard-negative replay;
- controlled decoding;
- OneCode hard gate.

## Hardware Strategy

### Local Mac

Use for:

- small MLX LoRA runs;
- 200-step experiments;
- strict prompt experiments;
- evaluation;
- adapter sanity checks.

Keep Hugging Face cache outside default home:

```bash
HF_HOME=/private/tmp/hf-cache-yizijue-...
```

Clean temporary caches after each run.

### Remote Archive Host

Use for:

- archiving adapters;
- archiving reports;
- storing older experiments;
- keeping local disk free.

Archive format:

```text
<archive-host>:~/yizijue-small-model-archive/<date>-<run-name>/
```

### Cloud GPU

Use only when local iteration proves the data and metrics are ready.

Use for:

- high-rank LoRA;
- full fine-tuning;
- GRPO;
- longer runs.

## Acceptance Gates

Do not call a model "trained" until it meets the gates below on held-out tests:

```text
unsafe_allow_count == 0
unknown_action_count == 0
json_valid_rate >= 0.90
action_match_rate >= 0.75
```

For a stronger release candidate:

```text
unsafe_allow_count == 0
unknown_action_count == 0
json_valid_rate >= 0.95
action_match_rate >= 0.90
```

The model is still only a proposal layer even if it passes these metrics.

## Current Best Local Adapter

From the 2026-06-02 session:

```text
models/yizijue-qwen06b-strict-hardened-lora
```

It improved output discipline but is not final:

- strict hardened self Eval-40:
  - JSON valid rate: 92.5%
  - action match rate: 85.0%
  - unsafe allow count: 1
- original Eval-40 with strict prompt:
  - JSON valid rate: 90.0%
  - action match rate: 75.0%
  - unsafe allow count: 2

Next session should start at Stage 4: hard-negative replay.

## Stop Rules

Stop training and return to data/evaluation if:

- unsafe allow increases;
- unknown action labels appear;
- JSON validity drops below 90%;
- action match improves only by making safety worse;
- model starts claiming execution authority;
- OneCode cannot parse or validate the proposal.

## Summary

The correct order is:

```text
clean distilled SFT
-> stratified security split
-> strict output vocabulary
-> hard-negative replay
-> controlled decoding
-> high-rank LoRA
-> full fine-tuning
-> GRPO
```

Do not skip to full fine-tuning or GRPO before the hard-negative and controlled-decoding loop is stable.
