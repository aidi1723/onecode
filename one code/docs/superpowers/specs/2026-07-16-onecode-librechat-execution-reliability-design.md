# OneCode LibreChat Execution Reliability Design

Date: 2026-07-16
Status: Approved direction, pending written-spec review
Scope: OneCode runtime, OpenAI-compatible web API, shell projection, and OneCode-specific LibreChat integration

## Problem

The OneCode and LibreChat integration has a sound approval boundary on the main
chat path, but the full product flow is not reliable enough to treat natural
language tasks as controlled execution requests.

The remaining failures form one connected workflow problem:

- common task phrasing is classified as ordinary chat and never reaches tools;
- resume can execute a newly generated mutating plan without explicit approval;
- approval is represented mainly as prose and requires an undocumented exact
  chat command;
- a missing project selection can fall back to the server workspace;
- shell projection cannot express a structured pending approval target;
- timeout, title generation, pseudo-streaming, skill status, Git status, and
  startup diagnostics create inconsistent operator feedback.

These issues must be closed as one release program because partial fixes can
leave the system safe but unusable, or usable but inconsistent with its safety
policy.

## Goals

1. Enforce one approval invariant across chat, resume, and Console workflows.
2. Route common Chinese and English task requests into the correct execution
   mode without turning ordinary explanations into tasks.
3. Prevent LibreChat task execution when no project has been selected.
4. Make pending plans discoverable and approvable through structured APIs and
   Console controls.
5. Represent approval state in the shell contract without parsing assistant
   prose.
6. Give users immediate and accurate planning, waiting, failure, and completion
   feedback.
7. Keep the changes compatible with the existing OneCode security boundary,
   LibreChat information architecture, and local-shell deployment model.

## Non-Goals

- Replacing deterministic task classification with an LLM classifier.
- Implementing token-by-token planning or execution streaming.
- Replacing LibreChat's component system or introducing a new UI framework.
- Redesigning LibreChat navigation, chat history, or general endpoint behavior.
- Automatically searching arbitrary filesystem locations for projects or the
  LibreChat installation.
- Merging project skill manifests and Safe-Agent runtime routing into one
  subsystem.

## Product Invariants

### Approval

- A plan containing `write_text`, `patch_text`, `run_command`, or any future
  approval-required tool must not execute before an explicit approval decision.
- The invariant applies equally to new chat tasks, resumed runs, repairs, and
  Console-triggered operations.
- Approving a stored plan executes that exact claimed and revalidated plan.
- A resume request creates a new plan. If the new plan mutates state, it requires
  a new approval even when the source run was previously approved.
- Rejected, completed, failed, or already claimed plans cannot be replayed.

### Workspace

- OneCode shell mode requires an explicit workspace for read tasks, change
  tasks, plan approval, plan listing, run inspection, and run resume.
- Direct chat may run without a workspace because it does not access project
  tools.
- Standalone API deployments may retain the existing default workspace behavior
  unless strict workspace mode is enabled.
- The shell launcher enables strict workspace mode for the LibreChat integration.
- The active workspace is shown on every Console action that can read or change
  project state.

### Errors

- OneCode model requests are never silently retried by LibreChat.
- Validation, conflict, configuration, provider, and timeout failures retain
  distinct status codes and user-facing states.
- A failure must not be represented as a successful chat completion.

## Architecture

The work is divided into six bounded components that ship together but remain
independently testable.

1. **Task intent classification** determines `chat`, `read_task`, or
   `change_task` using explicit mode first and deterministic language rules
   second.
2. **Workspace policy** decides whether an explicit workspace is required for
   the selected operation and validates it against allowed roots.
3. **Approval service** persists, lists, claims, rejects, executes, and archives
   approval plans.
4. **Shell projection v5** translates runtime results into a stable operator
   contract, including structured approval state.
5. **LibreChat OneCode client** transports workspace and mode metadata and
   exposes plan, approval, run, and evidence APIs.
6. **Console interaction layer** renders compact operational states and lets the
   user approve or reject plans without writing chat control commands.

No new third-party runtime dependency is required. OneCode remains Python;
LibreChat remains TypeScript, React, its existing request layer, and its current
component primitives.

## Request Flow

### Chat Completion

The OneCode chat handler processes requests in this order:

1. Extract and validate the latest user message.
2. Read optional `metadata.onecode_mode` and raw workspace metadata.
3. Detect an exact approval control message.
4. Classify the task using explicit mode or deterministic inference.
5. Apply workspace policy for the selected operation.
6. Route `chat` to direct model chat.
7. Route `read_task` and `change_task` to model planning with explicit approval
   enabled.
8. Return a structured result and shell projection.

Workspace resolution must no longer happen before the server knows whether the
request is project-scoped. In strict shell mode, a project-scoped request with
no explicit workspace returns HTTP 400 with `workspace_required` and performs
no model call, evidence write, plan persistence, command, or file operation.

### Resume

Resume requires an explicit workspace and calls model planning with
`require_explicit_approval=True`. A read-only resume may complete normally. A
mutating resume returns `approval_required` and persists a new plan. The existing
plan approval endpoint remains the only path that executes an approved stored
plan without asking for another approval.

### Approval

The approval service exposes:

- `GET /v1/onecode/plans?workspace=<path>&status=pending`
- `POST /v1/onecode/plans/<plan_id>/approval`

Plan listing returns only bounded, redacted summaries required for a decision:

- plan ID and plan hash;
- creation time and task summary;
- workspace;
- action count and approval-required tool names;
- redacted file, patch, and command action summaries;
- current lifecycle state.

It does not return full file content, secrets, raw model prompts, or unrestricted
command output.

Chat approval remains as an accessibility and compatibility path. Its parser is
anchored to the whole message and accepts only an optional polite prefix,
reasonable whitespace, an optional backtick wrapper, an explicit approve or
reject verb, and a 32-character hexadecimal plan ID. The plan ID is normalized
to lowercase before lookup. Arbitrary surrounding prose is rejected.

## Task Classification

Classification remains deterministic and follows this precedence:

1. A valid explicit mode wins.
2. A mutation action combined with a project object classifies as
   `change_task`.
3. A read or analysis action combined with a project object classifies as
   `read_task`.
4. Explanation and general questions remain `chat` unless they contain a clear
   project operation.
5. Unmatched input remains `chat`.

Mutation actions include Chinese forms such as `写`, `写个`, `写一个`, `修`,
`修一下`, `创建`, `运行`, and `跑`, and English forms such as `fix`, `create`,
`write`, `edit`, `run tests`, and `run command`.

Project objects include explicit paths, recognized source or document
extensions, and bounded nouns such as project, repository, code, tests, command,
and file. Generic nouns are not sufficient by themselves. For example,
`解释文件系统` remains chat, while `写一个 hello.txt` is a change task.

The classifier exposes a non-sensitive reason code for diagnostics, such as
`explicit_mode`, `mutation_action_with_path`, `read_action_with_repository`, or
`default_chat`. It does not record the complete user message in status payloads.

## Metadata Contract

LibreChat sends the following OneCode-specific metadata:

```json
{
  "workspace": "/absolute/selected/project",
  "onecode_mode": "read_task"
}
```

`workspace` is omitted only when no project is selected. `onecode_mode` is
omitted for automatic inference and otherwise accepts `chat`, `read_task`, or
`change_task`. The UI label `自动` is a client state and is not sent as an API value.

Invalid modes return HTTP 400 `invalid_task_mode`. A missing workspace on a
project-scoped operation in strict mode returns HTTP 400 `workspace_required`.
An outside-root workspace continues to return HTTP 400 `invalid_workspace`.

## Shell Projection v5

Shell projection v5 adds an `approval_state` object and makes approval the
recommended action when a plan is pending:

```json
{
  "version": 5,
  "status_label": "halted",
  "severity": "blocked",
  "next_action": "approve",
  "approval_state": {
    "required": true,
    "plan_id": "0123456789abcdef0123456789abcdef",
    "status": "pending"
  }
}
```

For results unrelated to approval, `approval_state.required` is `false` and the
remaining approval fields are null. Raw run status and severity remain unchanged:
pending approval is blocked, not failed or completed.

The v4 schema and fixture remain in the repository as historical contracts.
OneCode and LibreChat update to v5 atomically in this release. Tests verify the
exact v5 field set and the projection of stored historical runs.

## LibreChat Interaction Design

The existing OneCode LibreChat `DESIGN.md` remains the visual source of truth.
The integration continues to use LibreChat tokens, compact density, existing
focus behavior, and the right-side Console. No new component framework is
introduced.

### Mode Control

The input-bar OneCode project popover contains a compact segmented control:

- `自动`
- `问答`
- `读取`
- `变更`

The selected mode persists with the local OneCode project preference. Automatic
mode is the default. The active project remains more visually prominent than the
mode so the control does not turn the input bar into an IDE toolbar.

### Approval View

The Console adds an `审批` tab beside the existing operational tabs. It shows
pending plans for the selected workspace as compact bounded items. Each item
contains:

- task summary and creation time;
- monospaced plan ID;
- affected files or redacted command;
- action count and status;
- explicit `批准` and `拒绝` commands with familiar check and close icons.

The buttons use the existing LibreChat button and focus primitives. They remain
text-labelled because the commands are consequential. Approve is not styled as
ordinary success until execution completes. Reject uses the existing danger
treatment. Both buttons are disabled while the decision is in flight.

The view defines loading, empty, pending, executing, completed, rejected,
conflict, and error states. The empty state is one short sentence. Raw kernel
error details are available in a compact expandable area.

### Planning Feedback

As soon as a OneCode task submission begins, the chat surface and Console show
`OneCode 正在规划`. A pending mutation changes to `等待批准`. Execution after
approval changes to `正在执行` and then the terminal result state.

This is client-side request state, not false incremental server output. The
current single-chunk SSE compatibility response remains until a separate true
streaming design is approved.

### Accessibility And Responsive Behavior

- All controls are keyboard reachable and retain visible focus rings.
- Approval buttons have localized accessible names.
- Paths, hashes, commands, and plan IDs wrap or truncate without widening the
  panel.
- On small screens the Console continues to use its full-screen presentation.
- Approval actions remain visible without overlapping the details area.
- Status is communicated with text as well as color.

## Error Model

LibreChat preserves these distinctions:

| Status | OneCode type | UI behavior |
| --- | --- | --- |
| 400 | `workspace_required` | Prompt the user to select a project |
| 400 | `invalid_task_mode` | Reset the invalid local mode and show the error |
| 400 | `invalid_workspace` | Show the rejected path and allowed-root guidance |
| 409 | `invalid_approval_plan` | Refresh pending plans and show the terminal state |
| 502 | `model_provider_error` or `invalid_model_plan` | Show provider/planning failure without retry |
| 503 | `model_configuration_missing` | Link the user to OneCode model settings |
| 504 | `model_provider_timeout` | Show timeout and allow a deliberate manual retry |

`maxRetries: 0` remains enforced in both generated runtime configuration and
the OneCode endpoint adapter. Direct chat and task planning both use
`ONECODE_MODEL_TIMEOUT_SECONDS`.

## Secondary Consistency Work

The same release includes the following bounded cleanup:

- Set OneCode `titleConvo: false` so title generation does not issue a second
  OneCode model request.
- Remove the unreachable `chat_fallback` formatting branch.
- Present project skill manifests as `项目技能清单` and Safe-Agent routing as
  `运行时路由`, without implying that a missing project manifest means runtime
  skills are unavailable.
- Detect whether a workspace is a Git repository or is contained in a parent
  Git repository, and report those states separately.
- Include the resolved LibreChat directory in shell preflight failures and show
  the exact `--librechat-dir` correction command.
- Keep the current adjacent-directory default because it is correct for the
  supported layout.

## Test Strategy

### OneCode Unit And Contract Tests

- Table-driven positive classification tests for all known failed phrases.
- Negative classification tests for explanations and ambiguous nouns.
- Explicit mode override and invalid mode tests.
- Strict workspace tests proving no model, plan, evidence, command, or file
  operation occurs before `workspace_required`.
- Resume tests proving read-only completion and mutating-plan approval.
- Approval parser acceptance and rejection tables.
- Pending plan list redaction, workspace isolation, lifecycle, and replay tests.
- Shell projection v5 schema, approval state, and historical-run tests.
- Direct chat timeout configuration tests.

### LibreChat Tests

- OneCode metadata construction for workspace and explicit mode.
- Endpoint adapter tests preserving `maxRetries: 0`.
- Data-provider and API route tests for plan listing and approval.
- Console tests for loading, empty, approval, rejection, conflict, and error
  states.
- Input popover tests for automatic and explicit modes.
- Error mapping tests for 400, 409, 502, 503, and 504.
- Configuration test proving OneCode title generation is disabled.

### Integration And Browser Verification

The release candidate runs these end-to-end scenarios against a real local
OneCode and LibreChat shell:

1. Natural-language read task with a selected project.
2. Natural-language change task that stops before mutation.
3. Approval through Console followed by successful execution.
4. Rejection through Console with no mutation.
5. Mutating resume that returns a second approval requirement.
6. Project-scoped task with no selected workspace.
7. Provider timeout with exactly one upstream request.
8. Invalid or replayed approval plan.

Playwright verifies the Console on desktop and mobile, including keyboard focus,
button disabled states, path wrapping, pending state, raw error details, and the
absence of overlapping controls.

## Delivery Sequence

All work belongs to one release program but is merged in dependency order:

1. Approval and workspace safety invariants.
2. Classifier and explicit mode contract.
3. Pending plan and shell projection v5 contracts.
4. LibreChat API and data-provider integration.
5. Console approval and mode controls.
6. Timeout, title, status semantics, Git, startup diagnostics, and dead-code
   cleanup.
7. Full regression, build, browser, and live-shell verification.

Each stage must pass its targeted tests before the next begins. OneCode and
LibreChat contract changes are released together after the final compatibility
gate. No intermediate release may expose an approval action without a usable
approval target or enable strict workspace mode before LibreChat sends the
required workspace.

## Acceptance Criteria

- Every known failed task phrase is classified correctly and the negative suite
  remains chat.
- Chat and resume produce zero physical mutations before approval.
- A project-scoped LibreChat request without a selected workspace returns a
  visible selection error and creates no evidence or plan artifacts.
- A user can list, inspect, approve, and reject a pending plan entirely through
  the Console.
- Shell projection represents pending approval with `next_action=approve` and a
  structured plan ID.
- Approval replay remains rejected.
- 502 and 504 responses produce one upstream request and visible distinct errors.
- OneCode title generation produces no extra OneCode request.
- Desktop and mobile Console flows pass keyboard, focus, wrapping, and overlap
  checks.
- OneCode tests, LibreChat targeted tests, relevant builds, Playwright flows,
  and the live-shell matrix all pass before release.

## Residual Risks

- Deterministic classification will always have a long tail of ambiguous natural
  language. Explicit mode is the controlled escape hatch.
- Strict workspace mode is a behavior change for the shell integration and must
  be enabled only after the matching LibreChat metadata release is present.
- Projection v5 requires an atomic two-repository release because current
  consumers validate an exact field contract.
- Client-side planning feedback improves perceived responsiveness but does not
  provide server-side progress or cancellation checkpoints.
- Pending plan summaries must remain bounded and redacted as new tools are added;
  every future approval-required tool needs an explicit safe summary adapter.
