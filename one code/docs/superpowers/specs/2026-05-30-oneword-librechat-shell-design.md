# OneWord LibreChat Shell Design

Date: 2026-05-30
Status: Approved replacement direction
Scope: OneWord Web shell based on a LibreChat fork plus `oneword-agent-gateway`

## Decision

Use LibreChat instead of Open WebUI as the Web product shell for 一字诀 OneWord.

LibreChat is the better shell base because its repository license is MIT, its UI title and welcome copy are configurable, and its `librechat.yaml` supports OpenAI-compatible custom endpoints. This lets OneWord become the first-class brand without Open WebUI's 50-user branding ceiling.

## Architecture

```text
OneWord LibreChat fork
  -> LibreChat custom endpoint: OneWord
  -> http://host.docker.internal:8080/v1 or http://localhost:8080/v1
  -> oneword-agent-gateway
  -> upstream model or external agent
  -> OneWord execution words, tool gate, evidence, and artifacts
```

LibreChat must not hold real upstream provider credentials in the default OneWord configuration. The Web shell uses `ONEWORD_GATEWAY_TOKEN` as the custom endpoint key. The real upstream model key remains only in `oneword-agent-gateway` as `ONEWORD_UPSTREAM_API_KEY`.

## Phase 1 Scope

Phase 1 creates a branded OneWord LibreChat shell with the gateway as the default AI endpoint.

Required:

- Fork or clone LibreChat into a separate sibling repo, such as `../oneword-librechat`.
- Preserve the MIT `LICENSE` file and copyright notice.
- Set `APP_TITLE=一字诀 OneWord`.
- Add a `librechat.yaml` with `interface.customWelcome` written for OneWord.
- Configure `endpoints.custom` with a single `OneWord` endpoint.
- Point the endpoint to the gateway through `ONEWORD_GATEWAY_BASE_URL`.
- Use `ONEWORD_GATEWAY_TOKEN`, not upstream model keys.
- Configure SSRF allowed addresses for local gateway access, such as `host.docker.internal:8080` and `127.0.0.1:8080`.
- Add OneWord starter prompts around `查 / 解 / 修 / 造 / 改 / 测 / 审 / 设 / 卫 / 停 / 问 / 总`.
- Apply a restrained OneWord theme pass: dark graphite surfaces, warm gray text, restrained earth-gold accents.
- Provide local startup docs for LibreChat plus `oneword-agent-gateway`.

Non-goals:

- Do not implement runtime evidence panels in Phase 1.
- Do not duplicate gateway logic in LibreChat.
- Do not merge LibreChat into the Python `one code` package.
- Do not place `ONEWORD_UPSTREAM_API_KEY` in LibreChat `.env`, YAML, Docker Compose, browser config, or docs except as a warning.

## LibreChat Configuration Shape

Use `librechat.yaml` as the primary integration surface:

```yaml
version: 1.3.11
cache: true

interface:
  customWelcome: '一字诀 OneWord：输入一个执行字，让网关加载对应的工具权限、工作流和证据规则。'
  modelSelect: true
  parameters: true
  presets: true
  prompts:
    use: true
    create: true
    share: false
    public: false
  agents:
    use: true
    create: false
    share: false
    public: false
  marketplace:
    use: false

endpoints:
  allowedAddresses:
    - 'host.docker.internal:8080'
    - '127.0.0.1:8080'
    - 'localhost:8080'
  custom:
    - name: 'OneWord'
      apiKey: '${ONEWORD_GATEWAY_TOKEN}'
      baseURL: '${ONEWORD_GATEWAY_BASE_URL}'
      models:
        default: ['oneword-gateway']
        fetch: false
      titleConvo: true
      titleModel: 'oneword-gateway'
      summarize: false
      modelDisplayLabel: '一字诀'
      dropParams: ['stop', 'user', 'frequency_penalty', 'presence_penalty']
```

Use `.env` for deployment values:

```text
APP_TITLE=一字诀 OneWord
ONEWORD_GATEWAY_BASE_URL=http://host.docker.internal:8080/v1
ONEWORD_GATEWAY_TOKEN=dev-local-token
ENDPOINTS=custom
```

For non-Docker local development, `ONEWORD_GATEWAY_BASE_URL` can be `http://localhost:8080/v1`.

## Visual Direction

LibreChat already gives a mature chat product surface. Keep its information architecture, conversation list, model selector, auth, and settings ergonomics.

OneWord styling should be restrained:

- Background: near-black graphite.
- Surfaces: charcoal and warm dark gray.
- Accent: muted earth-gold for active endpoint/model states and starter chips.
- Text: off-white primary, warm gray secondary.
- Shape: small radii and crisp panels.
- Voice: concise Chinese product language, not mystical exposition.

Avoid a decorative landing page. The first screen should remain the usable chat workspace.

## Phase 2 Runtime Panels

Add these only after Phase 1 is running through the gateway:

- Execution-word state panel: current word, root opcode, macro chain, trace.
- Tool preflight panel: allowed, denied, and human-confirmation actions.
- Evidence panel: manifest path, audit log path, artifacts, SHA256 summaries.
- Workspace panel: active workspace root and recent runs.

Phase 2 must consume gateway control-plane endpoints and must not execute tools from the frontend.

## Error Handling

- If the gateway is offline, LibreChat should show the custom endpoint connection failure and docs should point to the gateway startup command.
- If `ONEWORD_GATEWAY_TOKEN` is wrong, show gateway auth failure without exposing upstream keys.
- If upstream key is missing, surface the gateway's `upstream_api_key_missing` response as a gateway state.
- If LibreChat blocks local gateway access through SSRF protection, update `endpoints.allowedAddresses`, not the gateway.

## Verification

Phase 1 is acceptable when:

- LibreChat starts under the OneWord title.
- The only enabled default endpoint is `OneWord`.
- A chat request reaches `oneword-agent-gateway`.
- No real upstream key is present in LibreChat config.
- `librechat.yaml` contains `endpoints.allowedAddresses` for local gateway access.
- The MIT license remains present.
- The UI is recognizably OneWord but still behaves like a polished chat product.

Phase 2 is acceptable only if it adds runtime visibility without weakening the gateway boundary.
