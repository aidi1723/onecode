# OneCode vNext Release-Line Audit

Date: 2026-07-03
Branch: `feature/vnext-maintenance-governance`
Parent milestone branch: `feature/gateway-iching-rule-sync`
Remote: `origin https://github.com/aidi1723/onecode.git`

## Audit Commands

- `git fetch origin`
- `git branch -vv`
- `git merge-base main feature/gateway-iching-rule-sync`
- `git merge-base origin/main feature/gateway-iching-rule-sync`
- `git log --oneline --decorate --graph --max-count=30 --all`
- `gh pr list --head feature/gateway-iching-rule-sync --repo aidi1723/onecode --json number,title,url,state,headRefName,baseRefName`

## Findings

- Local `feature/gateway-iching-rule-sync` is checked out in `/Users/aidi/大字典` at `d79be6b` and tracks `origin/feature/gateway-iching-rule-sync`, with the local branch ahead by 2 commits.
- Current implementation branch `feature/vnext-maintenance-governance` is checked out in `/Users/aidi/大字典/.worktrees/vnext-maintenance-governance` at `dd8c499`.
- Local `main` and `feature/gateway-iching-rule-sync` share merge base `0e8e0706d60eda5fe24da9c798a9b978e5ddde35`.
- `origin/main` and `feature/gateway-iching-rule-sync` do not share a merge base in this repository clone. `git merge-base origin/main feature/gateway-iching-rule-sync` exited with code 1 and printed no commit.
- `origin/main` currently points at `8690959 docs: publish built-in skill router update`.
- Local `main` currently points at `0e8e070 docs: define v0.7 task reliability design`.
- `gh pr list --head feature/gateway-iching-rule-sync --repo aidi1723/onecode --json number,title,url,state,headRefName,baseRefName` returned `[]`.

## Explanation

GitHub rejected PR creation from `feature/gateway-iching-rule-sync` to `main`
because the GitHub default line represented by `origin/main` has diverged into
a history that does not share ancestry with the feature branch. The local
`main` branch still shares ancestry with the feature branch, but it is not the
same history as the fetched `origin/main`.

This is a release-line governance issue, not a failure of the July 3 hardening
work. The hardening and closure commits remain preserved on the feature branch.

## Decision

Do not force-push, reset, or rewrite either history. Continue this maintenance
work on `feature/vnext-maintenance-governance`, preserving
`feature/gateway-iching-rule-sync` as the milestone record.

If a GitHub PR to `origin/main` is required, create a separate sync branch from
`origin/main` in an isolated worktree and replay only project-root changes under
`one code/`. That sync branch must pass the full verification gate before PR
creation.

## Verification Boundary

This audit used read-only Git and GitHub queries except for `git fetch origin`.
No tracked project files were modified by the audit commands before this
document was written.

## Follow-Up

- Keep current vNext implementation on `feature/vnext-maintenance-governance`.
- Push `feature/gateway-iching-rule-sync` again if the two local planning
  commits should be visible on that milestone branch.
- Create an `origin/main`-based sync branch only after the owner decides that a
  GitHub PR into the current remote mainline is required.
