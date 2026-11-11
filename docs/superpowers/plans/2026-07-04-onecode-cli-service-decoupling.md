# OneCode CLI Service Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move shared doctor, inspect, and list-runs behavior out of `onecode.cli` into kernel-owned service modules while preserving CLI/Web/TUI behavior.

**Architecture:** Add `onecode.kernel.diagnostics` for doctor checks and `onecode.kernel.run_inspection` for run inspection/listing. Keep compatibility imports in `onecode.cli`, then update Web and TUI callers to import kernel services directly.

**Tech Stack:** Python stdlib, existing OneCode kernel modules, `unittest`, shell verification scripts.

---

### Task 1: Add Import Boundary Tests

**Files:**
- Modify: `tests/test_source_quality.py`

- [ ] **Step 1: Write the failing test**

Add tests that read source files and reject non-CLI surfaces importing shared
runtime services from `onecode.cli`:

```python
    def test_web_and_tui_do_not_depend_on_cli_services(self):
        forbidden = "from onecode.cli import"
        for path in ["src/onecode/web/api.py", "src/onecode/tui/app.py"]:
            text = Path(path).read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_source_quality.SourceQualityTests.test_web_and_tui_do_not_depend_on_cli_services -v
```

Expected: FAIL because `src/onecode/web/api.py` and `src/onecode/tui/app.py`
currently import from `onecode.cli`.

### Task 2: Extract Diagnostics Service

**Files:**
- Create: `src/onecode/kernel/diagnostics.py`
- Modify: `src/onecode/cli.py`
- Test: `tests/test_doctor_cli.py`

- [ ] **Step 1: Move doctor functions**

Move these functions from `src/onecode/cli.py` to
`src/onecode/kernel/diagnostics.py`:

- `doctor_check`
- `doctor_result_detail`
- `doctor_rule_passed`
- `run_doctor`

Required imports in the new file:

```python
import tempfile
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import discover_project_context
from onecode.kernel.recovery_policy import recovery_status
from onecode.kernel.runner import run_task
from onecode.kernel.runtime_config import inspect_runtime_config
from onecode.kernel.skill_context import discover_skill_context, public_skill_context
```

In `src/onecode/cli.py`, import compatibility names:

```python
from onecode.kernel.diagnostics import run_doctor
```

- [ ] **Step 2: Verify focused doctor tests pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_doctor_cli -v
```

Expected: OK.

### Task 3: Extract Run Inspection Service

**Files:**
- Create: `src/onecode/kernel/run_inspection.py`
- Modify: `src/onecode/cli.py`
- Test: `tests/test_inspect_cli.py`, `tests/test_list_runs_cli.py`

- [ ] **Step 1: Move inspection functions**

Move these functions from `src/onecode/cli.py` to
`src/onecode/kernel/run_inspection.py`:

- `delivery_summary`
- `ledger_history_present`
- `task_completion_evidence`
- `apply_verifier_evidence`
- `apply_verifier_evidence_from_dicts`
- `task_status_from_verifier_dicts`
- `verifier_dicts`
- `verifier_failure`
- `write_result_ledger`
- `align_counts_with_manifest`
- `apply_task_resume_evidence`
- `halted_task_resume_result`
- `checkpoint_asset_path`
- `checkpoint_assets`
- `optional_task_inspect_fields`
- `compact_skill_selection_inspect_fields`
- `trace_repair_decision`
- `read_global_wal_segment`
- `read_global_wal_entries`
- `read_global_wal_run_entry`
- `inspect_global_wal_run`
- `global_wal_run_summaries`
- `inspect_run`
- `list_runs`

Keep imports in `src/onecode/cli.py` for compatibility:

```python
from onecode.kernel.run_inspection import (
    apply_task_resume_evidence,
    apply_verifier_evidence,
    apply_verifier_evidence_from_dicts,
    delivery_summary,
    halted_task_resume_result,
    inspect_run,
    list_runs,
    task_completion_evidence,
    task_status_from_verifier_dicts,
    verifier_dicts,
    verifier_failure,
)
```

- [ ] **Step 2: Verify focused inspection tests pass**

Run:

```bash
.venv/bin/python -m unittest tests.test_inspect_cli tests.test_list_runs_cli tests.test_run_plan_cli -v
```

Expected: OK.

### Task 4: Update Web and TUI Imports

**Files:**
- Modify: `src/onecode/web/api.py`
- Modify: `src/onecode/tui/app.py`
- Test: `tests/test_web_api.py`, `tests/test_tui_model_closure.py`

- [ ] **Step 1: Update Web API imports**

Replace:

```python
from onecode.cli import inspect_run, list_runs, run_doctor
```

With:

```python
from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.run_inspection import inspect_run, list_runs
```

- [ ] **Step 2: Update TUI lazy imports**

Replace worker-local imports:

```python
from onecode.cli import run_doctor
from onecode.cli import inspect_run
from onecode.cli import list_runs
```

With:

```python
from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.run_inspection import inspect_run
from onecode.kernel.run_inspection import list_runs
```

- [ ] **Step 3: Run import-boundary test**

Run:

```bash
.venv/bin/python -m unittest tests.test_source_quality.SourceQualityTests.test_web_and_tui_do_not_depend_on_cli_services -v
```

Expected: OK.

- [ ] **Step 4: Run Web/TUI focused tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_web_api tests.test_tui_model_closure -v
```

Expected: OK.

### Task 5: Verify Source Quality and Full Suite

**Files:**
- Modify: `CHANGELOG.md`
- Create or modify: `docs/ONECODE_MAINTENANCE_LOG_2026-07-04.md`

- [ ] **Step 1: Run source quality**

Run:

```bash
.venv/bin/python scripts/check_source_quality.py src
```

Expected: `source quality ok`.

- [ ] **Step 2: Run full verification**

Run:

```bash
bash scripts/verify.sh
```

Expected: full unittest suite passes and doctor status is `ok`.

- [ ] **Step 3: Update records**

Add a 2026-07-04 entry to `CHANGELOG.md` or extend the current 2026-07-04
section with:

- extracted doctor/inspection shared services from CLI into kernel modules
- Web/TUI no longer import shared runtime services from `onecode.cli`
- CLI compatibility exports preserved
- verification command results

Update the 2026-07-04 maintenance log with the same result and residual risks.
