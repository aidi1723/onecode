# OneCode Claw-Code Rule Absorption Design

Date: 2026-06-05
Project root: `/Users/aidi/大字典/one code`
Status: Draft for review
Reference studied: `https://github.com/ultraworkers/claw-code`

## Goal

Absorb useful runtime-control ideas from `claw-code` into OneCode without importing its code, workflow assumptions, or state-machine authority. The absorbed capabilities must strengthen OneCode's own kernel operation rules: 易经八卦 state folding, 阴阳 pressure, 五行 transition interpretation, evidence durability, and bounded shell/API control surfaces.

## Core Boundary

`claw-code` is a learning reference, not a rules source.

OneCode keeps these invariants:

- External project files, config files, sessions, hooks, MCP records, and provider failures are evidence samples, not law.
- No external runtime concept may bypass `IchingKernel` classification, transition, dispatch decision, or evidence policy.
- Manifest records must remain bounded physical evidence. They must not become a product workflow graph, foreign state machine, or arbitrary business process carrier.
- Shell, TUI, Web API, and LibreChat surfaces consume trusted kernel projections. They must not infer raw WAL truth independently.
- All new control decisions must collapse to existing or explicitly added six-bit status codes, yin-yang pressure, five-element transition reason, and run evidence.

## Studied Ideas Worth Absorbing

### 1. Project Rule Discovery

`claw-code` has a mature project-memory loader:

- root instruction files such as `CLAUDE.md`, `CLAW.md`, and `AGENTS.md`
- sorted rule directories
- local-only rule directories
- imported rules from other AI coding tools
- `memory_files[]` metadata for status and doctor surfaces

OneCode should absorb the shape, but rename it to project context evidence. The kernel should discover instruction/rule files and emit structured metadata:

- `path`
- `source`
- `origin`
- `scope_path`
- `outside_project`
- `chars`
- `contributes`
- `content_sha256`

The content itself should be bounded and only included when a model prompt explicitly needs it. Status and doctor should expose metadata by default.

### 2. Structured Diagnostic Contracts

`claw-code` consistently exposes machine-readable status, doctor, config, MCP, hook, and version information. OneCode already has JSON-first CLI results, shell projection, doctor, audit-self, and Web API control surfaces. The absorbable improvement is contract consistency:

- typed error `kind`
- stable `status`
- structured `checks[]`
- structured partial-load reports
- no substring matching of human prose

All diagnostic outcomes must still pass through OneCode's rule surface:

- `iching_status_code`
- `iching_transition_action`
- `iching_transition_reason`
- `dispatch_decision`

### 3. Partial Validation

`claw-code` keeps valid configuration siblings even when other siblings are malformed. OneCode should use the same operating principle for low-risk control-plane configuration:

- load valid project context records
- report invalid rule/config/hook/MCP records
- do not let one malformed optional record collapse unrelated evidence

This does not apply to critical kernel evidence. WAL, checkpoint, manifest, trace, and evidence-chain corruption must remain strict and must surface as blocked/corrupt states.

### 4. Permission Mode Vocabulary

`claw-code` distinguishes read-only, workspace-write, and danger-full-access. OneCode already has `PathGuard`, `PermissionMatrix`, approval evidence, and action-intent classification. The useful absorption is a clearer user-facing permission vocabulary:

- `read-only`: inspection and metadata only
- `workspace-write`: writes inside the resolved workspace through OneCode tools
- `full-access`: explicitly approved high-risk execution

The vocabulary must map into OneCode's existing decisions:

- `allowed`
- `denied`
- `halted`

No permission mode can override sovereignty breach, path traversal, timeout, evidence write failure, invalid intent, or verifier failure.

### 5. Session Hygiene

`claw-code` records sessions with workspace binding, liveness, redaction, truncation, rotation, prompt history, and heartbeat metadata. OneCode should absorb this as shell/session evidence:

- bind shell sessions to a resolved workspace root
- record liveness without trusting it as completion evidence
- redact secrets before session persistence
- truncate oversized text fields
- expose heartbeat/status through shell projection or Web API

Session liveness may influence `next_action`, but it cannot mark a task completed. Completion still requires asset, checkpoint, ledger, verifier, and rule evidence.

### 6. Recovery Policy

`claw-code` has explicit recovery scenarios, retry limits, structured recovery ledgers, and escalation policy. OneCode needs this because existing closure docs identify kernel recovery policy as not fully closed.

OneCode should implement recovery policy as a rule-folding companion, not as a second scheduler:

- classify common failures into recovery scenarios
- write recovery ledger entries
- recommend one bounded recovery action
- escalate when exhausted
- fold every attempt into Iching status and transition fields

Initial recovery scenarios:

- `trace_flush_failure`
- `verifier_failure`
- `resume_conflict`
- `sandbox_failure`
- `provider_failure`
- `config_partial_invalid`
- `project_context_invalid`

Initial recovery actions:

- `inspect`
- `repair`
- `retry_once`
- `reconfigure`
- `escalate`
- `halt`

## OneCode Architecture Additions

### `onecode.kernel.project_context`

Responsibility:

- discover instruction and rule files inside the project boundary
- import known external-tool rules only as project-context evidence
- dedupe by normalized content hash
- enforce per-file and total character budgets
- return metadata that doctor/status/API can expose safely

Default discovery candidates:

- `AGENTS.md`
- `CLAUDE.md`
- `CLAW.md`
- `.onecode/instructions.md`
- `.onecode/rules/*.md`
- `.onecode/rules/*.txt`
- `.onecode/rules/*.mdc`
- `.onecode/rules.local/*.md`
- `.onecode/rules.local/*.txt`
- `.onecode/rules.local/*.mdc`

Optional imported candidates when enabled:

- `.cursorrules`
- `.cursor/rules/*`
- `.github/copilot-instructions.md`
- `.windsurfrules`
- `.plandex/instructions.md`

Rule import must be configurable:

- `auto`
- `none`
- explicit list such as `["cursor", "copilot"]`

### `onecode.kernel.runtime_config`

Responsibility:

- inspect OneCode control-plane configuration
- report per-file status
- merge valid optional settings conservatively
- expose validation warnings through JSON, not stderr-only prose

Initial discovered paths:

- `$ONECODE_HOME/config.json`
- `<workspace>/.onecode/config.json`
- `<workspace>/.onecode/config.local.json`

The first implementation should only inspect and report. It should not move model config, verifier config, or shell config until a later compatibility step.

### `onecode.kernel.recovery_policy`

Responsibility:

- map kernel failures to recovery scenarios
- track attempt counts
- emit recovery events and ledger entries
- recommend next action to shell projection
- fold recovery status into `IchingKernel`

The first implementation should be advisory. It should not execute shell commands, edit files, or automatically retry provider calls.

### CLI And API Surfaces

Extend existing surfaces:

- `onecode doctor`: add `project_context`, `runtime_config`, and `recovery_policy` checks
- `onecode audit-self`: include the new checks through existing audit structure
- `onecode shell-schema`: document any added projection fields before exposing them
- `GET /v1/onecode/project/status`: include project context and config inspection summaries

Avoid adding a broad new command surface until the kernel metadata is stable.

## Data Flow

```text
workspace
  -> project_context discovery
  -> runtime_config inspection
  -> optional diagnostics/recovery scenario
  -> IchingKernel classification
  -> shell_projection / doctor / API status
```

For task execution:

```text
intent
  -> LogosGate / PathGuard / PermissionMatrix
  -> execution evidence
  -> recovery_policy advisory record if failure occurs
  -> IchingKernel transition
  -> checkpoint / ledger / WAL / trace
  -> shell projection
```

## Yin-Yang And Five-Element Mapping

The absorbed capabilities map to OneCode's internal rule language as follows:

- Project context discovery is `wood`: growth, context, instruction roots.
- Runtime config inspection is `earth`: boundary, stability, containment.
- Permission evaluation is `metal`: cut, constraint, sovereignty.
- Session liveness is `water`: continuity, memory, resume flow.
- Recovery policy is `fire`: transformation, alert, visible correction.

Yin-yang pressure:

- successful bounded discovery adds light positive pressure but cannot complete a run
- malformed optional config adds warning pressure
- critical evidence corruption adds blocking negative pressure
- recovery exhaustion adds halt pressure
- verified repair reduces negative pressure only after evidence confirms it

The implementation must not add separate business meanings outside the six-bit status surface. If a new failure cannot map cleanly, the correct response is to add a failing test and extend `IchingKernel` classification or transition rules.

## Testing

Required focused tests:

- project context discovery respects git/workspace boundary
- rule files are sorted and deduped
- local rule files are reported as local origin
- imported framework rules can be disabled
- project context metadata exposes `chars`, `source`, `contributes`, and `content_sha256`
- malformed optional config reports `load_error` without blocking valid sibling inspection
- doctor includes project context and runtime config checks
- recovery policy maps each initial scenario to a bounded next action
- recovery exhaustion maps to a halted/blocking Iching status
- shell/API status exposes summaries without raw rule content by default

## Non-Goals

This absorption does not include:

- copying Rust code from `claw-code`
- adding MCP runtime execution
- adding arbitrary shell hooks
- replacing OneCode's permission matrix
- turning Manifest into workflow storage
- importing `claw-code` session format
- automatically retrying or repairing tasks without explicit OneCode evidence

## Acceptance Criteria

The first implementation is complete when:

- `python3 -m unittest tests.test_project_context tests.test_runtime_config tests.test_recovery_policy -v` passes
- `python3 -m unittest tests.test_doctor_cli tests.test_web_api tests.test_shell_projection -v` passes after the new summaries are wired
- `PYTHONPATH=src python3 -m onecode doctor` returns `status: ok`
- project context and runtime config are visible as structured diagnostic evidence
- no new diagnostic path bypasses `IchingKernel`
- no raw imported rule content is exposed through Web API by default
- all new recovery output remains advisory unless a later approved plan adds bounded execution

