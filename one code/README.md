# OneCode

OneCode is a local-first agent kernel prototype. It focuses on scoped file writes, append-only run evidence, stateful resumption, and deterministic Iching-derived status profiles.

The code is intentionally small and currently runs with the Python standard library only.

The short module entrypoint is `python3 -m onecode`. The older explicit CLI module form, such as `python3 -m onecode.cli doctor`, remains supported.

## Verify

Run the complete local check:

```bash
bash scripts/verify.sh
```

This runs:

- `python3 -m compileall src tests`
- `python3 -m unittest discover -s tests -v`
- `python3 -m onecode doctor`

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

Each run contains `manifest.json`, `ledger.json`, and checkpoint files.

## Safety Model

All physical writes go through `PathGuard.write_text()` after `LogosGate.preflight()`. The current write surface is intentionally limited to `write_text`.

The kernel records an `iching_profile` in run evidence. This profile is a deterministic control view over status bits, yin-yang balance, four-symbol windows, trigram records, five-element relations, and runtime transition decisions.
