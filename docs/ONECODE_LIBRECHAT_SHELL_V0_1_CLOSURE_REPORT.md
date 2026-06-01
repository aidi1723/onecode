# OneCode LibreChat Shell v0.1 Closure Report

Date: 2026-05-31
Scope: OneCode core plus LibreChat Web shell
Status: Closed as v0.1 shell integration baseline

## Closure Point

This phase closes the standalone OneCode Agent shell line:

```text
OneCode core -> OneCode OpenAI-compatible API -> LibreChat custom endpoint -> OneCode Console panel
```

The gateway product line is intentionally out of scope. This stage does not depend on, import, route through, or configure `oneword-agent-gateway` or any other gateway service.

## Repositories

- OneCode core: `<private-development-workspace>`
- LibreChat shell: `<local-user-path>`

## Product Surface Closed In This Phase

LibreChat now acts as the mature chat shell for OneCode:

- local login and conversation shell
- custom `OneCode` OpenAI-compatible endpoint
- model label `onecode-agent`
- OneCode project selector in the chat input bar
- native folder picker for existing project folders
- new project folder creation
- filesystem MCP sync for the selected workspace
- right-side `OneCode Console` panel

The `OneCode Console` panel exposes the current kernel-facing product tabs:

- `项目`: active workspace, path status, Git/verifier status, project init, MCP sync
- `运行`: recent run list, inspect, resume
- `证据`: ledger, manifest, checkpoint evidence
- `验证`: verifier presets, verifier policy read/init/overwrite
- `诊断`: doctor and self-audit

## Core API Surface Added For The Shell

The OneCode API exposes shell-facing control endpoints in addition to `/v1/chat/completions`:

- `GET /v1/onecode/project/status`
- `POST /v1/onecode/project/init`
- `GET /v1/onecode/runs`
- `GET /v1/onecode/runs/<run_id>/inspect`
- `POST /v1/onecode/runs/<run_id>/resume`
- `GET /v1/onecode/runs/<run_id>/evidence`
- `GET /v1/onecode/verifier/presets`
- `GET /v1/onecode/verifier/policy`
- `POST /v1/onecode/verifier/policy`
- `POST /v1/onecode/doctor`
- `POST /v1/onecode/audit-self`

LibreChat bridges those through `/api/onecode/*` routes and typed client/data-provider helpers.

## Local Startup

From the OneCode repository:

```bash
PYTHONPATH=src python3 -m onecode shell \
  --onecode-port 19080 \
  --librechat-port 14080 \
  --mongo-port 39017 \
  --workspace <private-temp-path> \
  --no-browser \
  --show-credentials
```

Default local preview credentials:

```text
Email: onecode@local.test
Password: OneCode123!
```

Open:

```text
http://127.0.0.1:14080
```

If the UI does not show `打开控制台` or `OneCode Console`, rebuild the production frontend and restart LibreChat. LibreChat reads `client/dist/index.html` into memory at backend startup:

```bash
cd <local-user-path>
npm run build:client
```

Then restart the shell command above.

## Verification Evidence

Fresh verification run during closure:

- LibreChat client focused tests: `20 passed`
- LibreChat OneCode backend bridge tests: `18 passed`
- OneCode Web API tests: `34 passed`
- OneCode full verification: `bash scripts/verify.sh`, `Ran 332 tests ... OK`
- LibreChat data-provider build: passed
- LibreChat production frontend build: `npm run build:client`, passed
- Browser smoke: logged into the local shell and opened `OneCode Console`; tabs rendered as `项目 / 运行 / 证据 / 验证 / 诊断`
- HTTP smoke: OneCode API `/health` returned `{"status": "ok", "service": "onecode"}`

## Known Operational Notes

- The local preview shell uses temporary MongoDB and local credentials. It is a development preview, not production deployment hardening.
- The LibreChat backend must be restarted after a production frontend rebuild because it caches `index.html` at process startup.
- Existing browser service worker or cached assets can hide frontend changes. Use a fresh port, hard refresh, or clear site data if needed.
- Some repo-wide LibreChat typecheck issues are pre-existing upstream/local issues; this closure relied on focused Jest tests, data-provider build, production frontend build, and browser smoke.
- Local `doctor` may warn about optional RAG or Meilisearch services being unavailable; those are not required for the OneCode shell closure.

## Boundary Statement

Closed:

- standalone OneCode Agent Web shell
- OneCode core integration into LibreChat
- kernel evidence and diagnostics productized into the shell panel
- local project folder selection and MCP workspace binding

Not closed in this phase:

- production deployment packaging
- persistent production database setup
- enterprise auth hardening
- final UI polish pass
- automatic rebuild/restart orchestration
- any gateway product integration

## Next Phase Recommendation

Start the next phase as `OneCode Agent Shell v0.2` with these priorities:

- one-command stable dev launcher that rebuilds/restarts the shell when needed
- production deployment notes and environment matrix
- UI polish and empty/error state refinement for the console panel
- stronger browser smoke automation for project selection, evidence loading, verifier write, and diagnostics
- optional packaging of LibreChat shell and OneCode API as a managed local app
