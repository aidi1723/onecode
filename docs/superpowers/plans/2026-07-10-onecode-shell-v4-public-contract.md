# OneCode Shell v4 Public Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add distributable Shell v4 JSON fixtures and exact cross-entry-point contract tests without changing OneCode execution decisions.

**Architecture:** Store versioned schema and projection cases in a new read-only `onecode.contracts` package, load them with `importlib.resources`, and compare existing Python, CLI, Web, and HTTP outputs against those assets. Production shell projection remains the sole computation path; fixtures never feed runtime control logic.

**Tech Stack:** Python 3.11+, stdlib `json`, `importlib.resources`, `unittest`, setuptools package data.

---

### Task 1: Add Contract Loader Tests

**Files:**
- Create: `tests/test_shell_contracts.py`
- Create: `src/onecode/contracts/__init__.py`

- [x] **Step 1: Write failing loader tests**

Create `tests/test_shell_contracts.py` with tests that import
`load_shell_projection_v4_schema()` and `load_shell_projection_v4_cases()`,
assert schema name/version, assert the six ordered case names, and mutate one
returned value before reloading to prove fresh decoding:

```python
EXPECTED_CASE_NAMES = [
    "completed_full",
    "denied_full",
    "halted_resumable",
    "corrupt_evidence",
    "completed_wal_only",
    "legacy_missing_fields",
]

def test_shell_v4_contract_assets_are_versioned_and_fresh(self):
    schema = load_shell_projection_v4_schema()
    cases = load_shell_projection_v4_cases()
    self.assertEqual(schema["name"], "onecode.shell_projection")
    self.assertEqual(schema["version"], 4)
    self.assertEqual([case["name"] for case in cases], EXPECTED_CASE_NAMES)
    schema["version"] = 999
    cases[0]["name"] = "mutated"
    self.assertEqual(load_shell_projection_v4_schema()["version"], 4)
    self.assertEqual(load_shell_projection_v4_cases()[0]["name"], "completed_full")
```

- [x] **Step 2: Run the loader test to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_shell_contracts -v
```

Expected: FAIL because `onecode.contracts` and its loader functions do not
exist.

- [x] **Step 3: Add the minimal asset loader**

Create `src/onecode/contracts/__init__.py` with:

```python
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def _load_json_object(name: str) -> dict[str, Any]:
    value = json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid_contract_asset:{name}")
    return value


def load_shell_projection_v4_schema() -> dict[str, Any]:
    return _load_json_object("shell_projection_v4_schema.json")


def load_shell_projection_v4_cases() -> list[dict[str, Any]]:
    value = json.loads(
        files(__package__).joinpath("shell_projection_v4_cases.json").read_text(encoding="utf-8")
    )
    if not isinstance(value, list):
        raise ValueError("invalid_contract_asset:shell_projection_v4_cases.json")
    cases: list[dict[str, Any]] = []
    for case in value:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("name"), str)
            or not case["name"].strip()
            or not isinstance(case.get("input"), dict)
            or not isinstance(case.get("expected"), dict)
        ):
            raise ValueError("invalid_contract_asset:shell_projection_v4_cases.json")
        cases.append(case)
    return cases
```

Add temporary empty JSON assets only as needed for the loader import, then
continue directly to Task 2; the loader test is expected to remain red until
the real assets are added.

### Task 2: Freeze Schema and Six Projection Cases

**Files:**
- Create: `src/onecode/contracts/shell_projection_v4_schema.json`
- Create: `src/onecode/contracts/shell_projection_v4_cases.json`
- Modify: `tests/test_shell_contracts.py`

- [x] **Step 1: Add failing exact-output contract tests**

Add these tests to `tests/test_shell_contracts.py`:

```python
def test_shell_v4_schema_matches_public_fixture(self):
    self.assertEqual(shell_projection_schema(), load_shell_projection_v4_schema())

def test_shell_v4_projection_cases_match_public_fixtures(self):
    for case in load_shell_projection_v4_cases():
        with self.subTest(case=case["name"]):
            self.assertEqual(project_run_to_shell(case["input"]), case["expected"])
            self.assertEqual(list(case["expected"]), list(SHELL_PROJECTION_FIELDS))
```

- [x] **Step 2: Run exact-output tests to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_shell_contracts -v
```

Expected: FAIL because the schema and six expected projections are absent or
do not match current Shell v4 output.

- [x] **Step 3: Write the canonical schema fixture**

Serialize the current `shell_projection_schema()` result as indented UTF-8 JSON
with a trailing newline into
`src/onecode/contracts/shell_projection_v4_schema.json`. Preserve dictionary
insertion order; do not sort keys.

- [x] **Step 4: Write six deterministic case fixtures**

Create `src/onecode/contracts/shell_projection_v4_cases.json`. Each entry has
exactly `name`, `input`, and `expected`. Use deterministic run IDs and relative
paths. Inputs must cover:

```python
{
    "completed_full": {
        "status": "completed",
        "rule_schema": "onecode-iching-v2",
        "iching_status_code": 63,
        "iching_transition_action": "allow",
        "task_dispatch_decision": "allow",
        "delivery_status": "deliverable",
        "next_action": "idle",
        "balance_mutation_summary": {
            "changed_asset_count": 1,
            "total_changed_line_count": 1,
            "changed_bands": ["heaven"],
            "latest_before_status_code": 63,
            "latest_after_status_code": 31,
        },
    },
    "denied_full": {
        "status": "denied",
        "reason": "permission_denied",
        "iching_status_code": 40,
        "iching_transition_action": "halt",
        "iching_transition_reason": "sovereignty_fire_boundary_halt",
        "task_dispatch_decision": "deny",
    },
    "halted_resumable": {
        "status": "halted",
        "reason": "http_timeout",
        "iching_status_code": 17,
        "iching_transition_action": "checkpoint",
        "task_dispatch_decision": "stop",
        "next_action": "resume",
        "resumed": False,
        "resumed_from": "prior-run",
    },
    "corrupt_evidence": {
        "status": "corrupt",
        "corrupt_reason": "invalid_balance_mutation_evidence",
        "corrupt_path": ".onecode/runs/corrupt-evidence/ledger.json",
    },
    "completed_wal_only": {
        "status": "completed",
        "evidence_mode": "wal",
        "rsv": "onecode-iching-v2",
        "bm": [1, 1, 63, 31],
        "ssr": "capability_match",
        "ssc": 1,
        "ssh": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    "legacy_missing_fields": {
        "status": "completed",
        "iching_status_code": 49,
    },
}
```

Add the appropriate `run_id` and evidence paths for each case. Generate each
`expected` only by calling the current `project_run_to_shell()` during fixture
authoring, then review the resulting JSON manually. Do not add a runtime
fixture-generation path.

- [x] **Step 5: Run the contract tests to verify GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_shell_contracts tests.test_shell_projection -v
```

Expected: all tests pass.

### Task 3: Package and Cross-Check the Public Contract

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_shell_contracts.py`
- Modify: `tests/test_runner_cli.py`
- Modify: `tests/test_web_api.py`

- [x] **Step 1: Add failing package-data and entry-point tests**

Add tests that:

```python
def test_shell_v4_contract_assets_are_package_resources(self):
    contract_root = files("onecode.contracts")
    self.assertTrue(contract_root.joinpath("shell_projection_v4_schema.json").is_file())
    self.assertTrue(contract_root.joinpath("shell_projection_v4_cases.json").is_file())
```

Replace partial schema assertions in CLI, direct Web, and HTTP tests with exact
equality against `load_shell_projection_v4_schema()`.

- [x] **Step 2: Run entry-point tests to verify RED**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_shell_contracts \
  tests.test_runner_cli.CliTests.test_cli_shell_schema_prints_projection_contract \
  tests.test_web_api.OneCodeWebApiTests.test_onecode_shell_schema_endpoint_returns_projection_contract \
  tests.test_web_api.OneCodeWebApiTests.test_http_server_serves_shell_schema -v
```

Expected: package-data assertion or exact fixture comparison fails before the
package declaration and test updates are complete.

- [x] **Step 3: Declare contract JSON package data**

Add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"onecode.tui" = ["styles.tcss"]
"onecode.contracts" = ["*.json"]
```

Keep all existing package data entries.

- [x] **Step 4: Make every schema entry point compare exactly**

Update the CLI and Web tests to import
`load_shell_projection_v4_schema()` and assert complete payload equality. The
HTTP test must compare the decoded response object to the same fixture.

- [x] **Step 5: Run cross-entry-point tests to verify GREEN**

Run the command from Step 2.

Expected: all selected tests pass.

### Task 4: Prove Legacy Compatibility and Authority Isolation

**Files:**
- Modify: `tests/test_shell_contracts.py`
- Modify: `tests/test_shell_projection.py`

- [x] **Step 1: Add legacy and WAL assertions**

For `legacy_missing_fields`, assert:

```python
self.assertEqual(expected["rule_state"]["rule_schema"], "onecode-iching-v1")
self.assertEqual(expected["balance_state"]["changed_bands"], [])
self.assertIsNone(expected["balance_state"]["changed_asset_count"])
self.assertIsNone(expected["balance_state"]["before_status_code"])
```

For `completed_wal_only`, assert v2 schema, the restored mutation counts/status
pair, empty changed bands, compact skill-selection fields, and WAL evidence
mode.

- [x] **Step 2: Add authority-isolation pair tests**

Build a completed base input, then create variants changing only mutation
summary, evidence paths/profile hash, and skill-selection display fields. For
each variant assert equality of:

```python
(
    projection["severity"],
    projection["next_action"],
    projection["rule_state"]["transition_action"],
    projection["rule_state"]["transition_reason"],
    projection["rule_state"]["dispatch_decision"],
)
```

- [x] **Step 3: Run compatibility and authority tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_shell_contracts tests.test_shell_projection -v
```

Expected: all tests pass without production decision changes.

### Task 5: Document and Verify the Contract Closure

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/ONECODE_SHELL_V4_PUBLIC_CONTRACT_CLOSURE_2026-07-10.md`
- Modify: `docs/superpowers/plans/2026-07-10-onecode-shell-v4-public-contract.md`

- [x] **Step 1: Document fixture location and versioning policy**

Add a concise README section stating that Shell v4 fixtures are installed under
`onecode.contracts`, are available through the two loader functions, freeze v4
only, and must not be used as runtime decision inputs.

- [x] **Step 2: Record the change and closure boundary**

Add a changelog subsection and closure report covering six fixtures,
cross-entry-point exact equality, package-data inclusion, legacy/WAL behavior,
and authority isolation. Explicitly record that no historical evidence was
rewritten and no Yin/Yang, trigram, five-element, balance, transition, or
dispatch formula changed.

- [x] **Step 3: Run focused verification**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_shell_contracts \
  tests.test_shell_projection \
  tests.test_runner_cli \
  tests.test_web_api \
  tests.test_inspect_cli -v
```

Expected: all selected tests pass.

- [x] **Step 4: Run source and authority checks**

Run:

```bash
.venv/bin/python scripts/check_source_quality.py src
git diff --check -- .
git diff -- src/onecode/kernel/hexagram.py | \
  rg '^[-+].*(def transition|def apply_balanced_event|def balance_mask|def element_relation|def element_cross_relation|def element_dynamics|def dispatch_decision|ELEMENT_)'
```

Expected: source quality and diff check pass; the forbidden-formula scan prints
no output.

- [x] **Step 5: Run full verification and release audit**

Run:

```bash
bash scripts/verify.sh
bash scripts/release-audit.sh
```

Expected: full tests and Doctor pass; wheel assets include both contract JSON
files; publish action is not performed.

- [x] **Step 6: Record fresh evidence and final status**

Update the closure report and mark this plan complete only with the fresh test
counts, wheel audit result, authority scan result, and final
`git status --short -- .`. Do not commit unless explicitly requested.
