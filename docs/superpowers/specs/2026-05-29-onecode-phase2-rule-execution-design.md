# OneCode Phase 2 Rule Execution Design

## Goal

Phase 2 strengthens the kernel-owned execution loop without expanding unsafe tool permissions. The work covers richer Iching transitions, five-element modulation, patch resumption, dependency-layered parallel execution, and reusable LogosGate executor lifecycle.

## Scope

- `IchingKernel` remains pure state calculation with no file or network side effects.
- `checkpoint` keeps Phase 1 semantics: preserve recovery evidence and stop the current run.
- `bash_execution` and `execute_pytest` remain denied intent types.
- `run_task()` keeps ordered asset semantics. Parallelism is limited to the execution-plan layer.

## Design

The rule engine will expose more differentiated actions from existing evidence: yin excess activates, generation accelerates, hard control still halts, water-over-fire quenches, metal-over-wood prunes, wood-over-fire fuels, and earth-over-water dams. These actions remain ordinary transition labels consumed by the existing dispatch boundary.

Patch resumption will reuse checkpoint evidence for completed `patch_text` actions. A prior patch can become ready if its target path is inside the workspace and the current file content already contains the checkpointed replacement content. This avoids applying the same patch twice after an interrupted mixed plan.

Execution plans will be scheduled in dependency layers. Steps in the same layer can run concurrently with `ThreadPoolExecutor`, while layer ordering preserves dependency semantics. Safety failures stop later scheduling immediately.

`LogosGate` will own a reusable single-worker executor and expose `close()` / context-manager cleanup. This keeps timeout behavior but avoids creating a new executor for every bounded action.

## Verification

Each behavior gets a failing unittest before implementation. Full acceptance is `env -u PYTHONPATH "PATH=$PWD/.venv/bin:$PATH" bash scripts/verify.sh` plus `onecode audit-self`.
