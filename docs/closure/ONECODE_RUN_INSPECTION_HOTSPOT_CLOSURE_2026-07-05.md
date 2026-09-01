# OneCode Run Inspection Hotspot Closure

> 2026-07-06 alignment note: this report preserves the 2026-07-05 inspect refactor closure. The current post-verifier inspect consistency fix, including the `corrupt/status_mismatch` repair, is closed in `docs/ONECODE_N100_VERIFIER_SHELL_FINAL_CLOSURE_2026-07-06.md`; pressure testing is deferred in `docs/ONECODE_TEMPORARY_CLOSURE_HANDOFF_2026-07-06.md`.

Date: 2026-07-05
Branch: `feature/gateway-iching-rule-sync`
Repository: `https://github.com/aidi1723/onecode.git`
Status: Ready for online update

## Scope

This closure covers the focused source-quality follow-up for
`src/onecode/kernel/run_inspection.py:inspect_run`.

Included areas:

- behavior-preserving split of `inspect_run`
- source-quality allowlist cleanup
- focused inspect/list-runs/Web regression coverage
- changelog, maintenance log, release checklist, and closure alignment

Excluded areas:

- broad `onecode.cli` command-family decomposition
- broad `onecode.web.api` route/auth/parser decomposition
- shell projection fixture expansion
- production deployment changes

## Completion Summary

`inspect_run` now delegates validation, corrupt-response construction,
trace-evidence metrics, workspace-root resolution, and summary projection to
smaller kernel helpers. The public `inspect_run(workspace, run_id)` entry point
is preserved for CLI and Web callers.

The source-quality gate no longer needs an explicit exception for
`src/onecode/kernel/run_inspection.py:inspect_run`. A regression test now blocks
that hotspot from being re-added to the allowlist.

## Verification Evidence

Current focused verification for this closure:

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

## Publish Readiness

- [x] changelog updated
- [x] maintenance log updated
- [x] release checklist updated
- [x] source-quality allowlist cleaned
- [x] regression test added
- [x] focused verification passed
- [x] full `bash scripts/verify.sh` completed after documentation updates
- [x] branch prepared for push to `origin`

## Residual Risks

- `src/onecode/cli.py` and `src/onecode/web/api.py` remain large and are
  tracked as separate focused refactors.
- GitHub Actions matrix behavior still needs confirmation after push.
- This pass does not change production deployment behavior.

## Final Handoff

Commit this closure with the run-inspection refactor and push
`feature/gateway-iching-rule-sync` to `origin`.
