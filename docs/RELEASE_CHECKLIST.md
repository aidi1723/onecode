# Release Checklist

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
