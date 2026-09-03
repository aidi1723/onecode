# N100 Codex Game A/B Summary

Run dir: `/home/aidi/projects/codex-game-ab-20260526/run-20260526-195334-applypatch-fix`

## Result

| Group | Exit | Seconds | Static score | Files | Reported input+output tokens | Non-cached input+output tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| bare Codex | 0 | 153 | 100.0 | 2 | 99,661 | 19,021 |
| guarded 一字诀 | 0 | 116 | 100.0 | 4 | 13,696 | 13,696 |

## Comparison

- Quality by current static rubric: tie, both 100.0.
- Wall time: guarded was 37 seconds faster.
- Reported input+output token reduction: 85,965 tokens, 86.26%.
- Non-cached input+output token reduction: 5,325 tokens, 28.00%.
- JSONL transcript byte reduction: 95.95%.
- Guarded created the requested `index.html` and `README.md`; the other two files are `.yizijue` state evidence.

## Key Finding

The earlier guarded failures were not caused by the two仪/四象/八卦 state machine itself. The missing bridge was Codex CLI's native `apply_patch` tool: Codex sends project creation as `apply_patch(patch=...)`, while Build Mode originally only executed `write_file(path, content)`.

After adding a scoped `apply_patch` handler and requiring the `patch` schema field, the gateway executed the patch inside the guarded workspace and produced real files.

## Caveat

This is one real N100 task with a static file-content rubric. It proves the end-to-end path can produce a small browser game with materially fewer tokens on this task. It does not yet prove general superiority across larger projects, multi-turn test/fix loops, or dynamic browser gameplay validation.
