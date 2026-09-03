# 词典维护与发展路线

本文档对齐两个“词典”层：

- 汉字知识词典：`data/xinhua-base-entries.json`、`data/xinhua-base-lookup.json`、`data/hanzi-lifecycle-combined-001-189.json`
- Agent 执行词典：`网关/agent_skill_dictionary/programming-agent-skill-dictionary.json`、`oneword_dict.json`、根字 workflow 和 kernel policy

目标是让数据扩库、索引同步、执行字演进和验证命令保持同一套维护节奏。

## 当前基线

- 现代基础层：500 字，入口文件为 `xinhua-base-entries.json`。
- 历史扩展层：001-189，入口文件为 `hanzi-lifecycle-combined-001-189.json`。
- Agent 执行词典：22 个执行字，8 个根字 workflow，Kernel Runtime Policy 作为工具权限硬边界。
- 复核队列：`review_queue` 只收录需要复核的问题字；`history_pending` 是待补历史层，不单独算现代基础层问题。
- 当前收尾报告：`DICTIONARY_CLOSEOUT_REPORT_2026-07-05.md`。

## 源文件职责

| 文件 | 职责 | 维护规则 |
| --- | --- | --- |
| `xinhua-base-entries.json` | 现代基础层主数据 | 所有现代义、读音、部首、笔画、复核标签先改这里 |
| `xinhua-base-entries.csv` | 人工浏览和表格校对 | 必须与 JSON 同步，不作为权威源 |
| `xinhua-base-lookup.json` | Agent 快速索引 | 必须由主数据语义同步，不能出现异体键多归属 |
| `data/review/*.md` | 人工复核清单 | 数量、标签和原因必须与 lookup 保持一致 |
| `hanzi-lifecycle-combined-001-189.json` | 历史层总库 | 与基础层 001-189 的现代字段保持一致 |
| `programming-agent-skill-dictionary.json` | 执行字能力词典 | 新增/调整执行字必须同步 validator 和测试 |
| `kernel_policy.py` | 根字工具权限硬边界 | 响应侧和执行前检查都必须使用同一 allowlist |
| `workflow_registry.json` 与 `workflows/*.md` | 根字工作流提示 | 根字变更时同步 registry、workflow 和测试 |

旧批次文件是历史快照，不作为当前入口。当前入口以 `xinhua-base-*`、`data/review/*`、`hanzi-lifecycle-combined-001-189.*` 和 `agent-dictionary-manifest.json` 为准。

## 数据维护规则

1. 先改主数据，再同步派生文件。
2. `modern`、`id`、`unicode` 必须唯一。
3. `traditional_or_variants` 的每个键只能归属一个现代入口；如果一个字形确有多入口歧义，先不要放入快速反查键，改写到 `review_notes` 等人工复核字段。
4. 简繁关系优先按现代规范处理。例如 `華` 归属 `华`，不作为 `花` 的快速反查异体。
5. 复核标签减少或增加时，必须同步：
   - `xinhua-base-lookup.json` 的 `review_queue`
   - `review_groups`
   - `by_review_tag`
   - `data/review/*.md`
   - `data/review/REVIEW_INDEX.md`
6. 历史层待补不等于现代基础层错误；回答时要区分“现代义可用”和“字源/音韵仍待核”。

## 执行词典维护规则

1. 请求转发前和响应返回后都必须执行工具权限检查。
2. 响应侧 tool call 必须同时满足：
   - 执行字 `tool_policy`
   - 根字 `kernel_policy.allowed_tools`
3. 包含“需求不明确”“确认一下”“澄清”的请求优先进入 `问`，不要被 `测` 的“确认/验证”误吸收。
4. `use_docker=True` 是优先使用 Docker；只有 `require_docker=True` 才是硬依赖。Docker 守护进程不可用或权限失败时，非强制模式应降级到本地执行并记录 `sandbox_fallback`。
5. `修`、`测`、`卫` 等物理执行链必须保留审计证据；失败不能写成已完成。

## 必跑验证

修改汉字基础层后运行：

```bash
cd /Users/aidi/大字典/网关
python3 -m unittest tests.test_xinhua_base_dictionary
```

修改执行词典、网关路由或工具权限后运行：

```bash
cd /Users/aidi/大字典/网关
python3 -m agent_skill_dictionary.validator
python3 -m unittest tests.test_gateway_core tests.test_tool_guard tests.test_tool_preflight tests.test_executor tests.test_runner
```

发布前建议运行：

```bash
cd /Users/aidi/大字典/网关
python3 -m unittest discover tests
```

## 近期修正记录

- 移除 `花` 条目中的错误 `華` 异体归属，避免 `華` 同时指向 `花` 和 `华`。
- 响应侧 tool-call 守卫接入根字 kernel allowlist。
- `确认一下`、`需求不明确` 类请求优先路由到 `问`。
- Docker 可选沙箱在基础设施失败时降级到本地执行；强制 Docker 模式仍保持失败。

## 发展方向

### Phase 1: 500 字基础层稳定化

- 固化索引生成脚本，避免手工同步 lookup、CSV 和 review Markdown。
- 给 `xinhua-base-entry.schema.json` 增加整库级约束测试：唯一 ID、唯一 modern、唯一 Unicode、异体键唯一归属。
- 把 `agent-dictionary-lookup.json` 标为历史兼容文件或迁入 archive，降低误用风险。
- 清理或标注旧批次快照中的历史字段差异，避免把快照内容误读为当前主数据。

### Phase 2: 3500 常用字扩库

- 每批 100-200 字扩展 `xinhua_base`。
- 历史层默认 `pending`，只对高频、争议少、材料充分的字补草稿。
- 建立批次验收：条数、字段完整性、索引唯一性、复核标签数量变化。

### Phase 3: 历史层与复核工作台

- 优先复核简化合并、多音多义、异体多来源字。
- 将 `review_groups` 输出为可排序的复核任务表。
- 对每个 verified 字条保留材料来源、复核人/agent、复核日期和证据摘要。

### Phase 4: Agent 执行词典产品化

- 将 `tool_policy`、`kernel_policy`、响应侧守卫统一成单一判定函数，减少双路径漂移。
- 增加真实客户端协议测试，覆盖 OpenAI Chat、Responses、Anthropic Messages 三类响应 tool call。
- 把沙箱策略拆成 local、docker、required-docker 三个显式模式，并在审计日志中记录降级原因。

### Phase 5: 检索与应用层

- 先做本地文件检索，不急于引入向量库。
- 当 3500 字基础层稳定后，再评估 RAG/向量检索；检索结果必须保留 `id`、字、字段来源和复核状态。
- 对外回答默认引用现代基础层；涉及字源、古义、音韵时必须显式读取历史层并提示复核状态。
