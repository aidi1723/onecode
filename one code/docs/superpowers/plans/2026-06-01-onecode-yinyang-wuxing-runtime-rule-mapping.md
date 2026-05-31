# OneCode Yin-Yang Five-Element Runtime Rule Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Map yin-yang and five-element rules into OneCode runtime decisions first, then expose pure mathematical primitives, then enrich YiZiJue-LM basis and logits policy.

**Architecture:** Keep `IchingKernel` as the single rule authority. Runtime code consumes explicit kernel records and policy tables; math helpers stay pure and side-effect free; model-facing code receives compact basis facts derived from kernel state rather than duplicating interpretation.

**Tech Stack:** Python 3, stdlib `unittest`, existing OneCode kernel modules, existing YiZiJue-LM training and logits helpers.

---

## File Structure

- Modify `src/onecode/kernel/hexagram.py`: add explicit runtime relation policy, pure mathematical helpers, modular five-element helpers, and richer cross-cutting profile fields.
- Modify `tests/test_iching_kernel.py`: add TDD coverage for runtime policy priority, relation actions, math primitives, modular five-element arithmetic, and profile fields.
- Modify `src/onecode/kernel/training_data.py`: allow rich optional basis fields and derive them from `IchingKernel`.
- Modify `tests/test_training_data.py`: assert rich basis generation and validation compatibility.
- Modify `src/onecode/kernel/yizijue_logits.py`: add policy hints from rich basis fields while preserving forbidden token behavior.
- Modify `tests/test_yizijue_logits.py`: assert rich basis hints influence preferred text without weakening forbiddens.

---

### Task 1: Runtime Relation Policy

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing tests for explicit relation policy**

Add these tests to `TestIchingKernel` in `tests/test_iching_kernel.py` near the existing transition tests:

```python
    def test_runtime_relation_policy_covers_all_cross_relations(self):
        expected = {
            "generates": ("accelerate", "generating_relation_accelerates_execution"),
            "same": ("continue", None),
            "generated_by": ("recover", "generated_by_relation_recovers_execution"),
            "controlled_by": ("checkpoint", "controlled_by_relation_requires_verifier"),
            "neutral": ("discover", "neutral_relation_requires_discovery"),
        }

        for relation, expected_policy in expected.items():
            self.assertEqual(IchingKernel.runtime_relation_policy(relation, "normal"), expected_policy)

    def test_runtime_relation_policy_differentiates_control_modulations(self):
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "quench"), ("halt", "water_quenches_fire_boundary"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "hard_control"), ("halt", "sovereignty_fire_suppresses_asset"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "prune"), ("prune", "metal_prunes_wood_scope"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "dam"), ("throttle", "earth_dams_water_flow"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "break_ground"), ("activate", "wood_breaks_inert_ground"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "normal"), ("throttle", "controlling_relation_throttles_execution"))
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_runtime_relation_policy_covers_all_cross_relations tests.test_iching_kernel.TestIchingKernel.test_runtime_relation_policy_differentiates_control_modulations -v
```

Expected: FAIL with `AttributeError: type object 'IchingKernel' has no attribute 'runtime_relation_policy'`.

- [ ] **Step 3: Add explicit runtime policy tables**

In `src/onecode/kernel/hexagram.py`, add these class constants near `ELEMENT_EXECUTION_BANDWIDTH`:

```python
    RUNTIME_RELATION_POLICY = {
        "generates": ("accelerate", "generating_relation_accelerates_execution"),
        "same": ("continue", None),
        "generated_by": ("recover", "generated_by_relation_recovers_execution"),
        "controlled_by": ("checkpoint", "controlled_by_relation_requires_verifier"),
        "neutral": ("discover", "neutral_relation_requires_discovery"),
    }
    RUNTIME_CONTROL_MODULATION_POLICY = {
        "hard_control": ("halt", "sovereignty_fire_suppresses_asset"),
        "quench": ("halt", "water_quenches_fire_boundary"),
        "prune": ("prune", "metal_prunes_wood_scope"),
        "dam": ("throttle", "earth_dams_water_flow"),
        "break_ground": ("activate", "wood_breaks_inert_ground"),
        "normal": ("throttle", "controlling_relation_throttles_execution"),
    }
```

Then add this method near `element_cross_relation()`:

```python
    @classmethod
    def runtime_relation_policy(cls, relation: str, modulation: str) -> tuple[str, str | None]:
        if relation == "controls":
            return cls.RUNTIME_CONTROL_MODULATION_POLICY.get(
                modulation,
                cls.RUNTIME_CONTROL_MODULATION_POLICY["normal"],
            )
        return cls.RUNTIME_RELATION_POLICY.get(relation, cls.RUNTIME_RELATION_POLICY["neutral"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_runtime_relation_policy_covers_all_cross_relations tests.test_iching_kernel.TestIchingKernel.test_runtime_relation_policy_differentiates_control_modulations -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: add runtime relation policy"
```

---

### Task 2: Runtime Transition Priority

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing transition priority tests**

Add these tests to `TestIchingKernel`:

```python
    def test_element_dynamics_uses_cross_relation_and_break_ground_modulation(self):
        status = IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.KUN)
        dynamics = IchingKernel.element_dynamics(status)

        self.assertEqual(dynamics["outer_element"], "wood")
        self.assertEqual(dynamics["inner_element"], "earth")
        self.assertEqual(dynamics["relation"], "controls")
        self.assertEqual(dynamics["cross_relation"], "controls")
        self.assertEqual(dynamics["modulation"], "break_ground")

    def test_transition_uses_policy_after_safety_and_pressure_gates(self):
        break_ground = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.KUN))
        generated_by = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.GEN))
        controlled_by = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.DUI, IchingKernel.LI))

        self.assertEqual(break_ground.action, "activate")
        self.assertEqual(break_ground.reason, "wood_breaks_inert_ground")
        self.assertEqual(generated_by.action, "recover")
        self.assertEqual(generated_by.reason, "generated_by_relation_recovers_execution")
        self.assertEqual(controlled_by.action, "checkpoint")
        self.assertEqual(controlled_by.reason, "controlled_by_relation_requires_verifier")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_element_dynamics_uses_cross_relation_and_break_ground_modulation tests.test_iching_kernel.TestIchingKernel.test_transition_uses_policy_after_safety_and_pressure_gates -v
```

Expected: FAIL because `cross_relation` is missing and `recover` is not produced.

- [ ] **Step 3: Refine element dynamics**

Replace `element_dynamics()` in `src/onecode/kernel/hexagram.py` with:

```python
    @classmethod
    def element_dynamics(cls, status_code: int) -> dict[str, str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_relation(outer_element, inner_element)
        cross_relation = cls.element_cross_relation(outer_element, inner_element)
        pressure = cls.yin_yang_cross_profile(normalized)["pressure"]
        if cross_relation == "controls" and outer_element == "fire" and inner_element == "metal":
            modulation = "hard_control"
        elif cross_relation == "generates" and outer_element == "water" and inner_element == "wood":
            modulation = "recovery_seed"
        elif cross_relation == "controls" and outer_element == "water" and inner_element == "fire":
            modulation = "quench"
        elif cross_relation == "controls" and outer_element == "metal" and inner_element == "wood":
            modulation = "prune"
        elif cross_relation == "generates" and outer_element == "wood" and inner_element == "fire":
            modulation = "fuel"
        elif cross_relation == "controls" and outer_element == "earth" and inner_element == "water":
            modulation = "dam"
        elif cross_relation == "controls" and outer_element == "wood" and inner_element == "earth":
            modulation = "break_ground"
        else:
            modulation = "normal"
        return {
            "outer_element": outer_element,
            "inner_element": inner_element,
            "relation": relation,
            "cross_relation": cross_relation,
            "yin_yang_pressure": str(pressure),
            "modulation": modulation,
        }
```

- [ ] **Step 4: Refactor transition to consume the policy**

In `transition()`, keep the first two special cases for pure `KUN/KUN` and hard safety, then replace the relation tail with this structure:

```python
    @classmethod
    def transition(cls, status_code: int) -> IchingTransition:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        dynamics = cls.element_dynamics(normalized)

        if normalized == cls.compute_status(cls.KUN, cls.KUN):
            return IchingTransition(
                status_code=normalized,
                action="discover",
                reason="rule_gap_requires_discovery",
            )
        if dynamics["modulation"] == "hard_control":
            return IchingTransition(
                status_code=cls.compute_status(cls.LI, cls.KUN),
                action="halt",
                reason="sovereignty_fire_suppresses_asset",
            )
        if outer == cls.LI:
            return IchingTransition(
                status_code=normalized,
                action="halt",
                reason="sovereignty_fire_boundary_halt",
            )
        if normalized == cls.compute_status(cls.GEN, cls.KUN):
            return IchingTransition(
                status_code=normalized,
                action="checkpoint",
                reason="mountain_contains_local_executor_fault",
            )

        profile = cls.yin_yang_profile(normalized)
        if profile["balance"] in {"pure_yang", "yang_excess"}:
            return IchingTransition(
                status_code=cls.compute_status(cls.GEN, inner),
                action="cooldown",
                reason="yang_overload_cooldown",
            )
        if profile["balance"] == "pure_yin":
            return IchingTransition(
                status_code=normalized,
                action="discover",
                reason="rule_gap_requires_discovery",
            )
        if profile["balance"] == "yin_excess" and inner != cls.KUN:
            return IchingTransition(
                status_code=normalized,
                action="activate",
                reason="yin_excess_requires_activation",
            )

        if dynamics["modulation"] == "recovery_seed":
            return IchingTransition(
                status_code=normalized,
                action="checkpoint",
                reason="network_water_preserves_resume_seed",
            )

        action, reason = cls.runtime_relation_policy(dynamics["cross_relation"], dynamics["modulation"])
        return IchingTransition(status_code=normalized, action=action, reason=reason)
```

- [ ] **Step 5: Update dispatch for recover**

Modify `dispatch_decision()` in `src/onecode/kernel/hexagram.py`:

```python
    @classmethod
    def dispatch_decision(cls, transition: IchingTransition) -> str:
        if transition.action in {"halt", "checkpoint", "discover"}:
            return "stop"
        return "continue"
```

This implementation already allows `recover` to continue because it is not in the stop set.

- [ ] **Step 6: Run targeted transition tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_element_dynamics_uses_cross_relation_and_break_ground_modulation tests.test_iching_kernel.TestIchingKernel.test_transition_uses_policy_after_safety_and_pressure_gates tests.test_iching_kernel.TestIchingKernel.test_transition_applies_cross_cutting_dynamic_laws tests.test_iching_kernel.TestIchingKernel.test_transition_expands_yin_and_element_scheduling_actions -v
```

Expected: PASS. If an existing assertion expects `pure_yin` to be `discover`, keep that assertion unchanged.

- [ ] **Step 7: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: route transitions through relation policy"
```

---

### Task 3: Mathematical Kernel Primitives

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing math primitive tests**

Add these tests to `TestIchingKernel`:

```python
    def test_bit_state_primitives_generate_cartesian_state_space(self):
        self.assertEqual(IchingKernel.liangyi_values(), (0, 1))
        self.assertEqual(IchingKernel.cartesian_states(0), [0])
        self.assertEqual(IchingKernel.cartesian_states(1), [0, 1])
        self.assertEqual(IchingKernel.cartesian_states(2), [0, 1, 2, 3])
        self.assertEqual(IchingKernel.cartesian_states(3), list(range(8)))
        self.assertEqual(IchingKernel.cartesian_states(6), list(range(64)))

    def test_bits_round_trip_in_bottom_to_top_order(self):
        self.assertEqual(IchingKernel.bits_for_state(0b101101, 6), [1, 0, 1, 1, 0, 1])
        self.assertEqual(IchingKernel.state_for_bits([1, 0, 1, 1, 0, 1]), 0b101101)
        self.assertEqual(IchingKernel.state_for_bits(IchingKernel.bits_for_state(0b111000, 6)), 0b111000)

    def test_named_projection_helpers_match_existing_kernel_conventions(self):
        self.assertEqual(IchingKernel.four_symbol_for_pair(0b00), "tai_yin")
        self.assertEqual(IchingKernel.four_symbol_for_pair(0b01), "shao_yang")
        self.assertEqual(IchingKernel.hexagram_status(IchingKernel.QIAN, IchingKernel.DUI), 0b111011)
        record = IchingKernel.trigram_for_bits(0b101)
        self.assertEqual(record["trigram"], IchingKernel.XUN)
        self.assertEqual(record["name"], "xun")
        self.assertEqual(record["element"], "wood")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_bit_state_primitives_generate_cartesian_state_space tests.test_iching_kernel.TestIchingKernel.test_bits_round_trip_in_bottom_to_top_order tests.test_iching_kernel.TestIchingKernel.test_named_projection_helpers_match_existing_kernel_conventions -v
```

Expected: FAIL with missing helper attributes.

- [ ] **Step 3: Add pure bit helpers**

Add these methods in `src/onecode/kernel/hexagram.py` near `compute_status()`:

```python
    @classmethod
    def liangyi_values(cls) -> tuple[int, int]:
        return (0, 1)

    @classmethod
    def cartesian_states(cls, width: int) -> list[int]:
        if width < 0:
            raise ValueError(f"width must be non-negative: {width!r}")
        return list(range(1 << width))

    @classmethod
    def bits_for_state(cls, value: int, width: int) -> list[int]:
        if width < 0:
            raise ValueError(f"width must be non-negative: {width!r}")
        return [(value >> bit_index) & 1 for bit_index in range(width)]

    @classmethod
    def state_for_bits(cls, bits: list[int]) -> int:
        value = 0
        for bit_index, bit in enumerate(bits):
            if bit not in {0, 1}:
                raise ValueError(f"bits must contain only 0 or 1: {bit!r}")
            value |= bit << bit_index
        return value

    @classmethod
    def four_symbol_for_pair(cls, bits: int) -> str:
        return cls.four_symbol_for_bits(bits)

    @classmethod
    def trigram_for_bits(cls, bits: int) -> dict:
        return cls.standalone_trigram_record(bits)

    @classmethod
    def hexagram_status(cls, outer: int, inner: int) -> int:
        return cls.compute_status(outer, inner)
```

- [ ] **Step 4: Run math primitive tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_bit_state_primitives_generate_cartesian_state_space tests.test_iching_kernel.TestIchingKernel.test_bits_round_trip_in_bottom_to_top_order tests.test_iching_kernel.TestIchingKernel.test_named_projection_helpers_match_existing_kernel_conventions -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: expose iching math primitives"
```

---

### Task 4: Modular Five-Element Arithmetic

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing modular arithmetic tests**

Add these tests to `TestIchingKernel`:

```python
    def test_five_element_mod_arithmetic_matches_generation_and_control_cycles(self):
        self.assertEqual(IchingKernel.ELEMENT_GENERATION_ORDER, ("wood", "fire", "earth", "metal", "water"))

        self.assertEqual(IchingKernel.generate_element("wood"), "fire")
        self.assertEqual(IchingKernel.generate_element("water"), "wood")
        self.assertEqual(IchingKernel.control_element("wood"), "earth")
        self.assertEqual(IchingKernel.control_element("water"), "fire")

        self.assertEqual(IchingKernel.element_distance("wood", "wood"), 0)
        self.assertEqual(IchingKernel.element_distance("wood", "fire"), 1)
        self.assertEqual(IchingKernel.element_distance("wood", "earth"), 2)
        self.assertEqual(IchingKernel.element_distance("wood", "metal"), 3)
        self.assertEqual(IchingKernel.element_distance("wood", "water"), 4)

    def test_element_records_are_backed_by_mod_arithmetic(self):
        for element in IchingKernel.ELEMENT_GENERATION_ORDER:
            record = IchingKernel.element_records()[element]
            self.assertEqual(record["generates"], IchingKernel.generate_element(element))
            self.assertEqual(record["controls"], IchingKernel.control_element(element))
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_five_element_mod_arithmetic_matches_generation_and_control_cycles tests.test_iching_kernel.TestIchingKernel.test_element_records_are_backed_by_mod_arithmetic -v
```

Expected: FAIL because `ELEMENT_GENERATION_ORDER`, `generate_element()`, `control_element()`, or `element_distance()` is missing.

- [ ] **Step 3: Add canonical element order and helpers**

In `src/onecode/kernel/hexagram.py`, add this constant near `ELEMENT_ORDER`:

```python
    ELEMENT_GENERATION_ORDER = ("wood", "fire", "earth", "metal", "water")
```

Add these methods near `element_for_trigram()`:

```python
    @classmethod
    def element_distance(cls, source: str, target: str) -> int:
        if source not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown source element: {source!r}")
        if target not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown target element: {target!r}")
        source_index = cls.ELEMENT_GENERATION_ORDER.index(source)
        target_index = cls.ELEMENT_GENERATION_ORDER.index(target)
        return (target_index - source_index) % len(cls.ELEMENT_GENERATION_ORDER)

    @classmethod
    def generate_element(cls, element: str) -> str:
        if element not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown element: {element!r}")
        index = cls.ELEMENT_GENERATION_ORDER.index(element)
        return cls.ELEMENT_GENERATION_ORDER[(index + 1) % len(cls.ELEMENT_GENERATION_ORDER)]

    @classmethod
    def control_element(cls, element: str) -> str:
        if element not in cls.ELEMENT_GENERATION_ORDER:
            raise ValueError(f"unknown element: {element!r}")
        index = cls.ELEMENT_GENERATION_ORDER.index(element)
        return cls.ELEMENT_GENERATION_ORDER[(index + 2) % len(cls.ELEMENT_GENERATION_ORDER)]
```

- [ ] **Step 4: Refactor `element_relation()` to use modular arithmetic**

Replace `element_relation()` with:

```python
    @classmethod
    def element_relation(cls, source: str, target: str) -> str:
        distance = cls.element_distance(source, target)
        if distance == 0:
            return "same"
        if distance == 1:
            return "generates"
        if distance == 2:
            return "controls"
        return "neutral"
```

Keep `GENERATES` and `CONTROLS` constants for compatibility, but do not use them as the only proof of relation.

- [ ] **Step 5: Run modular tests and existing element tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_five_element_mod_arithmetic_matches_generation_and_control_cycles tests.test_iching_kernel.TestIchingKernel.test_element_records_are_backed_by_mod_arithmetic tests.test_iching_kernel.TestIchingKernel.test_five_element_matrix_maps_trigrams_and_relations tests.test_iching_kernel.TestIchingKernel.test_five_element_records_cover_generation_and_control_cross_matrix -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: prove five element cycles with mod arithmetic"
```

---

### Task 5: Rich Rule Profile Fields

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing profile tests**

Add this test to `TestIchingKernel`:

```python
    def test_cross_cutting_profile_exposes_runtime_policy_and_math_layers(self):
        status = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)
        profile = IchingKernel.cross_cutting_profile(status)

        self.assertEqual(profile["math"]["liangyi"], [0, 1])
        self.assertEqual(profile["math"]["state_space_sizes"], {"liangyi": 2, "sixiang": 4, "bagua": 8, "hexagram": 64})
        self.assertEqual(profile["element_dynamics"]["cross_relation"], "generates")
        self.assertEqual(profile["runtime_policy"], {"action": "checkpoint", "reason": "network_water_preserves_resume_seed"})
        self.assertEqual(profile["transition"]["action"], "checkpoint")
        self.assertEqual(profile["dispatch_decision"], "stop")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_exposes_runtime_policy_and_math_layers -v
```

Expected: FAIL because `math` and `runtime_policy` are missing.

- [ ] **Step 3: Add math and runtime policy fields to profile**

In `cross_cutting_profile()`, after computing `transition` and `dispatch_decision`, compute:

```python
        runtime_action, runtime_reason = cls.runtime_relation_policy(
            cls.element_dynamics(normalized)["cross_relation"],
            cls.element_dynamics(normalized)["modulation"],
        )
```

Then add these fields to the returned dictionary:

```python
            "math": {
                "liangyi": list(cls.liangyi_values()),
                "state_space_sizes": {
                    "liangyi": len(cls.cartesian_states(1)),
                    "sixiang": len(cls.cartesian_states(2)),
                    "bagua": len(cls.cartesian_states(3)),
                    "hexagram": len(cls.cartesian_states(6)),
                },
            },
            "runtime_policy": {
                "action": runtime_action,
                "reason": runtime_reason,
            },
```

Avoid calling `element_dynamics()` twice by storing it once:

```python
        dynamics = cls.element_dynamics(normalized)
        runtime_action, runtime_reason = cls.runtime_relation_policy(dynamics["cross_relation"], dynamics["modulation"])
```

Use `dynamics` for the existing `"element_dynamics"` field.

- [ ] **Step 4: Run profile tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_exposes_runtime_policy_and_math_layers tests.test_iching_kernel.TestIchingKernel.test_hexagram_record_contains_cross_cutting_rule_profile -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: expose runtime rule profile fields"
```

---

### Task 6: Rich YiZiJue-LM Basis

**Files:**
- Modify: `tests/test_training_data.py`
- Modify: `src/onecode/kernel/training_data.py`

- [ ] **Step 1: Write failing rich basis tests**

Add this test to `YiZiJueLmDataTests` in `tests/test_training_data.py` near `test_state_basis_for_lm_row_maps_core_actions`:

```python
    def test_state_basis_for_lm_row_includes_kernel_rule_chain(self):
        row = yizijue_lm_action_row(
            "state-verifier-rich",
            "运行 pytest",
            facts={
                "intent_type": "execute_pytest",
                "path_scope": "no_path",
                "sandbox_state": "required",
                "evidence_state": "required",
            },
            yizijue_state="010010",
            action="RUN_VERIFIER_IN_SANDBOX",
            reason="verifier_requires_sandbox",
        )

        basis = state_basis_for_lm_row(row)

        self.assertEqual(basis["state"], "010010")
        self.assertEqual(basis["yin_yang"]["balance"], "yin_excess")
        self.assertEqual(basis["yin_yang"]["pressure"], "activate")
        self.assertEqual(basis["trigrams"], {"outer": "kan", "inner": "kan"})
        self.assertEqual(basis["elements"]["outer"], "water")
        self.assertEqual(basis["elements"]["inner"], "water")
        self.assertEqual(basis["elements"]["relation"], "same")
        self.assertIn("modulation", basis["elements"])
        self.assertEqual(validate_yizijue_lm_state_sample({**row, "basis": basis})["basis"]["state"], "010010")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_training_data.YiZiJueLmDataTests.test_state_basis_for_lm_row_includes_kernel_rule_chain -v
```

Expected: FAIL because `validate_yizijue_lm_state_sample()` rejects unknown basis fields or `state_basis_for_lm_row()` does not include rich fields.

- [ ] **Step 3: Expand basis field contract**

In `src/onecode/kernel/training_data.py`, replace:

```python
YIZIJUE_LM_BASIS_FIELDS = {"projection", "state", "state_label", "transition", "rule"}
```

with:

```python
YIZIJUE_LM_REQUIRED_BASIS_FIELDS = {"projection", "state", "state_label", "transition", "rule"}
YIZIJUE_LM_OPTIONAL_BASIS_FIELDS = {"yin_yang", "trigrams", "elements"}
YIZIJUE_LM_BASIS_FIELDS = YIZIJUE_LM_REQUIRED_BASIS_FIELDS | YIZIJUE_LM_OPTIONAL_BASIS_FIELDS
```

In `validate_yizijue_lm_state_sample()`, replace the missing field check with:

```python
    unknown_fields = sorted(set(basis) - YIZIJUE_LM_BASIS_FIELDS)
    missing_fields = sorted(YIZIJUE_LM_REQUIRED_BASIS_FIELDS - set(basis))
```

Replace the string validation loop with:

```python
    for field in sorted(YIZIJUE_LM_REQUIRED_BASIS_FIELDS):
        require_string(basis[field], f"basis.{field}")
```

Then validate optional structures:

```python
    if "yin_yang" in basis:
        yin_yang = basis["yin_yang"]
        if not isinstance(yin_yang, dict):
            raise ValueError("basis.yin_yang must be an object")
        require_string(yin_yang.get("balance"), "basis.yin_yang.balance")
        require_string(yin_yang.get("pressure"), "basis.yin_yang.pressure")
    if "trigrams" in basis:
        trigrams = basis["trigrams"]
        if not isinstance(trigrams, dict):
            raise ValueError("basis.trigrams must be an object")
        require_string(trigrams.get("outer"), "basis.trigrams.outer")
        require_string(trigrams.get("inner"), "basis.trigrams.inner")
    if "elements" in basis:
        elements = basis["elements"]
        if not isinstance(elements, dict):
            raise ValueError("basis.elements must be an object")
        require_string(elements.get("outer"), "basis.elements.outer")
        require_string(elements.get("inner"), "basis.elements.inner")
        require_string(elements.get("relation"), "basis.elements.relation")
        require_string(elements.get("modulation"), "basis.elements.modulation")
```

- [ ] **Step 4: Add kernel-derived basis enrichment**

Add this helper above `state_basis_for_lm_row()`:

```python
def enrich_basis_with_kernel_profile(basis: dict[str, Any]) -> dict[str, Any]:
    state = require_string(basis["state"], "basis.state")
    status_code = int(state, 2)
    profile = IchingKernel.cross_cutting_profile(status_code)
    yin_yang = profile["yin_yang"]
    inner_record = profile["inner_trigram_record"]
    outer_record = profile["outer_trigram_record"]
    dynamics = profile["element_dynamics"]
    return {
        **basis,
        "yin_yang": {
            "balance": str(yin_yang["balance"]),
            "pressure": str(yin_yang["pressure"]),
        },
        "trigrams": {
            "outer": str(outer_record["name"]),
            "inner": str(inner_record["name"]),
        },
        "elements": {
            "outer": str(dynamics["outer_element"]),
            "inner": str(dynamics["inner_element"]),
            "relation": str(dynamics["cross_relation"]),
            "modulation": str(dynamics["modulation"]),
        },
    }
```

At the end of each branch in `state_basis_for_lm_row()`, return through this helper. The least invasive way is to build `basis` in each branch and return `enrich_basis_with_kernel_profile(basis)`.

For example, replace the chat branch with:

```python
        return enrich_basis_with_kernel_profile(
            {
                "projection": "simple_chat",
                "state": "000000",
                "state_label": "chat_smalltalk",
                "transition": "reply_only",
                "rule": "simple chat returns a short local reply without execution",
            }
        )
```

Apply the same wrapping to every branch in `state_basis_for_lm_row()`.

- [ ] **Step 5: Run training data tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_training_data.YiZiJueLmDataTests.test_state_basis_for_lm_row_includes_kernel_rule_chain tests.test_training_data.YiZiJueLmDataTests.test_state_basis_for_lm_row_maps_core_actions tests.test_training_data.YiZiJueLmDataTests.test_yizijue_lm_state_rows_from_lm_rows_adds_basis_to_every_row -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/kernel/training_data.py tests/test_training_data.py
git commit -m "feat: enrich yizijue basis with rule chain"
```

---

### Task 7: Logits Policy Rich Basis Hints

**Files:**
- Modify: `tests/test_yizijue_logits.py`
- Modify: `src/onecode/kernel/yizijue_logits.py`

- [ ] **Step 1: Write failing logits policy test**

Add this test to `tests/test_yizijue_logits.py` near existing `token_policy_for_basis` tests:

```python
    def test_policy_for_basis_consumes_rich_rule_chain_hints(self):
        policy = token_policy_for_basis(
            {
                "projection": "verification_request",
                "state": "010010",
                "state_label": "kan_sandbox_verifier",
                "transition": "sandbox_required",
                "rule": "verification commands must run in a sandbox",
                "yin_yang": {"balance": "yin_excess", "pressure": "activate"},
                "trigrams": {"outer": "kan", "inner": "kan"},
                "elements": {"outer": "water", "inner": "water", "relation": "same", "modulation": "normal"},
            }
        )

        self.assertIn("yin_excess", policy["preferred_text"])
        self.assertIn("activate", policy["preferred_text"])
        self.assertIn("same", policy["preferred_text"])
        self.assertIn("normal", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_yizijue_logits.YiZiJueLogitsPolicyTests.test_policy_for_basis_consumes_rich_rule_chain_hints -v
```

Expected: FAIL because rich fields are ignored.

- [ ] **Step 3: Add rich basis hint extraction**

In `src/onecode/kernel/yizijue_logits.py`, add this helper above `token_policy_for_basis()`:

```python
def rich_basis_hints(basis: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    yin_yang = basis.get("yin_yang")
    if isinstance(yin_yang, dict):
        for field in ("balance", "pressure"):
            value = yin_yang.get(field)
            if isinstance(value, str) and value:
                hints.append(value)
    elements = basis.get("elements")
    if isinstance(elements, dict):
        for field in ("relation", "modulation"):
            value = elements.get(field)
            if isinstance(value, str) and value:
                hints.append(value)
    return hints
```

Then inside `token_policy_for_basis()`, after `preferred = list(policy["preferred_text"])`, add:

```python
    preferred.extend(rich_basis_hints(basis))
```

Do not remove any existing forbidden text handling.

- [ ] **Step 4: Run logits policy tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_yizijue_logits -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/yizijue_logits.py tests/test_yizijue_logits.py
git commit -m "feat: add rich basis logits hints"
```

---

### Task 8: Full Verification and Docs Touch-Up

**Files:**
- Modify: `docs/README` only if an existing docs test requires it after the code changes.
- Verify: full source and test suite.

- [ ] **Step 1: Run compile verification**

Run:

```bash
PYTHONPATH=src python3 -m compileall src tests
```

Expected: command exits `0`; output may list compiled files and must not include syntax errors.

- [ ] **Step 2: Run full test suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Inspect git diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only files from this plan are modified, unless existing unrelated dirty files were already present before execution.

- [ ] **Step 4: Commit any final docs or compatibility fixes**

If Step 2 required a small docs or compatibility correction, commit only those files:

```bash
git add src/onecode/kernel/hexagram.py src/onecode/kernel/training_data.py src/onecode/kernel/yizijue_logits.py tests/test_iching_kernel.py tests/test_training_data.py tests/test_yizijue_logits.py
git commit -m "test: verify yinyang wuxing rule mapping"
```

If there were no remaining changes after earlier task commits, skip this commit.

---

## Self-Review

Spec coverage:

- Phase 1 runtime decision logic is covered by Tasks 1, 2, and 5.
- Phase 2 mathematical kernel completion is covered by Tasks 3 and 4.
- Phase 3 YiZiJue-LM basis and token policy is covered by Tasks 6 and 7.
- Verification is covered by Task 8.

Type consistency:

- New `IchingKernel` helpers are class methods.
- `runtime_relation_policy()` returns `tuple[str, str | None]`.
- `element_dynamics()` keeps existing fields and adds `cross_relation`.
- Rich basis fields are dictionaries under `yin_yang`, `trigrams`, and `elements`.
- Logits policy hints extend only `preferred_text` and preserve existing `forbidden_text`.
