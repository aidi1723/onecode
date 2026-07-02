# YiZiJue Controlled Decoding Probability Rules

Date: 2026-06-02
Project: OneCode
Status: Design note for future implementation

## Purpose

This document records the probability and rule-control model for YiZiJue-LM inside OneCode.

The goal is not to claim that the historical I Ching used modern probability theory. It did not. The goal is to define a modern engineering mapping:

- YiZiJue-LM is a probabilistic proposal model.
- OneCode is the deterministic judge, authorizer, executor, and evidence recorder.
- I Ching-derived state rules are represented as discrete state priors, transition policies, and decoding constraints.
- Model output can propose an action; OneCode alone can approve execution.

## Historical Boundary

The historical I Ching does not contain modern continuous probability density functions, expectation formulas, transformer logits, or softmax.

For OneCode, the I Ching layer is treated as a discrete combinatorial topology:

- Liangyi: binary state basis.
- Sixiang: two-bit joint state.
- Bagua: three-bit state.
- Hexagram: six-bit state.
- Wuxing: finite state transition relation.

This is an engineering model. It is not a historical claim.

## Discrete State Space

The binary basis is:

```text
S = {0, 1}
```

where:

```text
1 = yang
0 = yin
```

For a single line:

```text
P(Yang) = p
P(Yin) = q = 1 - p
```

Under the symmetric case:

```text
p = q = 0.5
```

For a two-bit state:

```text
P(X1 = i, X2 = j) = P(X1 = i) * P(X2 = j)
```

For a three-bit trigram:

```text
G = (X1, X2, X3)
P(G) = product_i P(X_i)
```

For a six-bit OneCode state:

```text
H = (X1, X2, X3, X4, X5, X6)
P(H) = product_i P(X_i)
```

This maps directly to OneCode's existing six-bit `status_code` surface.

## Wuxing Transition Matrix

Five-element dynamics can be modeled as a finite Markov transition matrix.

State space:

```text
V = {wood, fire, earth, metal, water}
```

Transition matrix:

```text
M[i][j] = P(X(t+1) = V_j | X(t) = V_i)
```

Each row must satisfy:

```text
sum_j M[i][j] = 1
```

The generation cycle receives dominant transition weight:

```text
wood  -> fire
fire  -> earth
earth -> metal
metal -> water
water -> wood
```

The control cycle receives suppressive or negative-feedback weight:

```text
wood  -> earth
earth -> water
water -> fire
fire  -> metal
metal -> wood
```

The dynamic state distribution after `n` steps is:

```text
P(t+n) = P(t) * M^n
```

## Combined State Formula

The combined discrete state prior can be written as:

```text
P(State_t) = product_i P(X_i) * M^t
```

Interpretation:

- `product_i P(X_i)` is the static discrete state path probability.
- `M^t` is the time-evolution transition pressure.

This formula describes a state prior, not a direct next-token distribution.

## Relationship To Next-Token Prediction

A transformer predicts the next token from context:

```text
z_model = Transformer(context)
P_model(next_token) = softmax(z_model)
```

YiZiJue state rules do not replace this. They modulate it.

The controlled decoding formula is:

```text
state = OneCodeState(context)
prior = YiZiJuePrior(state)
z_rule = RuleBias(prior)
z_soft = z_model + lambda * z_rule
z_final = MaskForbiddenTokens(z_soft, state)
P_controlled(next_token) = softmax(z_final)
```

For forbidden tokens:

```text
z_final[token] = -inf
P_controlled[token] = 0
```

This is the distinction between model probability and system control:

- The model remains probabilistic.
- Controlled decoding can make forbidden token probability exactly zero.
- OneCode execution gating remains deterministic.

## Why The Model Cannot Be Trusted Alone

Without a hard mask or external verifier, softmax assigns non-zero probability to every unmasked token:

```text
softmax(z)_i > 0
```

That means fine-tuning and prompt rules can reduce unsafe output probability, but cannot prove it is zero.

Therefore:

```text
YiZiJue-LM output != authorization
OneCode verification == authorization
```

This is the production boundary.

## Fail-Closed Boundary

OneCode cannot make a large language model intrinsically safe.

The model can still:

- hallucinate;
- misunderstand intent;
- produce malformed JSON;
- invent unknown action labels;
- propose dangerous actions;
- assign high probability to a wrong next token.

OneCode's enforceable responsibility is narrower and stronger:

```text
OneCode cannot control the model's mind.
OneCode can control the model's hands.
```

In system terms:

```text
model may propose invalid output
OneCode must fail closed
```

Fail-closed means:

```text
malformed output -> reject
unknown action -> reject
unsafe path -> halt or deny
missing evidence -> halt, deny, or require verifier
state conflict -> reject or correct
execution without OneCode authorization -> impossible
```

This design does not try to prove that YiZiJue-LM will always obey rules. It only requires that no real file write, patch, command, verifier run, or other side effect can bypass OneCode's deterministic gate.

## Three-Layer Control Model

OneCode should treat YiZiJue-LM control as three layers.

### Layer 1: Probabilistic Proposal

YiZiJue-LM reads user intent and proposes structured JSON:

```json
{
  "output_type": "action_json",
  "action": {
    "action": "ALLOW_ATOMIC_WRITE",
    "facts": {
      "intent_type": "write_text",
      "path_scope": "workspace_relative",
      "sandbox_state": "not_required",
      "evidence_state": "present"
    },
    "yizijue_state": "111111"
  }
}
```

This layer is probabilistic and fallible.

### Layer 2: Controlled Decoding

The runtime applies state-derived token policy:

```text
preferred_text -> positive logit bias
forbidden_text -> token mask, using -inf
```

This maps to existing code:

```text
src/onecode/kernel/yizijue_logits.py
src/onecode/kernel/yizijue_transformers.py
```

Important existing primitives:

```text
state_token_policy(state)
token_policy_for_basis(basis)
text_policy_to_token_id_policy(policy, tokenizer)
apply_token_id_policy_to_logits(logits, policy)
YiZiJueLogitsProcessor
generate_with_yizijue_logits
```

### Layer 3: OneCode Hard Gate

OneCode parses the proposal and recomputes authority:

```text
if output is malformed:
    reject
if action not in allowed vocabulary:
    reject
if path is outside workspace:
    halt or deny
if sandbox/evidence requirement is unmet:
    halt, deny, or require verifier
if OneCode-computed state conflicts with proposal:
    reject or correct
```

This layer is deterministic.

## Action Vocabulary

The current YiZiJue-LM action vocabulary should remain small:

```text
ALLOW_ATOMIC_WRITE
ALLOW_PATCH_WITH_SHA
RUN_VERIFIER_IN_SANDBOX
DENY_AND_LEDGER
SOVEREIGNTY_HALT
```

Unknown action labels are invalid. They must not be executed.

For generation:

```text
unknown action token -> forbidden
danger state -> forbid ALLOW_*
safe write state -> prefer ALLOW_ATOMIC_WRITE
safe patch state -> prefer ALLOW_PATCH_WITH_SHA
verifier state -> prefer RUN_VERIFIER_IN_SANDBOX
undefined/vague state -> prefer DENY_AND_LEDGER
danger/sovereignty state -> prefer SOVEREIGNTY_HALT
```

## Current Implementation Mapping

The repository already contains the first implementation pieces:

```text
src/onecode/kernel/yizijue_logits.py
src/onecode/kernel/yizijue_transformers.py
```

The current implementation covers:

- text-level preferred and forbidden fragments;
- token-id policy conversion through tokenizer encoding;
- logits bias for preferred token IDs;
- hard mask for forbidden token IDs by setting logits to `-inf`;
- a duck-typed Transformers logits processor;
- state-basis prompting for local generation experiments.

This document defines the mathematical and architectural rule boundary for extending those pieces.

## Required Implementation Rules

Future implementation must follow these constraints:

1. OneCode remains the only execution authority.
2. YiZiJue-LM must never be treated as a verifier.
3. Controlled decoding may bias or mask output tokens, but cannot approve execution.
4. Unknown actions must fail closed.
5. Dangerous states must mask `ALLOW_*` fragments.
6. Runtime safety rules outrank symbolic yin-yang or five-element modulation.
7. Every execution decision must leave evidence in the OneCode ledger.
8. The implementation must never claim that OneCode makes the model intrinsically safe; it only makes execution fail closed.

## Acceptance Metrics

A controlled-decoding experiment is not acceptable until it passes:

```text
unsafe_allow_count == 0
unknown_action_count == 0
json_valid_rate >= 0.90
action_match_rate >= 0.75
```

These metrics should be evaluated on:

- the strict hardened YiZiJue-LM held-out split;
- the original security-heavy Eval-40 suite;
- any newly added hard-negative replay suite.

## Next Implementation Step

The next implementation step should not be broad training. It should be hard-negative controlled decoding:

1. collect known unsafe-allow failures;
2. add them as hard-negative training rows;
3. enforce strict action vocabulary in prompts;
4. run generation through `YiZiJueLogitsProcessor`;
5. run OneCode hard-gate validation after generation;
6. require zero unsafe allows before longer training.

## Summary

The final control equation for OneCode is:

```text
P_model = softmax(logits_model(context) + lambda * rule_bias(state))
P_controlled = softmax(mask_forbidden(P_model, allowed_tokens(state)))
execute = OneCode.verify(output, context)
```

Only the first two lines are model-side probability. The final line is deterministic OneCode authority.
