# OneCode LibreChat Execution Reliability Closure

Date: 2026-07-16
Status: Implementation complete and merged to local `main`; OneCode GitHub feature-branch publication authorized after privacy and gate checks; LibreChat shell remains a separate local repository (no owner GitHub remote); live-shell matrix deferred to operator run

## Scope

Close the reliability program for OneCode task routing, workspace selection,
approval, resume, Console state, and error handling across:

- OneCode (parent monorepo Git root; package code root `one code/`)
- LibreChat (separate local shell repository; reliability branch tip recorded below)

Design: `docs/superpowers/specs/2026-07-16-onecode-librechat-execution-reliability-design.md`
Plan: `docs/superpowers/plans/2026-07-16-onecode-librechat-execution-reliability.md`

## Commits

### OneCode

Implementation was developed on `feature/onecode-execution-reliability`, then
fast-forward merged into local monorepo `main` at `59973e5`. Publication to
GitHub uses the owner-approved remote line
`origin/feature/gateway-iching-rule-sync` (not `origin/main`, which remains an
unrelated history).

| Commit | Summary |
| --- | --- |
| `431b109` | docs: design OneCode LibreChat reliability hardening |
| `5001745` | docs: plan OneCode LibreChat reliability hardening |
| `4a7181c` | fix: classify natural language project tasks |
| `86cb482` | fix: enforce shell workspace and resume approval |
| `161c1e3` | feat: expose redacted pending approval plans |
| `fe313e0` | feat: publish shell projection v5 approval state |
| `626f545` | fix: align OneCode shell status semantics |
| `59973e5` | docs: close OneCode LibreChat reliability work |

Implementation + first closure head: `59973e5246cd1d4afef9c31150ab17c7b0168932`

### LibreChat (local shell repository only)

| Commit | Summary |
| --- | --- |
| `cccb2f00c` | feat: add explicit OneCode task modes |
| `e75e894c8` | feat: forward OneCode task mode metadata |
| `0c1567fd2` | feat: proxy OneCode approval plans |
| `eea7e2bcc` | feat: add OneCode Console approvals |
| `e91505729` | fix: surface OneCode planning and errors |
| `c55ec4d4d` | fix: clarify OneCode project status labels |
| `9d5eb9b1f` | test: verify OneCode approval workflow |

Local `main` tip after fast-forward merge: `9d5eb9b1f730cf013ba122a0b27a98cb20133227`
Remote publication: **not performed**. The LibreChat checkout tracks the
community upstream only; there is no owner-controlled GitHub remote for the
OneCode shell fork. LibreChat changes stay local until a separate publication
decision is made.

## Projection Contract

- Shell projection version: **v5**
- Required nested field: `approval_state` with `required`, `plan_id`, `status`
- Pending approval next action: `approve`
- Project status adds `git.relation` (`workspace` \| `parent` \| `none`) and `skill_sources.runtime_router_status=per_run`

## Automated Gate Results

### OneCode

Commands (from package root `one code/`, using the project virtualenv when required):

```bash
cd "one code"
PYTHONPATH=src python3 -m unittest \
  tests.test_task_classification \
  tests.test_approval_plans \
  tests.test_web_api \
  tests.test_shell_projection -v
# Result: Ran 119 tests — OK

PYTHON="<project-venv>/bin/python" bash scripts/verify.sh --skip-tests
# Result: install skipped (venv), compileall OK, source-quality OK, doctor status=ok
```

Full suite notes (project venv Python):

```bash
PYTHONPATH=src "<project-venv>/bin/python" -m unittest discover -s tests -v
# Ran 926 tests: 1 failure + 1 error (pre-existing env issues, not reliability code paths)
# - test_venv_entrypoint: isolated worktree lacks .venv/bin/onecode entrypoint
# - test_verify_script smoke: recursive verify without PYTHON=venv hits PEP 668
```

Bare system `python3 -m unittest discover` without the project venv fails
additional TUI imports (`textual` missing). Reliability gates use the project
venv and the targeted modules above.

Post-merge re-check (local `main` tip `59973e5`): 119 reliability unit tests
OK. Publication-prep re-check on the clean publish worktree repeats the same
targeted modules and source-quality / doctor gates before push.

### LibreChat

```bash
cd packages/api && npx jest src/endpoints/custom/onecode.spec.ts \
  src/endpoints/custom/onecode.integration.spec.ts \
  src/endpoints/custom/initialize.spec.ts --coverage=false --runInBand
# PASS — 37 tests

cd packages/data-provider && npm run build
# PASS

cd api && npx jest server/routes/onecode.spec.js \
  server/services/OneCode/projectPicker.spec.js --runInBand
# PASS — 30 tests

cd client && npx jest src/onecode/project.test.ts src/onecode/errors.test.ts \
  src/components/OneCode \
  src/components/Chat/Input/OneCodeModeControl.test.tsx \
  src/components/Chat/Input/OneCodeActivityStatus.test.tsx \
  --runInBand --coverage=false
# PASS — 50 tests

npm run build:api   # PASS
npm run build:client  # PASS (PWA icon glob warnings only; dist produced)
```

Post-merge re-check on client reliability surfaces: 3 suites / 22 tests OK
(`ApprovalTab`, `OneCodeConsole`, `errors`).

### Playwright / live smoke

| Gate | Status | Notes |
| --- | --- | --- |
| `e2e/specs/onecode-console.spec.ts` | Spec committed (LibreChat local) | Requires authenticated local server (`e2e/playwright.config.local.ts`). Deferred (no running LibreChat + storageState). |
| `scripts/onecode-smoke.mjs` | Script expanded (LibreChat local) | Requires live OneCode API + `ONECODE_SMOKE_WORKSPACE`. Deferred (API process unavailable). |
| Manual live-shell matrix (approve/reject/resume/timeout/replay) | Deferred | Operator must record run IDs, plan IDs, status codes, and artifact hashes when shell is up. |

Playwright expected command (LibreChat checkout):

```bash
npx playwright test e2e/specs/onecode-console.spec.ts \
  --config=e2e/playwright.config.local.ts --workers=1
```

Smoke expected command (LibreChat checkout):

```bash
ONECODE_SMOKE_WORKSPACE=/path/to/allowed/workspace \
ONECODE_API_BASE_URL=http://localhost:19080/v1 \
ONECODE_API_TOKEN=dev-local-token \
node scripts/onecode-smoke.mjs
```

## Manual Live-Shell Matrix (operator checklist)

Launch shell with the LibreChat checkout and a disposable allowed workspace, then record evidence for:

1. `帮我看看这个仓库` → read task
2. `写一个 hello.txt` → `approval_required`, no file written
3. Console reject → no file
4. Console approve → only planned file
5. Mutating resume → new pending approval, no silent mutation
6. Clear project → `workspace_required`
7. Forced provider timeout → single upstream call, visible 504
8. Replay approved plan → 409

Do not record API keys or full sensitive prompts.

## Delivered Behavior

- Deterministic classification with stable reasons for common CN/EN task phrases
- Strict workspace for non-chat tasks; resume requires explicit approval
- Redacted pending-plan list + approval decision APIs
- Shell projection v5 `approval_state`
- LibreChat modes (`auto` / `chat` / `read_task` / `change_task`) with metadata forwarding
- Console **审批** tab: list, approve, reject, in-flight disable, 409 messaging
- Client planning status `OneCode 正在规划` (no fake token stream)
- Operational Chinese error mapping (`workspace_required`, timeout, model missing, …)
- `titleConvo: false` for OneCode endpoint in `librechat.yaml`
- Parent vs workspace Git labels; skill manifest vs per-run router status

## Privacy And Path Hygiene (publication delta)

Before GitHub update, the publication delta relative to
`origin/feature/gateway-iching-rule-sync` was reviewed:

- No real API keys, PEM private keys, or cloud tokens in changed files.
- Machine-local absolute paths in plan/closure docs were redacted to portable
  placeholders (`one code/`, `<project-venv>`, “parent monorepo Git root”).
- Historical docs already on the remote feature line may still mention local
  paths; they are out of this delta and not rewritten here.
- LibreChat local repository is excluded from this OneCode GitHub push.

## Unresolved Risks

1. Full OneCode `unittest discover` depends on project `.venv` layout; isolated
   worktrees may lack the `onecode` console entrypoint so entrypoint tests fail.
2. Playwright and live smoke still need a live dual process; deferred to the
   operator shell session.
3. Untracked local `node_modules` symlinks are test plumbing and must not be
   committed.
4. Combined product release should wait for operator completion of the
   live-shell matrix and Playwright screenshots.
5. LibreChat reliability commits are local-only until an owner GitHub remote
   exists for that shell.

## Rollback Points

- OneCode GitHub feature branch: after publication, create new revert commits
  for the intended range; do not force the remote branch backward.
- OneCode pre-program plan tip: `5001745` (docs-only) or per-commit reverts of
  `4a7181c`…`59973e5`.
- LibreChat local: revert `cccb2f00c`…`9d5eb9b1f` on the shell repository.
- Config-only: restore `titleConvo: true` in `librechat.yaml` if title
  generation must return immediately.

## Release Gate Checklist

| Condition | Met? |
| --- | --- |
| OneCode strict workspace exported by shell launcher | Yes (code + unit tests) |
| LibreChat sends workspace and optional mode metadata | Yes (local LibreChat) |
| Shell projection v5 served | Yes |
| LibreChat Console consumes pending plans | Yes (local LibreChat) |
| Resume uses explicit approval | Yes (unit tests) |
| OneCode targeted reliability tests + verify doctor | Yes |
| LibreChat targeted tests + api/client builds | Yes (local) |
| Privacy / absolute-path hygiene on OneCode publish delta | Yes (this pass) |
| Playwright desktop/mobile | Spec ready; operator execution deferred |
| Live-shell evidence matrix | Operator evidence deferred |
| OneCode GitHub feature-branch fast-forward | Recorded in GitHub publication closure |
| LibreChat GitHub publication | Not applicable / no owner remote |

## Placeholder Scan

Verified with a case-sensitive search for unfinished-marker tokens (the usual
unfinished-work abbreviations and fabricated-evidence phrases). Result: clean.
Live-shell and browser matrix rows above are explicitly deferred with commands
to execute, not left as unfinished markers.

## Related Records

- Design / plan under `docs/superpowers/`
- Prior shell baseline: `docs/ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md`
- Prior GitHub feature publication: `docs/ONECODE_V087_VNEXT_GITHUB_CLOSURE_2026-07-16.md`
- This publication: `docs/ONECODE_EXECUTION_RELIABILITY_GITHUB_PUBLICATION_2026-07-16.md`
