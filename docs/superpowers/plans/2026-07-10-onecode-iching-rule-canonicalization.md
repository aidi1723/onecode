# OneCode I Ching Rule Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned canonical trigram encoding boundary without changing existing v1 runtime evidence semantics.

**Architecture:** Introduce a pure `iching_encoding` module containing immutable v1/v2 tables and structural conversion helpers. Keep `IchingKernel` on v1 during Phase 1, prove all conversions with exhaustive tests, then add schema metadata to new evidence in a later separately verified phase.

**Tech Stack:** Python 3.11+, `unittest`, existing OneCode six-bit kernel.

---

## File Map

- Create `src/onecode/kernel/iching_encoding.py`: schema identifiers, trigram tables, validation, and pure v1/v2 conversions.
- Create `tests/test_iching_encoding.py`: canonical line invariants, complement pairs, exhaustive round trips, and validation tests.
- Modify `docs/superpowers/specs/2026-07-10-onecode-iching-rule-canonicalization-design.md`: record any implementation decision that changes the approved boundary.
- Modify `CHANGELOG.md`: record additive canonical encoding support after tests pass.

### Task 1: Prove Canonical Trigram Invariants

**Files:**
- Create: `tests/test_iching_encoding.py`

- [x] **Step 1: Write failing canonical table tests**

Add tests importing `CANONICAL_TRIGRAMS`, `LEGACY_TRIGRAMS`,
`RULE_SCHEMA_V1`, and `RULE_SCHEMA_V2`. Assert:

```python
CANONICAL_TRIGRAMS == {
    "kun": 0b000,
    "zhen": 0b001,
    "kan": 0b010,
    "dui": 0b011,
    "gen": 0b100,
    "li": 0b101,
    "xun": 0b110,
    "qian": 0b111,
}
```

Also assert the legacy table preserves `xun=101` and `li=110`, and the two
schema identifiers are distinct.

- [x] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_iching_encoding -v
```

Expected: FAIL with `ModuleNotFoundError` for
`onecode.kernel.iching_encoding`.

- [x] **Step 3: Implement the immutable tables**

Create `src/onecode/kernel/iching_encoding.py` with:

```python
RULE_SCHEMA_V1 = "onecode-iching-v1"
RULE_SCHEMA_V2 = "onecode-iching-v2"

LEGACY_TRIGRAMS = {
    "kun": 0b000,
    "zhen": 0b001,
    "kan": 0b010,
    "dui": 0b011,
    "gen": 0b100,
    "xun": 0b101,
    "li": 0b110,
    "qian": 0b111,
}

CANONICAL_TRIGRAMS = {
    "kun": 0b000,
    "zhen": 0b001,
    "kan": 0b010,
    "dui": 0b011,
    "gen": 0b100,
    "li": 0b101,
    "xun": 0b110,
    "qian": 0b111,
}
```

Expose read-only mappings using `MappingProxyType` so callers cannot mutate
the schema tables.

- [x] **Step 4: Run the test and verify GREEN**

Run the Task 1 test command. Expected: all Task 1 tests pass.

### Task 2: Add Schema and Value Validation

**Files:**
- Modify: `src/onecode/kernel/iching_encoding.py`
- Modify: `tests/test_iching_encoding.py`

- [x] **Step 1: Write failing validation tests**

Test that `trigram_table(schema)` returns the correct table and rejects an
unknown schema. Test that `validate_trigram()` rejects booleans, negative
values, and values above seven. Test that `validate_status()` rejects booleans,
negative values, and values above 63.

- [x] **Step 2: Run the focused tests and verify RED**

Expected: FAIL because validation helpers do not exist.

- [x] **Step 3: Implement minimal validation helpers**

Add:

```python
def trigram_table(schema: str) -> Mapping[str, int]: ...
def validate_trigram(value: int) -> int: ...
def validate_status(value: int) -> int: ...
```

Use strict integer checks so `bool` is rejected.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run `tests.test_iching_encoding` and expect all tests to pass.

### Task 3: Add Trigram Conversion

**Files:**
- Modify: `src/onecode/kernel/iching_encoding.py`
- Modify: `tests/test_iching_encoding.py`

- [x] **Step 1: Write failing conversion tests**

For every trigram name, convert the source schema numeric value into the target
schema numeric value. Assert v1 xun becomes v2 xun, v1 li becomes v2 li, and
the remaining six values are identity conversions. Assert exhaustive v1/v2
round trips.

- [x] **Step 2: Run the tests and verify RED**

Expected: FAIL because `convert_trigram()` does not exist.

- [x] **Step 3: Implement name-preserving conversion**

Implement:

```python
def convert_trigram(value: int, source_schema: str, target_schema: str) -> int:
    source = trigram_table(source_schema)
    target = trigram_table(target_schema)
    name_by_value = {bits: name for name, bits in source.items()}
    return target[name_by_value[validate_trigram(value)]]
```

- [x] **Step 4: Run the tests and verify GREEN**

Run the focused test module and expect all tests to pass.

### Task 4: Add Exhaustive Hexagram Conversion

**Files:**
- Modify: `src/onecode/kernel/iching_encoding.py`
- Modify: `tests/test_iching_encoding.py`

- [x] **Step 1: Write failing 64-state tests**

Assert that `convert_status()` converts inner and outer trigrams separately,
preserves qian/qian and kun/kun, converts legacy li/kun to canonical li/kun,
and round-trips every integer from zero through 63.

- [x] **Step 2: Run the tests and verify RED**

Expected: FAIL because `convert_status()` does not exist.

- [x] **Step 3: Implement structural conversion**

Implement:

```python
def convert_status(value: int, source_schema: str, target_schema: str) -> int:
    status = validate_status(value)
    inner = convert_trigram(status & 0b111, source_schema, target_schema)
    outer = convert_trigram((status >> 3) & 0b111, source_schema, target_schema)
    return (outer << 3) | inner
```

- [x] **Step 4: Run the tests and verify GREEN**

Run the focused test module and expect all tests to pass.

### Task 5: Add Canonical Complement Certificate

**Files:**
- Modify: `src/onecode/kernel/iching_encoding.py`
- Modify: `tests/test_iching_encoding.py`

- [x] **Step 1: Write failing complement tests**

Assert canonical complements:

```text
kun <-> qian
zhen <-> xun
kan <-> li
dui <-> gen
```

Assert the certificate reports all eight trigrams covered with no failures.

- [x] **Step 2: Run the tests and verify RED**

Expected: FAIL because `canonical_encoding_certificate()` does not exist.

- [x] **Step 3: Implement the certificate**

Return a deterministic dictionary containing schema, trigram count, checked
pairs, invalid pairs, and `valid` status. The certificate must derive
complements with `bits ^ 0b111` rather than hard-coding pass results.

- [x] **Step 4: Run the tests and verify GREEN**

Run the focused test module and expect all tests to pass.

### Task 6: Document Additive Support and Run Regression

**Files:**
- Modify: `CHANGELOG.md`

- [x] **Step 1: Add changelog entry**

Record the initial additive v2 encoding and pure conversion boundary. The
subsequent evidence migration plan records the approved runtime cutover.

- [x] **Step 2: Run focused encoding and kernel tests**

```bash
.venv/bin/python -m unittest \
  tests.test_iching_encoding \
  tests.test_iching_kernel \
  tests.test_iching_kernel_integration \
  -v
```

Expected: PASS.

- [x] **Step 3: Run source quality**

```bash
.venv/bin/python scripts/check_source_quality.py src
```

Expected: `source quality ok`.

- [x] **Step 4: Run full verification**

```bash
bash scripts/verify.sh
```

Expected: all tests pass and doctor returns status `ok`.

## Follow-Up Plans

The following require separate implementation plans after Phase 1 passes:

1. Add `rule_schema` metadata to newly written checkpoint, ledger, WAL, profile,
   shell, benchmark, and training artifacts.
2. Add a read-only migration audit that identifies v1 artifacts and calculates
   v2 interpretations without rewriting them.
3. Cut over new runtime classifications to v2 only after dual-read evidence and
   training-data regeneration are verified.
4. Add line position, centrality, correspondence, adjacency, trigram virtue,
   opposite, inverse, and logical timing profiles under the existing safety
   dominance rules.
