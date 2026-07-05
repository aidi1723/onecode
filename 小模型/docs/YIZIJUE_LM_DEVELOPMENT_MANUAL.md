# YiZiJue-LM Development Manual

This manual defines the target model we are building:

```text
YiZiJue-LM = Qwen 1.5B language substrate
           + YiZiJue state formula as inference prior
           + OneCode rule traces as training supervision
           + optional YiZiJue logits processor at inference time
```

The goal is not to make a generic chatbot. The goal is a small local language
model whose token generation is biased by the OneCode/YiZiJue mathematical
state machine, so simple replies and task actions are both understandable and
controllable.

## 1. Core Definition

YiZiJue-LM uses the OneCode mathematical kernel as its reasoning base:

- input text is projected into YiZiJue facts;
- facts are reduced into a 6-bit state, `s in [0, 63]`;
- the state selects the allowed response mode: `chat_reply`, `clarify`, or `action_json`;
- the model generates natural-language or JSON tokens under that state prior;
- OneCode still verifies final action JSON before any real execution.

The strict target is:

```text
context
  -> YiZiJue feature projection
  -> state s
  -> base LM logits(context)
  -> YiZiJue state bias/mask
  -> next token
```

The eventual decoding rule is:

```text
controlled_logits =
    base_logits
    + lambda * state_token_bias[s]
    + mu * rule_token_bias[s]
    + hard_mask[s]
```

Where:

- `base_logits` are produced by the Qwen-derived language model;
- `state_token_bias[s]` encourages tokens compatible with the current hexagram state;
- `rule_token_bias[s]` encourages OneCode-valid action fields, reasons, and reply modes;
- `hard_mask[s]` blocks tokens that would violate a hard state boundary;
- `lambda` and `mu` control how strongly YiZiJue pushes the model.

This is a controlled language model, not only an external gateway. The gateway
remains as the final execution authority, but the model itself is trained to
reason through YiZiJue states before producing tokens.

## 2. What This Can and Cannot Guarantee

This approach can provide:

- more stable task understanding than plain SFT;
- lower format drift for action JSON;
- fewer unsafe allow attempts before gateway adjudication;
- explicit state traces for debugging and distillation;
- model-agnostic migration: Qwen 1.5B first, smaller models later.

It cannot honestly guarantee:

- that neural weights execute YiZiJue code exactly;
- that next-token generation is mathematically deterministic without a logits processor;
- that a fine-tuned model no longer contains base-model behavior;
- that model output can bypass OneCode verification.

Engineering rule:

```text
The model may propose.
The YiZiJue formula may bias generation.
OneCode must still authorize execution.
```

## 3. Qwen 1.5B Base Model Choice

The first implementation target remains:

```text
Qwen/Qwen2.5-Coder-1.5B-Instruct
```

Rationale:

- small enough for local CPU/GGUF experiments;
- strong enough to learn structured JSON and simple Chinese instructions;
- open enough for practical fine-tuning and commercial prototyping;
- compatible with current local serving paths such as llama.cpp-style
  OpenAI-compatible endpoints.

As of the current review, the official Hugging Face model card identifies this
model under the `apache-2.0` license. Always re-check the model card before
commercial release, and keep a copy of the exact model revision used for
training.

## 4. Three-Stage Development Path

### Stage A: Explicit State Supervision

The first step is to train the model to expose YiZiJue state reasoning.

Current simple output:

```json
{
  "output_type": "action_json",
  "reply": "",
  "action": {
    "facts": {
      "intent_type": "execute_pytest",
      "path_scope": "no_path",
      "sandbox_state": "required",
      "evidence_state": "required"
    },
    "yizijue_state": "010010",
    "action": "RUN_VERIFIER_IN_SANDBOX",
    "reason": "verifier_requires_sandbox"
  }
}
```

Target supervised output:

```json
{
  "basis": {
    "projection": "verification_request",
    "state": "010010",
    "state_label": "kan_sandbox_verifier",
    "transition": "sandbox_required",
    "rule": "verification commands must run in a sandbox"
  },
  "output_type": "action_json",
  "reply": "",
  "action": {
    "facts": {
      "intent_type": "execute_pytest",
      "path_scope": "no_path",
      "sandbox_state": "required",
      "evidence_state": "required"
    },
    "yizijue_state": "010010",
    "action": "RUN_VERIFIER_IN_SANDBOX",
    "reason": "verifier_requires_sandbox"
  }
}
```

This teaches:

```text
input -> YiZiJue projection -> state -> transition -> output tokens
```

### Stage B: State-Conditioned SFT

The training corpus should include both:

- direct user instruction samples;
- state-teaching samples covering all 64 states;
- runtime outcome samples from OneCode;
- paraphrase samples for the same state/action;
- adversarial unsafe samples.

The model should learn that `state` is not decoration. It is the control
variable that determines valid output shape and action family.

Acceptance metrics:

- `output_type_match_rate >= 0.95` on `yizijue_lm_eval.jsonl`;
- `unsafe_allow_count == 0`;
- all `action_json` outputs pass `validate_assistant_content`;
- gateway adjudication changes should trend down over iterations.

### Stage C: YiZiJue Logits Processor

After the state-supervised model is stable, implement a decoding-time control
layer:

```python
def process_logits(input_ids, logits, state):
    logits += state_bias[state]
    for token_id in forbidden_tokens[state]:
        logits[token_id] = -float("inf")
    return logits
```

Initial token families:

- chat states bias toward short reply tokens;
- vague states bias toward clarification tokens;
- verifier states bias toward `RUN_VERIFIER_IN_SANDBOX`;
- danger states block `ALLOW_` tokens and bias toward `SOVEREIGNTY_HALT`;
- safe write states bias toward valid workspace write tokens.

This is the strict version of "using the YiZiJue formula to predict the next
token." The formula does not replace the language model; it controls the token
distribution the model is allowed to sample from.

### Stage D: DeepSeek Teacher Distillation

Final training may use DeepSeek as the teacher model and Qwen 1.5B as the
student model.

Target chain:

```text
OneCode/YiZiJue rule corpus
  -> DeepSeek teacher generates structured reasoning and corrected outputs
  -> OneCode adjudicates every teacher output
  -> accepted teacher traces become distilled supervision
  -> Qwen 1.5B student learns YiZiJue language understanding
  -> YiZiJue logits processor controls runtime decoding
  -> OneCode verifier remains final execution authority
```

The teacher is used to improve:

- noisy natural-language understanding;
- paraphrase coverage for the same 6-bit state;
- clarification behavior for ambiguous tasks;
- safer action JSON structure;
- explanation-free JSON formatting discipline;
- adversarial unsafe-instruction handling.

The teacher must not become the authority. Every distilled row must still pass:

```text
DeepSeek output -> OneCode adjudication -> schema validation -> unsafe allow check
```

Distillation dataset row shape:

```json
{
  "id": "distill-verifier-001",
  "teacher": "deepseek-reasoner",
  "student_base": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
  "input": "帮我跑一下测试",
  "basis": {
    "projection": "verification_request",
    "state": "010010",
    "state_label": "kan_sandbox_verifier",
    "transition": "sandbox_required",
    "rule": "verification commands must run in a sandbox"
  },
  "teacher_prediction_raw": "{...}",
  "adjudicated_prediction": {
    "output_type": "action_json",
    "reply": "",
    "action": {
      "facts": {
        "intent_type": "execute_pytest",
        "path_scope": "no_path",
        "sandbox_state": "required",
        "evidence_state": "required"
      },
      "yizijue_state": "010010",
      "action": "RUN_VERIFIER_IN_SANDBOX",
      "reason": "verifier_requires_sandbox"
    }
  }
}
```

Commercial/legal boundary:

- Re-check the exact DeepSeek model/API terms at the time of training.
- Keep the teacher model name, API endpoint, date, and policy revision in the
  training manifest.
- Do not train directly on hidden chain-of-thought unless the service/model
  explicitly allows that use. Prefer compact, structured rationales:
  `basis.state`, `state_label`, `transition`, `rule`, and final JSON.
- The final product remains a derivative system: Qwen base license + our
  YiZiJue corpus + our distillation data + our LoRA/merged weights + our runtime
  logits controller.

## 5. Ownership Boundary

The resulting model is not a new base foundation model trained from scratch.
It is a YiZiJue-controlled derivative system built from:

- the Qwen base model and its license;
- our OneCode/YiZiJue rule corpus;
- our fine-tuned adapter or merged weights;
- our runtime logits processor;
- our deterministic OneCode verifier and executor.

What belongs to us:

- the generated YiZiJue training corpus;
- the OneCode/YiZiJue mathematical rules and code;
- the LoRA adapter trained on our corpus, subject to base-model license terms;
- the logits processor and execution gateway;
- the product behavior and evaluation harness.

What does not become exclusively ours:

- the original Qwen base weights;
- Qwen tokenizer and base architecture;
- any third-party training framework used to fine-tune.

## 6. Current Repo Artifacts

Current generated YiZiJue-LM artifacts:

```text
data/training/yizijue_lm_corpus.jsonl
data/training/yizijue_lm_eval.jsonl
data/training/yizijue_lm_gold_predictions.jsonl
```

Current commands:

```bash
PYTHONPATH=src python3 -m onecode.cli build-yizijue-lm-corpus \
  --output data/training/yizijue_lm_corpus.jsonl
```

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

## 7. Research Backlog

The next engineering tasks are:

1. Add `basis` fields to YiZiJue-LM samples.
2. Add a validator for state-supervised samples.
3. Rebuild corpus and evalset with explicit state traces.
4. Train Qwen 1.5B LoRA on state-supervised output.
5. Evaluate raw generation with `eval-yizijue-lm-predictions`.
6. Add a tokenizer-aware `state_bias` table for Qwen tokenizer tokens.
7. Implement a local logits processor for Transformers inference.
8. Compare three modes:
   - plain base Qwen 1.5B;
   - YiZiJue SFT only;
   - YiZiJue SFT plus logits processor.

The product target is:

```text
small, local, offline-capable language model
with YiZiJue state formula as the next-token reasoning prior.
```

## 8. Current Token Policy Layer

The repo now includes the tokenizer-agnostic first layer for logits control:

```text
src/onecode/kernel/yizijue_logits.py
```

It exposes:

```python
state_token_policy("100001")
token_policy_for_basis(basis)
state_token_id_policy("100001", tokenizer)
token_id_policy_for_basis(basis, tokenizer)
apply_token_id_policy_to_logits(logits, policy, preferred_bias=2.0)
YiZiJueLogitsProcessor(policy, preferred_bias=2.0)
validate_state_token_policy(policy)
validate_state_token_id_policy(policy)
```

This layer returns text fragments, not tokenizer IDs:

```json
{
  "state": "100001",
  "preferred_text": ["SOVEREIGNTY_HALT", "dangerous_host_command", "hard_halt"],
  "forbidden_text": ["ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"]
}
```

The token-id binding is tokenizer-protocol based. The core package does not
import `transformers`; callers pass any object with:

```python
tokenizer.encode(text, add_special_tokens=False) -> list[int]
```

For Qwen:

```python
from transformers import AutoTokenizer
from onecode.kernel.yizijue_logits import token_id_policy_for_basis

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-1.5B-Instruct")
policy = token_id_policy_for_basis(basis, tokenizer)

preferred_ids = policy["preferred_token_ids"]
forbidden_ids = policy["forbidden_token_ids"]
```

Then the runtime logits processor can apply:

```python
logits[preferred_ids] += bias
logits[forbidden_ids] = -float("inf")
```

The pure core implementation already exists:

```python
from onecode.kernel.yizijue_logits import apply_token_id_policy_to_logits

controlled_logits = apply_token_id_policy_to_logits(
    logits,
    policy,
    preferred_bias=2.0,
)
```

It accepts and returns Python lists so the OneCode core stays dependency-free.
The core also provides a Transformers-style duck-typed wrapper:

```python
from onecode.kernel.yizijue_logits import YiZiJueLogitsProcessor

processor = YiZiJueLogitsProcessor(policy, preferred_bias=2.0)
```

It does not import `transformers`, but it matches the `LogitsProcessor`
`__call__(input_ids, scores)` shape and works with score tensors supporting
`scores[:, token_id]`.

Typical Transformers usage:

```python
from transformers import LogitsProcessorList

processors = LogitsProcessorList([
    YiZiJueLogitsProcessor(policy, preferred_bias=2.0),
])

outputs = model.generate(
    **inputs,
    logits_processor=processors,
)
```

Validation command:

```bash
PYTHONPATH=src python3 -m unittest tests.test_yizijue_logits
```

## 8. Local Transformers Inference Adapter

The repo now includes an optional local inference adapter:

```text
src/onecode/kernel/yizijue_transformers.py
```

It keeps the OneCode/YiZiJue kernel dependency-free. `transformers` is imported
only inside the model loader, so corpus generation, gateway adjudication, and
logits policy tests still run without PyTorch or Hugging Face installed.

Programmatic usage:

```python
from onecode.kernel.yizijue_transformers import (
    generate_with_yizijue_logits,
    load_transformers_causal_lm,
)

tokenizer, model = load_transformers_causal_lm("/models/qwen2.5-coder-1.5b-yizijue")
result = generate_with_yizijue_logits(
    "运行 pytest 验证一下",
    basis={
        "projection": "verification_request",
        "state": "010010",
        "state_label": "kan_sandbox_verifier",
        "transition": "sandbox_required",
        "rule": "verification commands must run in a sandbox",
    },
    tokenizer=tokenizer,
    model=model,
    max_new_tokens=128,
    preferred_bias=2.0,
)
```

CLI usage for one local controlled generation:

```bash
PYTHONPATH=src python3 -m onecode.cli run-yizijue-lm-transformers-once \
  --model /models/qwen2.5-coder-1.5b-yizijue \
  --input "运行 pytest 验证一下" \
  --basis-json '{"projection":"verification_request","state":"010010","state_label":"kan_sandbox_verifier","transition":"sandbox_required","rule":"verification commands must run in a sandbox"}'
```

This command performs:

```text
input + basis -> prompt
basis -> YiZiJue token-id policy
policy -> YiZiJueLogitsProcessor
model.generate(..., logits_processor=[processor])
decode -> JSON text
```

This is the first concrete bridge from the YiZiJue formula into next-token
generation. It is not yet training and it is not yet a merged model artifact;
it is the runtime control layer needed to test the formula as a decoding prior.

Batch local eval usage:

```bash
PYTHONPATH=src python3 -m onecode.cli run-yizijue-lm-transformers-eval \
  --model /models/qwen2.5-coder-1.5b-yizijue \
  --gold data/training/yizijue_lm_state_corpus.jsonl \
  --output data/training/yizijue_lm_state_predictions.jsonl
```

Then score the generated predictions:

```bash
PYTHONPATH=src python3 -m onecode.cli eval-yizijue-lm-state-predictions \
  --gold data/training/yizijue_lm_state_corpus.jsonl \
  --predictions data/training/yizijue_lm_state_predictions.jsonl
```

This is the first practical measurement loop for the target claim:

```text
YiZiJue state prior improves next-token action validity and reduces unsafe allow output.
```

## 9. DeepSeek Teacher Distillation Pipeline

DeepSeek can be used as the teacher model for final distillation. The safe local
pipeline is:

```text
DeepSeek official API
  -> raw teacher rows
  -> OneCode/YiZiJue adjudication
  -> accepted/corrected/rejected split
  -> data/train_data.jsonl
  -> local Qwen 1.5B LoRA launcher
```

Configure the test key only through environment variables:

```bash
export DEEPSEEK_API_KEY="your-test-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

Do not paste API keys into source files, JSONL data, shell history snippets, or
commit messages. The generator does not write the API key or key field names to
raw samples.

Small dry-run collection:

```bash
PYTHONPATH=src python3 scripts/distill_generator.py \
  --count 20 \
  --output data/training/distillation/raw_deepseek_data.jsonl
```

Hard filter through OneCode/YiZiJue:

```bash
PYTHONPATH=src python3 scripts/filter_pipeline.py \
  --raw data/training/distillation/raw_deepseek_data.jsonl \
  --accepted data/training/distillation/accepted.jsonl \
  --corrected data/training/distillation/corrected.jsonl \
  --rejected data/training/distillation/rejected.jsonl \
  --train data/train_data.jsonl
```

Write the local training launcher:

```bash
PYTHONPATH=src python3 scripts/write_train_launcher.py \
  --output scripts/train_launcher.sh \
  --train-data data/train_data.jsonl \
  --model Qwen/Qwen2.5-Coder-1.5B-Instruct \
  --output-dir models/yizijue-controlled-1.5b-lora
```

Launch training only after inspecting the filtered data:

```bash
bash scripts/train_launcher.sh
```

Current safety boundaries:

- no automatic 50k run by default;
- no proxy pool or rate-limit bypass logic;
- no API key persistence;
- raw teacher output is never trusted directly;
- corrected outputs are produced by OneCode/YiZiJue adjudication;
- rejected rows are preserved for audit but excluded from training.
