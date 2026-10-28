# WorkBuddy code exam closeout, 2026-10-28

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. No new hexagram was added. `IchingKernel.classify_outcome` was not edited. `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies stay `dependencies = []`.

This note closes the external code-subset exam described in [ONECODE_WORKBUDDY_CODE_EXAM_PROTOCOL_2026-10-26.md](ONECODE_WORKBUDDY_CODE_EXAM_PROTOCOL_2026-10-26.md). The score is not Pass@k and not a Harbor reward from the official task image. Hidden tests, `gold.patch`, and `scorer.py` stayed out of the model workspace on every row.

## Exam

The run was on n100, through the chat path, model `gpt-6.1-sol`, endpoint `https://anyrouter.top/v1/responses`, with `ONECODE_RESPONSES_TEXT_FORMAT=off` and `ONECODE_PROMPT_CACHE_KEY=any`. The runner approved at most four plans per task. The 80-row file is `~/workbuddy-exam/results-r2.jsonl` on n100. It is not in this repository.

| Result | Count |
| --- | --- |
| `completed`, hexagram 39 | 12 |
| `halted` / `no_actionable_plan` | 31 |
| `model_provider_error` (gateway HTTP 520, `Origin Error`) | 36 |
| `ValueError` while applying an empty patch | 1 |
| Approvals | 17 |
| `grader_inputs_withheld` | 80 |
| Numeric host rewards | 16, mean 0.190, none at 1.0 |
| `ungraded` | 64 |

Counting the 64 ungraded rows as 0 puts the whole-set mean near 0.038. The highest host reward is 0.750 on `refactor-medium-request_merge_path`. Those numbers come from running `verifier.py` or `scorer.py` with the n100 virtualenv, not from each task's Docker image. Several verifiers failed because `python` was not on `PATH`. Several scorers exited because they require `--agent-patch` and `--gold-patch`.

A second pass re-asked the 31 `no_actionable_plan` tasks and stored the model reason in `~/workbuddy-exam/results-r3-diagnose.jsonl`. Thirty refused again. One, `schema_behavior-hard-unevaluated_properties`, returned one asset and stopped at approval. The refusals split this way:

- 19: the prompt did not include the target file's text, and `execution_plan` was forbidden, so the model would not overwrite the file.
- 7: the file the task needed was outside the first eight paths the prompt listed.
- 3: the task asked for tests only, while `tests/` stays protected and the implementation file was also marked off limits.
- 1: the task asked for a root `analysis.json`, while the prompt asked for one existing Python file.

## What changed for this closeout

- A workspace path named in the task, such as `click_like/formatter.py`, becomes the single write target when that file exists and the task does not say to leave it alone. Up to four such files are copied into the preface, 4000 characters each.
- When several existing files are named, the prompt lists those files and points at the preface. It no longer treats the first eight alphabetical Python files as the only legal set.
- An empty `replace_block` is rejected while the plan is parsed. Building intents from an empty patch returns `invalid_intent` and does not raise.

## Still outside this closeout

- A task that only allows new tests still has no legal write, because `tests/` stays protected.
- A task that asks for `analysis.json` is not turned into a Python asset.
- HTTP 520 from the gateway is a channel failure. One retry does not make it a pass.
- The host grader is not the official WorkBuddy Harbor score.
- `production_ready` is still the local Docker, token, and authentication check. It is not a financial, industrial, or military certification.

## Gate

`bash scripts/verify.sh` on this Mac, without Docker:

- `unittest`: `Ran 1317 tests`, `OK (skipped=1)`
- skipped test: `test_global_onecode_command_points_to_project_entrypoint` because `ONECODE_GLOBAL_COMMAND` is unset
- `coverage`: 86% (14202 statements, 1943 missed)
- `doctor`: status `ok` (`docker_ready: false`, `production_ready: false`)

n100 was not asked to re-run `verify.sh` for this note. n100 remains the sandbox acceptance host.
