# OneCode Console Panel Design

Date: 2026-05-30
Status: Approved direction
Scope: `<private-development-workspace>` and `<local-user-path>`

## Goal

Productize the remaining OneCode kernel capabilities inside the LibreChat shell as a dedicated right-side control panel while keeping OneCode core as the only execution and evidence source of truth.

## Non-Goals

- Do not involve `oneword-agent-gateway`, gateway products, or any other project line.
- Do not build a full IDE, Monaco editor, arbitrary file browser, or visual diff editor in this phase.
- Do not expose raw filesystem access outside `ONECODE_ALLOWED_WORKSPACE_ROOTS`.
- Do not replace LibreChat's chat/conversation shell.

## Product Shape

The existing OneCode input-bar button remains the lightweight entry point beside attachments. It keeps project selection, new project creation, MCP sync, and a new `打开控制台` action.

The new `OneCode Console` is a right-side panel, matching LibreChat's existing resizable side-panel behavior. It is dense, operational, and developer-console-like. It has five tabs:

1. `项目`
   - Active workspace
   - Allowed roots
   - Git status
   - Verifier policy status
   - MCP sync status
   - Actions: refresh, initialize project, sync MCP

2. `运行`
   - Recent runs list
   - Status, reason, delivery status, next action, checkpoint count
   - Actions: inspect, resume when available, copy run ID

3. `证据`
   - Selected run detail
   - Ledger path, manifest path, checkpoint count
   - Assets summary
   - Raw evidence JSON viewer for ledger/manifest/checkpoints

4. `验证`
   - Available verifier presets
   - Current verifier policy
   - Actions: initialize default policy, overwrite policy with selected presets
   - Policy errors shown verbatim

5. `诊断`
   - Doctor result
   - Self-audit result
   - OneCode API health and shell bridge status
   - Actions: run doctor, run self-audit

## OneCode API Additions

Existing endpoints remain:

- `GET /v1/onecode/project/status`
- `POST /v1/onecode/project/init`
- `GET /v1/onecode/runs`
- `GET /v1/onecode/runs/<run_id>/inspect`
- `POST /v1/onecode/runs/<run_id>/resume`

New endpoints:

- `GET /v1/onecode/verifier/presets`
  - Returns `verifier_policy_presets_summary()`.

- `GET /v1/onecode/verifier/policy?workspace=...`
  - Returns whether `.onecode/verifier-policy.json` exists.
  - If present, returns parsed policy JSON and validation status.
  - If invalid, returns `valid: false` and `error`.

- `POST /v1/onecode/verifier/policy`
  - Body: `{ workspace, presetIds?: string[], force?: boolean }`.
  - Writes `.onecode/verifier-policy.json` through `write_verifier_policy`.
  - Rejects overwrite unless `force: true`.

- `POST /v1/onecode/doctor`
  - Runs `run_doctor()` and returns JSON.

- `POST /v1/onecode/audit-self`
  - Runs `run_self_audit()` and returns JSON.

- `GET /v1/onecode/runs/<run_id>/evidence?workspace=...`
  - Returns inspect summary plus raw `ledger`, `manifest`, and parsed checkpoint documents.
  - Missing/corrupt files are represented as structured errors, not tracebacks.

All workspace-aware endpoints use the same allowed-root guard already added to `src/onecode/web/api.py`.

## LibreChat Backend Additions

Add matching local-only authenticated routes under `/api/onecode/*`:

- `GET /api/onecode/verifier/presets`
- `GET /api/onecode/verifier/policy`
- `POST /api/onecode/verifier/policy`
- `POST /api/onecode/doctor`
- `POST /api/onecode/audit-self`
- `GET /api/onecode/runs/:runId/evidence`

These routes delegate to `api/server/services/OneCode/projectPicker.js`, which remains the shell bridge for OneCode local operations. It validates workspace roots before forwarding to OneCode.

## Data Provider And Client API

Extend `packages/data-provider` with endpoint builders, response types, and `dataService` functions for all new routes.

Extend `client/src/onecode/project.ts` with normalized helpers:

- `getOneCodeVerifierPresets`
- `getOneCodeVerifierPolicy`
- `writeOneCodeVerifierPolicy`
- `runOneCodeDoctor`
- `runOneCodeSelfAudit`
- `getOneCodeRunEvidence`

The helper layer remains the only client-side module that imports `librechat-data-provider` OneCode APIs.

## Frontend Architecture

Create a focused OneCode console feature area:

- `client/src/onecode/console.ts`
  - Console state helpers and tab constants.

- `client/src/components/OneCode/OneCodeConsolePanel.tsx`
  - Top-level panel with tabs, selected workspace, refresh behavior, and action wiring.

- `client/src/components/OneCode/ProjectTab.tsx`
- `client/src/components/OneCode/RunsTab.tsx`
- `client/src/components/OneCode/EvidenceTab.tsx`
- `client/src/components/OneCode/VerifierTab.tsx`
- `client/src/components/OneCode/DiagnosticsTab.tsx`
  - Small tab-specific presentational/action components.

Add tests beside the new feature files.

The existing `OneCodeProjectButton.tsx` gains `打开控制台`. Selecting it opens the panel. Existing project selection behavior stays intact.

## Panel Mounting

Use LibreChat's existing right-side panel pattern. The panel should appear beside the messages view on desktop and as an overlay on small screens, consistent with `ArtifactsPanel`.

If a global side-panel registry is too expensive to wire in this phase, use a OneCode-specific atom/state bridge from `ChatForm` to `SidePanelGroup`. The implementation must remain small and reversible.

## Error Handling

- Shell backend returns `400` for bad workspace or bad request, `502` for OneCode API bridge failures, and preserves the OneCode error message.
- Client helpers return `undefined` only for empty workspace inputs. Failed requests surface in the panel as compact error rows.
- Doctor and self-audit results are shown even when status is failed.
- Evidence endpoint returns partial payloads when one checkpoint is corrupt, including which file failed.

## Testing

OneCode:

- Unit tests for each new handler in `tests/test_web_api.py`.
- Coverage for valid policy, missing policy, invalid policy, overwrite rejection, doctor, self-audit, evidence payload, and outside-root rejection.
- Full `bash scripts/verify.sh`.

LibreChat backend:

- Jest tests for service URL construction and workspace guard forwarding.
- Route tests for auth/local-only behavior and route delegation.

Data provider/client:

- Tests for endpoint builders and helper normalization.
- Component tests for tab rendering and action calls.
- Focused Jest tests for `OneCodeConsolePanel` and updated `OneCodeProjectButton`.

Smoke:

- Start local shell on non-conflicting ports.
- Login.
- Call `/api/onecode/projects/status`, `/api/onecode/verifier/presets`, `/api/onecode/doctor`, and `/api/onecode/runs/:runId/evidence`.

## Success Criteria

- A user can open LibreChat, choose a OneCode project, and inspect all core OneCode runtime state from the panel.
- Runs, evidence, verifier policy, doctor, and self-audit are available without using the terminal.
- Workspace isolation remains enforced in both OneCode API and LibreChat shell bridge.
- Existing chat and OneCode message execution behavior are unchanged.
