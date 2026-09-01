# OneCode LibreChat v0.8.7 Upgrade and Runtime Hardening Design

Date: 2026-07-15
Status: Approved design, written specification pending review
Scope: LibreChat shell upgrade, OneCode model-planning reliability, local shell state, and cross-repository verification

## Objective

Upgrade the OneCode LibreChat shell to the latest non-RC community tag,
`v0.8.7`, without overwriting the existing OneCode customizations. Close the
confirmed timeout and retry amplification failure, make failed model planning
observable, and preserve local shell authentication state across controlled
restarts.

The result must remain a local-first OneCode shell. LibreChat is the user
interface and transport adapter; OneCode remains the execution, approval,
workspace, and evidence authority.

## Current Baseline

The investigation established the following baseline:

- The LibreChat customization branch is based on commit `a16f08a42` and has
  five local commits above that base.
- The branch is 275 community commits behind `v0.8.7` and 388 commits behind
  `origin/main` as fetched on 2026-07-15.
- The LibreChat worktree has 30 tracked changes, 16 untracked entries, and six
  tracked deletions. These include OneCode routes, services, UI components,
  data-provider contracts, branding, tests, and local documentation.
- The latest non-RC tag is `v0.8.7` at commit `9e74cc0e5`. It uses
  `@librechat/agents` 3.2.46 and `@langchain/core` 1.2.0.
- `origin/main` is 77 commits ahead of `v0.8.7` and is a moving development
  target. It is not the selected upgrade baseline.
- A failed OneCode review request produced seven model-planning runs with one
  task digest, no `model_call_completed` event, and a final LibreChat
  connection error after approximately nine minutes.
- OneCode uses a 60-second planning timeout. LibreChat's LangChain
  `AsyncCaller` defaults to six retries, producing one initial request plus six
  retries.
- The configured model endpoint is reachable and advertises the selected
  model, but the same structured planning request exceeded a bounded 20-second
  live diagnostic timeout.
- Shell authentication secrets are generated afresh on each launch. Existing
  logs contain repeated `invalid signature` errors after restarts.

## Selected Approach

Use a versioned migration rather than merging the community branch into the
dirty customization worktree.

1. Preserve the current LibreChat customization state as an explicit local
   checkpoint.
2. Create a clean upgrade branch and worktree from `v0.8.7`.
3. Verify the unmodified `v0.8.7` baseline before porting OneCode code.
4. Port OneCode behavior in bounded functional slices, resolving against the
   current community APIs instead of replaying old files wholesale.
5. Implement the OneCode runtime hardening in the isolated OneCode worktree.
6. Run unit, build, integration, and browser checks before any cutover.
7. Retain both original checkpoints until the upgraded shell passes the full
   acceptance suite.

This approach keeps community provenance clear and makes rollback a branch or
worktree switch rather than a reverse merge.

## Rejected Approaches

### Merge into the current dirty LibreChat worktree

This risks overwriting uncommitted OneCode routes and UI files, makes conflict
resolution dependent on index state, and prevents a reliable baseline test.

### Upgrade directly to `origin/main`

The development branch contains 77 commits beyond `v0.8.7`, including active
agent and UI architecture work. It increases the migration surface without
being required to close the confirmed reliability defects.

### Upgrade LibreChat without changing OneCode

The raw timeout escape and incomplete failure evidence originate in OneCode.
A LibreChat-only upgrade cannot close the root cause.

### Patch only the current versions

This would reduce immediate runtime risk but leave the shell hundreds of
community commits behind and make the next upgrade harder.

## Repository and Checkpoint Boundaries

### OneCode repository

Development uses the isolated branch:

```text
feature/onecode-shell-v087-hardening
```

The current user worktree and its unrelated modifications are not reset,
stashed, or rewritten.

### LibreChat repository

Before creating an upgrade worktree, preserve all OneCode-owned source and
tests in a dedicated checkpoint branch. The checkpoint excludes:

- `.env` and local credentials;
- `node_modules`;
- runtime logs;
- `.playwright-cli` artifacts;
- `.superpowers` transient files;
- build output and caches.

The upgrade branch is created from the exact `v0.8.7` tag. The original
`onecode-shell-phase1` worktree remains untouched after checkpoint creation.

## Community Upgrade Migration

OneCode customizations are ported in this order:

1. OneCode custom endpoint initialization and request metadata.
2. Server-side OneCode routes, project selection, and project-state services.
3. Shared API and data-provider contracts.
4. OneCode Console and project selection UI.
5. Chat metadata injection and approval-message behavior.
6. Branding, icons, localized strings, and shell documentation.
7. Smoke scripts and focused tests.

Each slice must compile and pass its focused tests before the next slice. Old
files are not copied when `v0.8.7` provides a replacement extension point. In
that case the OneCode behavior is re-expressed through the new public boundary.

The port preserves routing, information architecture, project selection,
model configuration, approval semantics, and evidence views. It does not add a
new landing page or redesign the shell.

## Model Timeout Contract

Introduce a typed timeout result at the OneCode provider boundary. A provider
timeout must not escape as an unclassified Python `TimeoutError`.

The runtime behavior is:

1. The model provider converts network timeouts into a typed
   `ModelProviderTimeout` derived from `ModelProviderError`.
2. The model loop writes `model_call_failed` with bounded provider, model,
   elapsed time, failure kind, and retryability metadata.
3. The run terminates with a structured halted result and complete evidence
   references.
4. The Web API returns HTTP 504 with a stable
   `model_provider_timeout` error type.
5. No credentials, raw authorization headers, or unrestricted exception text
   enter the response or evidence.

The timeout value remains bounded and configurable through an explicit
OneCode setting. This phase does not implement adaptive timeouts.

## Retry Contract

The OneCode custom endpoint must set LibreChat/LangChain retries explicitly.
The default is zero retries for a OneCode task request because OneCode already
creates a durable run for every request and an outer retry creates duplicate
run evidence.

Retry rules are:

- model-planning timeouts: no automatic LibreChat retry;
- OneCode HTTP 4xx responses: no automatic retry;
- OneCode approval-required and halted results: no retry;
- connection failure before an HTTP request reaches OneCode: at most one
  bounded retry may be enabled later, but is out of scope for the default;
- user-triggered retry remains available as a new explicit request.

The shell must not rely only on response headers because LangChain's outer
`AsyncCaller` applies its own retry policy. The OneCode endpoint configuration
must pass `maxRetries: 0` into the effective LLM configuration, with a focused
test proving the runtime value.

## Failure Evidence

Every model call must end with exactly one terminal trace event:

- `model_call_completed`, or
- `model_call_failed`.

A failed planning run must record:

- run ID and trace ID;
- provider kind and model name;
- bounded elapsed duration;
- normalized failure kind;
- retryable or non-retryable classification;
- Safe-Agent route summary when routing completed;
- ledger and manifest references for the terminal halted run.

The evidence must not record the API key, full environment, raw router bodies,
or unbounded upstream response content.

## Persistent Local Shell State

Replace the fixed temporary runtime state root with a persistent private state
directory under `ONECODE_HOME`, with an explicit CLI override for testing.

The state directory owns:

- generated LibreChat runtime configuration;
- JWT and credential-encryption secrets;
- the local MongoDB data directory;
- service PID/status metadata;
- bounded service logs.

Secrets are generated once, written atomically with mode `0600`, and reused on
subsequent launches. Secret values are never printed by `shell-status` or
normal launch output.

MongoMemoryServer receives an explicit persistent `dbPath` inside the state
directory. This preserves the local user and refresh-session records across a
normal stop and restart. Tests use temporary state roots and never touch the
operator's real state.

## Process Lifecycle and Diagnostics

The shell remains a foreground supervisor in this phase. Converting it into a
system daemon or login item is out of scope.

Before startup, the launcher checks:

- supported Python and Node versions;
- availability of `node`, `npm`, and the OneCode package;
- LibreChat `package.json` and expected version provenance;
- port availability;
- state-directory creation and permissions;
- model configuration presence without revealing its secret.

Each child process writes bounded logs under the shell state directory while
still surfacing concise startup failures in the foreground terminal.
`shell-status` reports service health, effective workspace, state path,
LibreChat tag/commit, and last bounded failure summary without returning login
passwords or secrets.

## Safe-Agent Routing

The current router may legitimately return `no_matching_scenario`. This phase
does not make Safe-Agent routing authoritative for execution.

Routing behavior remains:

- verified trusted route: pass bounded method context to planning;
- no matching scenario: continue with OneCode's local tool contract and record
  the no-match result;
- unavailable router: continue with an explicit unavailable result;
- invalid integrity or untrusted selection: halt before model execution.

The failure evidence work must ensure the route summary remains available even
when model planning times out.

## UI Compatibility

The migration uses the existing OneCode and LibreChat design references. UI
work is limited to adapting existing OneCode surfaces to `v0.8.7` component
and navigation APIs.

The port must preserve:

- OneCode Console entry and tabs;
- project folder selection;
- model configuration;
- run, evidence, verifier, and diagnostics views;
- approval-required action summaries;
- responsive layout and keyboard accessibility;
- existing OneCode branding without deleting community-required functional
  assets unless a tested replacement exists.

Shared components and tokens are updated before page-specific compatibility
patches. The final UI pass covers typography, spacing, surfaces, states,
responsiveness, and accessibility.

## Test Strategy

All behavior changes use test-driven development.

### OneCode focused tests

- Provider test: an upstream timeout becomes `ModelProviderTimeout`.
- Model-loop test: a timeout writes one `model_call_failed` event and no
  completed event.
- Web test: a timeout returns 504 `model_provider_timeout`.
- Evidence test: the halted run exposes trace, ledger, and manifest references
  without secrets.
- Shell-state test: secrets are stable across two launcher configurations that
  use the same state root.
- Shell-state test: permissions remain private and concurrent initialization is
  atomic.
- Shell-status test: public output is redacted and reports version provenance.

### LibreChat focused tests

- Custom endpoint test: OneCode resolves an effective `maxRetries` value of
  zero.
- Request test: a timeout response is surfaced once without a duplicate
  OneCode request.
- Route and project-selection tests are ported to `v0.8.7` APIs.
- OneCode Console component tests cover its navigation entry and core tabs.

### Integration tests

- A local stub model delays beyond the configured timeout.
- One shell task produces exactly one OneCode run.
- The response becomes a visible timeout within the configured bound.
- The trace contains one start and one failed event.
- The ledger and manifest are readable and redacted.
- Restarting the shell with the same state root preserves authentication state.
- A read-only project inspection completes.
- A write request stops at approval-required and does not mutate the target.

### Final verification

- OneCode focused suite;
- full `scripts/verify.sh`;
- LibreChat focused Jest suites;
- LibreChat package build;
- local shell startup and health checks;
- Playwright desktop and mobile smoke checks;
- final diff and secret scan in both repositories.

## Cutover and Rollback

Cutover is allowed only when all acceptance criteria pass in the isolated
worktrees. No publish, tag, push, or production deployment is part of this
phase.

Rollback consists of:

1. stop the upgraded foreground shell;
2. start the preserved checkpoint branch with its prior state directory;
3. verify the old API and shell health endpoints;
4. retain upgraded evidence separately for diagnosis.

The new persistent state format must either be backward-compatible or use a
versioned directory so the old shell does not interpret new state.

## Out of Scope

- tracking LibreChat `origin/main`;
- production deployment topology;
- multi-user authorization redesign;
- background daemon or OS login-item installation;
- a new UI or information architecture;
- changing OneCode approval or workspace authority;
- automatic dependency updates beyond the `v0.8.7` lockfiles;
- publishing, pushing, tagging, or deleting the preserved worktrees.

## Acceptance Criteria

1. The upgraded LibreChat source is based exactly on `v0.8.7`, with community
   provenance recorded.
2. All current OneCode shell capabilities have an explicit migrated test or an
   approved removal record; no customization is silently dropped.
3. A timed-out model-planning request produces one upstream OneCode request,
   not seven.
4. The timeout returns a visible 504 result within the configured bound.
5. Every model call writes exactly one terminal completed or failed event.
6. A failed planning run exposes redacted trace, ledger, and manifest evidence.
7. Shell secrets and local session data survive a controlled restart using the
   same private state root.
8. Read-only tasks still execute automatically and guarded actions still stop
   for explicit approval.
9. Safe-Agent no-match and unavailable results remain visible but do not grant
   authority or block valid local read plans.
10. OneCode tests, LibreChat focused tests, LibreChat build, shell health, and
    browser smoke checks pass in isolated worktrees.
11. The original LibreChat checkpoint and current user worktree remain intact
    and usable for rollback.
12. No secrets, runtime logs, browser artifacts, dependency directories, or
    operator state are committed.
