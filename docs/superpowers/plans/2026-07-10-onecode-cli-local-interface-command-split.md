# OneCode CLI Local Interface Command Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `serve`, `shell`, `shell-status`, and `tui` into a focused CLI adapter while preserving every parser, lazy-import, side-effect, error, and exit-code contract.

**Architecture:** Keep `onecode.cli.build_parser()` and `onecode.cli.main()` public, but delegate local-interface parser registration and dispatch to `onecode.cli_commands.local_interfaces`. The adapter has stdlib-only top-level imports and lazily loads Web, TUI, and shell-launcher modules only inside the selected command branch.

**Tech Stack:** Python 3.11+, stdlib `argparse`, `json`, `os`, `pathlib`, `types`, `unittest`, and `unittest.mock`.

---

### Task 1: Freeze Local Interface Parser Contracts

**Files:**
- Create: `tests/test_cli_local_interface_commands.py`

- [x] **Step 1: Write failing module import and command-set tests**

Import:

```python
from onecode.cli_commands.local_interfaces import (
    LOCAL_INTERFACE_COMMANDS,
    dispatch_local_interface_command,
    register_local_interface_commands,
)
```

Assert the set equals:

```python
frozenset({"serve", "shell", "shell-status", "tui"})
```

- [x] **Step 2: Run the test to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_local_interface_commands -v
```

Expected: FAIL because `onecode.cli_commands.local_interfaces` does not exist.

- [x] **Step 3: Freeze parser action contracts**

Reuse a parser-action serializer that records option strings, destination,
required, default, choices, nargs, action class, type name, parser description,
and parser-level defaults. Build expected dictionaries from the current parser
for all four commands, including the complete TUI provider choices and all shell
credential/port/browser defaults.

- [x] **Step 4: Verify current parser values before production changes**

Temporarily isolate the parser-contract assertion from the missing import if
needed and run it against `onecode.cli.build_parser()`. Record the exact current
values in the test; do not infer or simplify them.

### Task 2: Extract Parser Registration

**Files:**
- Create: `src/onecode/cli_commands/local_interfaces.py`
- Modify: `src/onecode/cli.py:380-435`
- Test: `tests/test_cli_local_interface_commands.py`

- [x] **Step 1: Add command constant and parser registration**

Create the module with only stdlib top-level imports. Move the four parser
blocks verbatim into `register_local_interface_commands()` and add a temporary
dispatcher returning `None`.

- [x] **Step 2: Delegate from `build_parser()`**

Import and call the registration function at the original block location, then
delete only the duplicated `serve`, `shell`, `shell-status`, and `tui` parser
construction.

- [x] **Step 3: Run parser and entrypoint tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_local_interface_commands \
  tests.test_shell_launcher \
  tests.test_venv_entrypoint -v
```

Expected: parser contracts and help entrypoints pass unchanged.

### Task 3: Extract Lazy Dispatch with Mocked Modules

**Files:**
- Modify: `tests/test_cli_local_interface_commands.py`
- Modify: `src/onecode/cli_commands/local_interfaces.py`
- Modify: `src/onecode/cli.py:600-630`

- [x] **Step 1: Write failing unknown and `serve` dispatch tests**

Assert an unhandled `run` namespace returns `None`. Install a fake
`onecode.web.api` module in `sys.modules`, call the dispatcher with a `serve`
namespace, and assert host/port arguments, return `0`, and the authenticated
environment behavior. Add a second test proving the unauthenticated flag sets
`ONECODE_ALLOW_UNAUTHENTICATED` to `true` immediately before the fake call.

- [x] **Step 2: Write failing `shell` and `shell-status` tests**

Install a fake `onecode.shell_launcher` module with recording
`config_from_args`, `launch_shell`, and `shell_status` functions. Prove exact
configuration flow, launcher exit-code passthrough, sorted JSON, `ok -> 0`,
non-ok `-> 1`, and `FileNotFoundError`/`RuntimeError` conversion through a real
`argparse.ArgumentParser.error()` yielding `SystemExit(2)`.

- [x] **Step 3: Write failing `tui` dispatch test**

Install fake `onecode.tui` and `onecode.tui.app` modules, record the `run_tui`
call, and assert workspace `Path` conversion, model/provider arguments, and
exit code `0` without importing Textual.

- [x] **Step 4: Run direct dispatch tests to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_local_interface_commands -v
```

Expected: handled-command tests fail because the temporary dispatcher returns
`None`.

- [x] **Step 5: Implement lazy dispatch and integrate `main()`**

Move the four branches without changing behavior. Call the dispatcher after the
read-only dispatcher and before remaining branches. Remove only the four old
branches.

- [x] **Step 6: Run direct and existing interface tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_local_interface_commands \
  tests.test_shell_launcher \
  tests.test_venv_entrypoint \
  tests.test_tui_layout \
  tests.test_tui_model_closure -v
```

Expected: all selected tests pass without real service or UI startup.

### Task 4: Enforce Lazy Imports and Structural Reduction

**Files:**
- Modify: `tests/test_cli_local_interface_commands.py`

- [x] **Step 1: Add top-level import boundary tests**

Parse the adapter AST and reject top-level imports beginning with `onecode.`.
Import the module after clearing relevant entries and assert it does not add
`onecode.web.api`, `onecode.tui.app`, or `onecode.shell_launcher` to
`sys.modules`.

- [x] **Step 2: Add reverse dependency checks**

Assert `src/onecode/web/api.py`, `src/onecode/tui/app.py`,
`src/onecode/shell_launcher.py`, and all `src/onecode/kernel/*.py` files do not
import `onecode.cli_commands.local_interfaces`.

- [x] **Step 3: Add structural tests**

Assert `onecode.cli.main` source has no direct comparisons for the four command
names and `build_parser` source has no direct `add_parser()` calls for them.
Record pre-change line counts and assert both functions shrink by at least the
number of lines actually present in the approved blocks; do not broaden scope
to satisfy an arbitrary threshold.

- [x] **Step 4: Run structural and source-quality tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_local_interface_commands tests.test_source_quality -v
.venv/bin/python scripts/check_source_quality.py src
```

Expected: all boundary checks pass and source quality is `ok`.

### Task 5: Record and Verify the Phase

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/ONECODE_CLI_LOCAL_INTERFACE_COMMAND_SPLIT_CLOSURE_2026-07-10.md`
- Modify: `docs/superpowers/plans/2026-07-10-onecode-cli-local-interface-command-split.md`

- [x] **Step 1: Document the adapter and side-effect boundary**

Record the four commands, parser compatibility, lazy imports, mocked test
strategy, unchanged startup behavior, and unchanged execution/kernel authority.

- [x] **Step 2: Run focused verification**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_local_interface_commands \
  tests.test_cli_read_only_commands \
  tests.test_shell_launcher \
  tests.test_venv_entrypoint \
  tests.test_tui_layout \
  tests.test_tui_model_closure \
  tests.test_web_api \
  tests.test_runner_cli -v
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

Update the closure report and mark the plan complete only with focused/full
test counts, final `main()` and `build_parser()` sizes, lazy-import proof,
source-quality result, authority scan, release audit, and
`git status --short -- .`. Do not commit unless explicitly requested.
