# OneWord LibreChat Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Phase 1 OneWord-branded LibreChat fork that connects by default to `oneword-agent-gateway` through a LibreChat custom OpenAI-compatible endpoint.

**Architecture:** Keep the Web shell in a sibling repository, separate from the Python `one code` package. LibreChat owns auth, conversations, settings, agents, model selection, and general chat UX; `oneword-agent-gateway` owns execution-word policy, tool gates, and evidence. Phase 2 runtime panels are intentionally excluded.

**Tech Stack:** LibreChat `0.8.x` codebase, React/Vite client, Node API, MongoDB, Meilisearch, Docker Compose, `librechat.yaml`, `oneword-agent-gateway` OpenAI-compatible `/v1/chat/completions`.

---

## Implementation Notes

- Use `/Users/aidi/大字典/oneword-librechat` as the working shell repository unless the user chooses another path before execution.
- Keep LibreChat's `LICENSE` file intact. The repo license is MIT, so full OneWord branding is acceptable as long as the license notice remains.
- Do not put real upstream model provider keys in LibreChat. Use `ONEWORD_GATEWAY_TOKEN` as the custom endpoint key; keep `ONEWORD_UPSTREAM_API_KEY` only in `../oneword-agent-gateway`.
- Use LibreChat configuration first: `.env`, `librechat.yaml`, `deploy-compose.yml`, and existing UI config. Edit React components only for brand polish that cannot be achieved by config.

## File Map

- Create sibling repo: `/Users/aidi/大字典/oneword-librechat`
- Modify: `/Users/aidi/大字典/oneword-librechat/.env.example`
- Create: `/Users/aidi/大字典/oneword-librechat/librechat.yaml`
- Create: `/Users/aidi/大字典/oneword-librechat/ONEWORD_SHELL.md`
- Modify: `/Users/aidi/大字典/oneword-librechat/deploy-compose.yml`
- Create: `/Users/aidi/大字典/oneword-librechat/scripts/oneword-smoke.mjs`
- Modify: `/Users/aidi/大字典/oneword-librechat/package.json`
- Create: `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.ts`
- Create: `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.test.ts`
- Modify later if needed: `/Users/aidi/大字典/oneword-librechat/client/src/components/Chat/Landing.tsx`
- Modify later if needed: `/Users/aidi/大字典/oneword-librechat/client/src/components/Chat/Input/ConversationStarters.tsx`

### Task 1: Create And Pin The LibreChat Fork

**Files:**
- Create/modify repository: `/Users/aidi/大字典/oneword-librechat`
- Read: `/Users/aidi/大字典/oneword-librechat/LICENSE`
- Create: `/Users/aidi/大字典/oneword-librechat/ONEWORD_SHELL.md`

- [ ] **Step 1: Clone upstream into sibling directory**

Run:

```bash
cd /Users/aidi/大字典
git clone https://github.com/danny-avila/LibreChat.git oneword-librechat
cd oneword-librechat
git status --short
```

Expected: repository exists and `git status --short` prints no tracked changes.

- [ ] **Step 2: Create a OneWord branch**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git switch -c oneword-shell-phase1
git rev-parse --short HEAD
```

Expected: prints an upstream commit hash. Record it in `ONEWORD_SHELL.md`.

- [ ] **Step 3: Add shell integration documentation**

Create `/Users/aidi/大字典/oneword-librechat/ONEWORD_SHELL.md` with:

```markdown
# OneWord LibreChat Shell

This fork adapts LibreChat as the Phase 1 Web shell for 一字诀 OneWord.

## Scope

- LibreChat provides the Web product shell: auth, conversations, settings, agents, model selection, and common chat UX.
- `oneword-agent-gateway` provides the model-facing API, execution-word policy, tool gate, and evidence chain.
- Phase 1 does not add OneWord runtime side panels.

## Default Local Connection

LibreChat talks to the gateway through a custom OpenAI-compatible endpoint:

```text
APP_TITLE=一字诀 OneWord
ENDPOINTS=custom
ONEWORD_GATEWAY_BASE_URL=http://host.docker.internal:8080/v1
ONEWORD_GATEWAY_TOKEN=dev-local-token
```

For non-Docker local development, use:

```text
ONEWORD_GATEWAY_BASE_URL=http://localhost:8080/v1
```

The real upstream model key must stay in `oneword-agent-gateway` as `ONEWORD_UPSTREAM_API_KEY`.

## License

LibreChat is MIT licensed. Keep the `LICENSE` file and copyright notice in redistributions.
```

- [ ] **Step 4: Verify MIT license file remains present**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
test -f LICENSE
rg -n "MIT License|Permission is hereby granted" LICENSE
```

Expected: `test` exits 0 and `rg` prints MIT license text.

- [ ] **Step 5: Commit fork documentation**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git add ONEWORD_SHELL.md
git commit -m "docs: add oneword librechat shell notes"
```

Expected: commit succeeds with only `ONEWORD_SHELL.md`.

### Task 2: Configure OneWord As The Default LibreChat Endpoint

**Files:**
- Modify: `/Users/aidi/大字典/oneword-librechat/.env.example`
- Create: `/Users/aidi/大字典/oneword-librechat/librechat.yaml`
- Test by command: `rg`

- [ ] **Step 1: Add OneWord environment defaults**

Modify the UI section of `/Users/aidi/大字典/oneword-librechat/.env.example` so it contains:

```dotenv
APP_TITLE=一字诀 OneWord
CUSTOM_FOOTER="一字诀 OneWord"
HELP_AND_FAQ_URL=
```

Add the OneWord gateway section near the provider endpoint settings:

```dotenv
# OneWord gateway. This is the only model-facing key the Web shell should hold.
ENDPOINTS=custom
ONEWORD_GATEWAY_BASE_URL=http://host.docker.internal:8080/v1
ONEWORD_GATEWAY_TOKEN=dev-local-token
```

Leave any real provider keys blank or `user_provided`.

- [ ] **Step 2: Add production `librechat.yaml`**

Create `/Users/aidi/大字典/oneword-librechat/librechat.yaml` with:

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
  bookmarks: true
  multiConvo: true
  agents:
    use: true
    create: false
    share: false
    public: false
  marketplace:
    use: false
  fileCitations: true

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

- [ ] **Step 3: Verify config boundary by search**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
rg -n "APP_TITLE=一字诀 OneWord|ENDPOINTS=custom|ONEWORD_GATEWAY_BASE_URL|ONEWORD_GATEWAY_TOKEN|ONEWORD_UPSTREAM_API_KEY|host.docker.internal:8080|oneword-gateway" .env.example librechat.yaml
```

Expected: OneWord gateway values appear. `ONEWORD_UPSTREAM_API_KEY` does not appear.

- [ ] **Step 4: Commit config**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git add .env.example librechat.yaml
git commit -m "feat: configure oneword custom endpoint"
```

Expected: commit succeeds.

### Task 3: Add OneWord Brand Constants And Tests

**Files:**
- Create: `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.ts`
- Create: `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.test.ts`

- [ ] **Step 1: Write brand tests**

Create `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.test.ts` with:

```ts
import { ONEWORD_BRAND, ONEWORD_EXECUTION_WORDS, ONEWORD_STARTER_PROMPTS } from './brand';

describe('OneWord brand constants', () => {
  it('uses OneWord as the primary product brand', () => {
    expect(ONEWORD_BRAND.productName).toBe('一字诀 OneWord');
    expect(ONEWORD_BRAND.endpointName).toBe('OneWord');
    expect(ONEWORD_BRAND.defaultModel).toBe('oneword-gateway');
  });

  it('contains the phase 1 execution words', () => {
    expect(ONEWORD_EXECUTION_WORDS.map((item) => item.word)).toEqual([
      '查',
      '解',
      '修',
      '造',
      '改',
      '测',
      '审',
      '设',
      '卫',
      '停',
      '问',
      '总',
    ]);
  });

  it('starter prompts use concise execution-word syntax', () => {
    expect(ONEWORD_STARTER_PROMPTS).toHaveLength(4);
    expect(ONEWORD_STARTER_PROMPTS[0]).toContain('查：');
    expect(ONEWORD_STARTER_PROMPTS.every((prompt) => prompt.length <= 36)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
npm run test:client -- client/src/oneword/brand.test.ts
```

Expected: FAIL because `client/src/oneword/brand.ts` does not exist.

- [ ] **Step 3: Add brand constants**

Create `/Users/aidi/大字典/oneword-librechat/client/src/oneword/brand.ts` with:

```ts
export const ONEWORD_BRAND = {
  productName: '一字诀 OneWord',
  tagline: '执行字驱动的 AI 工作台',
  endpointName: 'OneWord',
  defaultModel: 'oneword-gateway',
} as const;

export const ONEWORD_EXECUTION_WORDS = [
  { word: '查', label: '只读扫描' },
  { word: '解', label: '解释拆解' },
  { word: '修', label: '受控修复' },
  { word: '造', label: '创建实现' },
  { word: '改', label: '调整重构' },
  { word: '测', label: '验证测试' },
  { word: '审', label: '风险审查' },
  { word: '设', label: '方案设计' },
  { word: '卫', label: '安全守卫' },
  { word: '停', label: '熔断停止' },
  { word: '问', label: '人工确认' },
  { word: '总', label: '交付总结' },
] as const;

export const ONEWORD_STARTER_PROMPTS = [
  '查：看看这个项目结构',
  '设：给我一版实现方案',
  '修：定位并修复这个问题',
  '总：总结当前运行结果',
] as const;
```

- [ ] **Step 4: Run client test**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
npm run test:client -- client/src/oneword/brand.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit brand constants**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git add client/src/oneword/brand.ts client/src/oneword/brand.test.ts
git commit -m "feat: add oneword brand constants"
```

Expected: commit succeeds.

### Task 4: Add Gateway Smoke Script

**Files:**
- Create: `/Users/aidi/大字典/oneword-librechat/scripts/oneword-smoke.mjs`
- Modify: `/Users/aidi/大字典/oneword-librechat/package.json`

- [ ] **Step 1: Add smoke script**

Create `/Users/aidi/大字典/oneword-librechat/scripts/oneword-smoke.mjs` with:

```js
const rawBaseUrl = process.env.ONEWORD_GATEWAY_BASE_URL ?? 'http://localhost:8080/v1';
const baseUrl = rawBaseUrl.replace(/\/$/, '');
const token = process.env.ONEWORD_GATEWAY_TOKEN ?? 'dev-local-token';

const headers = {
  authorization: `Bearer ${token}`,
  'content-type': 'application/json',
};

async function request(url, init = {}) {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...headers,
      ...(init.headers ?? {}),
    },
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${url} failed with ${response.status}: ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

async function main() {
  const root = baseUrl.endsWith('/v1') ? baseUrl.slice(0, -3) : baseUrl;
  const ready = await request(`${root}/ready`, { headers: { authorization: `Bearer ${token}` } });
  console.log('ready:', JSON.stringify(ready));

  const chat = await request(`${baseUrl}/chat/completions`, {
    method: 'POST',
    body: JSON.stringify({
      model: 'oneword-gateway',
      messages: [{ role: 'user', content: '查：用一句话确认网关在线' }],
      stream: false,
    }),
  });

  console.log('chat:', JSON.stringify(chat).slice(0, 1000));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
```

- [ ] **Step 2: Add npm script**

In `/Users/aidi/大字典/oneword-librechat/package.json`, add to `scripts`:

```json
"oneword:smoke": "node scripts/oneword-smoke.mjs"
```

Keep valid JSON commas.

- [ ] **Step 3: Run script without gateway to verify useful failure**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
npm run oneword:smoke
```

Expected: FAIL with a connection error if the gateway is not running.

- [ ] **Step 4: Commit smoke script**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git add package.json scripts/oneword-smoke.mjs
git commit -m "test: add oneword gateway smoke script"
```

Expected: commit succeeds.

### Task 5: Verify Local Gateway And LibreChat

**Files:**
- Read/execute: `/Users/aidi/大字典/oneword-agent-gateway/README.md`
- Read/execute: `/Users/aidi/大字典/oneword-librechat/ONEWORD_SHELL.md`
- Execute: `/Users/aidi/大字典/oneword-librechat/deploy-compose.yml`

- [ ] **Step 1: Start the gateway**

Run in terminal A:

```bash
cd /Users/aidi/大字典/oneword-agent-gateway
export ONEWORD_WORKSPACE_ROOT="$(pwd)"
export ONEWORD_GATEWAY_TOKEN="${ONEWORD_GATEWAY_TOKEN:-dev-local-token}"
export ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY"
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

Expected: gateway starts on port `8080`.

- [ ] **Step 2: Verify gateway smoke**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
ONEWORD_GATEWAY_BASE_URL=http://localhost:8080/v1 ONEWORD_GATEWAY_TOKEN="${ONEWORD_GATEWAY_TOKEN:-dev-local-token}" npm run oneword:smoke
```

Expected: PASS if upstream key is configured. If upstream key is missing, the chat call should fail with the gateway's upstream-key state, proving the gateway boundary.

- [ ] **Step 3: Create local `.env` for LibreChat**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
cp .env.example .env
```

Then ensure `.env` contains:

```dotenv
APP_TITLE=一字诀 OneWord
ENDPOINTS=custom
ONEWORD_GATEWAY_BASE_URL=http://host.docker.internal:8080/v1
ONEWORD_GATEWAY_TOKEN=dev-local-token
```

- [ ] **Step 4: Start LibreChat**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
docker compose -f deploy-compose.yml up -d
```

Expected: API, client, MongoDB, Meilisearch, vector DB, and RAG services start.

- [ ] **Step 5: Browser smoke**

Open LibreChat at the exposed local URL and verify:

```text
Title/brand: 一字诀 OneWord
Enabled endpoint: OneWord
Default model: oneword-gateway
Welcome copy: 一字诀 OneWord execution-word language
Chat request reaches oneword-agent-gateway
No ONEWORD_UPSTREAM_API_KEY appears in LibreChat UI or config
```

- [ ] **Step 6: Commit docs if verification changes startup**

If startup commands need adjustment, update `ONEWORD_SHELL.md` and commit:

```bash
cd /Users/aidi/大字典/oneword-librechat
git add ONEWORD_SHELL.md
git commit -m "docs: document oneword librechat smoke path"
```

Expected: commit only if docs changed.

### Task 6: Final Consistency Pass

**Files:**
- Review: `/Users/aidi/大字典/oneword-librechat`
- Review: `/Users/aidi/大字典/one code/docs/superpowers/specs/2026-05-30-oneword-librechat-shell-design.md`

- [ ] **Step 1: Search for direct upstream key leakage**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
rg -n "ONEWORD_UPSTREAM_API_KEY|sk-|OPENAI_API_KEY=.*sk-" . -g '!node_modules' -g '!package-lock.json'
```

Expected: no real upstream provider key appears in LibreChat config.

- [ ] **Step 2: Search OneWord endpoint consistency**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
rg -n "一字诀|OneWord|oneword-gateway|ONEWORD_GATEWAY|ENDPOINTS=custom|allowedAddresses" .env.example librechat.yaml ONEWORD_SHELL.md client/src/oneword package.json
```

Expected: OneWord values appear consistently.

- [ ] **Step 3: Run final checks**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
npm run test:client -- client/src/oneword/brand.test.ts
npm run lint -- client/src/oneword/brand.ts client/src/oneword/brand.test.ts
```

Expected: both pass. If the repo lint command does not accept file arguments, run `npm run lint` and record the result.

- [ ] **Step 4: Review git history**

Run:

```bash
cd /Users/aidi/大字典/oneword-librechat
git status --short
git log --oneline --decorate -n 8
```

Expected: no uncommitted tracked changes unless final docs were intentionally left for review.

## Plan Self-Review

- Spec coverage: Phase 1 LibreChat shell, MIT license boundary, custom endpoint, key boundary, SSRF allowed addresses, welcome copy, startup docs, and verification are covered.
- Placeholder scan: no TODO/TBD placeholders are used.
- Type consistency: `ONEWORD_BRAND`, `ONEWORD_EXECUTION_WORDS`, and `ONEWORD_STARTER_PROMPTS` are defined before optional UI consumption.
- Scope control: Phase 2 runtime panels are intentionally excluded.
