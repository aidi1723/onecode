# OneCode LibreChat B Mapping Design

Date: 2026-05-30
Status: Approved for implementation planning
Scope: OneCode core plus the local LibreChat shell

## Product Boundary

OneCode remains a standalone agent project. LibreChat is only the Web shell for OneCode. This work must not depend on, import, route through, or configure any gateway product, OneWord gateway, or other project line.

The target is option B: productize the main OneCode agent loop inside LibreChat without turning LibreChat into a full IDE. The shell should make the project binding, run evidence, verifier state, and resume flow visible and usable. OneCode core remains responsible for execution, workspace enforcement, evidence, verification, and resume semantics.

## Goals

- Let the user select or create a project from the LibreChat input area without typing absolute paths.
- Make the active project state visible: workspace path, MCP sync state, verifier policy state, and safe workspace boundary state.
- Initialize new empty projects enough for OneCode work: create directory, run `git init`, and create a default verifier policy.
- Expose OneCode run evidence in the shell: recent runs, status, reason, ledger path, manifest path, inspect state, and whether resume is available.
- Allow a user to continue a resumable run from the shell.
- Restrict workspace selection and OneCode API execution to configured local workspace roots.
- Keep attachments from bypassing workspace controls. In the first version, attachment metadata may travel as chat context, but attachments do not grant filesystem access.

## Non-Goals

- No file tree or Explorer panel.
- No full diff editor.
- No Git branch switching UI.
- No multi-user remote workspace manager.
- No gateway integration.
- No replacement of LibreChat conversation, authentication, or MCP architecture.

## Architecture

The integration has three layers.

1. LibreChat client:
   - Keeps the project button beside the attachment control.
   - Stores active workspace and recent workspaces in browser local storage.
   - Shows a compact project status popover.
   - Sends `metadata.workspace` only for the `OneCode` custom endpoint.
   - Offers actions for selecting, creating, syncing MCP, initializing verifier policy, viewing runs, inspecting a run, and resuming a run.

2. LibreChat backend:
   - Owns local-only project picker routes under `/api/onecode`.
   - Uses macOS folder picker for local selection, with prompt fallback only as an error fallback.
   - Creates projects under an allowed parent directory.
   - Syncs the `onecode-filesystem` MCP server for the active workspace.
   - Proxies OneCode status and run-evidence requests to the local OneCode API.
   - Rejects non-loopback requests for local filesystem picker and project creation.

3. OneCode core:
   - Continues exposing OpenAI-compatible `/v1/chat/completions` and `/v1/models`.
   - Adds OneCode-native JSON endpoints for project status, verifier policy initialization, recent runs, inspect, and resume metadata.
   - Enforces configured allowed workspace roots before executing a request.
   - Keeps append-only evidence as the source of truth.

## API Shape

OneCode core should expose these local JSON endpoints:

- `GET /v1/onecode/project/status?workspace=<path>`
  - Returns workspace existence, allowed-root result, git repository state, verifier policy state, and latest run summary.
- `POST /v1/onecode/project/init`
  - Body: `{ "workspace": "/abs/path", "git": true, "verifierPolicy": true }`
  - Creates `.git` when requested and missing.
  - Writes `.onecode/verifier-policy.json` using the default preset when requested and missing.
- `GET /v1/onecode/runs?workspace=<path>&limit=20`
  - Returns recent run summaries using the existing run listing/inspection kernel.
- `GET /v1/onecode/runs/<run_id>/inspect?workspace=<path>`
  - Returns the same semantic inspect result as the CLI.
- `POST /v1/onecode/runs/<run_id>/resume`
  - Body: `{ "workspace": "/abs/path", "message": "..." }`
  - Runs a model task with `resume_from_run_id=<run_id>` when the inspected state allows resume.

LibreChat backend should expose matching authenticated local shell routes:

- `POST /api/onecode/projects/pick`
- `POST /api/onecode/projects/create`
- `POST /api/onecode/projects/mcp/sync`
- `GET /api/onecode/projects/status?workspace=<path>`
- `POST /api/onecode/projects/init`
- `GET /api/onecode/runs?workspace=<path>&limit=20`
- `GET /api/onecode/runs/:runId/inspect?workspace=<path>`
- `POST /api/onecode/runs/:runId/resume`

## Workspace Safety

OneCode and LibreChat must both apply workspace guards.

- OneCode reads `ONECODE_ALLOWED_WORKSPACE_ROOTS`, a path-list separated with `os.pathsep`.
- If the variable is empty, OneCode defaults to the configured `ONECODE_WORKSPACE_ROOT`.
- A requested workspace must exist, be a directory, and be equal to or inside one allowed root.
- LibreChat shell uses `ONECODE_ALLOWED_WORKSPACE_ROOTS` for project creation and selection status checks.
- The macOS picker may select any folder visually, but the backend must reject or mark it invalid if it is outside allowed roots.

## UI Behavior

The existing folder icon beside attachments remains the project entry point.

The popover should show:

- Current project basename and full path.
- Status badges:
  - Project selected or not selected.
  - MCP synced, syncing, or failed.
  - Verifier policy present or missing.
  - Workspace allowed or blocked.
- Actions:
  - Use existing folder.
  - New blank project.
  - Sync filesystem MCP.
  - Initialize verifier policy.
  - View recent runs.
  - Inspect latest run.
  - Continue latest resumable run.
  - Clear project binding.

The UI should stay compact and utility-first. It should not introduce a landing page or large dashboard. Cards are acceptable only for individual run rows or a small popover panel.

## Run Evidence UX

The shell should not parse ledger internals in the browser. It should render OneCode API summaries:

- Run ID.
- Status.
- Reason.
- Created or updated time when available.
- Ledger path.
- Manifest path.
- Checkpoint count.
- Inspect result: healthy, corrupt, halted, completed, or resumable.
- Resume action only when OneCode reports that resume is allowed.

The chat response can continue to include the short run result. The run evidence panel gives the richer view.

## Attachments

LibreChat attachments remain LibreChat attachments. First version rules:

- Attachment names and ordinary message text may still be sent through the normal conversation.
- Attachment storage paths are not passed as OneCode workspace privileges.
- OneCode execution remains scoped only by `metadata.workspace` and allowed roots.
- A later version may add explicit attachment import into the active workspace, but that is out of scope here.

## Error Handling

- Missing workspace: chat still works, but project actions show no active project.
- Workspace outside allowed roots: block OneCode execution and show a clear local-shell error.
- Missing verifier policy: show a warning badge and offer initialization.
- MCP sync failure: keep the project selected, mark MCP failed, and allow retry.
- OneCode API unavailable: show the project popover with a connection error and keep local selection state.
- Inspect corruption: show the inspect status and disable resume.

## Testing

OneCode core tests:

- Workspace allowed-root acceptance and rejection.
- Project status endpoint.
- Project init endpoint creating git repository and verifier policy.
- Runs list endpoint using evidence directories.
- Inspect endpoint matching CLI semantics.
- Resume endpoint using `resume_from_run_id`.

LibreChat shell tests:

- Project picker rejects non-local requests.
- Project create rejects invalid or out-of-root project names.
- MCP sync still registers `onecode-filesystem`.
- Backend proxies project status, init, runs, inspect, and resume to OneCode.
- Client stores active workspace and sends metadata only for `OneCode`.
- Project popover renders status badges and actions from mocked responses.

Manual verification:

- Start local shell.
- Register or log in locally.
- Select an existing project via folder picker.
- Send a OneCode task and confirm output lands in selected workspace.
- Open recent runs and inspect the generated run.
- Create a new blank project and confirm `.git` plus `.onecode/verifier-policy.json`.

## Open Decisions Resolved

- The implementation follows option B.
- MCP is used for project file tools and isolation metadata in LibreChat, but OneCode core remains the execution engine.
- Evidence remains OneCode-owned and append-only.
- The first version is not an IDE.
