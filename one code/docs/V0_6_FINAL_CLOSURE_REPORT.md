# OneCode v0.6 Final Closure Report

## Closure Point

- Branch: `main`
- Kernel closure commit: `01954ce fix: harden audit-reported kernel edges`
- Milestone tag: `onecode-v0.6-rule-closure`
- Tag target: `01954ce`
- Feature branch merged by fast-forward: `feature/onecode-phase2-rule-execution`

The tag marks the v0.6 kernel rule-closure code baseline. This report records the final project handoff state after that baseline was merged into `main`.

## Verification Evidence

The merged `main` branch was verified after the fast-forward merge and tag creation:

- `bash scripts/verify.sh`: `Ran 234 tests ... OK`
- `doctor`: `status: ok`
- `onecode audit-self`: `status: ok`
- `audit-self` internal unittest: `Ran 234 tests ... OK`

Doctor smoke cases remained aligned with the rule surface:

- completed write: `GEN/QIAN = 39`, `cooldown + continue`
- resume skip: status code `35`, `cooldown + continue`
- sovereignty breach: `LI/KUN = 48`, `halt + stop`
- HTTP timeout: `KAN/ZHEN = 17`, `checkpoint + stop`

## Rule Closure Summary

v0.6 closes the control chain around one 6-bit state tensor:

```text
Taiyi -> Liangyi -> Sixiang -> Bagua -> 64-hexagram
```

The runtime now exposes and tests these layers:

- bit-level yin-yang polarity and `polarity_index`
- four-symbol windows and overflow balancing
- trigram projection into inner asset and outer environment planes
- 64-hexagram transition rules
- five-element relation and modulation
- polarity-aware global entropy regulation
- execution bandwidth admission
- parallel status aggregation
- patch resume and multi-hash evidence

External facts remain evidence, not law. Runtime facts are collapsed into the state tensor and interpreted by `IchingKernel`, `LogosGate`, `PathGuard`, checkpoint, manifest, ledger, and execution-trace evidence.

## Closed Blocking Items

Current conclusion: no known open P0/P1 kernel blockers remain.

Closed issues:

- Full-success low entropy was previously treated as rollback. It is now `accept_positive_polarity`; macro transition handles cooldown.
- `KUN/KUN = 0` was previously a dead discovery branch. It now maps to `discover + stop`.
- `audit-self` failure previously risked a misleading continue dispatch. It now maps to `LI/KUN` halt semantics.
- `LogosGate` executor reuse could be poisoned by a timed-out worker. A timeout now resets the executor before later actions.
- `PathGuard` previously checked `.git` and `.github` only at the root path segment. It now rejects those control surfaces in any path segment.
- `verify.sh` previously depended on shell venv activation or system `python3`. It now honors `PYTHON`, `VIRTUAL_ENV`, and project `.venv` before falling back.
- Patch evidence was not surfaced at the manifest checkpoint index. Patch records now include `patch_evidence` with pre/post and block hashes.
- Negative entropy rollback could be confused with HTTP timeout at the status-code layer. Evidence now includes `global_entropy_reason=entropy_negative_polarity_rollback`.

## Non-Blocking Residuals

These are intentional or out of scope for v0.6:

- `bash_execution` and `execute_pytest` remain recognized but denied intent types. They are auditable placeholders, not executable capabilities.
- `ledger.json` is the latest user-facing result snapshot. `ledger.jsonl` is the append-only run result history.
- Negative entropy rollback still converges through status code `17`; the semantic difference from HTTP timeout is carried by `global_entropy_reason`.
- Repository-root untracked files outside `one code/` remain untouched and are not part of this kernel closure.

## Handoff State

The v0.6 rule-closure stage is complete and suitable as the next development baseline.

Recommended next phase:

- keep `onecode-v0.6-rule-closure` as the stable kernel milestone
- start any v0.7 work from `main`
- keep future UI, gateway, deployment, and root-level repository files separate from kernel-rule commits
- preserve the current audit discipline: failing test first, rule-surface fix, full verify, then audit-self
