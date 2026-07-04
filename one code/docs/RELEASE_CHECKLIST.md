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

## 2026-07-04 Release Readiness Pass

- [x] `CHANGELOG.md` records the release-readiness and source-quality update.
- [x] `docs/ONECODE_MAINTENANCE_LOG_2026-07-04.md` records the maintenance log.
- [x] `docs/ONECODE_RELEASE_READINESS_CLOSURE_2026-07-04.md` records closure and handoff.
- [x] `pyproject.toml` includes TUI package data for `styles.tcss`.
- [x] `scripts/check_wheel_assets.py` validates required wheel assets.
- [x] `.github/workflows/verify.yml` verifies Python 3.11, 3.12, and 3.13.
- [x] `scripts/check_source_quality.py` runs from both core and full verification scripts.
- [x] `scripts/release-audit.sh` runs readiness checks without publishing.
- [x] Local verification recorded: `bash scripts/verify.sh` passed with 740 tests, 1 skipped, doctor status ok.
- [x] Local release audit recorded: `bash scripts/release-audit.sh` passed with publish action not performed.

Not applicable for this pass:

- Browser smoke was not required because no browser UI behavior changed.
- Production frontend rebuild was not required because no shell UI bundle changed.

## 2026-07-05 Run Inspection Hotspot Pass

- [x] `CHANGELOG.md` records the run-inspection hotspot split.
- [x] `docs/ONECODE_MAINTENANCE_LOG_2026-07-05.md` records the maintenance log.
- [x] `docs/ONECODE_RUN_INSPECTION_HOTSPOT_CLOSURE_2026-07-05.md` records closure and handoff.
- [x] `scripts/check_source_quality.py` no longer allowlists `src/onecode/kernel/run_inspection.py:inspect_run`.
- [x] `tests/test_source_quality.py` prevents `inspect_run` from being re-added to the hotspot allowlist.
- [x] Focused local verification recorded: source quality and inspect/list-runs/Web regression tests passed.
- [x] Full local verification recorded: `bash scripts/verify.sh` passed with 743 tests, 1 skipped, doctor status ok.
- [x] Online update prepared for `origin/feature/gateway-iching-rule-sync`.

Not applicable for this pass:

- Browser smoke was not required because no browser UI behavior changed.
- Production frontend rebuild was not required because no shell UI bundle changed.
