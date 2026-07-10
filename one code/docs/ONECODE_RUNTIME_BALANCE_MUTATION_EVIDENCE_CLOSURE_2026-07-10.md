# OneCode Runtime Balance Mutation Evidence Closure

Date: 2026-07-10

## Objective

Make the existing yin/yang balance feedback observable without changing the
I Ching kernel's state, five-element, transition, or dispatch formulas.

## Implemented Boundary

- `cross_cutting_profile()` remains static and keeps `mutation: null`.
- `balance_mutation_evidence(before, after)` is a pure observation certificate.
- Runtime assets store the full certificate.
- Results aggregate changed assets, changed lines, triadic bands, and the latest
  before/after pair.
- Checkpoints, manifests, and ledgers persist bounded summaries.
- Global WAL stores `bm = [changed assets, changed lines, before, after]`.
- Paths without an actual raw-to-balanced pair do not fabricate mutation data.

## Bottom Theory

All before/after facts are read from the existing kernel:

```text
yin/yang lines
-> trigrams
-> five-element relation and modulation
-> yin/yang pressure and balance
-> transition
-> dispatch
```

The evidence does not choose a line, mutate a state, rebalance a result, or
override safety authority.

## Evidence Budget

The initial four-key WAL projection exceeded the existing compact-entry budget.
It was replaced with one fixed four-scalar tuple. The existing WAL size test
then passed without relaxing its threshold.

## Compatibility

- Legacy checkpoint, manifest, ledger, and WAL evidence remains readable.
- Mutation fields are additive and optional.
- Static profile hashes are unchanged because runtime mutation is not included
  in profile identity.

## Read-Side Integrity Follow-Up

The next phase validates full mutation certificates against a fresh calculation
from the existing kernel, checks persisted summary consistency, validates and
recovers the compact WAL tuple, and exposes a read-only shell v4
`balance_state`. This follow-up remains observational and is recorded in
`docs/ONECODE_MUTATION_EVIDENCE_INTEGRITY_SHELL_V4_CLOSURE_2026-07-10.md`.

## Verification Status

```text
Focused kernel, runner, checkpoint, WAL, benchmark, integration,
execution-engine, and model-loop tests: 238 passed
Safety-equivalence states: 64
Events per state: 5
Evidence pairs checked: 320
Authority mismatch count: 0
Static mutation non-null count: 0
Full verification: 772 tests passed, 1 skipped
Source quality: ok
Doctor: ok
Release audit: wheel assets ok
Publish action: not performed
```
