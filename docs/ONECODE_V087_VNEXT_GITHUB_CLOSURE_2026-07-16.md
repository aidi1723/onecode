# OneCode v0.8.7 And vNext GitHub Closure

Date: 2026-07-16
Status: Published to the owner-approved feature branch; refs verified equal
Owner-approved target: `origin/feature/gateway-iching-rule-sync`

## Closure Scope

This record closes the combined LibreChat `v0.8.7` shell-hardening and vNext
maintenance-governance cycle for the OneCode repository. It aligns the prior
phase records, defines the exact source and rollback points, and controls the
owner-requested GitHub update.

Included:

- bounded model timeout and failed-planning evidence behavior;
- persistent private shell authentication and Mongo state;
- LibreChat `v0.8.7` migration and live shell acceptance;
- Web API request, response, authentication, and workspace helper extraction;
- compatibility, source-quality, doctor, release, and publication checks;
- documentation alignment under `one code/`.

Excluded:

- all parent-directory user changes and untracked research assets;
- any merge, rebase, or history rewrite involving unrelated `origin/main`;
- LibreChat repository publication or operator-shell cutover;
- production deployment, tag, GitHub Release, package publication, or PR.

## Release Record

| Record | Exact value |
| --- | --- |
| OneCode branch | `feature/gateway-iching-rule-sync` |
| Remote feature baseline | `cca465af177e0d2c81d24aaa00900a9fc65c9f0d` |
| Integrated implementation head | `1f3d691b175754f5bd8c3677eaf0e3d72cdeb973` |
| Initial closure publication commit | `a4e77eeee6cd88daace1a6029dedc87d215ff2ca` |
| Pre-publication distance | 20 commits ahead, 0 behind |
| OneCode package version | `0.8.0` |
| LibreChat community tag | `v0.8.7` |
| LibreChat community commit | `9e74cc0e57b395926122bd4062c1fcedc48ed465` |
| LibreChat verified shell head | `224e73e8ea4ccd4f60e9f335691c78362efff7e0` |
| LibreChat rollback checkpoint | `a7201646608cb489f85e6b26b3a5c7117de348f8` |

The LibreChat community commit is an ancestor of the verified shell head. The
OneCode remote feature baseline is an ancestor of the integrated implementation
head. These are independent repositories and must not be treated as a single
Git history.

## Delivered Outcome

- The shell maps provider timeouts and failures to bounded HTTP 504/502
  responses with durable correlated evidence.
- OneCode's LibreChat endpoint uses zero outer retries, preventing duplicated
  durable tasks.
- Shell secrets, Mongo data, runtime records, and redacted logs survive
  controlled restarts under a private persistent state directory.
- The Web API coordinator preserves its public helper imports and route
  contracts while four stable responsibilities now live in focused stdlib-only
  modules.
- `src/onecode/web/api.py` decreased from 1,409 to 1,297 lines without changing
  route handlers, endpoint payloads, permissions, or trusted-loopback scope.

## Verification Record

Historical implementation evidence:

- LibreChat hardening phase: 903 OneCode tests passed with one environment-only
  skip; 90 focused LibreChat tests and all three production builds passed.
- vNext integrated phase: 75 Web API tests and 907 full-suite tests passed with
  one environment-only skip; source quality and doctor passed.
- Live shell health passed. A 10-second request returned one structured HTTP
  504 with durable evidence; a 60-second request completed with full evidence.
- Prior desktop `1440x900` and mobile `390x844` browser acceptance covered
  login, project selection, Console tabs, approval-required writes, restart
  persistence, focus behavior, and timeout evidence.

Final publication gates:

- [x] `bash scripts/release-audit.sh`: source quality, wheel build, and wheel
  asset integrity passed for `onecode-0.8.0-py3-none-any.whl`.
- [x] `bash scripts/verify-core.sh`: 234 tests passed; doctor status `ok`.
- [x] `PYTHONPATH=src bash scripts/verify.sh`: 907 tests passed, 1 existing
  environment-only skip; source quality and doctor passed.
- [x] `PYTHONPATH=src .venv/bin/python -m unittest tests.test_web_api -v`:
  75 tests passed.
- [x] whitespace and explicit staged-path scope checks passed.
- [x] remote fast-forward ancestry and post-push ref equality: the first push
  advanced `cca465a..a4e77ee`; a fresh fetch returned local and remote commit
  `a4e77eeee6cd88daace1a6029dedc87d215ff2ca`.

No frontend source changed during this final documentation pass, so rebuilding
or rerunning the prior browser acceptance would not add coverage to the
publication delta.

## Publication Decision

The owner authorized publication to the existing remote feature branch. The
only permitted operation is a normal, non-force push after all final gates
pass. The push must stop if the remote feature ref is no longer an ancestor of
local HEAD. Publication is complete only when local HEAD and the refreshed
remote feature ref are identical.

The authorized publication completed as a normal fast-forward from `cca465a`
through closure commit `a4e77ee`. The final documentation-only evidence update
that contains this post-push record is subject to the same non-force ancestry
and ref-equality checks.

The absence of a merge base between `origin/main` and this branch is an
explicit repository-history risk, not a reason to rewrite either line. A future
`main` synchronization requires a separate decision and replay plan.

## Rollback

OneCode repository rollback must preserve published history: create a new
revert commit for the intended range after reviewing
`cca465af177e0d2c81d24aaa00900a9fc65c9f0d..HEAD`; do not force the remote
branch backward.

LibreChat runtime rollback is separate:

1. Stop the foreground shell and confirm ports `14080`, `19080`, `39017`, and
   `16780` have no listeners.
2. Switch the LibreChat repository to
   `checkpoint/onecode-shell-pre-v087-20260715` at `a7201646`.
3. Restore or select the matching pre-upgrade state directory.
4. Run preflight and health checks before accepting new work.

## Remaining Risks

- The Web API remains intentionally local/trusted-loopback only.
- Upstream model latency can exceed short limits; failure is bounded and
  evidenced but model quality is not guaranteed.
- Optional Meilisearch, RAG, production supervision, and staged pressure tests
  remain separate milestones.
- Route-handler decomposition remains deferred until the extracted boundaries
  have remained stable through normal use.
- The remote feature line is publishable, but it cannot be merged directly into
  the current unrelated `origin/main` without an explicit history strategy.
