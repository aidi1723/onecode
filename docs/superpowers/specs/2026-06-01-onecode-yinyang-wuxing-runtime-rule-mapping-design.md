# OneCode Yin-Yang Five-Element Runtime Rule Mapping Design

Date: 2026-06-01
Project root: `<private-development-workspace>`
Status: Approved for spec review

## Goal

Map the formal yin-yang, four-symbol, bagua, and five-element rules into OneCode's executable rule system without weakening the existing safety model. The work must proceed in this order:

1. strengthen runtime decision logic;
2. complete the underlying mathematical kernel;
3. expose the richer rule state to YiZiJue-LM basis and logits policy.

The result should make `IchingKernel` the single rule authority. Runner, model-loop, verifier, finalization, and training code should consume kernel outputs instead of duplicating rule interpretation.

## Current Context

The project already has a working Iching control surface in `src/onecode/kernel/hexagram.py`:

- six-bit `status_code`;
- inner and outer trigram projection;
- yin-yang profile and pressure;
- four-symbol windows and balance;
- trigram-to-element mapping;
- five-element relation and modulation;
- transition, dispatch, entropy, topology, and safety certificates;
- YiZiJue-LM `basis` and logits policy consumers.

This design refines the mapping rather than replacing it.

## Rule Layer Boundaries

The implementation must keep three layers separate.

### Bit-Derived Layer

This layer is mathematically derived from bit structure and is safe to treat as hard kernel law:

- liangyi: each line is `0` or `1`;
- four symbols: two-bit projections;
- bagua: three-bit projections;
- sixty-four states: six-bit projections;
- yin-yang counts and polarity index;
- line flips and bit masks;
- cartesian state generation for width `n`.

No traditional correspondence table should be required to compute this layer.

### Correspondence-Derived Layer

This layer is traditional mapping data and must be explicit rather than implied by bit math:

- trigram names;
- trigram-to-five-element mapping;
- five-element generation and control cycles;
- four-symbol-to-direction or four-symbol-to-element mapping when needed;
- future heavenly-stem mapping from yin-yang and five elements.

Changing this layer should not change bit-derived facts.

### OneCode Runtime Layer

This layer maps rule facts to execution behavior:

- transition action;
- dispatch decision;
- execution bandwidth;
- verifier requirement;
- cooldown, checkpoint, prune, throttle, halt, continue, and discover semantics;
- model basis labels and token policy hints.

Safety and sovereignty decisions remain runtime rules, not folklore interpretation.

## Phase 1: Runtime Decision Logic

Phase 1 comes first because it directly improves execution behavior.

### Runtime Priority

`transition(status_code)` should evaluate rules in this order:

1. hard safety and sovereignty conditions;
2. verifier, sandbox, timeout, and resumability conditions;
3. yin-yang pressure;
4. five-element relation and modulation;
5. neutral fallback and rule-gap discovery.

Hard safety conditions must continue to dominate all symbolic modulation. For example, a sovereignty breach must halt even if a five-element relation would otherwise generate or recover.

### Yin-Yang Pressure

The existing `yin_yang_cross_profile()` and `balance_pressure()` should become the standard transition input for polarity pressure:

```text
pure_yang / yang_excess -> cooldown
pure_yin / yin_excess   -> activate or discover
balanced                -> allow element relation to decide
```

The runtime distinction between `activate` and `discover` should depend on whether the state has enough inner execution information to proceed. Pure empty states should remain `discover`; non-empty yin-heavy states can become `activate`.

### Five-Element Runtime Relation

`element_cross_relation(source, target)` should drive general scheduling once safety and polarity gates have passed:

```text
generates     -> accelerate or continue
controls      -> halt, throttle, or prune
same          -> stabilize or continue
generated_by  -> recover or resume
controlled_by -> checkpoint or require_verifier
neutral       -> discover
```

The source remains the outer trigram's element and the target remains the inner trigram's element. This keeps the current model of outer environment pressure acting on inner task state.

### Differentiated Control Actions

Control relations should not all collapse into `halt`. The runtime mapping should preserve the intent already present in tests:

```text
water controls fire -> halt boundary fire
fire controls metal -> halt or suppress unsafe asset confidence
metal controls wood -> prune scope
earth controls water -> throttle flow
wood controls earth -> activate or break inert ground when safe
```

The exact action should be table-driven so the behavior is auditable and testable.

### Dispatch and Bandwidth

`dispatch_decision()` should remain a small projection from transition action to loop behavior:

```text
halt, checkpoint, discover requiring user input -> stop
continue, accelerate, prune, throttle, activate when locally actionable -> continue
```

`execution_bandwidth()` should continue to consume the five-element matrix, but the matrix should be generated from element relation policy where possible and overridden only for explicitly justified runtime cases.

## Phase 2: Mathematical Kernel Completion

Phase 2 consolidates the pure math layer after runtime behavior is stabilized.

### New or Refined Kernel Functions

The kernel should expose small pure functions:

```python
liangyi_values() -> tuple[int, int]
cartesian_states(width: int) -> list[int]
bits_for_state(value: int, width: int) -> list[int]
state_for_bits(bits: list[int]) -> int
four_symbol_for_pair(bits: int) -> str
trigram_for_bits(bits: int) -> dict
hexagram_status(outer: int, inner: int) -> int
generate_element(element: str) -> str
control_element(element: str) -> str
element_distance(source: str, target: str) -> int
```

These functions should be deterministic, side-effect free, and tested without runner integration.

### Bit Order

The canonical order remains lowest bit first:

```text
bit 0: first line
bit 1: second line
bit 2: third line
bit 3: fourth line
bit 4: fifth line
bit 5: sixth line
```

`bits_for_state()` should return this same bottom-to-top order.

### Five-Element Mod Arithmetic

The five-element cycle should be represented with the canonical generation order:

```text
wood -> fire -> earth -> metal -> water -> wood
```

With this order:

```text
generate(x) = x + 1 mod 5
control(x)  = x + 2 mod 5
```

`element_distance(source, target)` should return the modular distance from source to target in this generation order. This lets tests prove generation, control, generated-by, and controlled-by without relying only on ad hoc mappings.

### Records and Rule Surface

Generated records should include enough fields to audit the full rule chain:

- status code and binary;
- line records;
- inner and outer trigram records;
- yin-yang profile and pressure;
- four-symbol windows and balance;
- element records and relation;
- evolved element modulation;
- transition and dispatch projection.

The record should identify each field's rule layer where practical.

## Phase 3: YiZiJue-LM Basis and Token Policy

Phase 3 exposes the richer rule state to model-facing components after the kernel behavior is stable.

### Basis Shape

`state_basis_for_lm_row()` should include compact rule facts in addition to the existing `state`, `state_label`, `transition`, and `rule`:

```json
{
  "state": "010010",
  "state_label": "kan_sandbox_verifier",
  "yin_yang": {
    "balance": "yin_excess",
    "pressure": "activate"
  },
  "trigrams": {
    "outer": "kan",
    "inner": "zhen"
  },
  "elements": {
    "outer": "water",
    "inner": "wood",
    "relation": "generates",
    "modulation": "recovery_seed"
  },
  "transition": "checkpoint",
  "rule": "network water preserves resume seed"
}
```

The basis must stay small enough to be useful for supervised examples and logits policy.

### Prompt and Policy Use

`build_yizijue_generation_prompt()` should preserve the existing JSON-only output contract. The richer basis should help the model infer why an action is allowed, denied, halted, or checkpointed.

`token_policy_for_basis()` should continue to prefer and forbid concrete action fragments. It may add hints from:

- transition action;
- yin-yang pressure;
- element relation;
- state label.

It should not allow the model to override kernel safety gates.

### Training Data Compatibility

Existing training rows should remain valid or have a deterministic migration path. Validation should require only stable fields, while optional rich fields can be accepted during rollout until all generated corpora are updated.

## Testing Strategy

Phase 1 tests:

- transition priority preserves sovereignty halts;
- yin-yang pressure maps to cooldown, activate, or discover;
- every five-element relation maps to an auditable runtime action;
- dispatch decisions remain consistent with transition actions;
- execution bandwidth matches the relation matrix and explicit overrides.

Phase 2 tests:

- cartesian state generation returns `2 ** width` states;
- bit order is bottom-to-top and round-trips through `state_for_bits()`;
- four-symbol and trigram projections are stable;
- five-element generation equals `+1 mod 5`;
- five-element control equals `+2 mod 5`;
- generated records cover all 64 states.

Phase 3 tests:

- basis generation includes yin-yang, trigram, element, transition, and rule fields;
- validation accepts migrated rich basis rows;
- logits policy consumes rich basis fields without weakening forbidden token handling;
- state corpus scoring still compares `state` and `state_label`.

Each phase should finish with:

```bash
PYTHONPATH=src python3 -m compileall src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Non-Goals

This work does not add:

- oracle text;
- changing-line interpretations;
- palace systems;
- date-based divination;
- external traditional datasets;
- UI or TUI changes;
- network lookups;
- autonomous permission expansion.

Future additions such as heavenly stems, earthly branches, na-jia, or palace assignment require separate source alignment and should enter through the correspondence layer, not through hard-coded runtime shortcuts.

## Acceptance Criteria

- Runtime decisions consume yin-yang pressure and five-element relation through explicit kernel functions.
- Safety and sovereignty rules remain higher priority than symbolic modulation.
- Mathematical primitives are exposed as pure functions with direct tests.
- Five-element generation and control are provable by modular arithmetic.
- YiZiJue-LM basis can carry the rule chain without changing the JSON output contract.
- Runner and model-facing code consume `IchingKernel` outputs instead of reimplementing rule interpretation.
