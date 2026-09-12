# OneCode

OneCode is a local-first agent kernel prototype. It focuses on scoped file writes, append-only run evidence, stateful resumption, and deterministic Iching-derived status profiles.

Current version: **v0.8.0**. The release closure and verification index is
recorded in `docs/ONECODE_V0_8_FINAL_CLOSURE_2026-07-10.md`.

The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency.

OneCode is licensed under the GNU General Public License, Version 3 only
(`GPL-3.0-only`). Modified and redistributed versions must remain under GPL v3
and provide the corresponding source as required by the license.

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

If `onecode` and `textual` are already importable for the selected Python
interpreter, the script skips the editable install step and runs the remaining
checks directly. This keeps the full verification usable in prepared virtual
environments and offline local runs.

This runs:

- `python3 -m compileall src tests`
- `python3 -m unittest discover -s tests -v`
- `python3 -m onecode doctor`

## Current Closure Records

The July 16, 2026 integrated LibreChat v0.8.7 and vNext maintenance line is
summarized in:

- `docs/ONECODE_V087_VNEXT_GITHUB_CLOSURE_2026-07-16.md`

The implementation is integrated on `feature/gateway-iching-rule-sync` at
OneCode implementation head `1f3d691b175754f5bd8c3677eaf0e3d72cdeb973`.
The exact LibreChat source is community tag `v0.8.7` at `9e74cc0e`, with the
verified OneCode shell at `224e73e8`. The final publication is intentionally a
fast-forward update of the existing feature branch; unrelated `origin/main`
history is not merged or rewritten.

The detailed July 15-16 records are:

- `docs/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md`
- `docs/ONECODE_VNEXT_MAINTENANCE_GOVERNANCE_V087_CLOSURE_2026-07-16.md`
- `docs/ONECODE_VNEXT_RELEASE_LINE_AUDIT_2026-07-16.md`

This record covers the versioned LibreChat migration, bounded model timeouts,
zero outer retries, persistent private shell state, restart verification, and
desktop/mobile browser acceptance. The LibreChat source and rollback checkpoint
remain in their separate local repository; publishing the OneCode feature
branch does not merge `origin/main`, publish a GitHub Release, or perform a
production shell cutover.

The July 10, 2026 v0.8.0 closure is documented in:

- `docs/ONECODE_V0_8_FINAL_CLOSURE_2026-07-10.md`
- `docs/ONECODE_ICHING_V2_CANONICALIZATION_CLOSURE_2026-07-10.md`
- `docs/ONECODE_TRAINING_BENCHMARK_RULE_SCHEMA_CLOSURE_2026-07-10.md`
- `docs/ONECODE_RUNTIME_BALANCE_MUTATION_EVIDENCE_CLOSURE_2026-07-10.md`
- `docs/ONECODE_MUTATION_EVIDENCE_INTEGRITY_SHELL_V4_CLOSURE_2026-07-10.md`
- `docs/ONECODE_SHELL_V4_PUBLIC_CONTRACT_CLOSURE_2026-07-10.md`
- `docs/ONECODE_CLI_READ_ONLY_COMMAND_SPLIT_CLOSURE_2026-07-10.md`
- `docs/ONECODE_CLI_LOCAL_INTERFACE_COMMAND_SPLIT_CLOSURE_2026-07-10.md`
- `docs/ONECODE_CLI_CONFIGURATION_COMMAND_SPLIT_CLOSURE_2026-07-10.md`

These records preserve the authority chain from yin/yang lines through
trigrams, five-element dynamics, balance, transition, and dispatch. Shell,
contract, evidence, and CLI changes remain subordinate to the kernel rules.

The July 3, 2026 hardening pass is documented in:

- `docs/ONECODE_PROJECT_OPTIMIZATION_REPORT_2026-07-03.md`
- `docs/ONECODE_PROJECT_CLOSURE_HANDOFF_2026-07-03.md`
- `docs/ONECODE_MAINTENANCE_LOG_2026-07-03.md`

These records capture the verification gate, residual risks, skill-boundary
decision, and recommended follow-up maintenance queue.

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
`version: 5` and exposes:

- `status_label`, `severity`, `next_action`, and `compact_message` for concise
  UI/CLI rendering
- `rule_state` for Iching-derived status code, transition action/reason, and
  dispatch decision
- `control_state` for bounded project/runtime/skill/recovery evidence summaries,
  including compact skill-selection hash/reason/count when present
- `balance_state` for descriptive raw-to-balanced mutation counts, bands, and
  before/after status codes when present
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

Versioned public fixtures are installed in `onecode.contracts`. The current
shell projection schema is `version: 5`. Versioned fixtures are installed in
`onecode.contracts`: use `load_shell_projection_v5_schema()` and
`load_shell_projection_v5_cases()` for the current contract. The v4 loaders
remain available for exact legacy fixture validation; they do not imply that
current runtime output is still v4. Runtime decisions remain kernel-owned.

The existing read-only CLI commands `inspect`, `list-runs`, `doctor`,
`math-audit`, and `shell-schema` are registered and dispatched by the focused
`onecode.cli_commands.read_only` adapter. `onecode.cli.build_parser()` and
`onecode.cli.main()` remain the public compatibility entry points. The adapter
does not own write, model, training, verifier, sandbox, Web, or TUI execution.

The local interface commands `serve`, `shell`, `shell-status`, and `tui` are
registered and dispatched by `onecode.cli_commands.local_interfaces`. Web, TUI,
and shell-launcher modules remain lazily imported only after their matching
command is selected, so importing the CLI does not start or initialize local
interface services.

The verifier-policy commands `list-verifier-presets` and
`init-verifier-policy`, together with the nested `config` model commands, are
registered and dispatched by `onecode.cli_commands.configuration`. Path
containment, preset validation, overwrite behavior, model-config permissions,
API-key masking, and model discovery remain owned by the existing verifier and
model-config services. The CLI adapter adds no configuration authority and
does not expose raw API keys in its JSON output.

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
PYTHONPATH=src ONECODE_API_TOKEN=<local-preview-token> python3 -m onecode serve --host 127.0.0.1 --port 19080
```

LibreChat should point its custom endpoint at:

```text
ONECODE_API_BASE_URL=http://localhost:19080/v1
ONECODE_API_TOKEN=<local-preview-token>
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
PYTHONPATH=src python3 -m onecode shell --show-credentials
```

This launches a temporary local MongoDB, the OneCode API, and the LibreChat Web shell. Open:

```text
http://127.0.0.1:14080/c/new
```

The launcher is a foreground process. Keep that terminal open while using the
shell. If the browser reports `ERR_CONNECTION_REFUSED`, check the local service
state with:

```bash
PYTHONPATH=src python3 -m onecode shell-status
```

The launcher can print the local preview login when `--show-credentials` is
set. You can also pass `--email` and `--password` explicitly or create a local
account from the login screen. Use `Ctrl+C` in the launcher terminal to stop all
local services.

Shell tasks run against the selected project workspace; LibreChat runtime
state remains under the temporary shell state directory. Natural-language
inspection requests are routed through the installed Safe-Agent Router and use
the current verified Schema v2 catalog dynamically, so OneCode does not embed a
stale catalog snapshot. The selected scenarios, trusted skill names, bounded
expected outputs, registry summary, and verifier expectations are recorded in
planning evidence. Safe-Agent guidance never grants tool or filesystem
permission.

Workspace-bounded `list_files`, `read_text`, `search_text`, and `git_status`
operations may run automatically. File writes, patches, and argv-only command
execution stop before mutation and return a persisted approval plan. Approve or
reject that exact plan in chat with:

```text
批准计划 <plan-id>
拒绝计划 <plan-id>
```

The approval reply displays bounded action details, including argv or target
paths plus content/diff previews and hashes. Approval atomically claims the
plan, then validates its digest, workspace, age, tools, and parameters before
execution. Replays return a conflict instead of executing twice. Commands run
with a scrubbed environment, and sensitive output is redacted before evidence
is persisted. Rejection records the decision without executing the plan.

Automatic search is literal-only and bounded by depth, file count, per-file
bytes, total bytes, and result count. Git inspection disables repository
fsmonitor/hooks. A model response without an actionable plan returns
`halted/no_actionable_plan`; it is never reported as a successful `noop`.
Missing model credentials return `503 model_configuration_missing`, also never
a successful fallback run. Project status exposes the effective provider,
endpoint source, and model source while keeping API keys redacted.

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

## Absorbed Rule-Evidence Layer

External AI tool rules and repositories, including ultraworkers and claw-code, are learning references and evidence sources, not authority. Project instruction discovery, runtime config diagnostics, and recovery advice are exposed as bounded metadata and folded through Iching status, transition, and dispatch fields.

`project_context` records metadata-only project rules with wood element semantics. `runtime_config` reports optional, redacted, approved effective values with earth element semantics. `skill_context` records read-only skill manifests and selected skill guidance with water element semantics. `recovery_policy` reports advisory recovery actions only with fire element semantics.

By default, doctor and Web project status do not expose raw rule content. Shell consumers should read `shell_projection.control_state`, which is derived primarily from nested kernel summaries, instead of inferring control state from raw evidence.

## Skill Context

OneCode treats skills as bounded rule evidence. Project-local skill manifests may be declared under `.onecode/skills/*.json`; the first implementation reads only manifest metadata such as name, capabilities, risk, mode, and content hash. Registry paths are kept inside the workspace, manifest files are size-bounded, and capability lists are count- and length-bounded. Raw skill bodies are not exposed by default, and skills do not gain execution authority from discovery.

Run execution records deterministic `skill_selection` evidence by matching task tokens against declared capabilities. Token routing handles conservative plural/verb variants, punctuation-separated task text, and phrase capabilities such as `code_review` when all component tokens are present. The selection record is written to result, ledger, manifest, and checkpoint evidence; global WAL entries only keep compact selection hash/reason/count when a skill is actually selected. Selection evidence must not include priority, confidence, score, raw skill text, allowed tools, or verifier expectations.

Run execution validates `skill_selection` immediately after deterministic selection, before trace, result, ledger, manifest, checkpoint, or WAL persistence. Direct checkpoint, ledger, global WAL writers, and full-evidence inspect reads also validate the same compact schema. Unknown fields, selected-count mismatches, boolean or non-integer counts, oversized evidence, invalid hashes, hash/content mismatches, invalid rule metadata, raw body fields, tool lists, verifier expectation text, and authority-like fields are rejected before evidence files are written or trusted by inspect summaries.

Numeric evidence and runtime-budget fields use strict numeric contracts. Boolean values are not accepted as counts, verifier timeouts, sandbox limits, runner budgets, model repair limits, execution guardrail limits, Web query limits, distillation limits, token limits, token ids, or 6-bit status evidence, even though Python normally treats `bool` as a subclass of `int`.

Global WAL readers only treat numeric `global-ledger.<n>.jsonl` archives and the active `global-ledger.jsonl` file as WAL segments. Non-numeric backup or scratch files are ignored, and invalid WAL JSON is reported through the stable `invalid_global_wal_json` reason.

Skill evidence is folded through `IchingKernel.classify_skill_context()` and then through the normal transition and dispatch projections. Execution-capable skill adapters require a separate approved design and must use the existing sandbox, verifier, approval, and path guard boundaries.

## Rule Discovery Protocol

Bug reports are rule-gap probes. When OneCode cannot process a task, the failure is treated as missing rule coverage until proven otherwise. The fix path is to add a failing test, collapse the observed evidence into an existing or new `6-bit status_code`, refine the yin-yang or five-element transition rule, and verify the resulting manifest, ledger, and checkpoint evidence.

If a runtime result cannot yet be mapped to a specific operating rule, the missing mapping must be closed by adding a failing test and extending `IchingKernel.transition()` or its classifiers. That audit output marks the next rule-discovery target; it is not permission to add external control variables.
