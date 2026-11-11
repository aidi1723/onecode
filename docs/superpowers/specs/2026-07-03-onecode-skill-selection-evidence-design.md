# OneCode Skill Selection Evidence Design

Date: 2026-07-03
Status: Approved continuation
Scope: Phase 1.5 read-only skill selection evidence

## Objective

Extend the read-only `skill_context` layer so a run can record which declared
skills were relevant to the task. This is evidence only. It must not grant
execution authority, tool access, approval bypass, path access, or scheduling
priority.

## Boundary

Skills remain external facts, not law. Selection evidence must fold through the
existing skill-context status and Iching transition fields, then be written into
run evidence as bounded metadata. The runner still decides actions through
`LogosGate`, `PathGuard`, verifier policy, sandbox policy, and
`IchingKernel.transition()`.

Disallowed fields:

- `skill_priority`
- `skill_confidence`
- `skill_score`
- direct skill-to-action dispatch
- raw skill description, allowed tool list, verifier expectations, or body text

## Selection Contract

`select_skill_evidence(workspace, task)` returns a compact dictionary:

- `status`: inherited from skill context
- `selection_reason`: deterministic reason such as `capability_match`,
  `no_matching_capability`, or `skill_context_unavailable`
- `selected_skills`: bounded list of skill summaries containing only `name`,
  `mode`, `risk`, `matched_capabilities`, and `content_sha256`
- `selected_count`
- `selection_sha256`
- `skill_context_summary`
- `iching_status_code`, `iching_transition_action`,
  `iching_transition_reason`, and `dispatch_decision`

Matching is deterministic:

1. tokenize the task into safe lowercase tokens
2. match tokens against manifest capabilities
3. keep only skills with at least one matched capability
4. order `method_only` before `reference_only`, then by safe skill name
5. cap the selected list

## Evidence Integration

`run_task()` attaches `skill_selection` to:

- returned result
- ledger
- manifest
- checkpoint records

The checkpoint payload does not receive raw task text or raw skill manifest
content. WAL compaction may include the compact selection evidence when it is
already present in the result, but must not expand raw skill content.

## Tests

Use TDD for:

- deterministic selection prefers `method_only` and omits raw manifest fields
- no-match selection records `no_matching_capability`
- `run_task()` persists `skill_selection` in result, ledger, manifest, and
  checkpoint evidence
- invalid skill context still records bounded warning evidence
