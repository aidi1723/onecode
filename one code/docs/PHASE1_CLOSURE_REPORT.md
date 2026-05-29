# OneCode Phase 1 Closure Report

## Status

Phase 1 is closed when these local gates pass:

- `onecode audit-self`
- `bash scripts/verify.sh`

Latest verified status:

- Self audit: `status: ok`
- Test suite: `199 tests OK`
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

## Security Notes

- Physical writes are guarded by `LogosGate.preflight()` and `PathGuard`.
- Model API keys are read from environment or explicit CLI arguments.
- API keys and Authorization headers must not be persisted to ledger, manifest, or checkpoint evidence.
- `tests.test_model_loop.ModelLoopTests.test_model_api_key_never_persists_to_run_evidence` locks this boundary.

## Phase 2 Backlog

These items are intentionally not part of Phase 1 closure because they change behavior or architecture shape:

- Split `model_provider.py` into a provider registry plus transport-specific modules.
- Split `runner.py` into orchestration and action dispatch modules.
- Add typed public interfaces and evaluate `mypy` for the kernel modules.
- Add CI once the repository boundary is finalized.
- Add concise public API documentation for external integration.
- Add bounded model-call retry rules through the Iching transition surface.
- Add structured logging if evidence files are not enough for operational debugging.
- Add optional API key shape validation without persisting secrets.
