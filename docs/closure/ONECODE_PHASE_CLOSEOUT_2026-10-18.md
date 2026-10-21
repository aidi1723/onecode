# Phase closeout, 2026-10-18

This phase is closed at v0.8.0. It is not a 1.0 release. `claims_mainstream_parity` stays false. No tag was created and nothing was pushed. `main` carries the rule fixes locally and is ahead of `origin/main`. The rule code is `8369b1f`. This note adds no kernel change.

## What closed

The task rules use one reading of the existing 64 hexagrams. The transition and the task schedule are the same action. Tagged writes, patches, commands, reads, and lists follow that action. Siblings are judged separately. One hexagram stays itself. Different hexagrams combine by the aggregate, and entropy stays evidence. A refusal reason classifies back to its family. A halted task exits nonzero. The reading is written in [ONECODE_HEXAGRAM_RUNTIME_CLOSEOUT_2026-10-18.md](ONECODE_HEXAGRAM_RUNTIME_CLOSEOUT_2026-10-18.md).

Three census rounds on the Mac and three on n100 matched that reading, with 0 mismatches. Focused rule tests passed three times on each machine: 148 on the Mac, and 143 Docker-free tests on n100. On n100, with a native amd64 image and a `python3` verifier command, a passing check stayed passed, a failing check halted on Li/Kun (40), a timeout on the arm64 tag checkpointed on Kan/Zhen (17), and all 64 tagged commands followed their hexagram. The container ran as user 65534, without a network, on a read-only root filesystem. The rounds are written in [ONECODE_RULE_AUDIT_ROUNDS_2026-10-18.md](ONECODE_RULE_AUDIT_ROUNDS_2026-10-18.md).

`bash scripts/verify.sh` remains the code gate. It was already green at `8369b1f` before these documents.

## Left for a later phase

n100 having a healthy Docker daemon does not close the default security path.

- The built-in verifier command uses the host interpreter path, so the container exits 127 and records `verifier_failed` before the tests run.
- User 65534 cannot create a file in a normal 755 workspace, so an allowed `run_command` that writes a file does not land.
- Three tests assume the Mac: no Docker, and the host interpreter inside the container.
- The local tag `python:3.12-slim` on this n100 is arm64. The native image used for the audit is `python:3.12-slim-amd64`.
- A version bump, a tag, a push, mainstream parity, and a third-party security review stay outside this phase.

The sandbox items above were delivered on 2026-10-19. See [ONECODE_SANDBOX_DELIVERY_2026-10-19.md](ONECODE_SANDBOX_DELIVERY_2026-10-19.md). Version 1.0.0 is [ONECODE_V1_0_RELEASE_2026-10-20.md](ONECODE_V1_0_RELEASE_2026-10-20.md). The later named-file and repair reading is [ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md](ONECODE_TASK_RULE_FOLLOWUP_2026-10-20.md).
