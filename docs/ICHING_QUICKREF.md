# I Ching Quick Reference Guide

A practical guide for debugging and understanding OneCode's I Ching-based state system.

## Quick Lookup: Common Status Codes

| Code | Hex | Hexagram | Decision | Reason | What It Means |
|------|-----|----------|----------|--------|---------------|
| **0** | 0x00 | Kun/Kun ☷☷ | Discover | rule_gap_requires_discovery | Pure yin state, no yang activity. System needs to discover next action. |
| **17** | 0x11 | Kan/Zhen ☵☳ | Checkpoint | network_water_preserves_resume_seed | Water over thunder. Network operation timed out, preserve state for resume. |
| **32** | 0x20 | Gen/Kun ☶☷ | Checkpoint | mountain_contains_local_executor_fault | Mountain over earth. Local execution issue, checkpoint for investigation. |
| **35** | 0x23 | Gen/Dui ☶☱ | Accelerate | generating_relation_accelerates_execution | Mountain over lake. Earth generates metal, harmonious acceleration. |
| **39** | 0x27 | Gen/Qian ☶☰ | Accelerate | generating_relation_accelerates_execution | Mountain over heaven. Earth generates metal, supporting decisive progress. |
| **40** | 0x28 | Li/Kun ☲☷ | Halt | sovereignty_fire_boundary_halt | Fire over earth. Path traversal or sovereignty breach detected. |
| **42** | 0x2A | Li/Kan ☲☵ | Halt | sovereignty_fire_boundary_halt | Fire over water. Security violation, hard halt. |
| **49** | 0x31 | Xun/Zhen ☴☳ | Continue | (same element) | Wind over thunder. Wood resonates with wood, balanced same-element continuation. |
| **63** | 0x3F | Qian/Qian ☰☰ | Cooldown | yang_overload_cooldown | Pure yang state (6 yang lines). Maximum yang pressure. |

## Trigram Reference


> **Note on Binary Endianness**: All binary mappings in OneCode follow a strict **Bottom-to-Top** coordinate system. The bottom line (初爻) is always **bit 0** (LSB), and the top line (上爻) is **bit 5** (MSB). For trigrams, the bottom line is bit 0 and the top line is bit 2.

### The Eight Trigrams (Ba Gua 八卦)

| Symbol | Name | Chinese | Binary | Element | Nature | Position |
|--------|------|---------|--------|---------|--------|----------|
| ☰ | Qian | 乾 | 111 | Metal | Creative, heaven, strong | Outer/Inner |
| ☷ | Kun | 坤 | 000 | Earth | Receptive, earth, yielding | Outer/Inner |
| ☳ | Zhen | 震 | 001 | Wood | Arousing, thunder, movement | Outer/Inner |
| ☵ | Kan | 坎 | 010 | Water | Abysmal, water, danger | Outer/Inner |
| ☶ | Gen | 艮 | 100 | Earth | Keeping still, mountain | Outer/Inner |
| ☴ | Xun | 巽 | 110 | Wood | Gentle, wind, penetrating | Outer/Inner |
| ☲ | Li | 离 | 101 | Fire | Clinging, fire, clarity | Outer/Inner |
| ☱ | Dui | 兑 | 011 | Metal | Joyful, lake, pleasure | Outer/Inner |

### Trigram to Element Mapping

- **Metal (金)**: Qian (☰), Dui (☱) - Strong, cutting, decisive
- **Wood (木)**: Zhen (☳), Xun (☴) - Growing, flexible, expansive
- **Water (水)**: Kan (☵) - Flowing, adaptive, preserving
- **Fire (火)**: Li (☲) - Bright, transforming, controlling
- **Earth (土)**: Kun (☷), Gen (☶) - Stable, containing, grounding

## Five-Element Relations

### Generation Cycle (生 Sheng) → Continue/Accelerate

Element relations that support forward progress:

```
Wood → Fire → Earth → Metal → Water → Wood
木   → 火   → 土    → 金    → 水    → 木

Wood generates Fire   (fuel)
Fire generates Earth  (ash)
Earth generates Metal (ore)
Metal generates Water (condensation)
Water generates Wood  (nourishment)
```

**When outer trigram generates inner trigram → Continue or Accelerate**

### Control Cycle (克 Ke) → Halt/Throttle/Prune

Element relations that restrict or stop progress:

```
Wood → Earth → Water → Fire → Metal → Wood
木   → 土    → 水    → 火   → 金    → 木

Wood controls Earth   (roots penetrate)
Earth controls Water  (dams contain)
Water controls Fire   (extinguishes)
Fire controls Metal   (melts)
Metal controls Wood   (axe cuts)
```

**When outer trigram controls inner trigram → Halt or Throttle**

## Decoding a Status Code

### Step-by-Step Example: Status Code 40

```
1. Convert to binary:
   40 (decimal) = 0b101000 (6 bits)

2. Split into trigrams:
   Bits 5-3 (outer): 101 = Li (☲) = Fire
   Bits 2-0 (inner): 000 = Kun (☷) = Earth

3. Determine yin-yang balance:
   Yang lines (1s): 2 out of 6
   Yin lines (0s): 4 out of 6
   → Slightly yin-leaning, balanced (not pure)

4. Check five-element relation:
   Outer (Fire) vs Inner (Earth)
   Fire generates Earth (generating cycle), BUT sovereignty hard boundary has higher priority:
   Fire over earth with sovereignty boundary breach overrides generation and triggers hard halt.

5. Apply decision priority:
   - Hard safety check first
   - If path breach → sovereignty_fire_boundary_halt
   - Fire over earth with breach → HALT

Result: Status 40 with sovereignty breach → HALT
Reason: "sovereignty_fire_boundary_halt"
```

## Decision Priority Hierarchy

When the kernel evaluates a state, it applies rules in this **strict order**:

### 1. Hard Safety Constraints (Highest Priority)
Override all symbolic rules:
- Path traversal / sovereignty breach → HALT (status 40, 42)
- Command timeout → CHECKPOINT (status 17)
- Security violations → HALT

### 2. Yin-Yang Pressure
Pure or extreme imbalances:
- **Pure yang** (6 yang lines, e.g., status 63) → COOLDOWN
- **Pure yin** (0 yang lines, e.g., status 0) → DISCOVER
- Balanced (3-4 yang lines) → Continue to next priority

### 3. Five-Element Relations
Outer trigram acts on inner trigram:
- **Generation cycle** → CONTINUE or ACCELERATE
- **Control cycle** → HALT, THROTTLE, or PRUNE
- **Same element** → Context-dependent
- **Neutral** → Continue to next priority

### 4. Neutral Fallback
When no strong relation exists:
- Default to DISCOVER or CONTINUE based on context

## Runtime Reason Rules

A finished write is classified as Qian/Qian (63) and recorded after the yang cooldown, so the stored code is Gen/Qian (39) and the action is `cooldown`. These named outcomes stay on the existing hexagrams:

| Reason | Code | Action | Reading |
|--------|------|--------|---------|
| `verifier_failed` | 40 Li/Kun | halt | The sandbox check ran and failed. With repair attempts left, one implementation patch runs first. A second failure uses this halt. |
| `sandbox_required`, `docker_not_found`, `docker_daemon_unavailable`, `interpreter_not_found` | 32 Gen/Kun | checkpoint | The local executor is missing, including a Docker socket that is not there or an image Python that is not there. |
| `verifier_timeout`, `model_provider_timeout`, `image_platform_mismatch` | 17 Kan/Zhen | checkpoint | The check or the model call timed out, or the image architecture cannot run on this host and no local native sibling is present. A local `image-amd64` or `image-arm64` tag is used when it matches the host. |
| `approval_rejected` | 40 Li/Kun | halt | The operator refused the write. |
| `resource_budget_exceeded`, `invalid_model_plan`, `approval_required` | 40 Li/Kun | halt | The plan or the budget reached the fire boundary. |

When a verifier fails, one patch repair of the implementation is allowed when repair attempts remain. That patch cannot change `tests/`. The check then runs again. A second failure replaces the write's cooled code. The entropy mix of the earlier write and the failure is evidence only. It does not choose the next action. A gateway status 408, 429, 502, 503, or 504 uses the same Kan/Zhen checkpoint as `model_provider_timeout`. A named Python file that the task asks to create or fix gets its own write slot when repair attempts remain. A path the task says not to modify, or any path other than one introduced with "only", is not a missing file and is not written. Once those required files are written, the sequence closes into the sandbox check. A later unusable plan does not replace that cooled write. Invalid JSON, a mixed `no_action`, or an empty task string retries once on the same step, and a second invalid plan is `invalid_model_plan`. An import of `src` module that is already on disk is present for that check. A long circulation run on 2026-10-18 kept code 39 after three verifier failures, and the entropy reading of the same failure was continue (56) on the first round and halt (40) on the later rounds. The control code is now the named reason above. A missing Colima socket is `sandbox_required`, not `verifier_failed`.

## Task Schedule

The hexagram transition remains the safety baseline. A task step also reads yin-yang balance and the five-element relation:

- Pure yang and excess yang still cool. A completed write lands on Gen/Qian (39). That landed state is earth generating metal, so the next task pressure is `accelerate` while the transition that got there stays `cooldown`.
- Excess yin no longer hides generation or control. The transition and the task schedule are the same action: earth controlling water is `throttle` (`earth_dams_water_flow`), and earth generating metal is `accelerate`. Same-element excess yin still activates.
- Outer fire, a missing local executor, and a water recovery seed keep their existing halt or checkpoint.
- A write, patch, or command tagged with any of the 64 hexagrams asks `write_ruling`. Pure yang and excess yang cool and refuse the change, except outer fire, which still halts. Pure yin discovers and does not write. Throttle, prune, halt, and checkpoint do not change the workspace. Generation, recovery, activation, and continuation do, including when raw bandwidth is zero. A zero-bandwidth pair keeps the I Ching reason, such as fire suppressing metal or metal pruning wood, instead of a separate bandwidth label. The step records that hexagram.
- A read or list during pure yin or yang rest is allowed. The same look during halt, control, prune, or checkpoint is refused.
- Steps in the same layer are judged separately. A dammed sibling does not cancel a generating sibling.
- A refused step keeps the I Ching reason and the hexagram that produced it. Classifying that reason returns the same schedule: earth damming water stays Kun/Kan throttle, fire suppressing metal stays the fire halt, and a halted task exits nonzero. One step, or several steps of the same hexagram, keep that hexagram on the trace. Different hexagrams in one plan combine by the I Ching aggregate. Entropy stays on the trace and does not replace that code.

## Debugging Flowchart

```
Run failed or unexpected status?
│
├─ 1. Get the run evidence:
│     $ onecode inspect --workspace /path --run-id <run-id>
│
├─ 2. Find the status code:
│     Look for "iching_status_code" in the output
│
├─ 3. Check the iching_profile:
│     - inner_trigram: which trigram (bits 2-0)
│     - outer_trigram: which trigram (bits 5-3)
│     - yin_yang_profile: balance state
│     - transition_action: what happened (halt/continue/cooldown/discover)
│     - transition_reason: why it happened
│
├─ 4. Look up the status code in this guide
│     Common codes: 0, 17, 35, 39, 40, 42, 49, 63
│
├─ 5. Understand the decision:
│     - Hard safety issue? (path breach, timeout)
│     - Yin-yang imbalance? (pure states)
│     - Element conflict? (control cycle)
│
└─ 6. Verify rule integrity:
      $ onecode math-audit
```

## Practical Examples

### Example 1: Pure Yang Cooldown (Status 63)

```json
{
  "status": "completed",
  "iching_status_code": 63,
  "iching_profile": {
    "inner_trigram": "qian",
    "outer_trigram": "qian",
    "inner_element": "metal",
    "outer_element": "metal",
    "yin_yang_profile": {
      "yang_count": 6,
      "yin_count": 0,
      "balance": "pure_yang"
    },
    "transition_action": "cooldown",
    "transition_reason": "yang_overload_cooldown"
  }
}
```

**Interpretation**: Task reached maximum yang capacity (all 6 yang lines). System deterministically triggers cooldown to stabilize execution.

### Example 2: Harmonious Progression (Status 39)

```json
{
  "status": "accelerate",
  "iching_status_code": 39,
  "iching_profile": {
    "inner_trigram": "qian",
    "outer_trigram": "gen",
    "inner_element": "metal",
    "outer_element": "earth",
    "yin_yang_profile": {
      "yang_count": 4,
      "yin_count": 2,
      "balance": "balanced"
    },
    "transition_action": "accelerate",
    "transition_reason": "generating_relation_accelerates_execution"
  }
}
```

**Interpretation**: Outer Earth generates Inner Metal (土生金, Gen/Qian 山天大畜). The generating relation between outer context and inner state accelerates progress.

### Example 3: Sovereignty Breach (Status 40)

```json
{
  "status": "halted",
  "reason": "sovereignty_breach",
  "iching_status_code": 40,
  "iching_profile": {
    "inner_trigram": "kun",
    "outer_trigram": "li",
    "inner_element": "earth",
    "outer_element": "fire",
    "yin_yang_profile": {
      "yang_count": 2,
      "yin_count": 4,
      "pressure": "balanced_yin_lean"
    },
    "transition_action": "halt",
    "transition_reason": "sovereignty_fire_boundary_halt"
  },
  "sovereignty_detail": {
    "requested_path": "../../../etc/passwd",
    "violation": "path_traversal"
  }
}
```

**Interpretation**: Attempted path traversal detected. Fire (outer) over Earth (inner) with sovereignty breach triggers hard halt. This is a safety override that ignores the balanced yin-yang state.

### Example 4: HTTP Timeout (Status 17)

```json
{
  "status": "halted",
  "reason": "http_timeout",
  "iching_status_code": 17,
  "iching_profile": {
    "inner_trigram": "gen",
    "outer_trigram": "kan",
    "inner_element": "earth",
    "outer_element": "water",
    "yin_yang_profile": {
      "yang_count": 1,
      "yin_count": 5,
      "pressure": "yin_heavy"
    },
    "transition_action": "checkpoint",
    "transition_reason": "network_water_preserves_resume_seed"
  }
}
```

**Interpretation**: Network operation timed out. Water (outer) over Thunder (inner) suggests containment and preservation. Status 17 triggers checkpoint to save resume state for retry.

## Full 64-Hexagram Table

For the complete mapping of all 64 status codes, see:
- [I Ching Complete Rule Kernel Design](superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md)
- Source code: `src/onecode/kernel/hexagram.py`

Each hexagram has specific semantics based on:
1. The combination of outer and inner trigrams
2. The five-element relationship between them
3. The yin-yang balance of the six lines
4. Safety context (path guards, timeouts, etc.)

## Tips for Contributors

### Adding New Transition Logic

When modifying `hexagram.py`, remember:

1. **Preserve the priority chain**: Safety → Yin-Yang → Elements → Neutral
2. **Keep it deterministic**: Same input must always produce same output
3. **Document the reasoning**: Why does this trigram combination produce this decision?
4. **Add tests**: Cover both normal flow and edge cases
5. **Run math-audit**: Verify state space integrity after changes

### Understanding Hexagram Names

Traditional I Ching hexagram names (like "Qian 乾" or "Kun 坤") are preserved in the code for cultural authenticity, but OneCode's decisions are based purely on:
- Binary encoding (which bits are 0 or 1)
- Element mappings (which trigrams map to which elements)
- Mathematical relations (generation vs control cycles)

The traditional meanings provide intuition but don't drive the control logic.

## Commands for Investigation

```bash
# Check system health and see status code examples
onecode doctor

# Verify mathematical integrity of the I Ching rule system
onecode math-audit

# Inspect a specific run's hexagram details
onecode inspect --workspace /path/to/workspace --run-id <run-id>

# List all runs in a workspace
onecode list-runs --workspace /path/to/workspace

# View the shell projection schema (for LibreChat integration)
onecode shell-schema
```

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - Visual diagrams and system flow
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Developer onboarding guide
- [I Ching Kernel Design](superpowers/specs/2026-05-28-onecode-v0.5-iching-complete-rule-kernel-design.md) - Mathematical foundation
- [Yin-Yang Runtime Mapping](superpowers/specs/2026-06-01-onecode-yinyang-wuxing-runtime-rule-mapping-design.md) - Element behavior mapping

---

**Pro Tip**: When debugging, always check the `transition_reason` field first. It tells you exactly which rule fired (e.g., `yang_overload_cooldown`, `sovereignty_fire_boundary_halt`). Then trace backward through the priority chain to understand why that rule won.
