# OneCode I Ching v2 Canonicalization Closure

Date: 2026-07-10

## Objective

Correct the Li/Xun trigram encoding boundary without invalidating historical
evidence or weakening OneCode's deterministic six-bit Agent execution kernel.

## Findings Resolved

1. The declared bottom-to-top line order requires `LI = 101` and `XUN = 110`.
2. Historical v1 evidence used the opposite Li/Xun numeric assignment and
   therefore could not be reinterpreted safely without schema metadata.
3. Runtime, checkpoint, manifest, ledger, WAL, profile, and shell evidence
   previously lacked a uniform rule-schema identity.
4. Position, centrality, correspondence, adjacency, trigram virtues, opposite,
   and inverse relationships were not exposed as auditable rule facts.

## Implemented Resolution

- Added immutable `onecode-iching-v1` and `onecode-iching-v2` schemas.
- Activated canonical v2 for all new runtime classifications and evidence.
- Interpreted missing historical `rule_schema` as v1 without mutating evidence.
- Added pure trigram/status conversion and a read-only evidence migration audit.
- Added schema identity to result, asset, profile, checkpoint, manifest, ledger,
  global WAL (`rsv`), and shell projection records.
- Bumped shell projection schema from version 2 to version 3.
- Added descriptive position, correspondence, virtue, and perspective profiles.

## Safety Result

The cutover comparison evaluated all 64 status states by preserving trigram
names across v1 and v2. The result was:

```text
semantic_diff_count = 0
stop_to_continue_count = 0
```

The action distribution is unchanged. LogosGate, PathGuard, approvals,
verifier, sandbox, physical evidence, and existing transition/dispatch logic
remain authoritative. The new descriptive profiles do not affect transition.

## Canonical Runtime Examples

| Scenario | Canonical v2 status | Outcome |
| --- | ---: | --- |
| sovereignty breach | 40 | halt + stop |
| valid project context | 49 | continue |
| provider failure | 42 | halt |
| timeout | 17 | checkpoint + stop |
| completed cooldown | 39 | cooldown behavior unchanged |

Older closure reports containing v1 numeric examples remain valid historical
records only when read under `onecode-iching-v1`.

## Compatibility Contract

- Never rewrite append-only historical evidence in place.
- Treat absent schema metadata as v1.
- Reject unknown schema identifiers and invalid status values.
- Include schema identity in new profile hashes and evidence projections.
- Require a separate TDD and safety-equivalence plan before descriptive I Ching
  profiles are allowed to modulate `transition()` or dispatch.

## Remaining Boundary

The training and benchmark projection follow-up now adds `rule_schema` to new
gateway JSONL, YiZiJue-LM corpus/evaluation/state rows, prediction envelopes,
framework exports, and benchmark reports. Legacy absence still deterministically
means v1, so bulk regeneration is not required for readability.

Historical v1 records are converted by trigram name before current-kernel
profile derivation. This preserves the bottom theory: Li remains fire, Xun
remains wood, five-element generation/control remains unchanged, and yin/yang
pressure and dynamic balance continue to come only from the existing kernel.

Runtime balance mutation evidence now records the line changes already produced
by `apply_balanced_event()`. It remains separate from static profile identity
and does not select lines or influence transition/dispatch.

The remaining boundary is unchanged: descriptive position, correspondence,
virtue, perspective, or mutation facts may not influence transition or dispatch
without a separate TDD and safety-equivalence proof.
