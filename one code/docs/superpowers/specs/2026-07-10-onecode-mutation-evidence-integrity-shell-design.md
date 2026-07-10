# OneCode Mutation Evidence Integrity and Shell Projection Design

## Goal

Close the read-side integrity boundary for runtime balance mutation evidence and
expose a bounded read-only summary to inspect and shell consumers without
changing any execution decision.

## Foundation Boundary

The validator uses the existing kernel as the only oracle:

```text
stored before/after status
-> existing mutation_profile()
-> existing cross_cutting_profile()
-> existing transition()/dispatch_decision()
-> compare with stored evidence
```

No validator, inspect projection, WAL decoder, or shell field may choose a line,
change a state, alter five-element relations, rebalance evidence, or affect
severity, next action, resume, transition, or dispatch.

## Integrity Validation

Add pure validation for:

- full asset `balance_mutation` evidence;
- result and ledger `balance_mutation_summary`;
- checkpoint and manifest summaries;
- WAL `bm` fixed tuple.

Full evidence must equal a fresh
`IchingKernel.balance_mutation_evidence(before, after)` calculation. Summary
counts and latest states must match the full asset list when full assets exist.

Missing mutation evidence remains valid legacy evidence. Malformed or
inconsistent present evidence fails closed with stable corruption reasons.

## Inspect Recovery

Full evidence inspection exposes the validated summary from ledger/manifest.
WAL-only inspection decodes:

```text
bm = [changed_asset_count, total_changed_line_count,
      latest_before_status_code, latest_after_status_code]
```

into the same named summary fields. WAL hash-chain validation remains the trust
boundary for the tuple.

## Shell Projection v4

Add a read-only `balance_state` section:

- `changed_asset_count`;
- `changed_line_count`;
- `changed_bands`;
- `before_status_code`;
- `after_status_code`.

`changed_bands` is available from full evidence; WAL-only summaries may expose
an empty list because the fixed WAL tuple intentionally omits it for size.

The new section is not read by `_severity()`, `_next_action()`, delivery state,
resume state, or control state.

## Compatibility

- Shell schema version increases from 3 to 4.
- Missing mutation fields project all-null counts/states and an empty band list.
- Existing v1/v2 rule schema compatibility remains unchanged.
- Historical evidence is never rewritten.

## Acceptance Criteria

1. Tampered full mutation evidence is reported as corrupt.
2. Tampered summaries inconsistent with assets are reported as corrupt.
3. WAL `bm` is type/range validated and projected by inspect.
4. Shell v4 exposes `balance_state` without changing severity or next action.
5. All transition, dispatch, yin/yang, five-element, and balance outputs remain
   unchanged.
