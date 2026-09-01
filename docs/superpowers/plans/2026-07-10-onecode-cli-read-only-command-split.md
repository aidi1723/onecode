# OneCode CLI Read-Only Command Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract five existing read-only CLI commands into a focused adapter package without changing parser contracts, JSON output, exit codes, or kernel authority.

**Architecture:** Keep `onecode.cli.build_parser()` and `onecode.cli.main()` as public compatibility entry points, but delegate read-only parser registration and dispatch to `onecode.cli_commands.read_only`. The adapter imports only existing read services and certificate helpers; all write, model, training, verifier, sandbox, and Web paths remain outside the package.

**Tech Stack:** Python 3.11+, stdlib `argparse` and `json`, `unittest`, existing OneCode kernel services.

---

### Task 1: Freeze Read-Only Parser Contracts

**Files:**
- Create: `tests/test_cli_read_only_commands.py`

- [x] **Step 1: Write the failing package import test**

Create `tests/test_cli_read_only_commands.py` and import:

```python
from onecode.cli_commands.read_only import (
    READ_ONLY_COMMANDS,
    dispatch_read_only_command,
    register_read_only_commands,
)
```

Assert:

```python
self.assertEqual(
    READ_ONLY_COMMANDS,
    frozenset({"inspect", "list-runs", "doctor", "math-audit", "shell-schema"}),
)
```

- [x] **Step 2: Run the test to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_read_only_commands -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'onecode.cli_commands'`.

- [x] **Step 3: Add parser contract extraction helpers in the test**

Add a test helper that finds the root `_SubParsersAction`, then serializes each
target parser action as:

```python
{
    "option_strings": list(action.option_strings),
    "dest": action.dest,
    "required": action.required,
    "default": action.default,
    "choices": list(action.choices) if action.choices is not None else None,
    "nargs": action.nargs,
    "action_class": type(action).__name__,
}
```

Exclude argparse's automatic help action. Freeze this expected contract:

```python
{
    "inspect": [
        {
            "option_strings": ["--workspace"],
            "dest": "workspace",
            "required": False,
            "default": ".",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
        {
            "option_strings": ["--run-id"],
            "dest": "run_id",
            "required": True,
            "default": None,
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
    ],
    "list-runs": [
        {
            "option_strings": ["--workspace"],
            "dest": "workspace",
            "required": False,
            "default": ".",
            "choices": None,
            "nargs": None,
            "action_class": "_StoreAction",
        },
    ],
    "doctor": [],
    "math-audit": [],
    "shell-schema": [],
}
```

Use `onecode.cli.build_parser()` for the baseline assertion.

- [x] **Step 4: Verify the baseline contract is GREEN**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_read_only_commands -v
```

Expected: the package import remains red, while the parser contract values have
been confirmed manually against the existing parser before production changes.

### Task 2: Extract Parser Registration

**Files:**
- Create: `src/onecode/cli_commands/__init__.py`
- Create: `src/onecode/cli_commands/read_only.py`
- Modify: `src/onecode/cli.py:161`
- Test: `tests/test_cli_read_only_commands.py`

- [x] **Step 1: Add the minimal command package and registration function**

Create an empty package initializer. In `read_only.py`, add:

```python
from __future__ import annotations

import argparse


READ_ONLY_COMMANDS = frozenset(
    {"inspect", "list-runs", "doctor", "math-audit", "shell-schema"}
)


def register_read_only_commands(subparsers: argparse._SubParsersAction) -> None:
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--workspace", default=".")
    inspect_parser.add_argument("--run-id", required=True)

    list_runs_parser = subparsers.add_parser("list-runs")
    list_runs_parser.add_argument("--workspace", default=".")

    subparsers.add_parser("doctor")
    subparsers.add_parser("math-audit")
    subparsers.add_parser("shell-schema")
```

Add a temporary `dispatch_read_only_command()` returning `None` so the import
contract is complete before dispatch extraction.

- [x] **Step 2: Delegate parser registration from `build_parser()`**

Import `register_read_only_commands` in `onecode.cli`. Call it immediately after
all parser registrations that precede the current `inspect` block, then delete
only the five duplicated registration statements. Preserve neighboring command
registration order.

- [x] **Step 3: Run parser and parser-consumer tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_read_only_commands \
  tests.test_shell_launcher \
  tests.test_runner_cli.CliTests.test_cli_shell_schema_prints_projection_contract -v
```

Expected: all tests pass with an identical parser contract.

### Task 3: Extract Direct Read-Only Dispatch

**Files:**
- Modify: `tests/test_cli_read_only_commands.py`
- Modify: `src/onecode/cli_commands/read_only.py`
- Modify: `src/onecode/cli.py:582`

- [x] **Step 1: Write failing unknown-command and shell-schema tests**

Add:

```python
def test_dispatch_returns_none_for_unhandled_command(self):
    args = argparse.Namespace(subcommand="run")
    self.assertIsNone(dispatch_read_only_command(args))

def test_dispatch_shell_schema_prints_exact_public_contract(self):
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = dispatch_read_only_command(argparse.Namespace(subcommand="shell-schema"))
    self.assertEqual(exit_code, 0)
    self.assertEqual(json.loads(stdout.getvalue()), load_shell_projection_v4_schema())
```

- [x] **Step 2: Run the dispatch tests to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_read_only_commands -v
```

Expected: shell-schema dispatch fails because the temporary dispatcher returns
`None` and prints nothing.

- [x] **Step 3: Implement `math_audit_payload()` and five dispatch branches**

Move the existing math-audit payload construction verbatim into
`math_audit_payload()`. Add imports only for:

```python
from pathlib import Path

from onecode.kernel.diagnostics import run_doctor
from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.run_inspection import inspect_run, list_runs
from onecode.kernel.shell_projection import (
    attach_shell_projection,
    attach_shell_projection_to_runs_payload,
    shell_projection_schema,
)
```

Implement exact JSON printing with `ensure_ascii=False, sort_keys=True`. Return
the original exit codes and `None` for unhandled commands.

- [x] **Step 4: Integrate early dispatch into `main()`**

Import `dispatch_read_only_command`, call it immediately after `parse_args()`,
return handled integer results, and remove only the five old inline branches.

- [x] **Step 5: Run direct and existing command tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_read_only_commands \
  tests.test_doctor_cli \
  tests.test_inspect_cli \
  tests.test_list_runs_cli \
  tests.test_runner_cli.CliTests.test_cli_shell_schema_prints_projection_contract -v
```

Expected: all tests pass with unchanged JSON and exit codes.

### Task 4: Enforce Import and Structural Boundaries

**Files:**
- Modify: `tests/test_cli_read_only_commands.py`
- Modify: `scripts/check_source_quality.py`

- [x] **Step 1: Add forbidden-import and main-branch tests**

Parse `src/onecode/cli_commands/read_only.py` with `ast` and reject imports
whose module begins with:

```python
(
    "onecode.cli",
    "onecode.web",
    "onecode.tui",
    "onecode.benchmark",
    "onecode.kernel.runner",
    "onecode.kernel.model_",
    "onecode.kernel.training_data",
    "onecode.kernel.sandbox",
    "onecode.kernel.verifier",
)
```

Parse `src/onecode/cli.py:main` and assert its source no longer contains direct
comparisons for the five extracted command names.

- [x] **Step 2: Add a source-quality regression for reduced `main()` size**

Record the pre-change `main()` size as 581 lines. Add a regression assertion
that the extracted result is below 510 lines and at least 70 lines shorter. The
initial 430-line estimate was corrected after the five-command-only extraction
proved to remove 81 lines; reaching 430 would require expanding the approved
scope into additional command families. Do not remove the existing allowlist
entry unless the function also falls below the global 160-line limit.

- [x] **Step 3: Run structural tests and source quality**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_read_only_commands tests.test_source_quality -v
.venv/bin/python scripts/check_source_quality.py src
```

Expected: import boundaries pass, `main()` is below 430 lines, and source
quality remains `ok`.

### Task 5: Record and Verify the Phase

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/ONECODE_CLI_READ_ONLY_COMMAND_SPLIT_CLOSURE_2026-07-10.md`
- Modify: `docs/superpowers/plans/2026-07-10-onecode-cli-read-only-command-split.md`

- [x] **Step 1: Document the CLI adapter boundary**

Record the five extracted commands, preserved parser/output contracts, one-way
dependency rule, and unchanged write/model/training execution paths.

- [x] **Step 2: Run focused verification**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_read_only_commands \
  tests.test_doctor_cli \
  tests.test_inspect_cli \
  tests.test_list_runs_cli \
  tests.test_runner_cli \
  tests.test_shell_launcher \
  tests.test_self_audit_cli -v
```

Expected: all selected tests pass.

- [x] **Step 3: Run source and authority checks**

Run:

```bash
.venv/bin/python scripts/check_source_quality.py src
git diff --check -- .
git diff -- src/onecode/kernel/hexagram.py | \
  rg '^[-+].*(def transition|def apply_balanced_event|def balance_mask|def element_relation|def element_cross_relation|def element_dynamics|def dispatch_decision|ELEMENT_)'
```

Expected: source quality and whitespace checks pass; forbidden-formula scan has
no output.

- [x] **Step 4: Run full verification and release audit**

Run:

```bash
bash scripts/verify.sh
bash scripts/release-audit.sh
```

Expected: full tests and Doctor pass, wheel assets pass, and publish action is
not performed.

- [x] **Step 5: Record fresh evidence and final status**

Update the closure report and mark the plan complete only with fresh focused
and full test counts, `main()` line count, source-quality result, authority scan,
release-audit result, and `git status --short -- .`. Do not commit unless the
user explicitly requests it.
