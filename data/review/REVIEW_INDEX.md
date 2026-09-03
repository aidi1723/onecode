# 复核清单索引

数据版本：0.4.2
总字数：500
需要人工/agent 复核字条：357
历史层待补字条：311

| 标签 | 清单 | 数量 | 用途 |
| --- | --- | ---: | --- |
| `polyphonic` | [多音字复核](./polyphonic.md) | 118 | 多音字复核 |
| `variant_or_traditional` | [繁体/异体复核](./variant_or_traditional.md) | 179 | 繁体/异体复核 |
| `simplified_merge_or_multi_variant` | [简化合并/多异体复核](./simplified_merge_or_multi_variant.md) | 8 | 简化合并/多异体复核 |
| `historical_draft_review` | [历史层草稿复核](./historical_draft_review.md) | 189 | 历史层草稿复核 |
| `history_pending` | [历史层待补](./history_pending.md) | 311 | 历史层待补 |

## 队列说明

- `review_queue` 只收录需要复核的问题字：多音、繁体/异体、简化合并、历史草稿待核。
- `history_pending` 是待补历史层清单，不单独计入复核问题队列。

## 建议复核顺序

1. 先处理 `simplified_merge_or_multi_variant`，因为它影响简繁反查和历史来源拆分。
2. 再处理 `polyphonic`，统一读音排序和义项对应。
3. 接着处理 `variant_or_traditional`，补齐异体来源说明。
4. 最后处理 `historical_draft_review` 与 `history_pending`，逐步补字形、字义、音韵层。
