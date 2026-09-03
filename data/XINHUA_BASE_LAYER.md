# Xinhua Base Layer

`xinhua-base-entries.json` 是“字溯东方”的现代基础字典层。

## Purpose

先把每个现代规范字的基础信息铺平：

- 现代字
- 繁体/异体
- Unicode
- 拼音
- 部首
- 笔画
- 现代简明义
- 常用词
- 后续层状态

历史字形、字义流变、音韵资料先作为扩展层，不作为继续扩库的前置条件。

## Files

- `xinhua-base-entries.json`
  - 基础层主数据。
- `xinhua-base-entries.csv`
  - 基础层表格索引。
- `xinhua-base-lookup.json`
  - 基础层快速检索索引。
- `hanzi-lifecycle-combined-001-189.json`
  - 当前已有历史扩展层总库。
- `DICTIONARY_MAINTENANCE_AND_ROADMAP.md`
  - 维护规则、验证命令和未来路线。
- `DICTIONARY_CLOSEOUT_REPORT_2026-07-05.md`
  - 本轮词典修正收尾报告。

## Source Policy

现代义项含义参考《新华字典》释义体系整理；当前文本为项目改写摘要，非逐字原文。

字段：

- `source_work`: `《新华字典》`
- `source_usage`: `meaning_reference`
- `quotation_status`: `not_verbatim`

## Layer Status

每个字有 `layer_status`：

- `xinhua_base`: 现代基础层状态。
- `shape_evolution`: 字形演变层状态。
- `meaning_evolution`: 字义流变层状态。
- `phonology`: 音韵层状态。
- `review`: 是否需要复核。

建议状态值：

- `pending`: 未开始。
- `draft`: 已有草稿。
- `verified`: 已核对。
- `needs_review`: 需要复核。

## Expansion Workflow

后续新增几千字时，优先只补 `xinhua_base`：

1. 分配稳定 `id`。
2. 填现代字、Unicode、拼音、部首、笔画。
3. 填现代简明义和常用词。
4. 标记历史层为 `pending`。
5. 后续按批次补 `shape_evolution`、`meaning_evolution`、`phonology`。

## Index Ownership Rule

繁体/异体快速反查键只能归属一个现代入口。存在历史关联但不适合作为现代反查入口的字形，应留在历史层说明或 `review_notes`，不要写入基础层 `traditional_or_variants`。

当前基线：`華` 在快速反查中归属 `华`；`花` 只保留自身入口，历史层继续说明“花/華”关系需复核。

这样项目可以先形成完整现代字典入口，再逐步加深历史层。
