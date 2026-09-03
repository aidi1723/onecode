# 扩库流程 V0.1

本流程用于把“字溯东方”从当前 189 字扩展到 500、3500 和更大规模。

## 阶段目标

### Phase 1: 高频核心字 500

目标：

- 补齐现代汉语高频核心字。
- 每字至少完成 `xinhua_base`。
- 历史层只补最关键、最确定的字。

验收：

- `xinhua_base` 500 条。
- 无重复 `id`。
- 无重复 `modern`。
- Unicode、拼音、部首、笔画格式通过校验。

### Phase 2: 常用字 3500

目标：

- 形成现代常用汉字基础入口。
- 先不追求每字都有完整字源。

验收：

- `xinhua_base` 3500 条。
- Agent 可按字、拼音、部首检索。
- 每条有现代简明义和常用词。

### Phase 3: 次常用字 7000

目标：

- 扩展到较完整现代字典层。
- 开始系统区分异体、繁体、生僻字。

验收：

- 基础层稳定。
- 可按繁体/异体反查现代主入口。

### Phase 4: 历史扩展层

目标：

- 逐字补字形演变、字义流变、音韵。
- 优先补高频、基础、争议少的字。

验收：

- 核心 500 字历史层达到 `verified` 或 `needs_review` 标记清晰。
- 不确定处有复核备注。

## 单批录入流程

每一批建议 50 到 200 字。

步骤：

1. 确定字表。
2. 分配连续 `id`。
3. 填 `modern`、`unicode`、`pinyin`、`radical`、`stroke_count`。
4. 填 `xinhua_base.brief_gloss`。
5. 填 `xinhua_base.simple_annotation`。
6. 填 `xinhua_base.common_words`。
7. 设置 `layer_status`：
   - `xinhua_base`: `draft`
   - `shape_evolution`: `pending`
   - `meaning_evolution`: `pending`
   - `phonology`: `pending`
   - `review`: `none` 或 `needs_review`
8. 生成 CSV 和 lookup。
9. 运行校验。
10. 合并到最新基础库。

## 历史层补充流程

当基础层足够大后，再按优先级补历史层：

1. 先补象形、指事、会意类核心字。
2. 再补形声字的声符/义符关系。
3. 最后补假借、转注、异体、简化合并复杂字。

每个历史层条目必须有：

- 字形演变摘要。
- 字义演变摘要。
- 复核备注。

音韵层必须有：

- 中古反切。
- 韵部。
- 是否入声。
- 来源说明。

## 复核优先级

优先复核：

1. 简化合并字，如 `后/後`、`丑/醜`、`发/發/髮`。
2. 本义与现代义分离的字，如 `来/來`、`能`、`无/無`。
3. 多音多义高频字，如 `行`、`乐`、`重`、`长`。
4. 字源多说的字，如 `民`、`真`、`前`。

## Agent 接口更新规则

每次扩库后更新：

- `xinhua-base-entries.json`
- `xinhua-base-entries.csv`
- `xinhua-base-lookup.json`
- `agent-dictionary-manifest.json` 中的 `entry_count`
- `DICTIONARY_MAINTENANCE_AND_ROADMAP.md` 中的当前基线和验证命令，如流程发生变化

精修复核后同步更新：

- `review_tags`
- `review_notes`
- `review_queue`
- `review_groups`
- `by_review_tag`
- `data/review/REVIEW_INDEX.md`

同步时必须检查繁体/异体快速反查键唯一归属；同一个异体键不能同时指向两个现代入口。

如果历史层也更新，同步更新：

- `hanzi-lifecycle-combined-*.json`
- `hanzi-lifecycle-combined-*-index.csv`

## 命名规则

基础层：

```text
xinhua-base-entries.json
xinhua-base-entries.csv
xinhua-base-lookup.json
```

历史层批次：

```text
hanzi-lifecycle-batch-011.json
hanzi-lifecycle-batch-011-index.csv
```

历史层合并：

```text
hanzi-lifecycle-combined-001-500.json
hanzi-lifecycle-combined-001-500-index.csv
```
