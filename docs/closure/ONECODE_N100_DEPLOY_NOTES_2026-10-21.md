# n100 deploy notes, 2026-10-21

Kernel tree: `~/onecode-rule-check`. Shell tree: `~/onecode-librechat-v088`, branch `feature/onecode-shell-v088`, package version `v0.8.8`. Dependencies were installed with `npm ci` (2988 packages). The old ungitted shell at `~/onecode-librechat` stays at `v0.8.6-rc1` and was not overwritten.

## What passed

- `production_ready` is true. Docker is ready and the private API token is set.
- 253 focused kernel tests passed: model loop, provider contract, read preface, host stage, shell launcher, web API, sandbox, verifier, and deployment boundary.
- A real sandbox command using `python:3.12-slim` ran as `x86_64` after the native-image fix, with no platform warning.
- OneCode shell Jest specs passed on n100: `server/routes/onecode.spec.js` and `server/services/OneCode/projectPicker.spec.js`, 27 tests.

## Problems

| Problem | Status |
| --- | --- |
| `run_in_sandbox` started the arm64 tag `python:3.12-slim` and Docker warned that the host is amd64. | Fixed. `run_in_sandbox` and `run_in_reused_sandbox` now use `with_runnable_image`. Re-checked on n100: stdout is `x86_64`, stderr is empty. |
| The new shell had no `node_modules`. | Fixed for this tree. `npm ci` completed in `~/onecode-librechat-v088`. |
| Folder picker tests assumed macOS and read the host `ONECODE_API_TOKEN`. On Linux the picker correctly refuses to run, and the test compared against the published dev token. | Fixed in the spec. It forces the dev token and covers both macOS and Linux. The picker itself remains macOS-only. |
| The launcher default directory is the sibling `../onecode-librechat`. That path does not exist next to the current project. On n100 the new tree is `~/onecode-librechat-v088`. | Open. Start with `--librechat-dir`. |
| A chat approval executes the approved plan, then asks for the next named file that is still missing. A file that does not advance the required set stops as `no_progress`. The sandbox check runs once the named files are present. | Fixed. |
| The full LibreChat client suite was not run. A broad API Jest invocation also executed unrelated agent specs and failed inside LibreChat's own agent mocks. | Open. Those failures are outside the OneCode routes. |
| Kernel and shell changes are local and not pushed. | Closed later the same day. Kernel `8d6ad91` and `812bab7` are on `origin/main`. See [ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md](ONECODE_SHELL_READ_CLOSEOUT_2026-10-21.md). |
