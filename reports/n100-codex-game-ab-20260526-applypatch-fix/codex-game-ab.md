# Codex Game A/B Report

Run dir: `/home/aidi/projects/codex-game-ab-20260526/run-20260526-195334-applypatch-fix`
Model: `gpt-5.5`

| Group | Exit | Seconds | Score | JSONL bytes | Files |
| --- | ---: | ---: | ---: | ---: | ---: |
| bare | 0 | 153 | 100.0 | 10271 | 2 |
| guarded | 0 | 116 | 100.0 | 416 | 4 |

## Comparison

```json
{
  "score_delta_guarded_minus_bare": 0.0,
  "wall_seconds_delta_guarded_minus_bare": -37,
  "jsonl_bytes_delta_guarded_minus_bare": -9855,
  "winner_by_score": "tie"
}
```

## Checks

### bare

| Check | Pass |
| --- | --- |
| `has_index_html` | True |
| `has_readme` | True |
| `has_canvas` | True |
| `has_keyboard_controls` | True |
| `has_buttons` | True |
| `has_score_life` | True |
| `has_level_or_speed` | True |
| `has_audio_toggle` | True |
| `no_external_assets` | True |
| `responsive_hint` | True |
| `readme_run_instructions` | True |

### guarded

| Check | Pass |
| --- | --- |
| `has_index_html` | True |
| `has_readme` | True |
| `has_canvas` | True |
| `has_keyboard_controls` | True |
| `has_buttons` | True |
| `has_score_life` | True |
| `has_level_or_speed` | True |
| `has_audio_toggle` | True |
| `no_external_assets` | True |
| `responsive_hint` | True |
| `readme_run_instructions` | True |
