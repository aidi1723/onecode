# OneCode Phase 1 Closure Report

## Status

Phase 1 is closed when these local gates pass:

- `onecode audit-self`
- `bash scripts/verify.sh`

Latest verified status:

- Self audit: `status: ok`
- Test suite: `204 tests OK`
- Doctor: `status: ok`

## Scope Closed

- Core kernel and Iching rule projection
- LogosGate and PathGuard sovereignty boundary
- Stateful resumption and ready-asset skip
- Guarded `write_text` and `patch_text`
- Execution plan engine
- Model plan loop through the kernel control plane
- OpenAI-compatible and domestic provider configuration
- Conversational TUI shell
- Self-audit command covering shell, model matrix, compile, unittest, and doctor
- Latest-result `ledger.json` plus append-only `ledger.jsonl` run history
- Immediate execution-plan circuit break for sovereignty and permission failures
- Multi-attempt model repair loop with detailed failure prompts

## Security Notes

- Physical writes are guarded by `LogosGate.preflight()` and `PathGuard`.
- PathGuard blocks workspace escapes, `.git`, root secrets/config, GitHub automation, and executable root configuration writes.
- Model API keys are read from environment or explicit CLI arguments.
- API keys and Authorization headers must not be persisted to ledger, manifest, or checkpoint evidence.
- `tests.test_model_loop.ModelLoopTests.test_model_api_key_never_persists_to_run_evidence` locks this boundary.

## Review Disposition

- Accepted and fixed: ledger evidence now has append-only `ledger.jsonl`; safety failures break execution immediately; `max_repair_attempts` now performs multiple patch-only repair attempts; repair prompts include step/tool failure details; PathGuard protects CI and executable configuration surfaces.
- Clarified: `bash_execution` and `execute_pytest` remain recognized intent types but are denied in Phase 1. They are not advertised as executable tools.
- Preserved by design: `checkpoint` still dispatches to `stop` because Phase 1 checkpoint means "end this run after preserving recovery seed", not "pause and continue in the same run".

## Phase 2 Backlog

These items are intentionally not part of Phase 1 closure because they change behavior or architecture shape:

- Expand `IchingKernel.transition()` coverage so yin excess, generation, control, and neutral element relations produce differentiated scheduling decisions.
- Expand `element_dynamics()` beyond the current minimal modulation set.
- Add dependency-layered parallel execution for independent plan steps.
- Add `patch_text` resume recognition and richer conflict audit records for SHA mismatches.
- Revisit `checkpoint` dispatch if Phase 2 introduces a true pause/resume-within-run state.
- Reuse or lifecycle-manage `LogosGate` executor resources if action volume grows.
- Split `model_provider.py` into a provider registry plus transport-specific modules.
- Split `runner.py` into orchestration and action dispatch modules.
- Add typed public interfaces and evaluate `mypy` for the kernel modules.
- Add CI once the repository boundary is finalized.
- Add concise public API documentation for external integration.
- Add bounded model-call retry rules through the Iching transition surface.
- Add structured logging if evidence files are not enough for operational debugging.
- Add optional API key shape validation without persisting secrets.
