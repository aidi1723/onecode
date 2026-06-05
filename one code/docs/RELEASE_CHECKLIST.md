# Release Checklist

## System Boundary

- [ ] Treat `/Users/aidi/大字典/one code` as the local development workspace.
      It may contain dirty experiments, generated assets, local shell files, and
      untracked research material.
- [ ] Treat `/private/tmp/onecode-open-source-sync` as the clean open-source
      synchronization worktree for GitHub `aidi1723/onecode`.
- [ ] Do not publish directly from the local development workspace when it has
      unrelated dirty files. Prepare GitHub updates from a clean worktree based
      on `origin/main`.
- [ ] Public release files live under `release/`; implementation truth remains
      `src/`, `tests/`, and verified commits.

- [ ] Worktree is clean except intentional release files.
- [ ] `bash scripts/release-audit.sh` shows only intentional tracked changes and release candidates.
- [ ] `bash scripts/verify-core.sh` passes.
- [ ] `bash scripts/verify.sh` passes.
- [ ] `PYTHONPATH=src python3 -m unittest tests.test_web_api -v` passes.
- [ ] LibreChat shell focused tests pass when shell files changed.
- [ ] Production frontend is rebuilt when shell UI changed.
- [ ] Browser smoke confirms OneCode Console opens.
- [ ] No gateway dependency is introduced.
- [ ] Version and closure report are updated.
