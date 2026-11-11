# OneCode Skill Selection Schema Hardening Design

Date: 2026-07-03
Status: Approved continuation
Scope: Skill selection evidence schema validation

## Objective

Harden `skill_selection` as a bounded evidence contract before it enters
checkpoint, manifest, ledger, or WAL records.

## Boundary

This does not add skill execution. Skill selection remains read-only evidence.
The runner, `LogosGate`, `PathGuard`, verifier policy, sandbox policy, and
`IchingKernel.transition()` remain the only execution-control boundaries.

## Contract

Checkpoint writes may include `skill_selection`, but the object must be
validated before persistence:

- only known top-level keys are allowed
- selected skill entries may contain only `name`, `mode`, `risk`,
  `matched_capabilities`, and `content_sha256`
- `selection_sha256` and `content_sha256` must be 64-character lowercase hex
- `selected_count` must match the selected list length
- selected list and matched capabilities are bounded
- total serialized evidence is bounded

Forbidden fields include:

- `description`
- `allowed_tools`
- `verifier_expectations`
- `skill_score`
- `skill_priority`
- `skill_confidence`
- raw body or instruction text

## Failure Mode

Invalid `skill_selection` evidence should fail before checkpoint files are
written. This is schema failure, not runtime failure, and should raise a
specific `ValueError` for tests and callers.

## Verification

Use focused regression tests in `tests/test_checkpoint.py` for invalid fields,
oversized evidence, selected count mismatch, and valid compact evidence.
