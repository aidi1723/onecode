# OneCode Release Readiness Closure

Date: 2026-07-04
Branch: `feature/gateway-iching-rule-sync`
Repository: `https://github.com/aidi1723/onecode.git`
Status: Ready for online update

## Scope

This closure covers the release-readiness and maintainability pass following
the project-wide review. The work focuses on packaging correctness, CI coverage,
design-source alignment, source quality gates, and local release audit hygiene.

Included areas:

- Python wheel package data for TUI assets
- wheel asset validation
- supported Python CI matrix
- TUI and local Web Gateway design contract documentation
- source quality checks for oversized functions/classes
- local release audit checks and artifact cleanup
- changelog, maintenance log, and release checklist alignment

Excluded areas:

- feature behavior changes
- production deployment changes
- broad decomposition of `src/onecode/cli.py`
- broad decomposition of `src/onecode/web/api.py`
- publishing a package artifact

## Completion Summary

This pass closes the release packaging gap where `onecode.tui/styles.tcss`
needed explicit wheel inclusion. It also adds a stdlib-only asset checker for
built wheels, expands GitHub Actions to Python 3.11, 3.12, and 3.13, and adds a
source quality gate that blocks new unlisted oversized functions/classes while
recording current large hotspots.

The local release audit is now an active readiness script. It runs whitespace,
source-quality, wheel-build, and wheel-asset checks, explicitly records that no
publish action is performed, and cleans temporary audit artifacts before
listing release candidates.

## Verification Evidence

Latest verification for this closure:

```text
git diff --check -- .
Result: passed

.venv/bin/python -m unittest tests.test_packaging tests.test_verify_script tests.test_source_quality tests.test_design_contract -v
Result: OK, 22 tests passed

bash scripts/verify-core.sh
Result: OK, 215 tests passed, doctor status ok

bash scripts/verify.sh
Result: OK, 740 tests passed, 1 skipped, doctor status ok

bash scripts/release-audit.sh
Result: passed; whitespace, source quality, wheel assets checked; publish action not performed
```

`bash scripts/release-audit.sh` requires network access when isolated wheel
build dependencies are not already available locally. In the sandboxed run, the
first attempt failed during build dependency resolution; the elevated rerun
completed successfully.

## Publish Readiness

- [x] changelog updated
- [x] maintenance log updated
- [x] release checklist updated
- [x] wheel package data declared
- [x] wheel asset checker added
- [x] CI matrix covers Python 3.11, 3.12, and 3.13
- [x] source quality gate added to core and full verification scripts
- [x] release audit checks run without publishing
- [x] temporary audit artifacts are cleaned
- [x] no new runtime dependency introduced

## Residual Risks

- GitHub Actions matrix still needs confirmation after the branch is pushed.
- `src/onecode/cli.py` remains a large CLI surface and is tracked as a focused
  follow-up refactor.
- `src/onecode/web/api.py` remains a large local Web Gateway module and is
  tracked as a focused follow-up refactor.
- The local Web Gateway remains scoped to trusted loopback use.

## Final Handoff

The branch is ready to commit and push to `origin`. The online update should
include only project-root files from this workspace and should not include
unrelated parent-directory material.
