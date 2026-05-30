# OneWord Open WebUI Shell Design

Date: 2026-05-30
Status: Superseded by `2026-05-30-oneword-librechat-shell-design.md`
Scope: OneWord Web shell based on an Open WebUI fork plus `oneword-agent-gateway`

## Supersession Note

This Open WebUI shell direction is no longer the recommended implementation base. The decisive blocker is Open WebUI's current branding restriction: deployments or distributions above the 50-user rolling window cannot alter, remove, obscure, or replace Open WebUI branding without written permission or an enterprise license. That makes it a poor fit for a first-class OneWord-branded shell.

Use the LibreChat-based design instead.

## Decision

Use Open WebUI as the Web product shell for 一字诀 OneWord, but keep it as a separate Web application from the Python `onecode` package. The first implementation should be a branded OneWord fork that connects to `oneword-agent-gateway` through an OpenAI-compatible provider connection. Deep OneWord runtime panels are reserved for a second phase after the branded shell proves the chat and gateway path.

The first phase is not a rewrite of the OneWord kernel, gateway, or Textual TUI. It is a Web shell that uses the existing gateway as its model backend.

## Current Context

`one code` is a Python package with a Textual TUI under `src/onecode/tui`. The TUI remains useful for local terminal workflows, but it is not the right long-term shell for a full product surface with accounts, chat history, model management, documents, and richer runtime inspection.

`../oneword-agent-gateway` already exposes an OpenAI-compatible `/v1/chat/completions` endpoint and control-plane endpoints such as `/v1/yizijue/resolve`, `/v1/yizijue/preflight-tool`, and `/v1/yizijue/run`. Its README defines the intended security boundary: clients use the gateway token as their API key, while the real upstream model key stays only on the gateway process.

Open WebUI is a mature self-hosted AI interface that supports OpenAI-compatible providers. It has enough product surface to serve as OneWord's Web shell without building accounts, chat history, model selection, and common AI UI flows from scratch.

## License Boundary

Open WebUI's current `v0.6.6+` license includes a branding protection clause. Official Open WebUI license documentation says self-hosted internal deployments with 50 or fewer users may fully rebrand, while larger deployments must preserve Open WebUI branding or obtain another permission path. The current license is public-source but not OSI-approved open source.

Implementation must therefore start with a license decision:

- For private/internal beta with 50 or fewer users: use the current Open WebUI codebase and fully rebrand to OneWord.
- For public or larger deployment: either preserve subordinate Open WebUI attribution as required, obtain permission, or fork from the last fully permissive version if the feature set is acceptable.
- Do not remove required copyright, license, or attribution files.

## Architecture

```text
OneWord Open WebUI fork
  -> OpenAI-compatible provider: http://localhost:8080/v1
  -> oneword-agent-gateway
  -> upstream model or external agent
  -> OneWord execution words, tool gate, evidence, and artifacts
```

Open WebUI must not call the real upstream model provider directly in the branded default configuration. The only default provider should be the OneWord gateway.

Default local environment:

```text
ONEWORD_GATEWAY_TOKEN=dev-local-token
ONEWORD_UPSTREAM_API_KEY=<real upstream key, gateway side only>
ONEWORD_WORKSPACE_ROOT=<workspace root, gateway side only>
Open WebUI provider base URL=http://localhost:8080/v1
Open WebUI provider API key=$ONEWORD_GATEWAY_TOKEN
```

## Phase 1: Branded Shell

Phase 1 turns Open WebUI into a OneWord-branded shell while keeping the underlying Open WebUI product flows intact.

Required changes:

- Product name: show `一字诀 OneWord` as the primary brand.
- Default provider: preconfigure an OpenAI-compatible connection to `http://localhost:8080/v1`.
- Default model label: use a OneWord gateway-facing model name such as `oneword-gateway` unless implementation discovers a stricter Open WebUI model registration requirement.
- Welcome copy: position the app as an execution-word AI workbench, not a generic chatbot.
- Prompt guidance: introduce common execution words such as `查 / 解 / 修 / 造 / 改 / 测 / 审 / 设 / 卫 / 停 / 问 / 总`.
- Visual language: keep Open WebUI's mature layout and interaction patterns, but shift the visual system toward OneWord's identity.
- Deployment: provide local startup documentation or compose files for Open WebUI plus `oneword-agent-gateway`.

Non-goals for Phase 1:

- Do not replace Open WebUI's auth, chat storage, RAG, model dropdown, or settings systems.
- Do not implement custom OneWord runtime side panels yet.
- Do not merge Open WebUI into the `one code` Python package.
- Do not bypass the gateway by placing upstream model API keys in the Web shell.

## Visual Direction

The shell should feel like a serious AI workbench, not a mystical theme page.

Use these design roles:

- Background: near-black graphite / 玄铁黑.
- Main surface: quiet charcoal with subtle borders.
- Muted surface: warm dark gray.
- Accent: restrained dark gold / 坤土金, used for active states, execution-word chips, and key affordances.
- Text: high-contrast off-white for primary content, warm gray for secondary content.
- Danger/safety: keep clear red/yellow/green semantics for blocked, warning, and allowed states.
- Shape: keep small radii and crisp panels; avoid ornamental blobs, oversized decorative gradients, and heavy hero styling.
- Typography: preserve Open WebUI's readable app typography, but use concise Chinese product copy where it improves clarity.

The app should still read as Open WebUI-class software in density and ergonomics. The OneWord layer should appear through brand, language, default flows, and runtime semantics rather than excessive decoration.

## Phase 2: Runtime Panels

Only add these if Phase 1 proves that the base shell and gateway connection work well:

- Execution-word state panel: current word, root opcode, macro chain, and trace.
- Tool preflight panel: allowed, denied, and human-confirmation actions.
- Evidence panel: manifest path, audit log path, artifacts, SHA256 summaries, and run status.
- Workspace panel: active workspace root, recent runs, and handoff artifacts.

Phase 2 should consume existing gateway endpoints instead of duplicating gateway logic in the frontend.

## Data Flow

Normal chat:

1. User sends a message from OneWord Web shell.
2. Open WebUI sends an OpenAI-compatible request to `oneword-agent-gateway`.
3. Gateway resolves execution words, injects runtime policy, applies tool gates, and forwards safe requests upstream.
4. Gateway returns an OpenAI-compatible response to Open WebUI.
5. Open WebUI renders the conversation using its existing chat UI.

Runtime inspection in Phase 2:

1. Frontend uses control-plane endpoints only after the gateway chat path is stable.
2. Gateway remains the source of truth for execution state and evidence.
3. Frontend renders summaries and links; it does not execute tools or write evidence directly.

## Error Handling

- If the gateway is offline, the Web shell should show a provider connection error and local startup instructions.
- If `ONEWORD_GATEWAY_TOKEN` is wrong, show an authentication failure without exposing the real upstream key.
- If the upstream key is missing, surface the gateway's `upstream_api_key_missing` state clearly.
- If the gateway blocks a tool action, display that as a OneWord safety decision, not as a generic model failure.
- If license constraints prevent full rebranding for the target deployment size, preserve required Open WebUI attribution or stop before distribution.

## Testing And Verification

Phase 1 verification:

- Gateway health endpoint responds.
- Open WebUI can list or select the OneWord gateway model.
- Chat request reaches `oneword-agent-gateway`.
- Streaming, if enabled, works through the gateway.
- The Web shell does not contain real upstream provider keys.
- Brand replacement is consistent across first-run, sidebar, title, settings, and empty states.
- Required Open WebUI license and attribution files remain present.
- Desktop and mobile layouts remain readable after theming.

Phase 2 verification, if implemented:

- Runtime panels render from gateway endpoints only.
- Evidence links and run identifiers match gateway outputs.
- Blocked and human-confirmation states are distinguishable without relying on color alone.
- UI remains usable when gateway control-plane endpoints fail.

## Open Questions For Implementation

- Which Open WebUI version should be the fork base after final license review: latest current release, current main branch, or the last fully permissive pre-branding-clause version?
- Does Open WebUI require static model registration for the OneWord gateway, or can the gateway expose a compatible model list endpoint cleanly enough?
- Should the first beta preserve an Open WebUI attribution footer even if the internal user count is below the full-rebrand threshold?
- Should Phase 1 live under a sibling directory such as `../oneword-open-webui`, or under a new top-level product repo?

## Acceptance Criteria

The Phase 1 shell is acceptable when a local user can start the gateway and the branded Web shell, open the OneWord UI, send a message, receive a gateway-mediated response, and see OneWord branding and execution-word guidance without any direct upstream model key in the browser-facing app.

Phase 2 is acceptable only if it adds OneWord runtime visibility without weakening the gateway security boundary or forking Open WebUI into an unmaintainable rewrite.
