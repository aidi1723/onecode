# Sandbox delivery, 2026-10-19

This phase delivers the default sandbox path at v0.8.0. It is not a 1.0 release. `claims_mainstream_parity` stays false: that flag is a claim of mainstream parity, and this delivery does not make that claim. The rule commit underneath this work is `8369b1f`. The sandbox path is included in the delivery commit on `main`.

## What is delivered

A command or verifier that enters Docker uses the image Python, `python3`, instead of the host interpreter path. The container user is the user who started the run, so an allowed command can create a file in a mode 755 workspace. The root filesystem stays read-only, the network stays closed, and capabilities stay dropped. Parallel steps in one workspace create the sandbox container once.

Two existing checkpoints cover the cases that still cannot run:

| Condition | Reason | Code | Action |
| --- | --- | --- | --- |
| The image Python is missing | `interpreter_not_found` | 32 Gen/Kun | checkpoint |
| The image architecture does not match the host, and no local native sibling exists | `image_platform_mismatch` | 17 Kan/Zhen | checkpoint |

If a local tag named `{image}-amd64` or `{image}-arm64` matches the host, that image runs. On this n100, `python:3.12-slim` is arm64 and `python:3.12-slim-amd64` is the native image, so the default name runs the native image. The arm64 tag was not retagged.

A check that runs and fails stays `verifier_failed`, Li/Kun (40), halt, and blocks delivery. A missing Docker daemon stays `sandbox_required`, Gen/Kun (32), checkpoint. No new hexagram was added.

## Evidence

`bash scripts/verify.sh` passed with 1219 tests and 1 skipped. The skipped test is `test_global_onecode_command_points_to_project_entrypoint`, because `ONECODE_GLOBAL_COMMAND` is not set. n100 is the acceptance host for this close.

On n100, with Docker running and `ONECODE_SANDBOX_IMAGE` unset:

- An allowed command in a mode 755 workspace wrote `ok`.
- A passing unittest stayed passed.
- A failing unittest was `verifier_failed`, code 40, action halt, delivery blocked.
- `python:3.12.3-slim` has no local native sibling, so it checkpointed as `image_platform_mismatch`, code 17, in 93 ms.
- The three sandbox tests that previously assumed the Mac passed.
- `docker_ready` is true and unauthenticated local access is off.

`docker_ready` is true and unauthenticated local access is off. The API token is not in the repository. On n100 it is stored only in `~/.onecode/shell/api-token` with mode `0600`. OneCode reads that file when `ONECODE_API_TOKEN` is unset, including a non-login command. A world-readable file does not count. With the private file present, `production_ready` is true.

## Handoff

Leave `ONECODE_ALLOW_UNAUTHENTICATED` off. Do not copy the token into the source tree. OneCode reads the private token file itself, so a non-login command does not need the shell to export it.

`claims_mainstream_parity` stays false. No third-party review has been contracted, so the flag is not turned on. No provider key is tracked in git. Revoking a key in the provider console remains an account-owner action.

The four-hour observation on n100 finished. The log is `~/onecode-soak-2026-10-19.log`. It ran 64156800 rounds in 14400 seconds. RSS moved from 14272 KB to 14280 KB and did not keep climbing.

## Close

This phase is closed. The sandbox delivery tag is `v0.8.0` at `e1adb3c`. The private-token fix is `53d09ff` on `main`. Version stays 0.8.0.
