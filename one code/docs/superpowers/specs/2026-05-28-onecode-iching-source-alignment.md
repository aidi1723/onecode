# OneCode Iching Source Alignment

Date: 2026-05-28
Project root: `/Users/aidi/大字典/one code`
Status: Source alignment for v0.5+ kernel work

## Purpose

This document separates stable mathematical facts from later symbolic correspondence systems before adding more Zhouyi/Yijing-inspired rules to OneCode.

The project should treat the Iching kernel as a deterministic control surface, not as a divination-text database. The kernel may use traditional terms as compact labels, but every rule must be assigned to a source layer.

## Source Baseline

The source review used these public references:

- Encyclopaedia Britannica, `Yijing`: describes the Yijing as a 64-hexagram system built from paired trigrams, with solid lines representing yang and broken lines representing yin.
- Internet Encyclopedia of Philosophy, `Yinyang`: describes yinyang as interaction, harmonization, and dynamic balance rather than static opposition.
- Stanford Encyclopedia of Philosophy, `Metaphysics in Chinese Philosophy`: describes five phases in terms of generation and overcoming/control cycles.
- Joseph Adler, `Yin-yang, the Five Phases (wu-xing), and the Yijing`: summarizes two modes, four images, eight trigrams, five phases, and binary-style trigram/hexagram composition.

These sources agree on the broad structural layers but do not justify collapsing every later correspondence table into the same kernel layer.

## Layer 1: Bit-Derived Mathematical Kernel

These rules are safe to encode as kernel invariants because they are direct consequences of binary line composition.

Current OneCode implementation:

- one line is either yin or yang
- six lines form one status code
- three lower lines form the inner trigram
- three upper lines form the outer trigram
- two trigrams form one 6-bit state
- there are exactly 64 possible states
- changing one line is a single bit flip

Code ownership:

- `compute_status()`
- `flip_line()`
- `hexagram_records()`
- `hexagram_record()`
- `cross_cutting_profile()`

The project uses `1 = yang` and `0 = yin`. This is a local engineering convention. Some traditional or teaching sources use the opposite binary assignment. The code must not claim that this convention is universal; it is the OneCode canonical encoding.

## Layer 2: Yin-Yang Dynamics

Yinyang should be treated as a cross-cutting dynamic profile, not a separate parallel module.

Current OneCode implementation:

- global six-line yin/yang count
- per-line polarity
- four-symbol window pressure
- inner-trigram pressure
- outer-trigram pressure
- global pressure: `cooldown`, `activate`, or `stable`

Code ownership:

- `yin_yang_profile()`
- `yin_yang_cross_profile()`
- `balance_pressure()`

Design rule:

Yin-yang pressure may modulate transitions, but it should not replace physical evidence such as path traversal, timeout, or asset SHA verification.

## Layer 3: Four-Symbol Projection

Four symbols are a two-line projection over the same six-bit state. They are not independent state.

Current OneCode implementation:

- `00 -> tai_yin`
- `01 -> shao_yang`
- `10 -> shao_yin`
- `11 -> tai_yang`

Code ownership:

- `four_symbol_for_bits()`
- `four_symbols()`

Design rule:

Four-symbol windows are diagnostic context. They should not directly authorize disk IO or tool execution.

## Layer 4: Trigram Element Correspondence

The trigram-to-five-phase table is a correspondence layer, not a bit-derived mathematical invariant.

Current OneCode implementation:

- `QIAN`, `DUI` -> `metal`
- `ZHEN`, `XUN` -> `wood`
- `KAN` -> `water`
- `LI` -> `fire`
- `KUN`, `GEN` -> `earth`

Code ownership:

- `TRIGRAM_ELEMENTS`
- `element_for_trigram()`

Design rule:

This layer should be marked as correspondence-derived. It may guide transition interpretation, but it must remain replaceable if future source review selects a different correspondence system.

## Layer 5: Five-Phase Dynamics

The five phases are modeled as generation and control relations.

Current OneCode implementation:

Generation:

```text
wood -> fire -> earth -> metal -> water -> wood
```

Control:

```text
wood -> earth -> water -> fire -> metal -> wood
```

Code ownership:

- `GENERATES`
- `CONTROLS`
- `element_relation()`
- `element_dynamics()`

Design rule:

Five-phase dynamics should consume yin-yang pressure as a modifier. Transition logic should consume `element_dynamics()` instead of manually checking raw trigram pairs.

## Layer 6: Runtime Sovereignty Semantics

This layer is OneCode-specific. It is not a historical Yijing claim.

Current mappings:

- `fire controls metal` -> `hard_control` -> sovereignty breach halt
- `water generates wood` -> `recovery_seed` -> checkpoint/resume seed
- yang excess -> cooldown

Code ownership:

- `classify_outcome()`
- `classify_resume_audit()`
- `transition()`

Design rule:

Runtime semantics must always be traceable to physical evidence:

- path boundary violation
- permission denial
- timeout
- asset ready state
- SHA mismatch
- missing file

The symbolic layer explains and compresses these facts; it does not replace them.

## Excluded From Kernel

These should not be encoded in the kernel until separately sourced and reviewed:

- hexagram names
- hexagram judgments
- line texts
- King Wen ordering
- Fuxi ordering beyond binary composition
- eight-palace assignment
- na-jia rules
- fortune-telling interpretations
- feng shui derivative tables
- personality or gender claims attached to trigrams

They can later live in a knowledge package or documentation layer, but not in the control kernel.

## Current Gap List

The kernel is now structurally aligned, but these follow-up improvements remain reasonable:

- Add explicit metadata fields marking each profile field as `bit_derived`, `correspondence_derived`, or `onecode_runtime`.
- Add tests proving `transition()` never performs disk or tool actions directly.
- Add a source note near `TRIGRAM_ELEMENTS` clarifying that it is a correspondence table.
- Add optional alternate correspondence tables only if a real use case requires them.

## Engineering Rule

When a future rule is proposed, classify it first:

1. Is it bit-derived?
2. Is it a symbolic correspondence?
3. Is it OneCode runtime semantics?
4. Is it interpretive text that belongs outside the kernel?

Only categories 1 through 3 may enter `src/onecode/kernel/hexagram.py`.
