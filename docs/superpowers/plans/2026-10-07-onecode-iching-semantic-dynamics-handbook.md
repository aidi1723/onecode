# OneCode I Ching Semantic Dynamics Handbook
**Date**: 2026-10-07
**Target Version**: v0.9 (Next-Gen I Ching Kernel)

## 1. Executive Summary

The current OneCode kernel (v0.8) has achieved mathematical perfection regarding the topological closure of the 64 hexagrams ($Q_6$) and basic Wuxing (五行) interactions. However, it treats the hexagram purely as a static 6-bit hash, lacking the temporal, relational, and contextual depth of authentic I Ching (易经) philosophy. 

This handbook outlines the next evolutionary leap for `one code`: transitioning from a **Static Mathematical Topology** to a **Dynamic Semantic Engine** by introducing moving lines (动爻), micro-relational gravity (承乘比应), and macro-temporal life cycles (十二消息卦).

---

## 2. Phase 1: Moving Lines & Combinatorial Semantics (变卦与动爻矩阵)

### 2.1 The Problem
Currently, any state transition is just an XOR bit-flip. The system does not differentiate whether the transition was triggered by the 1st line (initial stage of a task) or the 5th line (core architectural stage).

### 2.2 The Implementation
We will introduce the **Moving Line Oracle (动爻占断器)** based on classical rules (e.g., Zhu Xi's multi-line moving rules / 朱熹《易学启蒙》):
- **Single Line Moving**: The meaning of the specific moving line governs the action (e.g., moving Line 2 implies fixing a core foundational bug, allowing broader write bandwidth).
- **Two/Three Lines Moving**: Evaluate the conflict between the original hexagram (本卦) and the resulting hexagram (变卦).
- **Action**: Add `moving_lines: list[int]` to the `IchingTransition` data class. Instead of global fallback to "discover", transitions will carry semantic reasons like `line_5_moving_architectural_shift`.

---

## 3. Phase 2: Micro-Relational Gravity (承、乘、比、应)

### 3.1 The Problem
Yin and Yang counts are evaluated globally (e.g., `pure_yang`, `yang_excess`). The system ignores the physical structure of the lines. A Yin line resting on a Yang line is safe, but a Yin line pressing down on a Yang line is dangerous.

### 3.2 The Implementation
We will implement the **Structural Force Vectors (爻位力学约束)**:
- **Cheng (承 - Support)**: Yin below Yang. Boosts `execution_bandwidth`.
- **Sheng (乘 - Ride/Oppress)**: Yin above Yang. Triggers `throttle` or `prune`, signaling that a weak or experimental code module is trying to overwrite a core, stable module.
- **Ying (应 - Resonance)**: Lines 1-4, 2-5, 3-6 polarities match. If 2 and 5 resonate (Central resonance / 中正相应), the Sandbox validation requirement can be temporarily relaxed for trusted internal calls.
- **Action**: Extend `hexagram_profile.py` to calculate `sheng_violations_count` and feed it into `lyapunov_energy` (a high Sheng count sharply increases energy, forcing a halt).

---

## 4. Phase 3: Temporal Context & Macro Life Cycles (十二消息卦与大周期)

### 4.1 The Problem
The engine acts as if time does not exist. A `0b010101` at loop 1 is treated identically to a `0b010101` at loop 10,000. 

### 4.2 The Implementation
We will introduce the **Chronobiological Modulator (时空律令器)** using the 12 Sovereign Hexagrams (十二消息卦):
- Map the execution cycle count (or pipeline duration) to the 12 phases (e.g., early loops = Fu / 复卦 ☷☳, late loops = Bo / 剥卦 ☶☷).
- **Yin/Yang Base Pressure**: In early phases, the system naturally favors Yang (exploration, writes). In late phases, it forces Yin (convergence, testing, halting).
- **Action**: The `gateway_engine` will inject a `macro_phase_index` into the kernel. The Wuxing Wuxing Wuxing matrix (`ELEMENT_EXECUTION_BANDWIDTH`) will be dynamically scaled by this phase index (e.g., Wood generates Fire faster in the "Spring" of the cycle).

---

## 5. Phase 4: King Wen's Sequence Continuity (文王序卦连续性检查)

### 5.1 The Problem
Current state transitions are mathematically unbounded within the topology. A task can jump from state 3 to state 45 wildly if the bits flip.

### 5.2 The Implementation
We will establish the **Sequential Path Guard (序卦约束网)**:
- Track the delta between the actual execution path and the idealized King Wen sequence.
- If the system jumps erratically across non-contiguous topological domains without proper Wuxing generation logic, it implies the agent is "hallucinating" or thrashing.
- **Action**: If `topological_jump_distance > threshold` over N cycles, trigger a hard `sovereignty_fire_boundary_halt` with reason `erratic_sequence_violation`.

---

## 6. Implementation Roadmap

1. **Week 1**: Implement Phase 2 (Micro-Relational Gravity). It is pure math and can be directly integrated into `hexagram_profile.py` and `hexagram_dynamics.py` without breaking existing API contracts.
2. **Week 2**: Implement Phase 1 (Moving Lines). Refactor `IchingTransition` and update the ledger schema to support line-specific semantics.
3. **Week 3**: Implement Phase 3 (Temporal Context). Wire the `AgentCycle` loop count into the kernel's bandwidth calculations.
4. **Week 4**: Implement Phase 4 (Sequence Continuity). Add tracking into `checkpoint.py` and `wal.py`.

This roadmap will fundamentally upgrade `one code` from a passive mathematical state machine into a living, context-aware, temporally-bound philosophical engine.
