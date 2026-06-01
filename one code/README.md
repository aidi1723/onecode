# OneCode

OneCode is a local-first agent kernel prototype. It focuses on scoped file writes, append-only run evidence, stateful resumption, and deterministic Iching-derived status profiles.

The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency.

OneCode is licensed under the Apache License, Version 2.0.

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

Run the core local check when you want a fast gate without installing optional
TUI dependencies:

```bash
bash scripts/verify-core.sh
```

This runs:

- `python3 -m compileall src tests`
- focused core `unittest` suites for runner, inspect/list-runs, execution,
  model loop, benchmark, shell projection, Iching integration, resumption, and
  task resume
- `python3 -m onecode doctor`

Run the complete local check, including optional TUI installation and all tests:

```bash
bash scripts/verify.sh
```

This runs:

- `python3 -m compileall src tests`
- `python3 -m unittest discover -s tests -v`
- `python3 -m onecode doctor`

## v0.2 Hardening Foundations

OneCode v0.2 adds four maturity foundations around the existing local kernel:

- Docker sandbox command construction in `onecode.kernel.sandbox`
- append-only trace event JSONL records in `onecode.kernel.trace`, emitted
  through runner, model-call, checkpoint, and verifier paths
- human approval decision JSONL records in `onecode.kernel.approval`
- benchmark task loading, execution, scoring, and report writing in
  `onecode.benchmark`

List the current benchmark task set:

```bash
PYTHONPATH=src python3 -m onecode benchmark
```

Run the default benchmark task set and write a report:

```bash
PYTHONPATH=src python3 -m onecode benchmark --run \
  --workspace-root /tmp/onecode-benchmark-workspaces \
  --report /tmp/onecode-benchmark-report.json
```

The default benchmark set contains 20 executable local tasks. The sandbox
adapter is available to verifier callers as an explicit option, but OneCode does
not yet force all kernel execution paths through Docker.

## Shell Projection Contract

Shell-facing adapters should consume `shell_projection` instead of inferring
status from raw kernel evidence. The current projection schema is versioned as
`version: 1` and exposes:

- `status_label`, `severity`, `next_action`, and `compact_message` for concise
  UI/CLI rendering
- `rule_state` for Iching-derived status code, transition action/reason, and
  dispatch decision
- `delivery_state` for requested/completed/skipped/failed counts
- `evidence_ref` for WAL/full evidence references and profile hash lookup
- `resume_state` for resumed run relationships

Raw run dictionaries, ledgers, manifests, and WAL records remain kernel/audit
data. Shells may display them, but should not mutate them or rely on incidental
raw field combinations when `shell_projection` is present.

Shell adapters can discover the contract without reading source code:

```bash
PYTHONPATH=src python3 -m onecode shell-schema
```

The same contract is exposed over the local Web API:

```text
GET /v1/onecode/shell/schema
Authorization: Bearer <ONECODE_API_TOKEN>
```

Run the Docker sandbox smoke check:

```bash
mkdir -p /tmp/onecode-sandbox-smoke
PYTHONPATH=src python3 -m onecode sandbox-smoke \
  --workspace /tmp/onecode-sandbox-smoke \
  --report /tmp/onecode-sandbox-smoke/report.json
```

If Docker is not installed, the command exits with code `2` and writes a
structured `blocked` report with `reason: docker_not_found`.

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

## LibreChat Shell API

Start OneCode's OpenAI-compatible HTTP API for a LibreChat custom endpoint:

```bash
PYTHONPATH=src ONECODE_API_TOKEN=dev-local-token python3 -m onecode serve --host 127.0.0.1 --port 8080
```

LibreChat should point its custom endpoint at:

```text
ONECODE_API_BASE_URL=http://localhost:8080/v1
ONECODE_API_TOKEN=dev-local-token
```

The API exposes `/health`, `/v1/models`, and `/v1/chat/completions`. It calls OneCode core directly and does not depend on any OneWord gateway service.

This server uses Python's stdlib HTTP stack and is intended for local preview
or a trusted loopback bridge. Keep it on `127.0.0.1` unless it is placed behind
an explicit production gateway with TLS, rate limiting, request-size limits, and
operator-owned authentication. Token checks use constant-time comparison when a
token is configured; unauthenticated mode is only available through the explicit
loopback-only local flag.

## Local Agent Shell

If the LibreChat shell repository is installed next to this repository as `../onecode-librechat`, start the full local OneCode Agent shell with:

```bash
PYTHONPATH=src python3 -m onecode shell
```

This launches a temporary local MongoDB, the OneCode API, and the LibreChat Web shell. Open:

```text
http://127.0.0.1:3080
```

Local preview login:

```text
Email: onecode@local.test
Password: OneCode123!
```

Registration is enabled by the launcher, so you can also create a local account from the login screen. Use `Ctrl+C` in the launcher terminal to stop all local services.

## Run

Write one asset:

```bash
PYTHONPATH=src python3 -m onecode run "write asset" \
  --workspace /tmp/onecode-demo \
  --run-id demo-run \
  --write-path src/demo.py \
  --write-content "value = 1\n" \
  --max-write-bytes 5000000
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

Each run contains `manifest.json`, `ledger.json`, `ledger.jsonl`, `trace.jsonl`, `evidence-chain.jsonl`, and checkpoint files.
`ledger.json` is the latest user-facing result. `ledger.jsonl` is the append-only result history for repeated writes to the same run evidence directory.
`evidence-chain.jsonl` records a tamper-evident SHA256 chain over ledger writes.
`inspect` verifies checkpoint hashes, evidence-chain continuity, and, when a run records `trace_path`, requires a terminal `run_completed` trace event.

## Safety Model

All physical writes go through `PathGuard.write_text()` after `LogosGate.preflight()`. The current write surface is intentionally limited to guarded `write_text` and `patch_text`. `bash_execution` and `execute_pytest` are auditable intent types, but Phase 1 denies them before execution.

`bash_execution` and `execute_pytest` are not dead code and are not advertised as
usable tools. They are reserved intent names that let the kernel record and test
high-risk requests as `permission_denied` evidence without executing them.

Runtime action exceptions are contained by `LogosGate.run_bounded_action()` and
returned as halted evidence with `reason: action_exception`. Controlled
verifiers keep the compatible `status: failed` shape while also reporting a
machine-readable `failure_kind` such as `command_failed` or `timeout`.

Run-level failures are collapsed into halted evidence with `reason:
run_exception` where possible. Resource guardrails such as `--max-task-chars`,
`--max-write-bytes`, `--max-actions`, `--max-trace-bytes`, and
`--max-run-seconds` reject oversized or overlong runs with
`resource_budget_exceeded` before writing further target files where possible,
while still recording manifest, checkpoint, ledger, evidence-chain, and
`run_completed` trace evidence.

The Docker sandbox adapter uses local-first defensive defaults: network
disabled by default, memory and CPU limits, `--pids-limit`, `--cap-drop ALL`, a
read-only container filesystem where compatible, and a bounded `/tmp` tmpfs.
The sandbox is available for smoke checks and verifier execution; the main
write path remains a guarded file-change path rather than an unrestricted
command runner.

The kernel records an `iching_profile` in run evidence. This profile is a deterministic control view over status bits, yin-yang balance, four-symbol windows, trigram records, five-element relations, and runtime transition decisions.

Run the math-rule audit:

```bash
PYTHONPATH=src python3 -m onecode math-audit
```

`math-audit` is read-only. It reports the 64-state transition graph summary,
attractor count, `Q6` topology closure, stability boundaries, Lyapunov energy
certificates, entropy-gate efficiency probes, accepted control-theory mappings,
total-mapping safety certificates, collision-risk checks, and reference-only
formulas that are intentionally not part of the deterministic kernel.

## Rule Closure Principle

OneCode rule: external facts are evidence, not law. Filesystem presence, SHA256 matches, path traversal, permission denial, and timeout are sampled as physical evidence, then collapsed into the existing rule surface: `6-bit status_code`, yin-yang pressure, four-symbol windows, trigrams, five-element dynamics, and `IchingKernel.transition()`.

Bug fixes must close inside that rule surface. If a test exposes a runtime split, the fix should refine classification, yin-yang balance, five-element relations, or transition behavior. It must not add forbidden parallel control variables such as confidence levels, model moods, manual priorities, retry scores, or external policy flags.

## Rule Discovery Protocol

Bug reports are rule-gap probes. When OneCode cannot process a task, the failure is treated as missing rule coverage until proven otherwise. The fix path is to add a failing test, collapse the observed evidence into an existing or new `6-bit status_code`, refine the yin-yang or five-element transition rule, and verify the resulting manifest, ledger, and checkpoint evidence.

If a runtime result cannot yet be mapped to a specific operating rule, the missing mapping must be closed by adding a failing test and extending `IchingKernel.transition()` or its classifiers. That audit output marks the next rule-discovery target; it is not permission to add external control variables.
