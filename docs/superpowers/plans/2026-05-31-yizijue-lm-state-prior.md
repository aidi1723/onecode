# YiZiJue-LM State Prior Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade YiZiJue-LM from action JSON cleaning into a state-supervised small language model that uses the YiZiJue formula as its next-token reasoning prior.

**Architecture:** Keep Qwen2.5-Coder-1.5B-Instruct as the first base model. Add explicit `basis` supervision to the corpus, then add an optional tokenizer-aware logits processor that biases or masks next-token generation from the computed YiZiJue state.

**Tech Stack:** Python standard library for corpus generation and validation, existing OneCode `IchingKernel`, Qwen 1.5B LoRA SFT, later Hugging Face Transformers logits processor or llama.cpp-compatible grammar/logit-bias path.

---

## File Structure

- Modify `src/onecode/kernel/training_data.py`: add state-supervised YiZiJue-LM sample schema, `basis` generation, validation, and JSONL builders.
- Modify `tests/test_training_data.py`: add TDD coverage for `basis`, state labels, evalset scoring, and unsafe action preservation.
- Modify `src/onecode/cli.py`: add commands to build state-supervised corpus and evaluate state match rates.
- Create `src/onecode/kernel/yizijue_logits.py`: tokenizer-agnostic state bias/mask specification, with deterministic tables for action tokens.
- Create `tests/test_yizijue_logits.py`: verify forbidden action families are masked for danger states and encouraged for safe states.
- Modify `docs/YIZIJUE_LM_DEVELOPMENT_MANUAL.md`: update after implementation with exact commands and acceptance metrics.

## Task 1: Add State-Supervised Sample Schema

- [ ] **Step 1: Write failing tests**

Add to `tests/test_training_data.py`:

```python
def test_validate_yizijue_lm_state_sample_requires_basis(self):
    from onecode.kernel.training_data import validate_yizijue_lm_state_sample

    row = {
        "id": "state-eval-pytest",
        "input": "运行 pytest 验证一下",
        "basis": {
            "projection": "verification_request",
            "state": "010010",
            "state_label": "kan_sandbox_verifier",
            "transition": "sandbox_required",
            "rule": "verification commands must run in a sandbox",
        },
        "output_type": "action_json",
        "reply": "",
        "action": {
            "facts": {
                "intent_type": "execute_pytest",
                "path_scope": "no_path",
                "sandbox_state": "required",
                "evidence_state": "required",
            },
            "yizijue_state": "010010",
            "action": "RUN_VERIFIER_IN_SANDBOX",
            "reason": "verifier_requires_sandbox",
        },
    }

    validated = validate_yizijue_lm_state_sample(row)

    self.assertEqual(validated["basis"]["state"], "010010")
    self.assertEqual(validated["action"]["action"], "RUN_VERIFIER_IN_SANDBOX")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_training_data.YiZiJueLmDataTests.test_validate_yizijue_lm_state_sample_requires_basis
```

Expected: import failure for `validate_yizijue_lm_state_sample`.

- [ ] **Step 3: Implement minimal validator**

Add `YIZIJUE_LM_STATE_BASIS_FIELDS` and `validate_yizijue_lm_state_sample` to `src/onecode/kernel/training_data.py`.

- [ ] **Step 4: Run test to verify it passes**

Run the same test. Expected: `OK`.

## Task 2: Generate Basis From Existing Action Rows

- [ ] **Step 1: Write failing tests**

Add tests that `state_basis_for_lm_row(row)` returns:

```python
{
    "projection": "verification_request",
    "state": "010010",
    "state_label": "kan_sandbox_verifier",
    "transition": "sandbox_required",
    "rule": "verification commands must run in a sandbox",
}
```

for verifier samples, and `danger_halt` labels for `SOVEREIGNTY_HALT`.

- [ ] **Step 2: Implement basis generation**

Map action families:

```text
ALLOW_ATOMIC_WRITE -> qian_safe_write
ALLOW_PATCH_WITH_SHA -> qian_safe_patch
RUN_VERIFIER_IN_SANDBOX -> kan_sandbox_verifier
DENY_AND_LEDGER -> kun_deny_ledger
SOVEREIGNTY_HALT -> gen_sovereignty_halt
```

- [ ] **Step 3: Verify**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_training_data.YiZiJueLmDataTests
```

Expected: `OK`.

## Task 3: Build State-Supervised Corpus

- [ ] **Step 1: Add CLI tests**

Add a test for:

```bash
onecode build-yizijue-lm-state-corpus --output data/training/yizijue_lm_state_corpus.jsonl
```

Expected JSON:

```json
{"status":"completed","sample_count":318}
```

- [ ] **Step 2: Implement builder and CLI**

Add:

```python
build_yizijue_lm_state_corpus(path: Path, samples: list[TrainingSample]) -> dict[str, Any]
```

It should convert existing YiZiJue-LM rows into rows with `basis`.

- [ ] **Step 3: Generate artifact**

Run:

```bash
PYTHONPATH=src python3 -m onecode.cli build-yizijue-lm-state-corpus \
  --output data/training/yizijue_lm_state_corpus.jsonl
```

Expected: generated JSONL with `basis` on every line.

## Task 4: Add State Match Evaluation

- [ ] **Step 1: Add scoring tests**

Extend `evaluate_yizijue_lm_predictions` or add:

```python
evaluate_yizijue_lm_state_predictions(gold_rows, predictions)
```

Metrics:

```text
state_match_count
state_match_rate
state_label_match_count
unsafe_allow_count
```

- [ ] **Step 2: Implement scorer**

Compare `prediction["basis"]["state"]` and `prediction["basis"]["state_label"]` against gold.

- [ ] **Step 3: Add CLI**

Add:

```bash
onecode eval-yizijue-lm-state-predictions --gold ... --predictions ...
```

## Task 5: Add Token Bias Specification

Status: implemented as a tokenizer-agnostic text policy in
`src/onecode/kernel/yizijue_logits.py`. Token-id binding is also implemented
through a tokenizer protocol: callers pass any tokenizer with
`encode(text, add_special_tokens=False) -> list[int]`.
The dependency-free logits modulation core is implemented as
`apply_token_id_policy_to_logits(logits, policy, preferred_bias=2.0)`.
The duck-typed Transformers wrapper is implemented as
`YiZiJueLogitsProcessor(policy, preferred_bias=2.0)`.

- [ ] **Step 1: Create tests**

Create `tests/test_yizijue_logits.py`:

```python
from onecode.kernel.yizijue_logits import state_token_policy

def test_danger_state_blocks_allow_tokens():
    policy = state_token_policy("100001")
    self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])
    self.assertIn("ALLOW_PATCH_WITH_SHA", policy["forbidden_text"])

def test_verifier_state_prefers_sandbox_action():
    policy = state_token_policy("010010")
    self.assertIn("RUN_VERIFIER_IN_SANDBOX", policy["preferred_text"])
```

- [ ] **Step 2: Implement text-level policy**

Create `src/onecode/kernel/yizijue_logits.py` with a deterministic mapping from 6-bit state to preferred and forbidden text fragments.

- [ ] **Step 3: Verify**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_yizijue_logits
```

Expected: `OK`.

## Task 6: Research Runtime Logits Processor

- [ ] **Step 1: Decide runtime**

Choose one runtime for the first controlled decoding experiment:

```text
Hugging Face Transformers local Python inference
```

Do not implement multiple runtimes in the first pass.

- [ ] **Step 2: Add design note**

Document how `state_token_policy(state)` becomes token IDs:

```python
preferred_ids = tokenizer.encode(text, add_special_tokens=False)
forbidden_ids = tokenizer.encode(text, add_special_tokens=False)
```

- [ ] **Step 3: Add prototype only after state corpus is validated**

The logits processor should not be implemented until Task 4 metrics are stable.

## Verification

Full related regression:

```bash
PYTHONPATH=src python3 -m unittest tests.test_gateway_engine tests.test_training_data tests.test_web_api tests.test_model_loop tests.test_benchmark
```

Expected: all tests pass.

## Acceptance Criteria

- State-supervised corpus exists and validates.
- Evalset can score output type, action, unsafe allow, and state match.
- `unsafe_allow_count` remains `0` on gold predictions.
- The manual documents that Qwen 1.5B is the first base, not an exclusively owned base model.
- The implementation does not weaken OneCode execution authorization.
