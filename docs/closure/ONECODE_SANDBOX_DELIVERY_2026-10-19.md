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

`bash scripts/verify.sh` passed with 1217 tests and 1 skipped.

On n100, with Docker running and `ONECODE_SANDBOX_IMAGE` unset:

- An allowed command in a mode 755 workspace wrote `ok`.
- A passing unittest stayed passed.
- A failing unittest was `verifier_failed`, code 40, action halt, delivery blocked.
- `python:3.12.3-slim` has no local native sibling, so it checkpointed as `image_platform_mismatch`, code 17, in 93 ms.
- The three sandbox tests that previously assumed the Mac passed.
- `docker_ready` is true and unauthenticated local access is off.

`docker_ready` is true and unauthenticated local access is off. The API token is not in the repository. On n100 it is stored only in `~/.onecode/shell/api-token` with mode `0600`, and login shells load it through `~/.onecode/env`. With that environment loaded, `production_ready` is true.

## Handoff

Leave `ONECODE_ALLOW_UNAUTHENTICATED` off. Do not copy the token into the source tree. A non-login command that does not read `~/.profile` still needs `~/.onecode/env` sourced first.

Still outside this delivery: a version bump to 1.0, mainstream parity, a third-party security review, the four-hour soak, and key revocation. The delivery tag is `v0.8.0`.
