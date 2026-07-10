# OneCode I Ching Rule Canonicalization Design

## Goal

Preserve OneCode's verified six-bit execution kernel while correcting the
canonical trigram encoding boundary and preparing the rule surface for later
position, correspondence, perspective, and timing rules without invalidating
historical evidence.

## Confirmed Findings

### The kernel foundation remains valid

OneCode already closes physical evidence through one deterministic rule surface:

```text
physical evidence
-> yin/yang bits
-> four-symbol windows
-> inner and outer trigrams
-> 64-state hexagram code
-> five-element correspondence modulation
-> transition
-> dispatch
-> checkpoint, ledger, and WAL evidence
```

The existing state space, totality certificates, safety dominance, entropy,
transition graph, stability analysis, and evidence persistence remain the
authoritative execution foundation. This design does not introduce confidence,
priority, mood, retry score, or a parallel policy engine.

### Canonical trigram encoding defect

OneCode declares six-bit line order as bottom-to-top. Under that convention the
canonical trigram encodings are:

| Trigram | Bottom-to-top lines | Canonical bits |
| --- | --- | --- |
| kun | yin, yin, yin | `000` |
| zhen | yang, yin, yin | `001` |
| kan | yin, yang, yin | `010` |
| dui | yang, yang, yin | `011` |
| gen | yin, yin, yang | `100` |
| li | yang, yin, yang | `101` |
| xun | yin, yang, yang | `110` |
| qian | yang, yang, yang | `111` |

The legacy v1 runtime assigned `XUN = 101` and `LI = 110`. This was internally
self-consistent but not canonically consistent with the declared line order. It
also changed the expected complement pairs from `zhen <-> xun` and `kan <-> li`
to `zhen <-> li` and `kan <-> xun`.

### Compatibility constraint

Historical checkpoints, ledgers, WAL rows, profile hashes, tests, documentation,
benchmarks, and training labels contain v1 numeric status codes. Directly
swapping the two constants would reinterpret existing evidence and break the
meaning of persisted hashes. Historical evidence must remain readable under its
original rule schema.

## Rule Schema Model

OneCode will distinguish two rule schemas:

- `onecode-iching-v1`: the historical persisted encoding. Missing schema
  metadata is interpreted as v1 for deterministic legacy reads.
- `onecode-iching-v2`: the canonical bottom-to-top trigram encoding with
  `LI = 101` and `XUN = 110`. This is the active schema for new runtime and
  evidence writes.

Rule schema identifiers are immutable semantic contracts. A numeric state code
without a schema identifier must continue to be interpreted as v1 while legacy
evidence exists.

## Phase 1 Architecture

Create a focused `onecode.kernel.iching_encoding` module responsible only for:

- schema identifiers;
- canonical and legacy trigram tables;
- schema validation;
- trigram conversion between v1 and v2;
- six-bit status conversion by converting inner and outer trigrams separately;
- canonical line and complement invariants.

Phase 1 introduced this module additively while `IchingKernel` remained on v1.
The later evidence-schema phase added explicit metadata and completed the v2
runtime cutover only after exhaustive semantic comparison.

## Implemented Runtime State

- `ACTIVE_RULE_SCHEMA` is `onecode-iching-v2`.
- New results and evidence always carry the active schema.
- Missing historical schema metadata normalizes to v1.
- Shell projection schema version 3 exposes `rule_state.rule_schema`.
- The migration audit is read-only and records source SHA256 evidence.
- All 64 name-preserving v1/v2 interpretations retain the same transition
  action; no `stop` state becomes `continue`.

## Conversion Rules

Trigram conversion is identity for six trigrams and swaps only the v1 meanings
of bit patterns `101` and `110`:

```text
v1 XUN 101 -> v2 XUN 110
v1 LI  110 -> v2 LI  101
v2 XUN 110 -> v1 XUN 101
v2 LI  101 -> v1 LI  110
```

A hexagram status is converted structurally:

```text
outer = bits 3..5
inner = bits 0..2
converted = convert(outer) << 3 | convert(inner)
```

No conversion may inspect action names, five-element labels, or runtime reasons.
The conversion is a pure encoding transformation.

## Evidence Rules

- Existing evidence remains v1 and must not be rewritten in place.
- New schema-aware artifacts must store `rule_schema` beside a status code.
- Hash validation must use the schema that was active when the artifact was
  written.
- Migration tools must write new artifacts or explicit migration records; they
  must not mutate append-only WAL history.
- Unknown schema identifiers fail closed.

## Implemented Descriptive Rule Layers

The following layers are now emitted as deterministic, auditable profile facts.
They do not modify `transition()` or weaken the existing safety dispatch.

### Position and centrality

Line-position facts cover initial through top line, odd/even proper position,
second/fifth centrality, central-and-proper status, and middle alignment.

### Correspondence and adjacency

Response pairs `(0, 3)`, `(1, 4)`, `(2, 5)`, five adjacent pairs, and the
third/fourth line boundary are recorded explicitly.

### Trigram virtues

A trigram virtue layer records qian-strength, kun-receptivity, zhen-initiation,
xun-penetration, kan-risk, li-clarity/attachment, gen-stopping, and dui-exchange.

### Opposite and inverse certificates

Full-polarity complement and six-line reversal are emitted as perspective audit
certificates and do not influence dispatch.

### Logical timing and line mutation

Separate evidence reclassification, local line mutation, and macro policy
transition. Logical task phases may select which line is eligible to change;
wall-clock divination, random casting, and calendar-dependent rules are outside
scope.

## Explicit Non-Goals

- No reinterpretation or in-place rewriting of v1 evidence.
- No rewriting of existing WAL, checkpoint, or training artifacts.
- No Na Jia, stems and branches, six relatives, void branches, calendar luck,
  or random casting.
- No weakening of LogosGate, PathGuard, verifier, sandbox, or approval rules.
- No new authority-bearing variable outside the six-bit rule surface.

## Acceptance Criteria

Phase 1 is complete when:

1. Canonical trigram line invariants pass for all eight trigrams.
2. Canonical complement pairs pass for qian/kun, zhen/xun, kan/li, and dui/gen.
3. v1-to-v2 and v2-to-v1 conversion round-trip all eight trigrams.
4. Status conversion round-trips all 64 states.
5. Invalid schema identifiers and invalid trigram/status values are rejected.
6. Existing semantic actions and safety dominance remain unchanged.
7. New runtime evidence writes v2 while missing historical schemas read as v1.
8. Added descriptive rule layers remain outside transition authority.

## Rollout Decision

The rollout was additive and versioned: pure conversion first, explicit evidence
schema second, exhaustive 64-state comparison third, and runtime cutover last.
Future changes that allow position, correspondence, virtue, perspective, or
timing facts to influence dispatch require a separate TDD plan and proof that no
hard safety outcome is relaxed.
