# OneCode Multidimensional Hexagram Kernel Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bottom-level multidimensional hexagram calculation rules to `IchingKernel` without touching LM, basis, logits, training data, prompts, or changing current transition priority.

**Architecture:** Keep all new behavior in `src/onecode/kernel/hexagram.py` as pure deterministic helpers. Tests live in `tests/test_iching_kernel.py` beside the existing bit, trigram, element, and profile tests. `cross_cutting_profile()` only exposes the new calculated facts; `transition()` behavior remains unchanged.

**Tech Stack:** Python 3, stdlib `unittest`, existing `IchingKernel` class.

---

## File Structure

- Modify `src/onecode/kernel/hexagram.py`: add kernel-only helpers for dimension metadata, triadic profile, multi-line mutation, nuclear hexagram, harmony scoring, and profile exposure.
- Modify `tests/test_iching_kernel.py`: add focused unit tests for the new helpers and profile fields.
- Do not modify `src/onecode/kernel/training_data.py`, `src/onecode/kernel/yizijue_logits.py`, or any LM-facing tests.

---

### Task 1: Dimension and Triadic Profiles

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing tests for dimension metadata and triadic decomposition**

Add these tests to `TestIchingKernel` in `tests/test_iching_kernel.py` near `test_bit_state_primitives_generate_cartesian_state_space` and the existing four-symbol tests:

```python
    def test_dimension_profile_describes_known_y_power_state_spaces(self):
        self.assertEqual(
            IchingKernel.dimension_profile(1),
            {
                "width": 1,
                "state_count": 2,
                "bit_order": "bottom_to_top",
                "state_space": "Y^1",
                "label": "liangyi",
            },
        )
        self.assertEqual(IchingKernel.dimension_profile(2)["label"], "four_symbols")
        self.assertEqual(IchingKernel.dimension_profile(3)["label"], "bagua")
        self.assertEqual(IchingKernel.dimension_profile(6)["label"], "hexagram")
        self.assertEqual(IchingKernel.dimension_profile(4)["label"], "binary_state_space")
        self.assertEqual(IchingKernel.dimension_profile(4)["state_count"], 16)

        with self.assertRaises(ValueError):
            IchingKernel.dimension_profile(0)
        with self.assertRaises(ValueError):
            IchingKernel.dimension_profile(-1)

    def test_triadic_profile_splits_hexagram_into_earth_human_heaven_bands(self):
        profile = IchingKernel.triadic_profile(0b111011)

        self.assertEqual(
            profile,
            {
                "earth": {
                    "name": "earth",
                    "role": "environment",
                    "line_indexes": [0, 1],
                    "bits": 0b11,
                    "symbol": "tai_yang",
                    "yang_count": 2,
                    "yin_count": 0,
                    "balance": "pure_yang",
                },
                "human": {
                    "name": "human",
                    "role": "agent",
                    "line_indexes": [2, 3],
                    "bits": 0b10,
                    "symbol": "shao_yin",
                    "yang_count": 1,
                    "yin_count": 1,
                    "balance": "balanced",
                },
                "heaven": {
                    "name": "heaven",
                    "role": "feedback",
                    "line_indexes": [4, 5],
                    "bits": 0b11,
                    "symbol": "tai_yang",
                    "yang_count": 2,
                    "yin_count": 0,
                    "balance": "pure_yang",
                },
            },
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_dimension_profile_describes_known_y_power_state_spaces \
  tests.test_iching_kernel.TestIchingKernel.test_triadic_profile_splits_hexagram_into_earth_human_heaven_bands \
  -v
```

Expected: FAIL with `AttributeError` for `dimension_profile` or `triadic_profile`.

- [ ] **Step 3: Add constants and helper methods**

In `src/onecode/kernel/hexagram.py`, add these constants inside `class IchingKernel` near `FOUR_SYMBOL_RUNTIME_SEMANTICS`:

```python
    DIMENSION_LABELS = {
        1: "liangyi",
        2: "four_symbols",
        3: "bagua",
        6: "hexagram",
    }
    TRIADIC_BANDS = (
        ("earth", "environment", (0, 1)),
        ("human", "agent", (2, 3)),
        ("heaven", "feedback", (4, 5)),
    )
```

Add these methods after `cartesian_states()`:

```python
    @classmethod
    def dimension_profile(cls, width: int) -> dict[str, int | str]:
        if width <= 0:
            raise ValueError(f"width must be positive: {width!r}")
        return {
            "width": width,
            "state_count": 1 << width,
            "bit_order": "bottom_to_top",
            "state_space": f"Y^{width}",
            "label": cls.DIMENSION_LABELS.get(width, "binary_state_space"),
        }

    @classmethod
    def triadic_profile(cls, status_code: int) -> dict[str, dict[str, int | str | list[int]]]:
        normalized = status_code & 0b111111
        profile: dict[str, dict[str, int | str | list[int]]] = {}
        for name, role, line_indexes in cls.TRIADIC_BANDS:
            start = line_indexes[0]
            bits = (normalized >> start) & 0b11
            yin_yang = cls.yin_yang_profile_for_bits(bits, width=2)
            profile[name] = {
                "name": name,
                "role": role,
                "line_indexes": list(line_indexes),
                "bits": bits,
                "symbol": cls.four_symbol_for_bits(bits),
                "yang_count": yin_yang["yang_count"],
                "yin_count": yin_yang["yin_count"],
                "balance": yin_yang["balance"],
            }
        return profile
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_dimension_profile_describes_known_y_power_state_spaces \
  tests.test_iching_kernel.TestIchingKernel.test_triadic_profile_splits_hexagram_into_earth_human_heaven_bands \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: add hexagram dimension and triadic profiles"
```

---

### Task 2: Mutation Operators and Nuclear Hexagram

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing tests for multi-line mutation and nuclear projection**

Add these tests near `test_flip_line_mutates_exactly_one_line`:

```python
    def test_mutate_lines_flips_unique_line_indexes(self):
        self.assertEqual(IchingKernel.mutate_lines(0b000000, [0, 2, 2, 5]), 0b100101)
        self.assertEqual(IchingKernel.mutate_lines(0b111111, [1, 3]), 0b110101)
        self.assertEqual(IchingKernel.mutate_lines(0b101010, []), 0b101010)

        with self.assertRaises(ValueError):
            IchingKernel.mutate_lines(0b000000, [-1])
        with self.assertRaises(ValueError):
            IchingKernel.mutate_lines(0b000000, [6])

    def test_changed_lines_and_mutation_profile_report_triadic_bands(self):
        self.assertEqual(IchingKernel.changed_lines(0b111011, 0b110001), [1, 3])

        profile = IchingKernel.mutation_profile(0b000000, 0b101100)
        self.assertEqual(
            profile,
            {
                "before": 0b000000,
                "after": 0b101100,
                "changed_lines": [2, 3, 5],
                "change_count": 3,
                "changed_bands": ["human", "heaven"],
            },
        )

    def test_nuclear_hexagram_projects_inner_trend_bottom_to_top(self):
        status = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)

        self.assertEqual(status, 0b111011)
        self.assertEqual(IchingKernel.nuclear_hexagram(status), 0b110101)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_mutate_lines_flips_unique_line_indexes \
  tests.test_iching_kernel.TestIchingKernel.test_changed_lines_and_mutation_profile_report_triadic_bands \
  tests.test_iching_kernel.TestIchingKernel.test_nuclear_hexagram_projects_inner_trend_bottom_to_top \
  -v
```

Expected: FAIL with `AttributeError` for the new methods.

- [ ] **Step 3: Add mutation and nuclear helper methods**

In `src/onecode/kernel/hexagram.py`, add these methods immediately after `flip_line()`:

```python
    @classmethod
    def mutate_lines(cls, status_code: int, line_indexes) -> int:
        normalized = status_code & 0b111111
        mask = 0
        for line_index in sorted(set(line_indexes)):
            if line_index < 0 or line_index > 5:
                raise ValueError(f"line_index must be between 0 and 5: {line_index!r}")
            mask |= 1 << line_index
        return normalized ^ mask

    @classmethod
    def changed_lines(cls, before: int, after: int) -> list[int]:
        change_mask = (before ^ after) & 0b111111
        return [line_index for line_index in range(6) if change_mask & (1 << line_index)]

    @classmethod
    def mutation_profile(cls, before: int, after: int) -> dict[str, int | list[int] | list[str]]:
        normalized_before = before & 0b111111
        normalized_after = after & 0b111111
        changed = cls.changed_lines(normalized_before, normalized_after)
        changed_bands = [
            name
            for name, _role, line_indexes in cls.TRIADIC_BANDS
            if any(line_index in line_indexes for line_index in changed)
        ]
        return {
            "before": normalized_before,
            "after": normalized_after,
            "changed_lines": changed,
            "change_count": len(changed),
            "changed_bands": changed_bands,
        }

    @classmethod
    def nuclear_hexagram(cls, status_code: int) -> int:
        bits = cls.bits_for_state(status_code & 0b111111, width=6)
        return cls.state_for_bits([bits[1], bits[2], bits[3], bits[2], bits[3], bits[4]])
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_mutate_lines_flips_unique_line_indexes \
  tests.test_iching_kernel.TestIchingKernel.test_changed_lines_and_mutation_profile_report_triadic_bands \
  tests.test_iching_kernel.TestIchingKernel.test_nuclear_hexagram_projects_inner_trend_bottom_to_top \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: add hexagram mutation and nuclear projection"
```

---

### Task 3: Harmony Score

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing tests for deterministic harmony scoring**

Add this test near the existing five-element relation tests:

```python
    def test_harmony_score_uses_outer_inner_element_relation(self):
        generated = IchingKernel.harmony_score(IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))
        same = IchingKernel.harmony_score(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI))
        controls = IchingKernel.harmony_score(IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN))
        controlled_by = IchingKernel.harmony_score(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.LI))

        self.assertEqual(
            generated,
            {
                "score": 2,
                "relation": "generates",
                "outer_element": "water",
                "inner_element": "wood",
                "method": "outer_inner_element_relation",
            },
        )
        self.assertEqual(same["score"], 1)
        self.assertEqual(same["relation"], "same")
        self.assertEqual(controls["score"], -1)
        self.assertEqual(controls["relation"], "controls")
        self.assertEqual(controlled_by["score"], -2)
        self.assertEqual(controlled_by["relation"], "controlled_by")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_harmony_score_uses_outer_inner_element_relation \
  -v
```

Expected: FAIL with `AttributeError: type object 'IchingKernel' has no attribute 'harmony_score'`.

- [ ] **Step 3: Add score table and harmony method**

In `src/onecode/kernel/hexagram.py`, add this class constant near `RUNTIME_RELATION_POLICY`:

```python
    HARMONY_RELATION_SCORES = {
        "generates": 2,
        "same": 1,
        "generated_by": 1,
        "neutral": 0,
        "controls": -1,
        "controlled_by": -2,
    }
```

Add this method after `element_cross_relation()`:

```python
    @classmethod
    def harmony_score(cls, status_code: int) -> dict[str, int | str]:
        normalized = status_code & 0b111111
        inner = normalized & 0b111
        outer = (normalized >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        relation = cls.element_cross_relation(outer_element, inner_element)
        return {
            "score": cls.HARMONY_RELATION_SCORES[relation],
            "relation": relation,
            "outer_element": outer_element,
            "inner_element": inner_element,
            "method": "outer_inner_element_relation",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_harmony_score_uses_outer_inner_element_relation \
  -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: add hexagram harmony scoring"
```

---

### Task 4: Cross-Cutting Profile Exposure and Rule Layers

**Files:**
- Modify: `tests/test_iching_kernel.py`
- Modify: `src/onecode/kernel/hexagram.py`

- [ ] **Step 1: Write failing tests for profile exposure and unchanged transitions**

Add this test near `test_cross_cutting_profile_exposes_runtime_policy_and_math_layers`:

```python
    def test_cross_cutting_profile_exposes_kernel_only_multidimensional_fields(self):
        status = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)
        profile = IchingKernel.cross_cutting_profile(status)

        self.assertEqual(profile["dimension"], IchingKernel.dimension_profile(6))
        self.assertEqual(profile["triadic"], IchingKernel.triadic_profile(status))
        self.assertIsNone(profile["mutation"])

        nuclear = IchingKernel.nuclear_hexagram(status)
        self.assertEqual(profile["nuclear"]["status_code"], nuclear)
        self.assertEqual(profile["nuclear"]["binary"], format(nuclear, "06b"))
        self.assertEqual(profile["nuclear"]["inner_trigram"], nuclear & 0b111)
        self.assertEqual(profile["nuclear"]["outer_trigram"], (nuclear >> 3) & 0b111)
        self.assertEqual(profile["nuclear"]["transition_action"], IchingKernel.transition(nuclear).action)

        self.assertEqual(profile["harmony"], IchingKernel.harmony_score(status))
        self.assertEqual(IchingKernel.transition(status).action, "checkpoint")
```

Update `test_cross_cutting_profile_marks_rule_source_layers` by adding the new field names to the expected lists:

```python
        self.assertEqual(
            profile["rule_layers"]["bit_derived"],
            [
                "status_code",
                "binary",
                "math",
                "dimension",
                "triadic",
                "mutation",
                "nuclear",
                "inner_trigram",
                "outer_trigram",
                "trigram_records",
                "liangyi",
                "yin_yang",
                "polarity_index",
                "balance_mask",
                "four_symbols",
                "overlapping_four_symbols",
                "four_symbol_balance",
            ],
        )
        self.assertEqual(
            profile["rule_layers"]["correspondence_derived"],
            [
                "inner_element",
                "outer_element",
                "element_records",
                "element_matrix",
                "element_relation",
                "element_dynamics",
                "evolved_element_modulation",
                "harmony",
            ],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_exposes_kernel_only_multidimensional_fields \
  tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_marks_rule_source_layers \
  -v
```

Expected: FAIL because `cross_cutting_profile()` and `RULE_LAYERS` do not expose the new fields.

- [ ] **Step 3: Update rule layer classification**

In `src/onecode/kernel/hexagram.py`, update `RULE_LAYERS["bit_derived"]` so the list begins:

```python
        "bit_derived": [
            "status_code",
            "binary",
            "math",
            "dimension",
            "triadic",
            "mutation",
            "nuclear",
            "inner_trigram",
            "outer_trigram",
            "trigram_records",
            "liangyi",
            "yin_yang",
            "polarity_index",
            "balance_mask",
            "four_symbols",
            "overlapping_four_symbols",
            "four_symbol_balance",
        ],
```

Update `RULE_LAYERS["correspondence_derived"]` so it ends with `harmony`:

```python
        "correspondence_derived": [
            "inner_element",
            "outer_element",
            "element_records",
            "element_matrix",
            "element_relation",
            "element_dynamics",
            "evolved_element_modulation",
            "harmony",
        ],
```

- [ ] **Step 4: Add nuclear profile helper and expose new fields**

Add this method after `nuclear_hexagram()`:

```python
    @classmethod
    def nuclear_profile(cls, status_code: int) -> dict[str, int | str]:
        nuclear = cls.nuclear_hexagram(status_code)
        inner = nuclear & 0b111
        outer = (nuclear >> 3) & 0b111
        outer_element = cls.element_for_trigram(outer)
        inner_element = cls.element_for_trigram(inner)
        transition = cls.transition(nuclear)
        return {
            "status_code": nuclear,
            "binary": format(nuclear, "06b"),
            "inner_trigram": inner,
            "outer_trigram": outer,
            "outer_element": outer_element,
            "inner_element": inner_element,
            "element_relation": cls.element_cross_relation(outer_element, inner_element),
            "transition_action": transition.action,
            "transition_reason": transition.reason,
        }
```

In `cross_cutting_profile()`, add these keys after the existing `math` block:

```python
            "dimension": cls.dimension_profile(6),
            "triadic": cls.triadic_profile(normalized),
            "mutation": None,
            "nuclear": cls.nuclear_profile(normalized),
```

Add this key after `evolved_element_modulation`:

```python
            "harmony": cls.harmony_score(normalized),
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_exposes_kernel_only_multidimensional_fields \
  tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_marks_rule_source_layers \
  tests.test_iching_kernel.TestIchingKernel.test_cross_cutting_profile_unifies_all_rule_projections \
  tests.test_iching_kernel.TestIchingKernel.test_hexagram_record_contains_cross_cutting_rule_profile \
  -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/onecode/kernel/hexagram.py tests/test_iching_kernel.py
git commit -m "feat: expose multidimensional kernel profile fields"
```

---

### Task 5: Kernel-Only Verification

**Files:**
- No source edits.

- [ ] **Step 1: Run focused kernel tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_iching_kernel -v
```

Expected: PASS.

- [ ] **Step 2: Run compile verification**

Run:

```bash
PYTHONPATH=src python3 -m compileall src tests
```

Expected: PASS with exit code `0`.

- [ ] **Step 3: Run full test discovery**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected in a fully provisioned environment: PASS. If it fails with `ModuleNotFoundError: No module named 'textual'`, record that as the existing optional TUI dependency issue and include the focused kernel test result in the handoff.

- [ ] **Step 4: Confirm no LM-facing files changed**

Run:

```bash
git diff --name-only b528558..HEAD
```

Expected changed files after the implementation commits are limited to:

```text
one code/src/onecode/kernel/hexagram.py
one code/tests/test_iching_kernel.py
```

If `training_data.py`, `yizijue_logits.py`, or any prompt/training file appears, stop and remove that change from this task.
