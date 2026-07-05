# YiZiJue Qwen 1.5B Training Runbook

This runbook fixes the first practical training path for the YiZiJue-controlled model:

- base model: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- model role: learn natural-language understanding with the OneCode/YiZiJue state formula as the reasoning prior
- first output role: translate user or agent intent into simple replies, clarification requests, or strict YiZiJue action JSON
- authority boundary: the neural model learns YiZiJue state reasoning, but OneCode/YiZiJue still validates, executes, records evidence, and halts unsafe paths

No command in this runbook requires a GPU until the final optional training step.

For the full model definition, read:

```text
docs/YIZIJUE_LM_DEVELOPMENT_MANUAL.md
```

The target architecture is:

```text
context
  -> YiZiJue feature projection
  -> 6-bit state
  -> Qwen 1.5B token logits
  -> YiZiJue state bias/mask
  -> next token
```

The first training iteration approximates this through explicit state
supervision. A later runtime iteration should implement a tokenizer-aware
YiZiJue logits processor.

## 0. Research Direction: YiZiJue as Next-Token Prior

The training path has two levels:

1. **Current SFT level:** teach Qwen 1.5B to expose YiZiJue state, transition,
   and action reasoning in its structured output.
2. **Controlled decoding level:** apply the YiZiJue state as a logits
   bias/mask during next-token generation.

This means the model is not only trained to output OneCode-compatible JSON. It
is trained to use the YiZiJue formula as a reasoning base:

```text
input -> projection -> state -> transition -> token output
```

The final execution rule remains unchanged:

```text
model output can propose; OneCode must authorize.
```

## 1. Generate Rule Samples

Generate the deterministic rule-expanded dataset:

```bash
PYTHONPATH=src python3 -m onecode.cli generate-training-data \
  --profile expanded \
  --output data/training/yizijue_qwen15b_expanded.jsonl
```

Validate it:

```bash
PYTHONPATH=src python3 -m onecode.cli validate-training-data \
  --input data/training/yizijue_qwen15b_expanded.jsonl
```

Expected current result:

```text
sample_count: 152
status: ok
```

## 2. Generate OneCode Replay Samples

Generate samples from real OneCode benchmark execution:

```bash
PYTHONPATH=src python3 -m onecode.cli generate-training-data \
  --profile benchmark-replay \
  --tasks-dir benchmarks/tasks \
  --workspace-root data/training/replay-workspaces \
  --output data/training/yizijue_qwen15b_replay.jsonl
```

Validate it:

```bash
PYTHONPATH=src python3 -m onecode.cli validate-training-data \
  --input data/training/yizijue_qwen15b_replay.jsonl
```

Expected current result:

```text
sample_count: 17
status: ok
```

## 3. Build Train/Eval Corpus

Build the merged training corpus:

```bash
PYTHONPATH=src python3 -m onecode.cli build-training-corpus \
  --output-dir data/training/corpus \
  --tasks-dir benchmarks/tasks \
  --workspace-root data/training/corpus-replay-workspaces \
  --eval-ratio 0.1
```

Generated files:

```text
data/training/corpus/train.jsonl
data/training/corpus/eval.jsonl
data/training/corpus/quality_report.json
```

Expected current corpus:

```text
train_count: 153
eval_count: 16
total: 169
quality status: ok
```

The quality gate checks:

- assistant JSON can be parsed;
- all required actions are covered;
- duplicate sample IDs are rejected;
- invalid samples are counted;
- halt/deny sample ratio must stay high enough for safety training;
- eval split is action-stratified so it covers the safety surface.

## 4. Write Training Configs

Generate training config templates:

```bash
PYTHONPATH=src python3 -m onecode.cli write-training-configs \
  --corpus-dir data/training/corpus \
  --output-dir data/training/configs
```

Generated files:

```text
data/training/configs/llamafactory_qwen15b_lora.yaml
data/training/configs/axolotl_qwen15b_lora.yml
```

Both configs point at:

```text
base model: Qwen/Qwen2.5-Coder-1.5B-Instruct
train: data/training/corpus/train.jsonl
eval: data/training/corpus/eval.jsonl
method: LoRA SFT
sequence length: 4096
```

## 5. Optional Training Execution

Training is intentionally not run by OneCode yet. Use one of the generated configs in a dedicated training environment.

LLaMA-Factory path:

```bash
llamafactory-cli train data/training/configs/llamafactory_qwen15b_lora.yaml
```

Axolotl path:

```bash
axolotl train data/training/configs/axolotl_qwen15b_lora.yml
```

Before running either command, confirm the chosen framework supports the exact dataset fields and chat template in the installed version.

## 6. Post-Training Acceptance

The fine-tuned adapter is not trusted just because training completes.

Minimum acceptance:

- model output must be valid JSON;
- output must pass the same YiZiJue training-data schema;
- action distribution on eval must include deny/halt paths;
- unsafe prompts must not produce `ALLOW_*`;
- YiZiJue-LM eval must report `unsafe_allow_count: 0`;
- `output_type_match_rate` should be tracked separately from exact text match;
- gateway adjudication changes should decrease after each training iteration;
- OneCode must remain the final authority for execution.

Current YiZiJue-LM local evaluation commands:

```bash
PYTHONPATH=src python3 -m onecode.cli build-yizijue-lm-evalset \
  --output data/training/yizijue_lm_eval.jsonl
```

```bash
PYTHONPATH=src python3 -m onecode.cli run-yizijue-lm-eval \
  --gold data/training/yizijue_lm_eval.jsonl \
  --output data/training/yizijue_lm_predictions.jsonl \
  --endpoint http://127.0.0.1:8000/v1 \
  --model yizijue-qwen15b \
  --api-key local
```

```bash
PYTHONPATH=src python3 -m onecode.cli eval-yizijue-lm-predictions \
  --gold data/training/yizijue_lm_eval.jsonl \
  --predictions data/training/yizijue_lm_predictions.jsonl
```

## 7. Qwen 1.5B Ownership and Product Boundary

The first YiZiJue-LM is a Qwen-derived controlled model, not a base model
trained from scratch.

Owned by this project:

- OneCode/YiZiJue formulas, state mappings, rule corpus, and evaluation harness;
- YiZiJue-LM training corpus and evalset;
- LoRA adapter or merged derivative weights created from project data, subject
  to the base model license;
- future YiZiJue logits processor and runtime control code.

Not exclusively owned by this project:

- original Qwen base weights;
- Qwen tokenizer and architecture;
- third-party training frameworks.

Before commercial release, re-check the exact Qwen model card and revision.
The current review finds `Qwen/Qwen2.5-Coder-1.5B-Instruct` identified with an
Apache-2.0 license on Hugging Face, which is suitable for the first practical
prototype.
