# 词典修复与文档对齐收尾报告

日期：2026-07-05

范围：仅覆盖词典相关内容，包括汉字知识词典、复核清单、Agent 执行词典网关、相关测试和维护文档。

## 完成状态

本轮词典修复已经完成并通过验证。当前主入口保持一致：

- 现代基础层：`xinhua-base-entries.json`，500 条。
- 快速索引：`xinhua-base-lookup.json`，`華` 归属 `华`。
- 复核清单：`variant_or_traditional` 当前为 179 条。
- 历史扩展层：`hanzi-lifecycle-combined-001-189.json` 与基础层 001-189 的现代入口字段对齐。
- Agent 执行词典：响应侧和执行前工具检查均接入根字 kernel allowlist。

## 修复内容

### 1. 汉字基础词典

- 修复 `花 / 華 / 华` 的快速反查冲突。
- `花` 条目保留现代入口 `花`，不再把 `華` 放入 `traditional_or_variants` 或 `variant_unicodes`。
- `華` 在快速反查中归属 `华`。
- 同步更新：
  - `xinhua-base-entries.json`
  - `xinhua-base-entries.csv`
  - `xinhua-base-lookup.json`
  - `data/review/variant_or_traditional.md`
  - `data/review/historical_draft_review.md`
  - `data/review/REVIEW_INDEX.md`
  - `hanzi-lifecycle-combined-001-189.json`
  - `hanzi-lifecycle-combined-001-189-index.csv`

说明：历史层仍保留“花/華关系复杂”的复核提示，但这不再代表 `華` 是 `花` 的快速反查异体。

### 2. Agent 执行词典

- 响应侧 tool-call 守卫现在同时检查：
  - 执行字 `tool_policy`
  - 根字 `KernelPolicy.allowed_tools`
- 修复派生字 metadata 场景：如果 metadata 中 `root_opcode` 是 `造` 等派生字，会回落到该执行字声明的真实根字后再查询 kernel policy。
- 修复 `确认一下`、`需求不明确`、`澄清` 类请求被误路由到 `测` 的问题；这些请求优先进入 `问`。
- 保留动作链路由：`修 + 测 + 总`、`造 + 测 + 总` 不会被 `总` 提前截断。
- Docker 可选沙箱策略对齐：
  - `use_docker=true` 优先使用 Docker。
  - Docker 不可用、守护进程不可连或 socket 权限失败时，非强制模式降级到本地执行。
  - `require_docker=true` 仍硬失败，不降级。

### 3. 文档对齐

已更新维护入口和当前行为说明：

- `AGENT_DICTIONARY_API.md`
- `DATA_ENTRY_STANDARD.md`
- `XINHUA_BASE_LAYER.md`
- `EXPANSION_WORKFLOW.md`
- `DICTIONARY_MAINTENANCE_AND_ROADMAP.md`
- `网关/README.md`
- `网关/docs/dictionary-contract.md`

## 验证证据

已运行：

```bash
cd /Users/aidi/大字典/网关
python3 -m agent_skill_dictionary.validator
```

结果：`OK`

已运行：

```bash
cd /Users/aidi/大字典/网关
python3 -m unittest discover tests
```

结果：`Ran 571 tests in 33.683s`，`OK (skipped=13)`。

另有数据一致性检查：

- `entries=500`
- `variant_or_traditional=179`
- `華 -> 华`
- `花` 不再包含 `華` 快速反查异体

## 当前未决风险

- 历史旧批次文件仍可能保留当时快照中的 `花|華` 表述；这些属于历史快照，不作为当前入口。当前入口以 `xinhua-base-*` 和 `hanzi-lifecycle-combined-001-189.*` 为准。
- `agent-dictionary-lookup.json` 是 189 条旧索引，当前主入口不再引用；后续建议归档或标注为 legacy。
- 还没有统一的索引生成脚本，当前 lookup、CSV、review Markdown 仍需人工同步，容易再次漂移。

## 下一步发展方向

1. 建立生成器：从 `xinhua-base-entries.json` 生成 CSV、lookup 和 review Markdown。
2. 建立整库校验：唯一 ID、唯一现代字、唯一 Unicode、异体键唯一归属、review 队列计数一致。
3. 归档旧索引：将 `agent-dictionary-lookup.json` 移入 legacy/archive 或加醒目标注。
4. 扩展到 3500 常用字：每批 100-200 字，只要求现代基础层完整，历史层默认 pending。
5. 复核优先级：先处理简化合并和多异体，再处理多音字，最后补历史层和音韵层。
6. Agent 执行词典继续收敛：把响应侧守卫、preflight、kernel policy 的工具判断抽成单一判定函数。
7. 上层应用再推进：3500 字基础层稳定后，再评估本地检索、RAG 或向量索引。
