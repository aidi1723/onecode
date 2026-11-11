# OneCode Skill Rule Kernel Integration Design

Date: 2026-07-03
Status: Draft for user review
Scope: Skill intake, rule evidence folding, kernel authority boundaries

## Objective

Integrate skills into OneCode as bounded evidence sources while preserving the original rule closure principle:

```text
External facts are evidence, not law.
```

Skills may describe capabilities, recommended workflows, execution boundaries, verification expectations, and failure modes. They must not bypass `IchingKernel`, `LogosGate`, `PathGuard`, verifier policy, sandbox policy, or evidence writing. Every skill-driven decision must collapse into the existing OneCode rule surface:

- `6-bit status_code`
- yin-yang pressure
- four-symbol windows
- trigram and five-element dynamics
- `IchingKernel.transition()`
- dispatch decision
- manifest, ledger, trace, and WAL evidence

## Current Baseline

OneCode already has three related evidence layers:

- `project_context` reads project rule files as metadata-only wood element evidence.
- `runtime_config` reads approved local config keys as earth element evidence.
- `recovery_policy` exposes advisory recovery status as fire element evidence.

The next missing layer is `skill_context`: a bounded view of available skills and selected skill guidance.

## Non-Goals

- Do not let skill instructions become direct execution authority.
- Do not import arbitrary remote skills at runtime.
- Do not add unbounded web browsing, package installation, or account actions.
- Do not add parallel control variables such as confidence, priority, mood, or score as runtime authority.
- Do not move transition ownership out of `IchingKernel`.
- Do not make skills mutate project files directly; all mutations still flow through existing guarded runners and path checks.

## Architecture

The skill integration should add a new kernel-side layer:

```text
Skill sources
  -> skill registry inspection
  -> skill selection evidence
  -> skill_context summary
  -> IchingKernel classification
  -> execution/verifier dispatch
  -> manifest/ledger/trace/WAL evidence
```

The layer is read-only by default. Skill execution belongs to a future approved phase and must pass the same approval, sandbox, verifier, and path boundaries as any other tool action.

## Skill Registry Model

Create a local skill registry abstraction that can inspect declared skills from controlled sources:

- built-in OneCode skill records
- project-local `.onecode/skills/*.json`
- optional user-home OneCode skill records when enabled by config

The first implementation should support a compact JSON manifest:

```json
{
  "name": "code-test-regression",
  "version": "1",
  "source": "project",
  "description": "Guides regression test creation.",
  "capabilities": ["test", "verification"],
  "risk": "low",
  "mode": "method_only",
  "allowed_tools": [],
  "verifier_expectations": ["focused_test", "full_relevant_suite"]
}
```

Manifest constraints:

- `name` must be a safe identifier.
- `mode` starts as `method_only` or `reference_only`.
- `risk` starts as `low`, `medium`, or `high`.
- `allowed_tools` is descriptive evidence only in phase 1.
- registry directories must not escape the workspace through symlinks.
- manifest files, field lengths, and capability counts must be bounded before raw content is trusted.
- invalid manifests are recorded as evidence and do not load.

## Skill Evidence Shape

`discover_skill_context(workspace)` should return a bounded summary:

```json
{
  "status": "ok",
  "skills": [
    {
      "name": "code-test-regression",
      "source": "project",
      "risk": "low",
      "mode": "method_only",
      "capability_count": 2,
      "content_sha256": "..."
    }
  ],
  "invalid_skills": [],
  "summary": {
    "skill_count": 1,
    "invalid_count": 0,
    "method_only_count": 1,
    "reference_only_count": 0,
    "element": "water",
    "yin_yang_pressure": "stable"
  },
  "iching_status_code": 17,
  "iching_transition_action": "checkpoint",
  "iching_transition_reason": "network_water_preserves_resume_seed",
  "dispatch_decision": "stop"
}
```

The raw skill body should not be exposed by default. Reports should expose names, sources, content hashes, capabilities, risk, and mode.

## Rule Mapping

Skill evidence should map to kernel states through an explicit classifier:

```python
IchingKernel.classify_skill_context(status: str, reason: str | None) -> int
```

Initial mapping:

- `ok` with valid method-only skills -> water over thunder or another recovery/flow state
- `warning` for invalid or duplicate manifests -> water over mountain or mountain over water
- `blocked` for unsafe or untrusted executable skill requests -> fire over earth
- `missing` when no skills are available -> earth over earth, treated as rule discovery only if a task requires skills

The exact status codes must be selected in tests and documented with the reason. The classifier is the only place where skill-context status becomes a runtime control input.

## Skill Selection

Skill selection should be evidence-driven and deterministic:

1. Normalize the user task into capability hints.
2. Match hints to registry skills by declared capabilities and safe name.
3. Prefer `method_only` over `reference_only` when both match.
4. Reject or block executable skills until a separate approved execution design exists.
5. Record selected skill names and rejected candidates as evidence.

Selection output should remain advisory until an execution plan explicitly consumes it.

## Runtime Integration

### Doctor

Add a `skill_context` check to doctor after project context and runtime config. It should verify:

- registry paths are bounded
- valid manifests parse
- invalid manifests are reported without crashing
- classification collapses through `IchingKernel`

### Project Status

Expose `skill_context` summary in Web project status, without raw instruction bodies.

### Task Execution

Before model-driven or plan-driven execution, selected skill evidence may be attached to the run payload:

```json
{
  "selected_skills": ["code-test-regression"],
  "skill_context_status": "ok",
  "skill_context_hash": "..."
}
```

The runner must continue to use existing action validation, path guarding, verifier policy, sandbox checks, and evidence writes.

## Formula and Kernel Boundary

Skill integration should improve the formula surface by adding one classification path, not a separate scheduler.

Allowed kernel additions:

- `classify_skill_context()`
- rule-layer entries for `skill_context`
- cross-cutting profile fields that identify skill evidence as absorbed external evidence

Disallowed additions:

- `skill_priority`
- `skill_confidence`
- `skill_score` as execution authority
- direct skill-to-action dispatch without `IchingKernel.transition()`

## Failure Classification

Skill failures are rule-gap probes:

- invalid manifest -> malformed external evidence
- missing required skill -> missing capability evidence
- unsafe requested skill -> sovereignty boundary
- unsupported tool need -> rule gap requiring discovery
- verifier mismatch -> verifier policy conflict

Each failure must have a focused failing test before implementation.

## Testing Strategy

Use TDD for each behavior:

- manifest safe-name validation
- valid registry discovery
- invalid manifest reporting
- path traversal rejection for skill files
- duplicate skill handling
- `IchingKernel.classify_skill_context()` mappings
- doctor includes skill context
- Web project status exposes summary only
- selected skill evidence is written into run payload without raw body

Verification commands:

```bash
.venv/bin/python -m unittest tests.test_skill_context tests.test_iching_kernel tests.test_doctor_cli tests.test_web_api -v
bash scripts/verify.sh
git diff --check -- src tests docs README.md
```

## Phased Plan

### Phase 1: Read-Only Skill Context

Implement manifest parsing, bounded discovery, redacted summary, invalid reporting, and kernel classification. No skill execution.

### Phase 2: Selection Evidence

Add deterministic skill selection for task planning. Record selected and rejected skills in run evidence. Still no direct skill execution.

### Phase 3: Controlled Execution Boundary

Only after phases 1 and 2 are stable, design executable skill adapters. They must use the existing sandbox, verifier, approval, and path guard boundaries.

### Phase 4: Formula Refinement

Refine the skill-context classifier and cross-cutting profile fields after real failure cases produce tests. Formula changes must remain table-driven and test-backed.

## Closure Criteria

This design is ready for implementation when:

- the user approves this spec
- an implementation plan lists exact files and tests
- the first implementation phase is limited to read-only skill context
- every new runtime decision has a failing test first
- full verification remains green
