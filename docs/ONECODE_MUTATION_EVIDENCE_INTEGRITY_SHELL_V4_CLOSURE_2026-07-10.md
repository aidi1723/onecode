# OneCode Mutation Evidence Integrity and Shell v4 Closure

Date: 2026-07-10

## Objective

Close the read-side integrity boundary for runtime balance mutation evidence
and expose a bounded shell projection without changing the I Ching execution
kernel or any safety authority.

## Implemented Integrity Boundary

- Full asset mutation evidence is recomputed through
  `IchingKernel.balance_mutation_evidence(before, after)` and compared with the
  persisted certificate.
- Tampered full evidence fails closed with
  `invalid_balance_mutation_evidence`.
- Result summaries inconsistent with full assets fail closed with
  `balance_mutation_summary_mismatch`.
- Checkpoint summaries must match their manifest checkpoint records, and the
  manifest top-level summary must match the latest checkpoint summary.
- Legacy evidence without mutation fields remains readable and valid.

## WAL Recovery Boundary

The compact global WAL field remains:

```text
bm = [changed_asset_count, total_changed_line_count,
      latest_before_status_code, latest_after_status_code]
```

The decoder requires exactly four non-boolean integers, nonnegative counts,
changed lines no greater than six per changed asset, and status codes in
`0..63`. Invalid present evidence fails with
`invalid_global_wal_balance_mutation`. A validated tuple is restored into a
named inspection summary without expanding the persisted WAL record.

## Shell v4 Projection

Shell schema version 4 adds the read-only `balance_state` fields:

- `changed_asset_count`;
- `changed_line_count`;
- `changed_bands`;
- `before_status_code`;
- `after_status_code`.

Full evidence can provide changed bands. WAL-only evidence intentionally
projects an empty band list because the compact tuple does not persist bands.

## Bottom-Theory and Authority Preservation

The implementation does not modify or bypass:

```text
yin/yang line bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> transition
-> dispatch
```

It does not add confidence, priority, mood, retry scores, or external policy
state. LogosGate, PathGuard, approvals, verifier, sandbox, and physical evidence
remain dominant. Mutation evidence is descriptive and auditable only; shell
severity, next action, control, delivery, and resume logic do not consume it.

## Compatibility

- Missing `rule_schema` continues to mean `onecode-iching-v1`.
- New runtime evidence continues to use the active v2 schema.
- Historical WAL, checkpoint, manifest, ledger, and training evidence is not
  rewritten.
- Missing mutation evidence projects null counts/states and an empty band list.

## Verification Record

Fresh verification after implementation and documentation completion:

```text
Source quality: ok
Focused inspect/WAL/shell/Web/runner/kernel tests: 213 passed
Safety-equivalence states: 64
Mutation evidence pairs checked: 4096
Transition output mismatch count: 0
Dispatch output mismatch count: 0
Static mutation non-null count: 0
Shell authority mismatch count: 0
Full verification: 779 tests passed, 10 skipped
Doctor: ok
Release audit: wheel assets ok
Publish action: not performed
git diff --check: passed
Forbidden formula diff scan: no matches
```
