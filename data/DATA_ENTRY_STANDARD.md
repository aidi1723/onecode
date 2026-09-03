# 字溯东方数据录入标准 V0.1

本标准用于规范“新华字典基础层”和后续历史扩展层的数据录入。当前原则是：先保证现代基础层完整、稳定、可批量扩展，再逐步补字形演变、字义流变和音韵资料。

## 1. 编号规则

- 字段：`id`
- 格式：三位数字字符串，如 `001`、`130`、`189`。
- 规则：
  - 编号一旦分配，不再变更。
  - 删除或合并字条时，原编号保留为废弃记录，不复用。
  - 扩库时按批次递增。

示例：

```json
"id": "001"
```

## 2. 现代字入口

- 字段：`modern`
- 内容：现代规范简化字或现代通行字。
- 规则：
  - 一个字条只对应一个现代主入口。
  - 繁体、异体、古体不放在 `modern`，放入 `traditional_or_variants`。

示例：

```json
"modern": "国"
```

## 3. 繁体与异体

- 字段：`traditional_or_variants`
- 类型：字符串数组。
- 内容：繁体、异体、重要历史相关字形。
- 规则：
  - 繁体优先放第一位。
  - 简繁合并字必须保留原繁体来源，如 `后/後`、`丑/醜`。
  - 如果古今同形，也保留现代字本身。
  - 每个繁体/异体键在快速反查中只能归属一个现代入口。
  - 如果某字形存在历史关联但不适合作为现代反查入口，应写入 `review_notes` 或历史层说明，不放入 `traditional_or_variants`。

示例：

```json
"traditional_or_variants": ["國", "或", "囶", "圀"]
```

## 4. Unicode

- 字段：`unicode`
- 格式：`U+` 加四位或更多大写十六进制码位。
- 规则：
  - `unicode` 只记录 `modern` 的码位。
  - 繁体码位放在 `traditional_unicode`。
  - 多个异体码位统一放入 `variant_unicodes`。

示例：

```json
"unicode": "U+56FD",
"traditional_unicode": "U+570B",
"variant_unicodes": {
  "國": "U+570B",
  "圀": "U+5700"
}
```

## 5. 拼音

- 字段：`pinyin`
- 类型：字符串数组。
- 格式：数字标调，如 `tian1`、`guo2`、`shi4`。
- 规则：
  - 不使用声调符号，如 `tiān`。
  - 多音字按常用义优先排列。
  - 轻声可写为无声调或 `0`，项目后续统一前暂用无声调，如 `zi`。

示例：

```json
"pinyin": ["xing2", "hang2"]
```

## 6. 部首与笔画

- 字段：`radical`、`stroke_count`
- 规则：
  - 采用现代检字口径。
  - `stroke_count` 为数字，不写字符串。
  - 对部首有争议的字，先按当前基础库口径录入，争议写入 `review_notes`。

示例：

```json
"radical": "日",
"stroke_count": 9
```

## 7. 新华字典基础层

- 字段：`xinhua_base`
- 作用：承载现代字典入口信息。

必备子字段：

- `source_work`
- `source_note`
- `reference_edition`
- `brief_gloss`
- `simple_annotation`
- `common_words`
- `quotation_status`

规则：

- `brief_gloss` 用短语数组，不写长段落。
- `simple_annotation` 用项目改写句，不逐字复制工具书原文。
- `common_words` 优先列常用词，数量建议 3 到 8 个。
- 当前 `quotation_status` 固定为 `not_verbatim`。

示例：

```json
"xinhua_base": {
  "source_work": "《新华字典》",
  "source_note": "现代义项含义参考《新华字典》释义体系整理；当前为项目改写摘要，非逐字原文。",
  "reference_edition": "版本待核：建议统一指定第12版或项目实际采用版本。",
  "brief_gloss": ["天空", "自然界", "一天"],
  "simple_annotation": "天：现代主要用于表示天空、自然界、一昼夜等。",
  "common_words": ["天空", "今天", "天气"],
  "quotation_status": "not_verbatim"
}
```

## 8. 历史扩展层

历史扩展层不是扩库前置条件。新增大量字时，可以先不填历史层。

当前扩展层包括：

- `shape_evolution`
- `meaning_evolution`
- `phonology_sources`
- `review_notes`

规则：

- 不确定的字源解释必须写入 `review_notes`。
- 不把假借义、简化合并义直接当成本义。
- 遇到简繁合并字，必须说明来源差异。
- 没有可靠材料时，状态保留 `pending`，不要编造。

## 9. 层状态

- 字段：`layer_status`
- 允许值：
  - `pending`: 未开始。
  - `draft`: 已有草稿。
  - `verified`: 已核对。
  - `needs_review`: 需要复核。
  - `none`: 无复核问题。

推荐结构：

```json
"layer_status": {
  "xinhua_base": "draft",
  "shape_evolution": "pending",
  "meaning_evolution": "pending",
  "phonology": "pending",
  "review": "needs_review"
}
```

## 10. 复核备注

- 字段：`review_notes`
- 类型：字符串数组。
- 必须写复核备注的情况：
  - 字源解释有多说。
  - 现代简化字合并了不同繁体来源。
  - 本义和现代义明显分离。
  - 多音字需要按义项复核读音排序。
  - `traditional_or_variants` 含多个异体或繁体来源。

推荐写法：

```json
"review_notes": [
  "多音字：xing2、hang2；需按义项和常用词复核读音排序。",
  "含繁体/异体：後；需复核简繁对应、异体来源和义项是否完全合并。"
]
```

## 11. 复核标签

- 字段：`review_tags`
- 类型：字符串数组。
- 作用：给 agent 和人工校对提供机器可读的分组入口。

当前允许标签：

- `polyphonic`: 多音字。
- `variant_or_traditional`: 含繁体或异体。
- `simplified_merge_or_multi_variant`: 简化合并或多异体入口。
- `historical_draft_review`: 已有历史层草稿，需要复核。
- `history_pending`: 历史层尚未补充。

规则：

- `review_queue` 只收录需要复核的问题字。
- `history_pending` 是待补历史层任务，不单独表示现代基础层有问题。
- 一个字可以同时拥有多个 `review_tags`。
  - 多音字需要按义项拆分。
  - 音韵资料暂未核定。

示例：

```json
"review_notes": [
  "丑/醜是简化合并的关键样板，现代丑陋义不可直接回推到丑本字。"
]
```

## 11. 扩库优先级

扩库优先级如下：

1. 高频核心字 500。
2. 常用字 3500。
3. 次常用字 7000。
4. 生僻字、异体字、古文字扩展。

每一批先完成 `xinhua_base`，再决定是否补历史扩展层。

## 12. Agent 使用规则

Agent 默认读取：

```text
data/xinhua-base-entries.json
data/xinhua-base-lookup.json
```

当用户追问字源、演变、古义、音韵时，再读取：

```text
data/hanzi-lifecycle-combined-001-189.json
```

回答时：

- 现代义可说“参考《新华字典》释义体系整理”。
- 不说“以下为《新华字典》原文”。
- 遇到 `review_notes`，必须提示该处需要复核。

## 13. 维护入口

跨文件同步、验证命令、收尾报告和发展路线优先阅读：

```text
data/DICTIONARY_MAINTENANCE_AND_ROADMAP.md
data/DICTIONARY_CLOSEOUT_REPORT_2026-07-05.md
```
