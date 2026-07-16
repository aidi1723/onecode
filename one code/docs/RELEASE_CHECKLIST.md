# Release Checklist

## System Boundary

- [ ] Treat `<onecode-repo>` as the local development workspace.
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

## 2026-07-06 n100 Verifier And Shell Closure Pass

- [x] `docs/ONECODE_MAINTENANCE_LOG_2026-07-06.md` records the command-by-command maintenance log.
- [x] `docs/ONECODE_N100_VERIFIER_SHELL_FINAL_CLOSURE_2026-07-06.md` records the final closure and handoff.
- [x] `docs/ONECODE_TEMPORARY_CLOSURE_HANDOFF_2026-07-06.md` records temporary closure and pressure-test deferral.
- [x] `run-model --verifier-policy --verifier` blocks delivery when a selected verifier fails.
- [x] Verifier-failed runs inspect as `halted/verifier_failed/blocked` instead of `corrupt/status_mismatch`.
- [x] Final result writes align `ledger.json`, `manifest.json`, and final `run_completed` trace state.
- [x] Local focused verification passed: `tests.test_model_loop tests.test_inspect_cli tests.test_run_plan_cli`, 94 tests.
- [x] Local full verification passed: `bash scripts/verify.sh`, 748 tests, 1 skipped, doctor status ok.
- [x] n100 focused regression verification passed: 2 tests.
- [x] n100 related suite passed: 94 tests.
- [x] n100 real failing-verifier smoke returned `halted verifier_failed blocked` with non-corrupt inspect.
- [x] n100 real passing-verifier smoke returned `completed deliverable passed` with non-corrupt inspect.
- [x] n100 concrete programming smoke generated code/tests, passed verifier, passed manual unittest, and inspected as deliverable.
- [x] n100 live shell smoke passed for launcher, health checks, LibreChat, shell schema, authenticated chat completion, file generation, and inspect.
- [x] n100 shell services were stopped after testing; ports `19080`, `14080`, and `39017` returned connection refused.
- [x] Pressure testing was explicitly deferred and is not claimed as complete.

Not applicable for this pass:

- Production deployment packaging was not changed.
- LibreChat UI bundle was not changed.
- Pressure testing was not run.
- Previously recorded UI polish issues such as `/api/balance` console noise and command-shaped chat UX remain follow-ups.

## 2026-07-10 v0.8.0 Canonical Runtime and CLI Closure Pass

- [x] Package, Python, TUI, and HTTP public version identifiers are aligned to `0.8.0`.
- [x] Canonical `onecode-iching-v2` encoding and deterministic legacy v1 interpretation are documented.
- [x] Training, benchmark, mutation evidence, Shell v4, and CLI command-family closures are indexed.
- [x] Shell contract fixtures are packaged as wheel assets and remain read-only.
- [x] CLI read-only, local-interface, and configuration adapters preserve parser and dispatch compatibility.
- [x] Raw API keys are absent from public CLI output and closure records.
- [x] Forbidden core-formula diff scan has no matches.
- [x] Focused configuration/Web/runner verification passed: 161 tests.
- [x] Full local verification passed for v0.8.0: 824 tests, 1 environment-dependent skip, doctor status ok.
- [x] Release audit built `onecode-0.8.0-py3-none-any.whl`, verified wheel assets, and performed no package publication.
- [x] GitHub branch update pushed commit `35ac8fa` to `feature/gateway-iching-rule-sync`.

Not applicable for this pass:

- No production deployment is performed.
- No GitHub Release or package registry publication is performed.
- No merge into `main` is performed without a separate operator instruction.

## 2026-07-10 GPL v3 Relicensing Pass

- [x] `LICENSE` contains the unmodified GNU General Public License Version 3 text.
- [x] `pyproject.toml` declares the PEP 639 SPDX expression `GPL-3.0-only`
      without the superseded License classifier.
- [x] README identifies GPL v3 only and its source-availability obligation.
- [x] Historical Apache statements are retained only as dated historical context.
- [x] Local contributor history shows project-controlled author identities and no separate external contributor identity.
- [x] No `NOTICE`, bundled third-party source license, or alternate copying file was found in the project tree.
- [x] Automated license consistency coverage was added.
- [x] Full verification passed with 825 tests and 1 environment-dependent skip;
      wheel metadata reports `License-Expression: GPL-3.0-only` and includes
      `License-File: LICENSE`.
- [x] GitHub branch update pushed license commit `4878c18` to
      `feature/gateway-iching-rule-sync`.

## 2026-07-16 LibreChat v0.8.7 And vNext GitHub Closure Pass

- [x] LibreChat provenance is pinned to community tag `v0.8.7` at `9e74cc0e`,
      verified shell head `224e73e8`, and rollback checkpoint `a7201646`.
- [x] vNext helper extraction is integrated on
      `feature/gateway-iching-rule-sync` at implementation head `1f3d691b`.
- [x] `origin/feature/gateway-iching-rule-sync` at `cca465af` is an ancestor of
      the integrated line; no force-push is required or authorized.
- [x] `origin/main` remains unrelated and is excluded from this publication.
- [x] Parent-directory dirty files and untracked assets are excluded; only
      explicit `one code/` paths may be staged.
- [x] `bash scripts/release-audit.sh` passes, including source quality, wheel
      build, and wheel-asset integrity.
- [x] `bash scripts/verify-core.sh` passes with 234 tests and doctor status
      `ok`.
- [x] `PYTHONPATH=src bash scripts/verify.sh` passes with 907 tests, 1 existing
      environment-only skip, and doctor status `ok`.
- [x] `PYTHONPATH=src .venv/bin/python -m unittest tests.test_web_api -v`
      passes.
- [x] `git diff --check` and final staged-path review pass.
- [x] Local and remote feature-branch refs matched at `a4e77ee` after the first
      non-force push; the final documentation-only evidence update uses the
      same ancestry and ref-equality gate.

Not applicable for this pass:

- Frontend source did not change in the final alignment pass, so the prior
  LibreChat build and desktop/mobile browser acceptance remain the applicable
  UI evidence; no new frontend build or browser run is required.
- No SEO content, social announcement, production deployment, GitHub Release,
  package registry publication, tag, pull request, or `main` merge is included.

## 2026-07-16 LibreChat Execution Reliability GitHub Publication Pass

- [x] Reliability implementation commits are present on the publication tip
      (`4a7181c`…`59973e5` plus design/plan/closure docs).
- [x] Shell projection v5 contract files and tests are included.
- [x] Local monorepo `main` already contains the reliability tip via fast-forward.
- [x] Publication target is `origin/feature/gateway-iching-rule-sync` only;
      unrelated `origin/main` is excluded.
- [x] Absolute local paths were redacted from the reliability plan and closure
      documents in the publication delta.
- [x] Privacy/secret scan of the publication delta found no real API keys or
      PEM material; unit-test fixture tokens remain fixtures only.
- [x] Targeted reliability unit tests: 119 passed.
- [x] Source-quality and `git diff --check` pass on the clean publish worktree.
- [x] LibreChat reliability work is recorded as local-only (no owner GitHub
      remote for the shell fork).
- [ ] Post-push: local tip equals refreshed
      `origin/feature/gateway-iching-rule-sync` (completed during publication).

Not applicable for this pass:

- No production deployment, tag, GitHub Release, or package publication.
- No merge into `origin/main`.
- Live Playwright and dual-process smoke remain operator-deferred.
