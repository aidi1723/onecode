# OneCode

OneCode is a local-first agent kernel prototype. It focuses on scoped file writes, append-only run evidence, stateful resumption, and deterministic Iching-derived status profiles.

The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency.

The short module entrypoint is `python3 -m onecode`. The older explicit CLI module form, such as `python3 -m onecode.cli doctor`, remains supported.

## Install

Install the core CLI:

```bash
pip install -e .
```

Install the optional conversational TUI:

```bash
pip install -e .[tui]
```

The pinned TUI dependency is also mirrored in `requirements-tui.txt` for local virtualenv workflows.

## Verify

Run the complete local check:

```bash
bash scripts/verify.sh
```

This runs:

- `python3 -m compileall src tests`
- `python3 -m unittest discover -s tests -v`
- `python3 -m onecode doctor`

## Local Demo

Run the v0.7 local verifier workflow in a temporary workspace:

```bash
bash scripts/demo_v07.sh
```

## Doctor

Run the built-in smoke check:

```bash
PYTHONPATH=src python3 -m onecode doctor
```

`doctor` runs four real local paths in a temporary workspace:

- `write_text`
- `resume_skip`
- `sovereignty_breach`
- `http_timeout`

It prints JSON and exits non-zero if any check fails.

## Self Audit

Run the project-level self audit:

```bash
onecode audit-self
```

`audit-self` reviews the CLI shell, TUI bootstrap, model provider matrix, `compileall`, unittest, and `doctor`. The final status is collapsed through `IchingKernel` into an `iching_status_code`, transition action, and dispatch decision.

## TUI

Start the conversational shell:

```bash
onecode tui
```

The TUI is optional and requires Textual. It routes chat through the configured model endpoint, while task execution still flows through the kernel loop, `LogosGate`, `PathGuard`, and ledger evidence.

TUI output is also written as plain text under the active workspace:

```text
.onecode/tui-transcript.txt
.onecode/tui-last-output.txt
```

Use `/export` or `/export-last` in the TUI to print those paths when terminal box selection is inconvenient.

## Run

Write one asset:

```bash
PYTHONPATH=src python3 -m onecode run "write asset" \
  --workspace /tmp/onecode-demo \
  --run-id demo-run \
  --write-path src/demo.py \
  --write-content "value = 1\n"
```

Write multiple assets:

```bash
PYTHONPATH=src python3 -m onecode run "write assets" \
  --workspace /tmp/onecode-demo \
  --run-id demo-multi \
  --write-text "src/a.py=a = 1\n" \
  --write-text "tests/test_a.py=def test_a():\n    assert True\n"
```

Resume from an earlier run:

```bash
PYTHONPATH=src python3 -m onecode run "resume asset" \
  --workspace /tmp/onecode-demo \
  --run-id demo-resume \
  --resume-from demo-run \
  --write-path src/demo.py \
  --write-content "value = 2\n"
```

If the prior asset exists and its SHA256 matches the old manifest, OneCode skips the write and records `resumed_asset_ready`.

## Run Plan

Run a structured task plan:

```json
{
  "task": "build demo",
  "assets": [
    {"path": "src/demo.py", "content": "value = 1\n"},
    {"path": "tests/test_demo.py", "content": "def test_demo():\n    assert True\n"}
  ]
}
```

```bash
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan \
  --plan /tmp/onecode-demo/task-plan.json
```

Resume a plan-backed task through the same checkpoint and skip rules:

```bash
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan-resume \
  --resume-from demo-plan \
  --plan /tmp/onecode-demo/task-plan.json
```

Generate a local verifier policy and require a controlled verifier before delivery:

```bash
PYTHONPATH=src python3 -m onecode list-verifier-presets

PYTHONPATH=src python3 -m onecode init-verifier-policy \
  --workspace /tmp/onecode-demo \
  --preset python-unittest
```

After initialization, `run-plan --verifier` reads the workspace default policy at `.onecode/verifier-policy.json`:

```bash
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan-verified \
  --plan /tmp/onecode-demo/task-plan.json \
  --verifier python-unittest
```

Use `--verifier-policy` to override the workspace default policy path.

## Inspect

Inspect one run:

```bash
PYTHONPATH=src python3 -m onecode inspect \
  --workspace /tmp/onecode-demo \
  --run-id demo-run
```

List all runs in a workspace:

```bash
PYTHONPATH=src python3 -m onecode list-runs \
  --workspace /tmp/onecode-demo
```

Run evidence is stored under:

```text
<workspace>/.onecode/runs/<run-id>/
```

Each run contains `manifest.json`, `ledger.json`, `ledger.jsonl`, and checkpoint files.
`ledger.json` is the latest user-facing result. `ledger.jsonl` is the append-only result history for repeated writes to the same run evidence directory.

## Safety Model

All physical writes go through `PathGuard.write_text()` after `LogosGate.preflight()`. The current write surface is intentionally limited to guarded `write_text` and `patch_text`. `bash_execution` and `execute_pytest` are auditable intent types, but Phase 1 denies them before execution.

The kernel records an `iching_profile` in run evidence. This profile is a deterministic control view over status bits, yin-yang balance, four-symbol windows, trigram records, five-element relations, and runtime transition decisions.

## Rule Closure Principle

OneCode rule: external facts are evidence, not law. Filesystem presence, SHA256 matches, path traversal, permission denial, and timeout are sampled as physical evidence, then collapsed into the existing rule surface: `6-bit status_code`, yin-yang pressure, four-symbol windows, trigrams, five-element dynamics, and `IchingKernel.transition()`.

Bug fixes must close inside that rule surface. If a test exposes a runtime split, the fix should refine classification, yin-yang balance, five-element relations, or transition behavior. It must not add forbidden parallel control variables such as confidence levels, model moods, manual priorities, retry scores, or external policy flags.

## Rule Discovery Protocol

Bug reports are rule-gap probes. When OneCode cannot process a task, the failure is treated as missing rule coverage until proven otherwise. The fix path is to add a failing test, collapse the observed evidence into an existing or new `6-bit status_code`, refine the yin-yang or five-element transition rule, and verify the resulting manifest, ledger, and checkpoint evidence.

If a runtime result cannot yet be mapped to a specific operating rule, the missing mapping must be closed by adding a failing test and extending `IchingKernel.transition()` or its classifiers. That audit output marks the next rule-discovery target; it is not permission to add external control variables.
