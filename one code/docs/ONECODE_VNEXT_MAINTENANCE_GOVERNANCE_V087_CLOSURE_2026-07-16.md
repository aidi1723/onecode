# OneCode vNext Maintenance Governance v0.8.7 Closure

Date: 2026-07-16
Status: Verified in isolated local worktree; not published or integrated
Branch: `feature/vnext-maintenance-governance-v087`
Base: `1a59db6208b3f5ee63a69b0a0108a3373c65409d`

## Outcome

The approved vNext maintenance-governance helper extraction has been replayed
on top of the verified LibreChat `v0.8.7` shell hardening line. The replay did
not merge the older maintenance branch, which trails the current line by 44
commits. This avoided reintroducing stale Web API and shell code.

`src/onecode/web/api.py` remains the route coordinator and continues to expose
the established helper names. Stable responsibilities now live in:

- `src/onecode/web/request_body.py`
- `src/onecode/web/responses.py`
- `src/onecode/web/auth.py`
- `src/onecode/web/workspace.py`

The coordinator decreased from 1,409 to 1,297 lines. No route handler, endpoint
shape, status code, approval rule, execution permission, or shell projection
contract changed.

## TDD Evidence

Each module boundary was introduced through a separate red-green cycle. The
new direct-import test first failed with `ModuleNotFoundError`, then passed
after the minimum extraction. Existing compatibility tests continued to import
the same names from `onecode.web.api`.

Focused gates:

| Boundary | Result |
| --- | --- |
| Request body | 4 passed |
| Responses | 3 passed |
| Authentication | 7 passed |
| Workspace | 4 passed |
| Full Web API | 75 passed |

## Full Verification

- `PYTHONPATH=src bash scripts/verify.sh`: 907 passed, 1 environment-only skip.
- Source-quality gate: passed.
- Doctor: `status: ok`.
- Diff whitespace checks: passed before each helper commit.
- No new runtime third-party dependency was introduced.

## Live Shell Acceptance

The isolated source launched the normal LibreChat directory at community
version `v0.8.7`, commit `224e73e8ea4ccd4f60e9f335691c78362efff7e0`.
Mongo, OneCode API, and LibreChat health checks passed, and the community base
commit remained an ancestor.

Two model boundaries were exercised:

- With a 10-second model limit, the upstream request ended after about 10.014
  seconds as one structured HTTP 504 with durable failed-run evidence.
- With a 60-second model limit, the same smoke workflow completed and produced
  run `6db9bb9e761f433a9f5e4aeb49c62046` with full evidence.

The temporary shell was stopped after verification.

## Release-Line Decision

The refreshed audit found:

- local `main` and `feature/gateway-iching-rule-sync` share merge base
  `0e8e0706d60eda5fe24da9c798a9b978e5ddde35`;
- fetched `origin/main` and the current review line have no merge base;
- the current review line is 13 commits ahead of its remote;
- GitHub reports no current pull request from that line.

No force-push, unrelated-history merge, remote push, tag, or pull request was
performed. A future publication must use an isolated sync branch based on
`origin/main` and repeat the full release verification gate.

## Remaining Risks

- The Web API remains intentionally local/trusted-loopback only.
- Route-handler decomposition is deferred until these helper boundaries remain
  stable through normal use.
- Upstream model latency can exceed a deliberately short 10-second limit; the
  system now demonstrates both bounded failure and successful longer-budget
  behavior.
- Optional Meilisearch, RAG, production supervision, and staged pressure tests
  remain separate milestones.
