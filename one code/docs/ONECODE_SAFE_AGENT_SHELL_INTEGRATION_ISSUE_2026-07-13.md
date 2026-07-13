# OneCode Safe-Agent Shell Integration Issue

Date: 2026-07-13
Status: Confirmed
Severity: High
Affected surface: LibreChat shell, OneCode Web API, model planning, skill routing

## Summary

The local LibreChat shell was healthy at `http://127.0.0.1:14080`, but chat
requests could not reliably inspect or change the selected project. The
Safe-Agent-Skills repository and router were installed on the host, while the
OneCode shell runtime did not invoke the router or expose the tools required by
inspection tasks.

## User-visible symptoms

- Natural-language requests such as `检查当前项目...` could be classified as
  ordinary chat instead of OneCode tasks.
- A task could be reported as completed without reading files or executing a
  tool.
- Safe-Agent skill selection was not visible in shell run evidence.
- The shell used a temporary workspace instead of the OneCode repository.

## Evidence

- Shell project status reported workspace
  `/private/tmp/onecode-librechat-live`.
- Shell project status reported `skill_context.status=missing`,
  `skill_count=0`, and `dispatch_decision=stop`.
- Neither the OneCode project nor the temporary shell workspace contained
  `.onecode/skills` manifests.
- Run `6b44117346864792af21a78965b05b28` recorded
  `model_call_started` without `model_call_completed`.
- The following WAL record used the default `noop` intent and reported a
  completed result.
- The default execution tool registry exposed only `write_text` and
  `patch_text`.
- The installed Safe-Agent Router worked independently and verified 172
  catalog skills, 166 trusted skills, and zero tampered records.

## Root causes

1. `onecode shell` defaulted to a fixed temporary workspace.
2. The OneCode skill layer implemented metadata-only selection evidence and
   did not call the Safe-Agent Router.
3. Chat/task classification depended on a narrow prefix and keyword list.
4. The model prompt did not provide a complete, authoritative tool contract.
5. The execution registry lacked read-only project inspection tools and
   controlled shell/test tools.
6. Empty model plans were converted to a successful lightweight `noop` run.
7. Environment variables could override stored model configuration without a
   visible effective-configuration record.

## Safety decision

- Read-only workspace inspection may run automatically.
- File mutation, shell execution, tests with side effects, dependency
  installation, and network-affecting actions require a visible plan and
  explicit user approval.
- Safe-Agent task packs provide method guidance only. They never grant tool or
  filesystem authority.

## Latest Safe-Agent baseline

The integration target is the standalone `safe-agent-skills` checkout on
`main`, verified after fetching `origin`:

- commit: `c7e91bb8e9254ccab3ad852759ee62ade0260c11`
- package: `onecode-skill-sanitizer 0.2.0`
- router output: Schema v2
- registry: 172 total, 166 trusted, 0 tampered

OneCode must invoke the installed router dynamically. It must not copy a
snapshot of the catalog into the OneCode repository.

## Acceptance criteria

1. The shell defaults to the selected OneCode project workspace.
2. Non-trivial tasks receive a verified Schema v2 Safe-Agent task pack when
   the router is available.
3. Router unavailability or invalid output is explicit in run evidence and
   does not bypass OneCode policy.
4. Natural-language inspection requests enter task mode without requiring a
   magic prefix.
5. Read/list/search/git-status tools are workspace-bounded and automatic.
6. Mutating and shell actions stop at an approval-required result unless an
   explicit approval is supplied.
7. Empty plans return `no_actionable_plan`; they never produce a successful
   `noop` response.
8. Effective model provider, endpoint source, and model are observable without
   exposing credentials.
9. Unit, contract, Web API, and live shell smoke tests cover the repaired flow.

