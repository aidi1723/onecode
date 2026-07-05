# YiZiJue-LM Small Model Utility Boundary

## Core Conclusion

Training YiZiJue-LM is useful, but it should not be treated as the source of truth.

The small model should be a proposal layer:

```text
natural language
-> candidate OneCode-compatible JSON
-> OneCode validation
-> OneCode final decision
```

It should not be treated as:

```text
authorization
execution authority
final safety judgment
complete rule understanding
```

## Why Blind Training Has Diminishing Returns

The 2026-06-02 hard-negative runs showed the real trade-off:

```text
unsafe_allow_count can be pushed to 0
but action_match_rate may drop below the target gate
```

Latest observed result:

```text
json_valid_rate: 0.95
action_match_rate: 0.725
unsafe_allow_count: 0
```

This means the model can be made more conservative, but it may lose precision in mapping allowed actions.

For a 0.6B model, more SFT can fix one failure while creating another. That is expected behavior for a small probabilistic model, not a training accident.

## What Small-Model Training Is Useful For

Use the small model for:

```text
intent classification
path and evidence extraction
risk-flag proposal
OneCode action JSON drafting
local low-cost first pass
hard-negative pattern exposure
teacher-model distillation compression
```

The small model is useful when the output is checked by OneCode.

## What Small-Model Training Is Not Useful For

Do not rely on the small model for:

```text
absolute rule obedience
final allow/deny decisions
execution permission
security boundary enforcement
complete OneCode logic ownership
eliminating all unsafe generations by SFT alone
```

If the system requires deterministic safety, that safety must live in OneCode.

## Correct Architecture

The desired architecture is:

```text
User request
-> YiZiJue-LM proposes structured facts and candidate action
-> OneCode validates the facts
-> OneCode applies deterministic rules
-> OneCode rejects, rewrites, or approves the candidate
-> OneCode logs the decision
```

The model output is never the final decision.

## Training Target Should Change

Do not train the small model to "understand everything."

Train it to map user intent into a constrained OneCode rule surface:

```text
intent_type
path_scope
evidence_state
sandbox_state
risk_flags
yizijue_state
candidate_action
reason
```

Example:

```json
{
  "intent_type": "write_text",
  "path_scope": "workspace_relative",
  "evidence_state": "present",
  "sandbox_state": "required",
  "risk_flags": ["prompt_injection"],
  "candidate_action": "DENY_AND_LEDGER",
  "reason": "prompt_injection_attempt",
  "yizijue_state": "000000"
}
```

OneCode should then enforce:

```text
if risk_flags contains prompt_injection
and candidate_action starts with ALLOW_
then fail closed to DENY_AND_LEDGER or SOVEREIGNTY_HALT
```

## Next Engineering Priority

The next priority is not more blind SFT.

The next priority is:

```text
controlled decoding
OneCode action whitelist
OneCode risk-flag validator
OneCode fail-closed rewrite layer
failure mining
hard-negative replay only for repeated failures
```

Small-model training continues only as part of this loop:

```text
evaluate
-> mine failures
-> classify failure type
-> add targeted hard negatives
-> train small adapter
-> evaluate again
-> OneCode remains final authority
```

## Practical Rule

If a failure can be solved deterministically in OneCode, solve it in OneCode first.

Use training only when the model repeatedly fails to extract or map the user intent into the correct OneCode rule fields.

That is the stable division of responsibility:

```text
YiZiJue-LM = perception and proposal
OneCode = rules, judgment, execution, ledger
```
