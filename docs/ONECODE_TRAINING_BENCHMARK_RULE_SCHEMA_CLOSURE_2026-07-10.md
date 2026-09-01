# OneCode Training and Benchmark Rule Schema Closure

Date: 2026-07-10

## Objective

Close the schema boundary around training, evaluation, prediction, framework
export, and benchmark records without changing OneCode's I Ching execution
formulas.

## Foundation Constraint

All records remain projections of the same bottom theory:

```text
six yin/yang line bits
-> inner and outer trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> existing transition and dispatch
```

This phase did not modify line classification, five-element relations, balance
formulas, `transition()`, dispatch, LogosGate, PathGuard, approvals, verifier,
or sandbox authority.

## Problems Resolved

1. Gateway training JSONL rows did not identify whether six-bit states used v1
   or canonical v2 encoding.
2. YiZiJue-LM corpus, evaluation, state, and prediction records could lose the
   encoding identity when separated from their source files.
3. LLaMA-Factory and Axolotl exports retained messages but discarded the rule
   schema envelope.
4. Benchmark and A/B reports embedded runtime status codes without a report-level
   schema identity.
5. Historical v1 Li/Xun states could be misread if their raw numeric values were
   passed directly into the active v2 kernel profile.

## Implemented Resolution

- Added record-level `rule_schema` to gateway training rows.
- Added schema normalization to YiZiJue-LM corpus, evaluation, state, and
  prediction envelopes.
- Added schema metadata to LLaMA-Factory and Axolotl exported records.
- Added active schema metadata to benchmark and A/B report roots.
- Made new generators emit `onecode-iching-v2` explicitly.
- Kept missing historical metadata normalized to `onecode-iching-v1`.
- Preserved schema through training-row reconstruction and prediction writing.
- Converted historical status codes by trigram name before deriving current
  kernel profiles, without changing the original stored state.

## Strict Model Contract

The Action JSON contract remains unchanged:

```text
facts
yizijue_state
action
reason
```

`rule_schema` belongs to the persisted record envelope. It is not a model
decision variable and does not participate in transition or dispatch.

## Bottom-Theory Verification

A 64-state dual-schema certificate compared historical v1 states with their
name-preserving v2 equivalents across:

- inner and outer trigram names;
- inner and outer elements;
- five-element generation/control relation;
- modulation;
- yin/yang balance;
- yin/yang pressure;
- transition action;
- dispatch decision.

Result:

```text
states_checked = 64
foundation_mismatch_count = 0
legacy_li_trigrams = li/li
legacy_li_elements = fire/fire
```

## TDD Evidence

- RED confirmed missing schema fields in training, YiZiJue, framework export,
  prediction, and benchmark envelopes.
- GREEN added only record metadata and name-preserving compatibility conversion.
- The strict Action JSON test remained green throughout.
- Historical v1 Li regression proves `110` remains Li/fire under v1 semantics.

## Verification

```text
Focused training/benchmark/kernel verification: 230 tests passed
Full verification: 770 tests passed, 1 skipped
Source quality: ok
Doctor: ok
Release audit: wheel assets ok
Publish action: not performed
```

## Remaining Boundary

The next phase must not modify the bottom theory casually. The current visible
gap is that `cross_cutting_profile()` exposes `mutation: null` even though a
pure `mutation_profile(before, after)` certificate already exists. Any next
step should first determine whether runtime before/after evidence can populate
this field descriptively without selecting a new line, changing a state, or
modulating transition/dispatch.
