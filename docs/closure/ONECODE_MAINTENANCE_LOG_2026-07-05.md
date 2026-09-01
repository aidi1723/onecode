# OneCode Maintenance Log

Date: 2026-07-05
Maintainer: Codex session
Scope: Run inspection source-quality follow-up

## Session Goal

Complete the focused follow-up from the CLI service decoupling phase by
removing `src/onecode/kernel/run_inspection.py:inspect_run` from the
source-quality hotspot allowlist without changing CLI, Web, or list-runs
behavior.

## Change Record

### Run Inspection Refactor

- Split `inspect_run` into smaller helpers for corrupt inspection payloads,
  status/count/checkpoint validation, trace evidence metrics, workspace-root
  resolution, and summary projection.
- Kept `inspect_run(workspace, run_id)` as the public kernel service used by
  CLI and Web callers.
- Preserved WAL-only fallback behavior, corrupt evidence reporting,
  trace-repair projection, and optional task-inspection fields.

### Source Quality

- Removed `src/onecode/kernel/run_inspection.py:inspect_run` from
  `scripts/check_source_quality.py`'s explicit long-function allowlist.
- Added a regression test that prevents this hotspot from being re-added to the
  allowlist.
- Confirmed the current `src/` tree passes the source-quality gate.

### Documentation Alignment

- Updated `CHANGELOG.md` with the 2026-07-05 run-inspection hotspot split.
- Updated the 2026-07-04 maintenance log so its follow-up queue and open risks
  no longer list `inspect_run` as pending.
- Added `docs/ONECODE_RUN_INSPECTION_HOTSPOT_CLOSURE_2026-07-05.md`.
- Updated `docs/RELEASE_CHECKLIST.md` with this maintenance pass.

## Verification Log

```text
.venv/bin/python -m unittest tests.test_source_quality.SourceQualityTests.test_run_inspection_inspect_run_is_not_allowlisted_as_hotspot -v
Result: OK, 1 test passed

.venv/bin/python scripts/check_source_quality.py src
Result: source quality ok

.venv/bin/python -m unittest tests.test_source_quality tests.test_inspect_cli tests.test_list_runs_cli tests.test_web_api -v
Result: OK, 99 tests passed, 9 skipped

git diff --check -- .
Result: passed

bash scripts/verify.sh
Result: OK, 743 tests passed, 1 skipped, doctor status ok
```

## Publish Checklist

- [x] no runtime dependency introduced
- [x] public CLI/Web inspection behavior preserved
- [x] source-quality allowlist updated
- [x] regression test added for the removed hotspot
- [x] focused local verification passed
- [x] full `bash scripts/verify.sh` completed after documentation updates
- [x] changelog updated
- [x] maintenance log updated
- [x] closure report added
- [x] branch prepared for push to `origin`

## Follow-Up Queue

1. Split `src/onecode/cli.py` by command family.
2. Split `src/onecode/web/api.py` into request parsing, auth, route dispatch,
   and response/projection modules.
3. Add stable public shell projection fixtures for downstream adapters.

## Open Risks

- Large `onecode.cli` and `onecode.web.api` decomposition remains future work
  and is intentionally tracked through the remaining source-quality hotspots.
- GitHub Actions matrix behavior must still be confirmed after push.
- The Web API remains scoped to local/trusted-loopback use.
