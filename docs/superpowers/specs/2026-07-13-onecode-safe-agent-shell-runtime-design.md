# OneCode Safe-Agent Shell Runtime Design

Date: 2026-07-13
Status: Approved
Scope: OneCode shell task routing and guarded execution

## Objective

Make the LibreChat shell a real OneCode task surface: route non-trivial work
through the latest verified Safe-Agent-Skills catalog, plan against an explicit
tool contract, execute workspace-bounded reads automatically, and require
approval before side effects.

## Selected approach

Use an in-process OneCode adapter around the installed
`safe-agent-router-task-pack` command. The adapter consumes Schema v2 JSON,
validates the registry and trusted-only selection boundary, reduces the output
to bounded planning context, and records a compact evidence summary.

The catalog remains a standalone checkout. OneCode does not vendor catalog
entries or maintain a second registry. This makes upgrades immediately
available after the standalone router is updated while preserving a single
provenance and hash authority.

## Rejected approaches

### Manifest-only integration

Copying selected manifests into `.onecode/skills` would improve status output
but would not load task-pack guidance or enable tools. It also creates a stale
second catalog.

### External general-purpose agent delegation

Forwarding shell requests to Codex, Claude, or another autonomous runtime would
expand permissions and deployment scope beyond OneCode's current approval and
evidence contracts.

## Components

### Safe-Agent router adapter

A focused kernel module will:

- resolve `safe-agent-router-task-pack` from `PATH`;
- invoke it with the user task and `--format json`;
- enforce a timeout and output-size limit;
- require Schema v2, `routing_status=complete`,
  `registry_verification.status=ok`, and zero tampered records;
- accept only skills whose status is `trusted`;
- expose selected scenario IDs, skill names, execution order, expected output,
  verifier expectations, and the method-only safety boundary;
- exclude raw source bodies, credentials, arbitrary commands, and authority
  escalation fields;
- return a typed unavailable or invalid result instead of throwing away the
  reason.

The adapter never executes a selected skill. It supplies bounded method context
to the model planner.

### Task classification

Replace the single boolean heuristic with a three-way classification:

- `chat`: questions and explanatory conversation;
- `read_task`: inspect, check, review, list, search, diagnose, or report on the
  workspace;
- `change_task`: create, modify, repair, run tests, execute commands, install,
  or otherwise request side effects.

Explicit prefixes remain supported for compatibility. File paths and imperative
language are signals, while a question mark alone does not force task requests
back into chat.

LibreChat metadata may explicitly request a mode. The server validates that
value and otherwise uses deterministic classification.

### Model planning context

The model planner receives:

1. the user task;
2. task mode;
3. compact Safe-Agent task-pack guidance when available;
4. an exact list of supported tools and parameter schemas;
5. the approval rules for each tool;
6. an instruction to return `no_action` with a reason when no valid plan can be
   produced.

Both Responses and Chat Completions providers use the same canonical planning
contract. The Chat provider's prose prompt must not contradict the JSON schema.

### Tool registry

Add workspace-bounded tools:

- `list_files`: list relative files with count and depth limits;
- `read_text`: read UTF-8 text with byte and line limits;
- `search_text`: literal or regular-expression search with match limits;
- `git_status`: return porcelain status for the selected workspace;
- `run_command`: execute an argv list in the selected workspace;
- existing `write_text` and `patch_text` tools.

The first four tools are read-only and may run automatically. `run_command`,
`write_text`, and `patch_text` require approval. Dependency installation is a
`run_command` action and therefore also requires approval. Commands are never
accepted as an interpolated shell string.

Read tools resolve every path through `PathGuard`, reject symlink escapes, and
bound output before it enters evidence or model context.

### Approval flow

The OpenAI-compatible chat response can return an approval-required OneCode
result containing a stable plan ID and a bounded plan summary. No guarded tool
runs when approval is absent.

An approval endpoint accepts the plan ID and an explicit decision. Approved
plans are revalidated against the stored digest, workspace, tool registry, and
current guardrails before execution. Rejected or stale plans remain
non-executed evidence.

### Workspace selection

`onecode shell` defaults to `onecode_root`, not a fixed temporary directory.
`--workspace` remains authoritative. Runtime-only LibreChat configuration and
MongoDB state use a separate temporary state directory so they do not pollute
the selected project.

Allowed workspace roots are derived from the selected workspace and remain
enforced by the Web API.

### Effective model configuration

Resolve the effective provider, endpoint, model, and value source in one helper
used by chat, task planning, resume, diagnostics, and project status. Public
output includes source labels such as `environment`, `stored`, or `default` and
never includes the API key.

## Data flow

1. LibreChat sends messages and optional OneCode metadata.
2. The Web API resolves the workspace and task mode.
3. Non-trivial tasks call the Safe-Agent router adapter.
4. The planner receives the task pack and canonical tool schema.
5. The plan validator rejects unknown tools and invalid parameters.
6. A read-only plan executes through `ExecutionEngine` and OneCode guards.
7. A guarded plan is persisted as approval-required without execution.
8. Approval revalidates and executes the persisted plan.
9. Shell projection returns outcome, selected skills, approval state, and
   evidence references.

## Error handling

- Missing router: continue with OneCode's local tool contract and record
  `safe_agent_router_unavailable`.
- Invalid or untrusted router output: stop task planning with
  `safe_agent_router_invalid`; do not silently ignore integrity failures.
- No matching Safe-Agent scenario: continue with an empty method pack and
  record `no_matching_scenario`.
- Empty model plan: return `no_actionable_plan` with the model-plan trace.
- Unknown tool: reject before execution with `unsupported_tool`.
- Missing approval: return `approval_required`, not completed or skipped.
- Stale or modified plan: reject with `approval_plan_mismatch`.
- Model configuration drift: expose effective source metadata in diagnostics.

## Evidence boundary

Run evidence may include:

- router route ID and schema version;
- registry verification counts;
- selected scenario and trusted skill names;
- task-pack digest;
- tool names, bounded parameters, results, and approval state;
- effective model configuration without secrets.

Run evidence must not include API keys, raw skill source bodies, unrelated
environment variables, or unrestricted command output.

## Compatibility

- Existing chat responses remain OpenAI-compatible.
- Existing explicit task prefixes remain valid.
- Existing write and patch plans continue through the same runner and guards.
- Existing `.onecode/skills` metadata evidence remains supported, but the
  Safe-Agent task pack becomes the runtime method source.
- CLI `run`, `run-plan`, and TUI behavior remain unchanged unless they opt into
  the new router adapter.

## Testing

Use test-driven development for each boundary:

1. Router adapter tests cover latest Schema v2, trusted-only validation,
   timeout, missing command, invalid JSON, tampering, and size limits.
2. Classification tests cover Chinese and English chat, read, change, question,
   prefix, and path cases.
3. Tool tests cover normal reads, bounds, binary files, traversal, symlink
   escape, regex errors, Git workspaces, and approval requirements.
4. Provider contract tests prove both providers receive identical tool and
   task-pack semantics.
5. Web tests prove empty plans are errors, read plans execute, guarded plans do
   not execute, approval revalidation works, and public config is redacted.
6. Shell launcher tests prove workspace and runtime-state separation.
7. The relevant unit suite, full project verification script, and a live
   `14080` shell smoke test close the change.

## Acceptance criteria

The issue record's nine acceptance criteria are authoritative. The live smoke
test must additionally demonstrate:

- `检查当前项目状态` produces a real read-only execution trace;
- the result includes the latest Safe-Agent Schema v2 route summary;
- `修改 README.md` returns approval-required without changing the file;
- an approved bounded change executes and records evidence;
- an empty plan is visibly non-successful.
