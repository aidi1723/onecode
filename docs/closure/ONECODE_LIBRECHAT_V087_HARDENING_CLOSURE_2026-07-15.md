# OneCode LibreChat v0.8.7 Hardening Closure

Date: 2026-07-15
Status: Verified in isolated worktrees; no cutover or publication performed

Post-closure update (2026-07-16): the OneCode commits from this verified phase
were integrated into `feature/gateway-iching-rule-sync` and are included in the
owner-authorized fast-forward GitHub update described in
`ONECODE_V087_VNEXT_GITHUB_CLOSURE_2026-07-16.md`. The status above remains the
historical state at the end of the July 15 verification session. The separate
LibreChat repository was not published or cut over by this OneCode update.

## Outcome

OneCode's local Web shell is ported to the exact LibreChat `v0.8.7` community
baseline. The migration preserves OneCode's execution and approval authority,
eliminates retry-amplified planning timeouts, persists private authentication
and Mongo state across controlled restarts, and retains the existing project,
Console, evidence, verifier, and diagnostics workflows.

## Provenance And Rollback

- Community tag: `v0.8.7`
- Community commit: `9e74cc0e57b395926122bd4062c1fcedc48ed465`
- OneCode verified head: `c45a1647cc0b576c698fc811409665163f24474d`
- LibreChat verified implementation head: `cde7eef12ba7bae8aac1b186a62e429d0f7f4fd8`
- Upgrade branch in both repositories: `feature/onecode-shell-v087-hardening`
- Preserved LibreChat checkpoint: `checkpoint/onecode-shell-pre-v087-20260715`
- Checkpoint commit: `a7201646608cb489f85e6b26b3a5c7117de348f8`

The community commit is an ancestor of the LibreChat upgrade head. The original
checkpoint and the operator's pre-existing dirty worktree were not reset,
cleaned, merged, or replaced. Rollback is a deliberate switch to the checkpoint
branch and its prior state directory after stopping the foreground shell.

## Reliability Changes

- Provider timeouts are normalized as `ModelProviderTimeout`.
- Failed planning returns stable HTTP 504/502 payloads with evidence refs.
- Every provider call writes one started event and exactly one completed or
  failed terminal event.
- Failed calls record a SHA-256 task digest, not the raw prompt.
- LibreChat's effective OneCode LLM config forces `maxRetries: 0`.
- Runtime timeout configuration is bounded to `(0, 600]` seconds.
- Authentication secrets use atomic private `0700/0600` state and are reused.
- Mongo uses a persistent `dbPath` and stops with `doCleanup: false`.
- Preflight checks versions, ports, baseline ancestry, state, and redacted model
  configuration; process logs and runtime records are bounded and redacted.

## Verification Evidence

| Gate | Result |
| --- | --- |
| OneCode focused suite | 163 passed |
| Final OneCode `scripts/verify.sh` | 903 passed, 1 environment-only skip |
| OneCode source quality and doctor | Passed |
| LibreChat endpoint tests | 35 passed |
| LibreChat server tests | 27 passed |
| LibreChat client tests | 28 passed |
| LibreChat builds | data-provider, API, and client passed |
| Client production build | 9,315 modules transformed; PWA post-build passed |
| Browser console | 0 errors, 0 warnings |

The one full-suite skip is the existing environment-only optional check. An
existing Web test emits a Python `ResourceWarning` while implicitly closing an
HTTP 503 response; it does not fail the suite or affect runtime requests.

## Live Acceptance

- API smoke returned healthy service/model payloads and completed a real
  read-only project inspection with full evidence.
- Desktop `1440x900` and mobile `390x844` views showed no overlapping controls.
  The mobile Console used a full-screen layout and wrapped long workspace paths.
- Login, project status, all six Console tabs, evidence loading, verifier
  presets, and doctor were exercised through visible browser controls.
- Keyboard Tab moved from the chat input to the attachment control with a
  visible active focus state.
- A read task completed and displayed its ledger reference.
- A write task returned `approval_required` with target, bytes, digest, and
  preview. `browser-approval-check.txt` remained absent.
- Controlled restart kept the authenticated browser at its existing `/c/...`
  route. The secret-file digest was unchanged, the Mongo file count remained
  278, and logs contained no `invalid signature` entry.
- A delayed-model request produced one new run, HTTP 504 in the browser, and
  `model_call_started` followed by `model_call_failed` after about 510 ms.
- Live run `6c874b701ec546f69f7fca0b9dea4fd7` had readable ledger,
  manifest, checkpoint, and trace files. Its `task_sha256` matched the local
  digest and no API key, Authorization header, or bearer token appeared in the
  run directory.

Screenshots were retained only under the temporary state directory. Key
artifacts were `page-2026-07-15T16-27-40-896Z.png` (desktop Console),
`page-2026-07-15T16-35-23-616Z.png` (desktop approval),
`page-2026-07-15T16-38-32-001Z.png` (mobile Console), and
`page-2026-07-15T16-49-34-365Z.png` (mobile timeout). No browser artifact is
tracked by either repository.

## Migration Inventory

All 54 checkpoint rows were reconciled. `ported` means the behavior was
re-expressed at the current `v0.8.7` boundary. `superseded-by-v0.8.7` means the
old modification was intentionally replaced by a tested community/config
mechanism. No business capability required an approved removal.

| # | Checkpoint row | Classification | Verification |
| ---: | --- | --- | --- |
| 1 | `.env.example` | ported | Shell config/build |
| 2 | `DESIGN.md` | ported | Browser UI audit |
| 3 | `ONECODE_SHELL.md` | ported | Provenance review |
| 4 | `api/server/index.js` | ported | Server tests |
| 5 | `api/server/routes/index.js` | ported | Server tests |
| 6 | `api/server/routes/onecode.js` | ported | Route tests |
| 7 | `api/server/routes/onecode.spec.js` | ported | 27 server tests |
| 8 | `api/server/services/Endpoints/agents/build.js` | ported | Agent build tests |
| 9 | `api/server/services/Endpoints/agents/build.spec.js` | ported | Agent build tests |
| 10 | `api/server/services/OneCode/projectPicker.js` | ported | Picker tests/browser |
| 11 | `api/server/services/OneCode/projectPicker.spec.js` | ported | Picker tests |
| 12 | `client/index.html` | ported | Client build/browser |
| 13 | `client/public/assets/apple-touch-icon-180x180.png` deletion | superseded-by-v0.8.7 | PWA post-build |
| 14 | `client/public/assets/favicon-16x16.png` deletion | superseded-by-v0.8.7 | PWA post-build |
| 15 | `client/public/assets/favicon-32x32.png` deletion | superseded-by-v0.8.7 | PWA post-build |
| 16 | `client/public/assets/icon-192x192.png` deletion | superseded-by-v0.8.7 | PWA post-build |
| 17 | `client/public/assets/logo.svg` deletion | superseded-by-v0.8.7 | Assets retained/browser |
| 18 | `client/public/assets/maskable-icon.png` deletion | superseded-by-v0.8.7 | PWA post-build |
| 19 | `client/src/components/Auth/AuthLayout.tsx` | ported | Login/browser |
| 20 | `client/src/components/Chat/Input/ChatForm.tsx` | ported | Client tests/browser |
| 21 | `OneCodeProjectButton.test.tsx` | ported | Client tests |
| 22 | `OneCodeProjectButton.tsx` | ported | Client tests/browser |
| 23 | `client/src/components/Chat/Landing.tsx` modification | superseded-by-v0.8.7 | `customWelcome`/browser |
| 24 | `DiagnosticsTab.tsx` | ported | Client tests/browser |
| 25 | `EvidenceTab.tsx` | ported | Client tests/browser |
| 26 | `ModelConfigTab.tsx` | ported | Client tests/browser |
| 27 | `OneCodeConsolePanel.test.tsx` | ported | Client tests |
| 28 | `OneCodeConsolePanel.tsx` | ported | Client tests/browser |
| 29 | `ProjectTab.tsx` | ported | Client tests/browser |
| 30 | `RunsTab.tsx` | ported | Client tests/browser |
| 31 | `VerifierTab.tsx` | ported | Client tests/browser |
| 32 | `SidePanelGroup.test.tsx` | ported | Client tests |
| 33 | `SidePanelGroup.tsx` | ported | Client tests/browser |
| 34 | `client/src/hooks/Chat/useChatFunctions.ts` | ported | Metadata tests/live run |
| 35 | `client/src/hooks/Nav/useSideNavLinks.ts` | ported | Client tests/browser |
| 36 | `client/src/locales/en/translation.json` | ported | Client build |
| 37 | `client/src/locales/zh-Hans/translation.json` | ported | Client build/browser |
| 38 | `client/src/onecode/brand.test.ts` | ported | Brand tests |
| 39 | `client/src/onecode/brand.ts` | ported | Brand tests/browser |
| 40 | `client/src/onecode/console.ts` | ported | Console tests/browser |
| 41 | `client/src/onecode/project.test.ts` | ported | Client tests |
| 42 | `client/src/onecode/project.ts` | ported | Client tests/browser |
| 43 | `client/vite.config.ts` | ported | Client/PWA build |
| 44 | `librechat.yaml` | ported | Config review/live shell |
| 45 | `package.json` | ported | Smoke registration/build |
| 46 | `initialize.spec.ts` | ported | Endpoint tests |
| 47 | `initialize.ts` | ported | Endpoint tests |
| 48 | `onecode.spec.ts` | ported | Endpoint tests |
| 49 | `onecode.ts` | ported | LangChain one-request test |
| 50 | `packages/api/src/types/http.ts` | ported | API build |
| 51 | `packages/data-provider/src/api-endpoints.ts` | ported | Data-provider build |
| 52 | `packages/data-provider/src/data-service.ts` | ported | Data-provider build |
| 53 | `packages/data-provider/src/types.ts` | ported | Data-provider build |
| 54 | `scripts/onecode-smoke.mjs` | ported | Live API smoke |

Summary: 47 `ported`, 7 `superseded-by-v0.8.7`, 0 `approved-removal`.

## Remaining Risks

- Optional Meilisearch and RAG services remain outside this local shell scope;
  their absence can produce bounded warnings while chat and OneCode stay healthy.
- The upstream model may still return an invalid plan. OneCode fails closed and
  records evidence; improving model quality is separate from execution safety.
- `librechat.yaml` is intentionally tracked with force because upstream ignores
  local runtime config files. Future upgrades must preserve that tracked file.
- At the end of the July 15 phase, no merge, push, tag, deployment, worktree
  deletion, or operator-shell cutover had been performed. On July 16 the
  OneCode commits were locally integrated and authorized for publication to the
  existing feature branch. LibreChat publication, deployment, and shell cutover
  remain separate explicit decisions.

## Stop Condition

The isolated shell, delayed fixture, and browser session were stopped after
verification. Ports `14080`, `19080`, `39017`, and `16780` had no listeners,
and the final runtime status was `stopped`.
