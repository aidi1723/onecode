# OneCode Multidimensional Hexagram Agent Rule Extension Design

Date: 2026-06-01
Project root: `/Users/aidi/大字典/one code`
Status: Approved direction, pending implementation plan

## Goal

Extend OneCode's yin-yang and five-element foundation with bottom-level computational rules that treat two lines, three lines, and six lines as one coherent algebraic state family:

```text
Y^1 -> Y^2 -> Y^3 -> Y^6
```

The extension should improve deterministic calculation, rule auditability, and transition explainability without weakening the existing safety model. `IchingKernel` remains the single rule authority.

## Design Principle

The new model must preserve a strict boundary between deterministic kernel math and interpretive correspondence rules.

- Bit math is hard kernel law.
- Five-element relation tables are explicit correspondence data.
- Runtime safety gates remain dominant over symbolic modulation.
- Traditional mappings such as Na Jia, time divination, and line text semantics stay outside the hard transition path until separately specified and tested.

## Current Context

The current kernel already has:

- six-bit status codes;
- bottom-to-top line records;
- trigram projections;
- four-symbol projections;
- yin-yang pressure;
- five-element relation and modulation;
- transition, dispatch, stability, and safety certificates.

This design adds higher quality state interpretation around that surface rather than replacing it.

## Scope

### In Scope

Add pure, deterministic helpers and profile fields for:

- dimensional state metadata for `Y^n`;
- triadic decomposition of a hexagram into earth, human, and heaven bands;
- multi-line mutation operations;
- changed-line comparison between two six-bit states;
- nuclear hexagram or inner-trend projection;
- harmony scoring derived from existing five-element relation functions.

### Out of Scope

This design does not add:

- Na Jia or line-branch tables;
- time-based or random state generation;
- guaci/yaoci text databases;
- reward-driven autonomous line rewriting;
- YiZiJue-LM basis, logits, training rows, or prompt changes;
- any transition rule that can override sovereignty, path guard, verifier, or sandbox safety.

These can be future extensions, but they need separate specs because they introduce traditional correspondence data, learning feedback loops, or model-facing behavior.

## Mathematical Model

### Dimensional State Family

The kernel should expose a uniform description of `Y^n`:

```python
dimension_profile(width: int) -> dict
```

For `width = 1`, it describes liangyi. For `width = 2`, four symbols. For `width = 3`, bagua. For `width = 6`, hexagrams. The profile should include:

- `width`;
- `state_count = 1 << width`;
- `bit_order = "bottom_to_top"`;
- `state_space = "Y^n"`;
- a stable label where known: `liangyi`, `four_symbols`, `bagua`, `hexagram`.

This is a metadata helper. It must not change runtime behavior.

### Triadic Hexagram Profile

A six-bit status should be decomposed into three two-line bands:

```text
earth  = lines 0-1: environment, input, objective condition
human  = lines 2-3: agent internal state, intent, action
heaven = lines 4-5: external trend, target feedback, constraint
```

The helper should be:

```python
triadic_profile(status_code: int) -> dict
```

Each band should include:

- band name;
- line indexes;
- two-bit value;
- four-symbol name;
- yin count and yang count;
- polarity balance.

The mapping is explanatory. Transition rules may consume it later only through explicit policy tables.

### Mutation Operators

The existing single-line flip should be lifted into a multi-line mutation operator:

```python
mutate_lines(status_code: int, line_indexes: Iterable[int]) -> int
changed_lines(before: int, after: int) -> list[int]
mutation_profile(before: int, after: int) -> dict
```

Rules:

- line indexes are canonical bottom-to-top indexes `0..5`;
- duplicate line indexes are ignored or normalized;
- out-of-range indexes raise `ValueError`;
- mutation is XOR-based and deterministic;
- `changed_lines()` returns sorted line indexes;
- `mutation_profile()` reports change count and which triadic bands changed.

This gives the runtime a precise way to explain a transition as moving lines from a source state to a target state.

### Nuclear Hexagram / Inner Trend

The kernel should expose the traditional inner-trend projection:

```text
H = (x2, x3, x4, x3, x4, x5)
```

Using zero-based line indexes, this means:

```text
new lines = [line1, line2, line3, line2, line3, line4]
```

Both the input lines and output lines use the existing bottom-to-top bit order.

The helper should be:

```python
nuclear_hexagram(status_code: int) -> int
```

It should be pure bit transformation. The profile may expose the resulting status code, inner trigram, outer trigram, element relation, and transition action for explanation.

Nuclear hexagram data should initially inform kernel diagnostics and profile inspection only. It should not alter `transition()` in this phase.

### Harmony Score

The kernel should expose a small score derived from existing trigram and element relation functions:

```python
harmony_score(status_code: int) -> dict
```

The first implementation should stay conservative:

- compare adjacent triadic bands or inner/outer trigram elements;
- use existing `element_relation()` and `element_cross_relation()`;
- score `generates` as `+2`, `same` as `+1`, `generated_by` as `+1`, `neutral` as `0`, `controls` as `-1`, and `controlled_by` as `-2`;
- return both numeric score and explanation fields.

The score is an explanatory and ranking signal. It must not override hard safety gates.

## Runtime Integration

### Cross-Cutting Profile

`cross_cutting_profile(status_code)` should expose the new fields under stable keys:

```json
{
  "dimension": {},
  "triadic": {},
  "mutation": null,
  "nuclear": {},
  "harmony": {}
}
```

For a single status code, `mutation` can be omitted or `null`. Transition comparison helpers can produce mutation profiles when both source and target are known.

The rule-layer metadata should classify these fields as:

- `dimension`: bit-derived;
- `triadic`: bit-derived with symbolic labels;
- `mutation`: bit-derived;
- `nuclear`: bit-derived projection;
- `harmony`: correspondence-derived score.

### Transition Safety Boundary

No new field in this design changes `transition()` priority. The existing priority remains:

1. hard safety and sovereignty;
2. verifier, sandbox, timeout, and resumability;
3. yin-yang pressure;
4. five-element relation and modulation;
5. fallback discovery.

Future runtime use of `triadic`, `nuclear`, or `harmony` must be table-driven and covered by dedicated tests.

## Testing Strategy

Tests should cover:

- dimensional profiles for widths `1`, `2`, `3`, and `6`;
- invalid width handling;
- triadic band decomposition and line indexes;
- multi-line mutation, duplicate normalization, and invalid indexes;
- changed-line comparison;
- nuclear hexagram bit mapping;
- harmony score determinism and relation explanation;
- cross-cutting profile field presence and rule-layer classification.

Full-suite verification should still account for the current optional TUI dependency requirement. Rule-specific tests should be runnable without installing TUI extras.

## Acceptance Criteria

- The multidimensional helpers are pure, deterministic, and covered by unit tests.
- Existing transition outputs are unchanged unless a future plan explicitly changes them.
- Cross-cutting profiles expose the new facts without duplicating rule logic outside `IchingKernel`.
- No LM, basis, logits, training-data, or prompt behavior is changed by this work.
- Safety, sovereignty, verifier, and sandbox rules continue to dominate all symbolic interpretation.
