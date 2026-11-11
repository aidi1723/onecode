# WorkBuddy code-subset exam protocol, 2026-10-26

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. No new hexagram was added. `IchingKernel.classify_outcome` is not changed by this protocol. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`.

This protocol is the first step of the corrected Harness² comparison. It names an external exam. It does not run that exam, and it does not authorize a Harness² adapter, a `--substrate` flag, or a model that rewrites its own skills, scripts, or tests. The run is recorded in [ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md](ONECODE_WORKBUDDY_EXAM_CLOSEOUT_2026-10-28.md).

The local commit that holds the audit remediation is `efb4447`. `origin/main` is still `2e5696d`. The Mac gate recorded for the remediation tree is `Ran 1306 tests`, `OK (skipped=1)`. The gate recorded for `2e5696d` is `Ran 1293 tests`, `OK (skipped=1)`. Neither number is a WorkBuddy score.

## What is in scope

The exam set is the WorkBuddy Bench **code** subset only:

- Archive `wb-bench-code-v1.0.tar.gz`, 80 tasks, published on Hugging Face as `tencent/workbuddy-bench`.
- The GitHub project is `Tencent/workbuddy-bench`. The archives are not stored in that git repository.
- After a checksum-verified extract, tasks live under `datasets/wb-bench-code-v1.0/tasks/<task-id>/`.
- Each task has `instruction.md`, `task.toml`, `environment/` (`Dockerfile`, `docker-compose.yaml`, `scorer.py`, `workspace.tar.gz`), and `tests/`. The code subset also ships `gold.patch` with the hidden grader material.

Web, Office, and Security subsets are out of this protocol. JobBench and Harvey LAB are out of this protocol.

## What the model may see

The model prompt is `instruction.md` plus the unpacked workspace that `environment/workspace.tar.gz` contains. `workspace.tar.gz` stays packed on the host until the exam runner extracts it into the task container. It is not unpacked into the OneCode git repository.

The model does not receive `tests/`, `gold.patch`, `scorer.py`, the task Dockerfile, or the official score. Those files are grader inputs. Copying them into the model workspace, the preface, or the ledger body fails that task's record.

## How a task is run

The acceptance host is n100, because the published tasks run in Docker. This Mac has no Docker and cannot host the exam.

1. Download only the code archive. Verify it against the published `SHA256SUMS` before extracting. Do not commit the archive or the extracted tasks.
2. Extract `workspace.tar.gz` only inside the task's own container, or into a disposable directory outside the OneCode repository. The OneCode repository is not the task workspace.
3. Start OneCode on that disposable workspace with the chat path: `strict` approval, `max_repair_attempts=1`, sandbox network `none`.
4. Every write waits for a human `approved: true`. The model may change implementation files that `PathGuard` already allows. It may not write `.git`, `.github`, `.onecode`, or a path under `tests/`.
5. Stop the task when the human stops approving, when the kernel halts, or when the existing repair budget is spent. Do not open a second repair inside the same run.
6. Grade the resulting diff with the published task environment and `scorer.py`. OneCode's `python:3.12-slim` image is not a substitute for the task Dockerfile. A missing official grade is recorded as `ungraded`. It is not recorded as a pass.

## What is recorded

For each task, keep one row outside the OneCode repository:

| Field | Meaning |
| --- | --- |
| `task_id` | Directory name under `tasks/` |
| `instruction_sha256` | SHA-256 of `instruction.md` |
| `approvals` | Count of approved plans |
| `status` | OneCode status at stop |
| `reason` | OneCode reason at stop, if any |
| `iching_status_code` | Code returned at stop |
| `delivery_status` | OneCode delivery field |
| `grader_inputs_withheld` | True only if `tests/`, `gold.patch`, and `scorer.py` never entered the model workspace or prompt |
| `official_reward` | Harbor run-level reward for that task, or `ungraded` |
| `ledger_matches` | Result of `ledger_matches_workspace` on the disposable workspace |

The headline number, if an official runner is used later, is the Harbor run-level reward: the average of the per-task hidden-test scores. A task-level pass rate and an LLM-judge reading may be stored beside it. They are not Pass@k, and they are not the OneCode unittest count.

`claims_mainstream_parity` stays false after this exam, including a high reward. Turning that flag on still requires a separate written decision.

## Skill and script changes

A failed task does not edit `.onecode/skills/`, add a script library, or rewrite a prompt. `.onecode/` is already denied by `PathGuard`.

A later skill manifest or a later deterministic helper script is a separate human decision. It becomes part of the baseline only after an approved plan and a ledger entry. This protocol does not implement that path.

## What stays in code

`path_guard.py`, `preset_tests.py`, the unittest guard, and the read-only sandbox mounts for `.git`, `.github`, `.onecode`, and `tests` stay as code. They are not moved into a Markdown guardrail file.

No `--substrate` parameter is added. OneCode is not registered as an OpenCode or Codex executor by this document.
