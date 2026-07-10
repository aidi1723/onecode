# OneCode CLI Configuration Command Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract verifier-policy and model-configuration commands into a focused CLI adapter without changing path safety, secret handling, parser contracts, output, errors, or exit codes.

**Architecture:** Keep `onecode.cli.build_parser()` and `onecode.cli.main()` public, but delegate configuration parser registration and dispatch to `onecode.cli_commands.configuration`. Existing model-config and verifier-policy services remain the sole validation and persistence authorities.

**Tech Stack:** Python 3.11+, stdlib `argparse`, `json`, `pathlib`, `unittest`, `unittest.mock`, and existing OneCode configuration services.

---

### Task 1: Freeze Configuration Parser Contracts

**Files:**
- Create: `tests/test_cli_configuration_commands.py`

- [x] **Step 1: Write failing module import and command-set tests**

Import:

```python
from onecode.cli_commands.configuration import (
    CONFIGURATION_COMMANDS,
    dispatch_configuration_command,
    register_configuration_commands,
)
```

Assert:

```python
CONFIGURATION_COMMANDS == frozenset(
    {"list-verifier-presets", "init-verifier-policy", "config"}
)
```

- [x] **Step 2: Run the test to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_configuration_commands -v
```

Expected: FAIL because `onecode.cli_commands.configuration` does not exist.

- [x] **Step 3: Freeze top-level and nested parser contracts**

Serialize the current parser actions for `list-verifier-presets`,
`init-verifier-policy`, and `config`. For `config`, also locate its nested
`_SubParsersAction` and freeze the `set-model`, `show`, and `discover-models`
actions. Record option strings, destinations, required flags, defaults, choices,
nargs, action classes, types, subparser destination, and required status.

- [x] **Step 4: Verify current values before production changes**

Run the parser-only assertion against `onecode.cli.build_parser()` while the
module import remains the expected RED. Copy exact current values into the test;
do not simplify the nested parser contract.

### Task 2: Extract Parser Registration

**Files:**
- Create: `src/onecode/cli_commands/configuration.py`
- Modify: `src/onecode/cli.py:244-264`
- Test: `tests/test_cli_configuration_commands.py`

- [x] **Step 1: Add the command constant and parser registration function**

Create the module with stdlib imports plus
`DEFAULT_VERIFIER_POLICY_PATH`. Move the three parser blocks verbatim. Add a
temporary dispatcher returning `None`.

- [x] **Step 2: Delegate registration from `build_parser()`**

Call `register_configuration_commands(subparsers)` at the original location and
delete only duplicated configuration parser construction.

- [x] **Step 3: Run parser and existing config tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_configuration_commands \
  tests.test_model_config_cli \
  tests.test_verifier_policy_init_cli -v
```

Expected: parser and existing behavior tests pass unchanged.

### Task 3: Extract Dispatch with Service Mocks

**Files:**
- Modify: `tests/test_cli_configuration_commands.py`
- Modify: `src/onecode/cli_commands/configuration.py`
- Modify: `src/onecode/cli.py:535-572`

- [x] **Step 1: Write failing unknown and preset-summary tests**

Assert unhandled `run` returns `None`. Patch
`verifier_policy_presets_summary()` to return a sentinel payload, capture stdout,
and assert exact JSON plus exit code `0`.

- [x] **Step 2: Write failing policy-write and parser-error tests**

Patch `write_verifier_policy()` and assert exact workspace `Path`, output,
preset list, and force arguments. Add a `ValueError("unsafe output")` case using
a real parser and assert `SystemExit(2)` plus stderr text.

- [x] **Step 3: Write failing model config action tests**

Patch `write_model_config()`, `read_model_config()`, and `discover_models()`.
Assert exact arguments, sorted JSON, exit `0`, and that stdout never contains
the supplied raw secret. The discovery patch must prove no real network call is
made.

- [x] **Step 4: Run direct dispatch tests to verify RED**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_configuration_commands -v
```

Expected: handled-command tests fail because the temporary dispatcher returns
`None`.

- [x] **Step 5: Implement dispatch and integrate `main()`**

Call only the existing service functions. Preserve sorted UTF-8 JSON and error
behavior. Invoke the dispatcher after the local-interface adapter, then remove
only the original configuration branches.

- [x] **Step 6: Run direct and existing behavior tests**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_configuration_commands \
  tests.test_model_config \
  tests.test_model_config_cli \
  tests.test_verifier_policy_init_cli \
  tests.test_web_api -v
```

Expected: all tests pass, with no real model discovery request in direct tests.

### Task 4: Enforce Dependencies, Secrets, and Structure

**Files:**
- Modify: `tests/test_cli_configuration_commands.py`

- [x] **Step 1: Add adapter dependency tests**

Parse adapter imports and permit only stdlib, `onecode.kernel.model_config`, and
`onecode.kernel.verifier`. Reject runner, execution, model loop/provider,
training, benchmark, sandbox, Web/TUI, evidence modules, `IchingKernel`, and
reverse `onecode.cli` imports.

- [x] **Step 2: Add reverse-dependency tests**

Assert Web, TUI, kernel modules outside model-config/verifier, and existing CLI
adapters do not import `onecode.cli_commands.configuration`.

- [x] **Step 3: Add secret-output and structural tests**

Run the existing temporary-home set/show path with a sentinel secret and assert
captured stdout and closure fixtures omit it. Assert `main()` has no direct
configuration comparisons and `build_parser()` has no direct registrations.
Record actual pre/post line counts and require material reduction without
expanding scope.

- [x] **Step 4: Run structural and source-quality tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_cli_configuration_commands tests.test_source_quality -v
.venv/bin/python scripts/check_source_quality.py src
```

Expected: all boundary tests pass and source quality is `ok`.

### Task 5: Record and Verify the Phase

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/ONECODE_CLI_CONFIGURATION_COMMAND_SPLIT_CLOSURE_2026-07-10.md`
- Modify: `docs/superpowers/plans/2026-07-10-onecode-cli-configuration-command-split.md`

- [x] **Step 1: Document configuration authority and secret boundary**

Record extracted commands, service authority, temporary test paths, masked
output, unchanged network behavior, parser compatibility, and unchanged kernel
authority. Do not record raw secrets.

- [x] **Step 2: Run focused verification**

Run:

```bash
.venv/bin/python -m unittest \
  tests.test_cli_configuration_commands \
  tests.test_cli_local_interface_commands \
  tests.test_cli_read_only_commands \
  tests.test_model_config \
  tests.test_model_config_cli \
  tests.test_verifier_policy_init_cli \
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
test counts, final CLI function sizes, dependency/secret checks, source quality,
authority scan, release audit, and `git status --short -- .`. Do not commit
unless explicitly requested.
