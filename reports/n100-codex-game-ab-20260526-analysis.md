# N100 Codex Game A/B Analysis

Date: 2026-05-26
Host: yami-n100
Model: gpt-5.5
Codex CLI: 0.133.0
Task: from-scratch browser Canvas game `star-catcher-mini`

## Valid Result

| Group | Endpoint | Exit | Wall seconds | Quality score | Files | JSONL bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bare | `http://10.0.0.184:6780/v1` | 0 | 261 | 100.0 | 2 | 20048 |
| guarded | `http://127.0.0.1:18082/v1` | 124 | 600 | 0.0 | 0 | 394 |

Winner by physical deliverable: bare Codex.

## Bare Output Evidence

Bare Codex created:

- `bare/workspace/star-catcher-mini/index.html`
- `bare/workspace/star-catcher-mini/README.md`

The evaluator found all required checks true:

- `has_index_html`
- `has_readme`
- `has_canvas`
- `has_keyboard_controls`
- `has_buttons`
- `has_score_life`
- `has_level_or_speed`
- `has_audio_toggle`
- `no_external_assets`
- `responsive_hint`
- `readme_run_instructions`

## Guarded Failure Evidence

Guarded Codex did not create files. It timed out after 600 seconds.

Codex JSONL errors:

- high-demand reconnect
- `502 Bad Gateway: Failed to contact upstream model API`

Gateway log root cause:

```text
IsADirectoryError: [Errno 21] Is a directory: '/home/aidi/projects/oneword-buildmode-ab-20260526'
```

The exception happened in:

```text
agent_skill_dictionary/build_mode_writer.py -> safe_write()
agent_skill_dictionary/build_mode_tool_executor.py -> execute_build_mode_tool()
agent_skill_dictionary/gateway_server.py -> _execute_build_mode_responses_tool_calls()
```

Interpretation: the Build Mode gateway tried to execute a write tool, but the parsed path was empty or resolved to the workspace root directory. `safe_write()` then called `write_text()` on a directory, raised `IsADirectoryError`, and the gateway returned 500/502 instead of soft feedback.

## Additional Integration Finding

Before the explicit `造：` run, the same game task was routed to `停` because the Chinese word `暂停` in the requirements matched the old halt keyword policy. That caused immediate 503:

```text
System halted by 一字诀 kernel policy. Wait for human activation token.
```

This is a route priority bug: normal product wording such as `暂停按钮` must not trigger system halt when the overall task is a build/create task.

## Conclusion

This run does not prove that 一字诀 improves Codex project-building quality. It proves the opposite for the current Codex Build Mode integration:

1. Bare Codex can complete the小游戏 project on N100.
2. Guarded Codex currently fails before producing files.
3. The failure is caused by gateway integration defects, not by model inability.

## Required Fixes Before Retest

1. Route priority fix: Build/create intent must outrank incidental halt words like `暂停按钮`.
2. Tool argument hardening: Build Mode `safe_write()` must reject empty path / directory path as `ViolationEvidence` and convert it through Soft Feedback instead of raising 500.
3. Codex Responses tool schema alignment: ensure Codex-visible write tools carry required `path` and `content` schema, or map Codex native file-change events into Build Mode write evidence.
4. Retest with the same run harness after fixes.

## Artifacts

- JSON report: `reports/codex-game-ab.json`
- Markdown summary: `reports/codex-game-ab.md`
- Rescored JSON stdout: `reports/codex-game-ab-rescored.json`
- Bare output: `bare/workspace/star-catcher-mini/`
- Guarded output: `guarded/`
