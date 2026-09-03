# Codex Game A/B Report

Run dir: `/home/aidi/projects/codex-game-ab-20260526/run-20260526-191450-explicit-create`
Model: `gpt-5.5`

| Group | Exit | Seconds | Score | JSONL bytes | Files |
| --- | ---: | ---: | ---: | ---: | ---: |
| bare | 0 | 261 | 100.0 | 20048 | 2 |
| guarded | 124 | 600 | 0.0 | 394 | 0 |

## Comparison

```json
{
  "score_delta_guarded_minus_bare": -100.0,
  "wall_seconds_delta_guarded_minus_bare": 339,
  "jsonl_bytes_delta_guarded_minus_bare": -19654,
  "winner_by_score": "bare"
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
| `has_index_html` | False |
| `has_readme` | False |
| `has_canvas` | False |
| `has_keyboard_controls` | False |
| `has_buttons` | False |
| `has_score_life` | False |
| `has_level_or_speed` | False |
| `has_audio_toggle` | False |
| `no_external_assets` | False |
| `responsive_hint` | False |
| `readme_run_instructions` | False |
