# Agent Dictionary API

本目录提供一套本地文件接口，方便 agent 直接调阅和理解“字溯东方”汉字基础库。当前不需要启动服务，agent 读取 JSON 文件即可完成查询。

## Files

- `agent-dictionary-manifest.json`
  - 字典入口说明。
  - 告诉 agent 最新数据集、字段含义、推荐查询方式和使用策略。
- `xinhua-base-lookup.json`
  - 轻量查询索引。
  - 适合按字、异体、Unicode、编号、拼音、部首和复核队列快速定位。
- `xinhua-base-entries.json`
  - 当前 500 字新华基础层主数据。
  - 适合读取现代简注、常用词、复核备注和层状态。
- `xinhua-base-entries.csv`
  - 表格索引。
  - 适合人工浏览、筛选和批量校对。
- `DICTIONARY_MAINTENANCE_AND_ROADMAP.md`
  - 词典维护、验证命令和未来发展方向。
  - 适合扩库、修索引、调整执行字或做交接时阅读。
- `DICTIONARY_CLOSEOUT_REPORT_2026-07-05.md`
  - 本轮词典修复和文档对齐收尾报告。
  - 适合确认已改内容、验证证据和下一步开发方向。

## Lookup Contract

`xinhua-base-lookup.json` 提供以下索引：

- `by_modern_or_variant`
  - key: 简体字、繁体字或重要异体。
  - value: 轻量字条摘要。
- `by_unicode`
  - key: Unicode，如 `U+5929`。
  - value: 现代字。
- `by_id`
  - key: 项目编号，如 `001`。
  - value: 现代字。
- `by_pinyin`
  - key: 带数字声调拼音，如 `tian1`。
  - value: 现代字数组。
- `by_radical`
  - key: 部首，如 `心`。
  - value: 现代字数组。
- `review_queue`
  - 需要复核的字条列表，包含 `id`、`modern` 和复核原因。
- `review_groups`
  - 按复核标签分组的清单，如多音字、繁体/异体、简化合并、历史草稿待核。
- `by_review_tag`
  - key: 复核标签。
  - value: 现代字数组。

## Full Entry Contract

完整字条在 `xinhua-base-entries.json` 的 `entries` 数组中。

核心字段：

- `id`: 稳定编号。
- `modern`: 现代规范字，主要检索入口。
- `traditional_or_variants`: 繁体、异体或重要历史相关字形。
- `unicode`: 现代字 Unicode。
- `variant_unicodes`: 繁体、异体或重要相关字形的 Unicode 映射。
- `pinyin`: 普通话读音，数字标调。
- `radical`: 现代检字部首。
- `stroke_count`: 现代总笔画。
- `xinhua_base`: 现代基础义、简注、常用词和来源说明。
- `layer_status`: 新华基础层、字形演变、字义流变、音韵层和复核状态。
- `review_tags`: 机器可读复核分类。
- `review_notes`: 多音、简繁/异体、简化合并、历史层草稿等复核原因。

当前 `review_tags` 包括：

- `polyphonic`: 多音字，需要核对读音排序和义项对应。
- `variant_or_traditional`: 含繁体或异体，需要核对字形来源。
- `simplified_merge_or_multi_variant`: 简化合并或多异体入口，需要拆分历史来源。
- `historical_draft_review`: 已有历史层草稿，需要按材料复核。
- `history_pending`: 历史层尚未补充；这是待补工作，不等于现代基础层有问题。

## Modern Dictionary Source Note

现代义项含义参考《新华字典》释义体系整理；当前文本为项目改写摘要，非逐字原文。

Agent 回答时应这样表述：

- 可以说：“现代义参考《新华字典》释义体系整理。”
- 不要说：“以下为《新华字典》原文。”
- 如果 `review_notes` 提到复核、争议、待核，应说明“该字源解释仍需复核”。

## Query Recipes

### 查一个字

1. 读取 `xinhua-base-lookup.json`。
2. 用 `by_modern_or_variant[字]` 获取摘要。
3. 用摘要中的 `id` 或 `modern` 去完整数据集中取完整字条。

### 查一个拼音

1. 读取 `by_pinyin[pinyin]`。
2. 返回候选字数组。
3. 按用户需求读取完整字条。

### 查一个部首

1. 读取 `by_radical[radical]`。
2. 返回该部首下已有字。
3. 需要完整解释时读取主数据。

### 找待复核字

读取 `review_queue`，按 `review_notes` 展示待复核原因。

### 按复核类型找字

1. 读取 `by_review_tag[tag]`。
2. 或读取 `review_groups[tag]` 获取带原因的清单。
3. 注意：`history_pending` 是待补历史层清单，不单独计入现代基础层问题队列。

## Recommended Agent Response Shape

回答单字查询时建议输出：

1. 现代简注
2. 常用词
3. 繁体/异体与读音
4. 层状态
5. 待复核说明

示例：

```text
天
现代义：天空、自然界、一昼夜等。现代义参考《新华字典》释义体系整理。
常用词：天空、今天、天气、天命、天下。
读音：tian1。
层状态：新华基础层为 draft；历史层如果为 pending 或 draft，应说明仍在整理。
备注：若 `review_notes` 非空，应列出复核原因。
```
