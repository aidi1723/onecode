# OneCode Runtime Balance Mutation Evidence Design

## Goal

Expose the line changes already produced by `apply_balanced_event()` as
auditable runtime evidence without changing how any state, line, element,
transition, or dispatch decision is calculated.

## Foundation Boundary

The authoritative chain remains:

```text
physical evidence
-> six yin/yang bits
-> trigrams
-> five-element generation/control
-> yin/yang pressure and dynamic balance
-> existing transition and dispatch
```

This phase observes the existing `raw_status_code -> balanced_status_code`
result. It does not select a changing line, generate a new state, rebalance the
kernel, or feed mutation facts back into transition or dispatch.

## Static and Dynamic Separation

`cross_cutting_profile(status_code)` remains a static identity document and
continues to expose `mutation: null`. This preserves stable profile hashes and
registry reuse.

Dynamic evidence is stored separately:

- full `balance_mutation` on each runtime asset;
- aggregate `balance_mutation_summary` on the run result;
- compact summary on checkpoint and manifest records;
- fixed-size compact aliases in the global WAL.

## Full Asset Evidence

`balance_mutation` contains:

- before and after status codes and binaries;
- changed line indexes, count, and earth/human/heaven bands;
- before and after yin/yang balance and pressure;
- before and after inner/outer elements;
- before and after five-element cross relation and modulation;
- before and after transition action and dispatch decision.

All values come from existing `mutation_profile()`,
`cross_cutting_profile()`, `transition()`, and `dispatch_decision()` methods.

## Compact Persistence

Checkpoint and manifest summaries contain bounded counts, bands, and before/
after status codes. The WAL uses one fixed tuple alias:

```text
bm = [changed_asset_count, total_changed_line_count,
      latest_before_status_code, latest_after_status_code]
```

The tuple has exactly four scalar entries. No full profile or unbounded list is
added to the WAL.

## Compatibility

- Existing evidence without mutation fields remains readable.
- No schema-version bump is required because fields are additive.
- Static profile hashes remain unchanged.
- Unknown or malformed mutation evidence is never used as execution authority.

## Acceptance Criteria

1. Assets expose deterministic full mutation evidence.
2. Result summaries aggregate multiple assets without recomputing states.
3. Checkpoint, manifest, ledger, and WAL preserve bounded mutation evidence.
4. `cross_cutting_profile()["mutation"]` remains `None`.
5. The 64-state transition and dispatch tables remain unchanged.
6. Existing yin/yang, five-element, and balance formulas remain untouched.
