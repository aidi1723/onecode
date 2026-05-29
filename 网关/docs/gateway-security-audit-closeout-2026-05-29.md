# Gateway Security Audit Closeout

Date: 2026-05-29
Branch: `feature/gateway-iching-rule-sync`
Closeout commit: `f458cd9 fix: harden gateway audit edges`

## Scope

This report closes the gateway security audit pass for the `网关/` product line.

The work applies the OneCode / 一字诀 rule model to the standalone agent governance gateway used by Claude Code, Codex, OpenAI-compatible clients, and Anthropic-compatible clients. It does not create a OneCode-specific gateway and does not modify the OneCode kernel.

## Executive Conclusion

The current gateway phase is ready to close.

The audit found several practical runtime risks around authentication defaults, HTTP `/run` execution boundaries, route coverage, JSON request handling, and an orphan benchmark test module. These have been fixed and verified with a full local regression run.

The product position remains:

- deterministic agent governance layer
- controllable task execution gateway
- evidence and compliance surface
- rule-mapped reliability engine using yin-yang, four-symbol, trigram, hexagram, and five-element metadata

It is not positioned as another coding assistant.

## Audit Findings Resolved

### P0 / High: Gateway Auth Fail-Open

Previous behavior:

- Missing `ONEWORD_GATEWAY_TOKEN` caused protected gateway requests to pass.
- A production env omission would expose protected endpoints.

Final behavior:

- Gateway auth now fails closed when no token is configured.
- Token checks use `hmac.compare_digest`.
- Client `Authorization` is still never forwarded upstream as the upstream model key.

Evidence:

- `tests.test_gateway_auth.GatewayAuthTest.test_gateway_request_fails_closed_without_configured_token`
- `tests.test_gateway_auth.GatewayAuthTest.test_gateway_request_uses_constant_time_token_compare`

### P0 / High: HTTP `/v1/yizijue/run` Execution Boundary

Previous behavior:

- HTTP `/run` could accept arbitrary `verification_command` lists.
- `use_docker` was not a hard default.
- Missing `ONEWORD_WORKSPACE_ROOT` left workspace boundaries implicit.

Final behavior:

- HTTP `/run` requires `ONEWORD_WORKSPACE_ROOT` by default.
- HTTP `/run` rejects unapproved verification commands by default.
- Allowed command surface is intentionally narrow: `pytest`, `py.test`, `python -m unittest`, `python -m pytest`, and Python 3 equivalents.
- Local CLI keeps a trusted developer escape hatch by explicitly opting out of HTTP hardening flags.

Evidence:

- `tests.test_gateway_server_import.GatewayServerImportTest.test_run_endpoint_rejects_when_workspace_root_is_not_configured`
- `tests.test_gateway_server_import.GatewayServerImportTest.test_run_endpoint_rejects_unapproved_verification_command`
- CLI regression remains covered by `tests.test_agent_cli`.

### P1 / Medium: Control Plane Route Auth Gaps

Previous behavior:

- `/v1/yizijue/resolve` was not protected.
- `/v1/yizijue/preflight-tool` required auth only when explicitly enabled.

Final behavior:

- `/v1/yizijue/resolve` requires gateway auth.
- `/v1/yizijue/preflight-tool` requires gateway auth by default.
- `ONEWORD_PROTECT_PREFLIGHT=0|false|no|off` remains available only as an explicit local/test opt-out.

Evidence:

- `tests.test_gateway_server_routes.GatewayServerRoutesTest.test_resolve_route_requires_gateway_auth`
- `tests.test_gateway_server_routes.GatewayServerRoutesTest.test_preflight_tool_route_requires_gateway_auth_by_default`
- `tests.test_gateway_auth.GatewayAuthTest.test_preflight_auth_is_required_by_default`

### P1 / Medium: Missing Cluster A/B Script

Previous behavior:

- `tests/test_cluster_state_sync_ab.py` imported `scripts.cluster_state_sync_ab`, but the module was missing after directory consolidation.
- This made the suite fail even though the issue was not core gateway logic.

Final behavior:

- Restored `scripts/cluster_state_sync_ab.py`.
- The module covers model probing, tool-call extraction, bare tool execution safety checks, and workspace finding collection.
- Dangerous bare shell cases such as `kill -9`, port probes, and `rm -rf` are blocked in this benchmark harness.

Evidence:

- `tests.test_cluster_state_sync_ab.ClusterStateSyncABTest`

### P2 / Medium: Invalid JSON Request Handling

Previous behavior:

- Several HTTP handlers called `await request.json()` directly.
- Malformed request bodies could bubble into a server exception path.

Final behavior:

- JSON body parsing is centralized through `_request_json_payload`.
- Malformed JSON returns stable `400 invalid_json`.
- Non-object JSON bodies return stable `400 invalid_json`.

Evidence:

- `tests.test_gateway_server_import.GatewayServerImportTest.test_request_json_payload_returns_stable_error_for_invalid_body`
- Route-level FastAPI coverage exists when `fastapi.testclient` is installed.

### P2 / Documentation: Stream and Version Narrative

Previous behavior:

- README still claimed `stream=true` was explicitly rejected.
- README version language mixed older V0.3/V0.4 descriptions with Build Mode V2 wording.

Final behavior:

- README now states current baseline as `Build Mode V2 + Kernel Runtime Policy`.
- README now states streaming support for OpenAI Chat Completions and Anthropic Messages, including stream chunk inspection and structured SSE evidence notice behavior.
- README now documents `ONEWORD_GATEWAY_TOKEN` and `ONEWORD_WORKSPACE_ROOT` as required safety configuration for protected/runtime endpoints.

## Verification Baseline

Fresh verification after the audit fixes:

```text
python3 -m unittest discover -v
Ran 566 tests in 33.786s
OK (skipped=13)

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import py_compile
from pathlib import Path
for path in Path('.').rglob('*.py'):
    if any(part in {'.git', '.venv', '__pycache__'} for part in path.parts):
        continue
    py_compile.compile(str(path), doraise=True)
print('py_compile OK')
PY
py_compile OK

python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
OK

git diff --check
OK
```

Additional focused verification:

```text
python3 -m unittest tests.test_gateway_auth tests.test_gateway_server_import tests.test_cluster_state_sync_ab tests.test_live_agent_benchmark -v
Ran 136 tests in 28.346s
OK
```

## Repository State

Committed gateway changes:

```text
f458cd9 fix: harden gateway audit edges
```

Files included in the closeout commit:

```text
README.md
agent_skill_dictionary/cli.py
agent_skill_dictionary/gateway_server.py
scripts/cluster_state_sync_ab.py
tests/test_gateway_auth.py
tests/test_gateway_server_import.py
tests/test_gateway_server_routes.py
```

Known unrelated workspace noise remains outside `网关/` under the parent repository root:

```text
../1.png
../2.jpeg
../3.jpeg
../data/
../home/
../reports-real-model-ab-gpt-5.4-mini.json
../reports/
../schemas/
../字源东方 (Hanzi Spectrum) 项目白皮书与数据文档 V1.docx
../封面.png
```

These files are not part of this gateway security closeout and were not committed.

## Residual Boundaries

These are not blockers for this phase:

- FastAPI route tests are skipped in dependency-light environments when `fastapi.testclient` is unavailable; helper-level and import-level tests still cover the core behavior.
- HTTP `/run` command allowlist is intentionally conservative. Broader command execution should go through explicit policy expansion, not silent default allowance.
- Local CLI remains a trusted developer interface and intentionally has a wider execution surface than public HTTP routes.
- Production deployment still requires correct environment configuration: `ONEWORD_GATEWAY_TOKEN`, `ONEWORD_WORKSPACE_ROOT`, upstream model keys, and any sandbox policy flags.

## Closeout Decision

This phase is closed.

The gateway now has:

- rule-synced evidence metadata
- b2b mesh live benchmark support
- fail-closed gateway authentication
- protected control-plane endpoints
- bounded HTTP `/run` execution surface
- stable bad-request behavior
- restored A/B benchmark module
- green regression baseline

Recommended next phase:

1. Deploy this branch to the N100 environment.
2. Run the same A/B benchmark against the configured OpenAI-compatible endpoint.
3. Capture deployment logs and benchmark output as the next operational evidence package.
