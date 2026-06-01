# OneCode LibreChat Shell

This fork adapts LibreChat as the Web shell for OneCode.

Upstream base commit: `a16f08a42`

Current OneCode shell phase: `v0.1 shell integration baseline`.

This directory is the bundled OneCode Web shell shipped with the public
OneCode repository.

## Scope

- LibreChat provides the Web product shell: auth, conversations, settings, model selection, and common chat UX.
- OneCode provides the agent core and its own OpenAI-compatible API.
- This shell does not depend on any separate gateway service.

## Default Local Connection

LibreChat talks to OneCode through a custom OpenAI-compatible endpoint:

```text
APP_TITLE=one code
ENDPOINTS=custom
ONECODE_API_BASE_URL=http://127.0.0.1:19080/v1
ONECODE_API_TOKEN=dev-local-token
```

For non-Docker local development, use:

```text
ONECODE_API_BASE_URL=http://localhost:19080/v1
```

The real upstream model key, when used, belongs to the OneCode process environment, not to LibreChat browser code.

## Local Preview

From the OneCode repository:

```bash
cd shell/onecode-librechat
npm install
cd ../..
PYTHONPATH=src python3 -m onecode shell --show-credentials
```

Default local preview login:

```text
Email: onecode@local.test
Password: OneCode123!
```

Open:

```text
http://127.0.0.1:14080/c/new
```

For the complete kernel and shell deployment guide, see the repository root
`DEPLOYMENT.md`.

完整的内核和壳部署说明见仓库根目录 `DEPLOYMENT.md`。

If frontend changes do not appear, rebuild the production frontend and restart the shell. The LibreChat backend reads `client/dist/index.html` into memory on startup:

```bash
npm run build:client
```

## OneCode Console

The chat input bar includes a `OneCode 项目` button. Its menu can bind a project folder, create a new project folder, sync filesystem MCP, and open the right-side `OneCode Console`.

The console closes the v0.1 shell integration surface:

- `项目`: workspace status, project init, MCP sync
- `运行`: recent runs, inspect, resume
- `证据`: ledger, manifest, checkpoints
- `验证`: verifier presets and verifier policy management
- `诊断`: doctor and self-audit

## License

LibreChat is MIT licensed. Keep the `LICENSE` file and copyright notice in redistributions.
