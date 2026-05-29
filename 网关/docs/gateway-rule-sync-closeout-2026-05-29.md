# Gateway Rule Sync Closeout

Date: 2026-05-29
Branch: `feature/gateway-iching-rule-sync`

## Scope

This closeout covers the gateway product line under `网关/`.

It does not modify the OneCode kernel and does not create a OneCode-specific gateway. The gateway remains a Claude Code / Codex / OpenAI-compatible / Anthropic-compatible control plane.

## Completed Work

### Phase 1: Gateway Rule Adapter

Added a pure `gateway_rule_adapter` that maps gateway evidence into a 6-bit rule envelope:

- Liangyi bits
- Sixiang windows
- outer / inner trigrams
- 64-state `gateway_status_code`
- polarity index
- five-element relation
- transition action / reason
- dispatch decision

The envelope is attached to:

- chat completion metadata
- Anthropic messages metadata
- OpenAI Responses metadata
- resolve plan metadata
- preflight-tool response
- Build Mode compact results

This is evidence-only. It does not change tool filtering, dispatch, request forwarding, model calls, or execution behavior.

### Phase 2: State Persistence

Build Mode state files now persist rule evidence at two levels:

- per-result `results[*].gateway_rule`
- top-level aggregated `gateway_rule`

Expert handoff state also persists top-level `gateway_rule`.

This allows resumed sessions and external audits to read the global rule surface directly from state files without recomputing it from raw results.

### Phase 3: Caveman Internal Compression

Added a pure `gateway_compression_adapter` for internal-only Caveman-style compression.

The compression layer:

- writes `compressed_summary`
- writes `compression_rule`
- preserves raw `repair_card`
- preserves raw `repo_card`
- preserves raw `results`
- preserves paths, hashes, and function-like symbols

This is not a user-facing voice. It is an internal Yin/Metal context pruning layer for state size control.

## Design Position

The gateway now treats the I Ching rule model as a reliability-control mapping:

- Yin/Yang: work vs constraint
- Four Symbols: local operational quadrant
- Eight Trigrams: functional control plane
- 64 Hexagrams: global runtime topology
- Five Elements: cross-plane relation and modulation
- Caveman compression: internal context pruning, not product voice

The product remains positioned as an agent governance and task reliability gateway, not a coding assistant.

## Verification

Fresh verification run on this branch:

```text
python3 -m unittest tests.test_gateway_compression_adapter tests.test_gateway_rule_adapter tests.test_gateway_core tests.test_gateway_plan tests.test_minimal_gateway_mvp -v
Ran 51 tests ... OK

/private/tmp/gateway-route-test-venv-39/bin/python -m unittest tests.test_gateway_server_routes -v
Ran 10 tests ... OK

python3 -m unittest discover -s tests -p 'test_gateway*.py' -v
Ran 156 tests ... OK (skipped=10)

python3 -m unittest discover -s tests -p 'test_build_mode*.py' -v
Ran 124 tests ... OK

git diff --check
OK
```

The default Python environment skips 10 route tests when FastAPI TestClient is unavailable. A Python 3.9 temporary validation environment with `requirements-gateway.txt` installed ran those route tests directly and passed.

Additional closeout hardening:

- `gateway_rule_adapter` avoids Python 3.10+ `int.bit_count()` so the rule evidence layer runs on Python 3.9 route-test environments.
- A focused compatibility test locks this requirement.

## Remaining Non-Blocking Items

- FastAPI TestClient route tests are skipped in dependency-light local environments, but pass when `requirements-gateway.txt` is installed.
- Upper-level repository files outside `网关/` remain untracked and unrelated to this gateway closeout.
- This branch is not merged into `main` yet.

## Closeout Recommendation

This phase is ready to commit on `feature/gateway-iching-rule-sync`.

Recommended next action:

1. Commit this gateway phase.
2. Keep the branch for review.
3. Merge after a final review of the diff boundary.
