# OneCode LibreChat Shell Design

Date: 2026-05-30
Status: Approved direction
Scope: OneCode Web shell based on LibreChat, with no OneWord gateway dependency

## Decision

OneCode becomes a standalone agent product by pairing the existing OneCode core with a LibreChat Web shell. This line does not depend on `oneword-agent-gateway`, `agent_skill_dictionary`, or any OneWord gateway service.

## Architecture

```text
LibreChat shell
  -> custom endpoint: OneCode
  -> OneCode native OpenAI-compatible API
  -> OneCode core
  -> guarded run evidence and chat completion response
```

OneCode owns the API boundary. LibreChat only provides the chat product shell: auth, conversations, model selector, settings, and message UI.

## Phase 1 Scope

- Add a small stdlib HTTP API under `src/onecode/web`.
- Support `GET /health`, `GET /v1/models`, and `POST /v1/chat/completions`.
- Use `ONECODE_API_TOKEN` for bearer-token authentication when configured.
- Extract the latest user message from a LibreChat/OpenAI-style request.
- Execute OneCode locally:
  - model-backed mode uses `run_model_task` when a model API key exists;
  - fallback mode uses `run_task` so the shell can still prove the loop without external model credentials.
- Return OpenAI Chat Completions-compatible JSON.
- Keep OneCode core free of mandatory third-party runtime dependencies.
- Configure a LibreChat fork endpoint named `OneCode` pointing at this API.

## Non-Goals

- Do not call or configure `oneword-agent-gateway`.
- Do not reuse OneWord branding, endpoint names, env vars, or docs.
- Do not move OneCode into the LibreChat repository.
- Do not execute tools from LibreChat frontend code.

## LibreChat Configuration Shape

```yaml
endpoints:
  allowedAddresses:
    - 'host.docker.internal:8080'
    - '127.0.0.1:8080'
    - 'localhost:8080'
  custom:
    - name: 'OneCode'
      apiKey: '${ONECODE_API_TOKEN}'
      baseURL: '${ONECODE_API_BASE_URL}'
      models:
        default: ['onecode-agent']
        fetch: false
      titleConvo: true
      titleModel: 'onecode-agent'
      summarize: false
      modelDisplayLabel: 'OneCode'
```

## Acceptance

- OneCode API responds to `/health`.
- LibreChat-style `/v1/models` returns `onecode-agent`.
- Unauthorized requests are rejected when `ONECODE_API_TOKEN` is set.
- `/v1/chat/completions` returns a valid assistant message with OneCode run evidence metadata.
- No OneWord gateway code is required to run the flow.
