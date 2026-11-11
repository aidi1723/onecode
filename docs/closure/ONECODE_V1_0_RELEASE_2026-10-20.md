# OneCode 1.0.0 release, 2026-10-20

This is the formal release. Version is 1.0.0. The acceptance host is n100.

## Basis

- The 64-hexagram task rules match one reading. Three census rounds on n100 had no mismatches.
- The default sandbox uses `python3` and the user who started the run. On n100, `python:3.12-slim` resolves to the local native image `python:3.12-slim-amd64`. An allowed command wrote a file in a mode 755 workspace. A passing check stayed passed. A failing check halted on Li/Kun (40) and blocked delivery. An image with no native sibling checkpointed on Kan/Zhen (17).
- A non-login process reads `$ONECODE_HOME/shell/api-token` when the file mode is `0600`. On n100, `production_ready` is true.
- The four-hour observation finished: 64156800 rounds, RSS from 14272 KB to 14280 KB, with no continued climb. The log is `~/onecode-soak-2026-10-19.log` on n100.
- `bash scripts/verify.sh` passed with 1219 tests and 1 skipped. The skip is `ONECODE_GLOBAL_COMMAND` not being set.

## Not claimed

`claims_mainstream_parity` stays false. No third-party security review was contracted, so this release does not claim parity with general coding agents. No provider key is stored in git. Revoking a key in a provider console remains the account owner's action.

The model channel User-Agent stays `onecode/0.8` so the existing gateway still accepts the client.

## Tags

`v0.8.0` remains at `e1adb3c`. `v1.0.0` names this release commit, `dd51424`, on `main`.

## Follow-up

The task-rule follow-up on the same version is [ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md](ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md). Commit `654ddb2` gives a named Python file its own write slot, retries invalid JSON once on the same step, allows one implementation patch after a failed sandbox check, and keeps that patch out of `tests/`. The 2026-10-21 close keeps a protected path unwritten, closes a finished named write into the sandbox check, retries an empty task string once, and treats a `src` module already on disk as present. A second failure still halts on Li/Kun (40). Gateway statuses 408, 429, 502, 503, and 504 checkpoint on Kan/Zhen (17). The tag above does not move.
