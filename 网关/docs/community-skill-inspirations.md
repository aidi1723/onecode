# 一字诀与社区优秀 Skill 思想映射

一字诀不是提示词合集，也不是把某个外部仓库原样复制进项目。它做的是另一件事：

```text
用一个执行字，调用并固化一类优秀 Agent Skill / 工程提示词 / 工作流规范的精髓。
```

社区里已经出现了很多优秀的 Agent 工程实践，例如工程闭环、TDD、Karpathy 式防卫性编程、DESIGN.md、权限防护、多 Agent 隔离等。一字诀把这些经验进一步压缩成可路由、可校验、可组合的执行字。

换句话说：

```text
优秀社区 Skill 的思想 → 能力模式 → 执行字 → 词典规则 → 网关注入 → Agent 执行
```

## 设计原则

### 不绑定单一外部仓库

一字诀不把某个执行字写死为“调用某个 GitHub 项目”。外部项目会更新、停更、改协议，也可能不适合某个本地环境。

因此我们绑定的是能力模式：

```text
修 = 系统调试 + TDD + 最小修改 + 验证证据
卫 = 权限防护 + 危险动作阻断 + 安全审计
设 = DESIGN.md 风格约束 + UI 一致性 + 可访问性检查
```

具体外部项目可以作为参考来源，而不是系统唯一依赖。

### 一个字只管一类能力

执行字必须边界清晰：

- `查` 只读调查。
- `审` 只读审查。
- `源` 做来源和依赖审计。
- `卫` 做安全防护和危险动作阻断。
- `修` 可以修改，但必须受限、验证和熔断。

这避免了一个字承载太多含义，导致 Agent 又回到模糊执行。

### 多字组合走指令堆栈

多个执行字不能混成一个大 Prompt。比如：

```text
修 + 测
```

表示先执行 `修`，完成后触发上下文预算断路器，再执行 `测`。每个字重新加载自己的权限、Skill 和验证要求。

## 执行字与社区思想映射

| 执行字 | 一字诀能力 | 吸收的社区 Skill / 提示词精髓 |
| --- | --- | --- |
| `查` | 只读调查 | Reader-only、上下文收集、最小权限探索 |
| `解` | 解释代码和概念 | 结构化解释、文档化输出、事实与推断分离 |
| `修` | 修复 bug | 系统调试、TDD、最小复现、验证优先 |
| `造` | 新增功能 | Spec-first、计划拆解、测试驱动、实现闭环 |
| `改` | 修改和重构 | 外科手术式改动、保持接口、避免无关重写 |
| `测` | 测试验证 | Red-Green-Refactor、回归测试、证据优先 |
| `审` | 代码审查 | Review-only、风险优先、文件行号证据 |
| `设` | UI 设计系统 | DESIGN.md、品牌规范、响应式和可访问性 |
| `源` | 来源与依赖审计 | 依赖来源检查、License 风险、本地复用优先 |
| `卫` | 安全防护 | 权限白名单、危险命令阻断、依赖安装审批 |
| `隔` | 多 Agent 隔离 | Reader / Orchestrator / Writer 分权隔离 |
| `简` | 极简实现 | Simplicity first、防卫性 vibe coding、少封装 |
| `部` | 部署发布 | Release checklist、CI/CD 验证、人工确认高风险动作 |
| `数` | 数据处理 | 可复现数据清洗、schema 保留、数据质量报告 |
| `文` | 文档维护 | README、API docs、事实与规划分离 |
| `合` | 合规审查 | License review、政策风险、人工确认清单 |
| `搜` | 外部检索 | Source attribution、权威来源优先、日期和引用记录 |
| `问` | 澄清与人工确认 | Human-in-the-loop、PermissionRequest、需求边界确认 |
| `停` | 熔断与暂停 | Guardrail tripwire、interrupt/resume、权限收回 |
| `记` | 项目记忆 | CLAUDE.md / AGENTS.md、ADR、长期上下文治理 |
| `评` | 二次评估 | Guardrail evaluation、反方审查、质量门 |
| `总` | 上下文压缩 | Context compaction、handoff summary、证据保留 |

## V0.2 的关键升级：从“参考模式”到“专业协议”

V0.2 不再只要求执行字绑定 `reference_workflow_patterns`，还要求每个字都有 `professional_protocol`：

```text
source_projects = 它参考了哪些优秀项目、官方文档或成熟工程实践
operating_logic = 进入这个字后必须如何执行
hard_gates = 哪些情况必须阻断、追问、降级或熔断
```

例如 `修` 不是“帮我修一下”的提示词，而是：

```text
来源：superpowers systematic-debugging / TDD / SWE-agent 复现工作流
逻辑：捕获真实失败 -> 最小复现 -> 定位根因 -> 最小修改 -> 运行验证 -> 证据摘要
硬门：没有复现不得宣称修复；失败超过上限熔断到 查；禁止安装未批准依赖
```

这就是一字诀真正有价值的地方：一个字背后是可执行的专业流程，而不是一个漂亮代号。

## 典型来源思想

### 工程闭环类 Skill

这类工作流强调：

- 先澄清目标。
- 写 Spec 或计划。
- 拆任务。
- 写测试。
- 做最小实现。
- 跑验证。
- 再汇报结果。

一字诀吸收后形成：

```text
造 = Spec + Plan + TDD + Implementation + Verification
修 = Debugging + MRE + Surgical Fix + Verification
测 = Test + Evidence
```

### Karpathy 式防卫性编程

这类规则强调：

- 修改前先思考。
- 简单优先。
- 不做无关大改。
- 少封装。
- 目标驱动。
- 测试兜底。

一字诀吸收后形成：

```text
简 = 极简策略
改 = 有边界的重构
修 = 不顺手重写的 bug fix
```

### DESIGN.md 与 UI 设计系统

这类工作流强调：

- 用 Markdown 描述品牌视觉规则。
- 统一颜色、字体、间距和组件状态。
- 避免 AI 生成随意、不一致的 UI。

一字诀吸收后形成：

```text
设 = 加载设计系统，按视觉规范实现或修正 UI
审 + 设 = 只读检查 UI 一致性，不直接改
```

### 安全防护与零信任规则

这类工作流强调：

- 高风险命令需要拦截。
- 依赖安装需要审批。
- 外部输入不能直接进入写入上下文。
- Agent 不应拥有默认无限权限。

一字诀吸收后形成：

```text
卫 = 安全守卫
源 = 依赖和来源审计
隔 = 不可信输入隔离
源 + 卫 = 先审依赖来源，再决定是否允许执行
```

### 多 Agent 隔离架构

这类工作流强调：

- Reader 只读外部内容。
- Orchestrator 只调度。
- Writer 只接收干净上下文并写入。

一字诀吸收后形成：

```text
隔 = Reader / Orchestrator / Writer 分权协作
卫 + 隔 = 高风险内容进入隔离执行模式
```

### 部署、数据、文档、合规与检索

这类工作流把 Agent 从“写代码”扩展到完整工程协作：

- 部署发布需要 release checklist、CI/CD 验证和人工确认。
- 数据处理需要可复现转换、字段保留和数据质量说明。
- 文档生成需要基于真实代码，不编造未验证行为。
- 合规审查需要 License、政策和风险清单。
- 外部检索需要来源、日期和权威性标注。

一字诀吸收后形成：

```text
部 = 部署 / 发布 / CI 检查
数 = 数据清洗 / 表格处理 / 结构化转换
文 = README / API 文档 / 项目说明
合 = 合规 / License / 政策风险
搜 = 外部资料检索 / 来源记录
```

### 人工确认、熔断、记忆、评估与上下文压缩

这类工作流把 Agent 从“自动执行”升级成“可暂停、可审计、可交接”的系统：

- `问` 负责低置信度澄清和人工确认。
- `停` 负责安全熔断、撤销写权限和等待恢复。
- `记` 负责把稳定项目知识写入记忆或 ADR。
- `评` 负责二次评估、反例查找和质量门。
- `总` 负责长上下文压缩、交接摘要和下一执行字推荐。

一字诀吸收后形成：

```text
问 = Human-in-the-loop / Permission Request
停 = Guardrail Tripwire / Interrupt
记 = Project Memory / ADR
评 = Second-pass Evaluation / Red-team Review
总 = Context Compaction / Handoff Summary
```

## 为什么一字诀更进一步

普通提示词通常是：

```text
把一段规则告诉模型，希望模型遵守。
```

一字诀是：

```text
把规则变成执行字，再由词典、网关、权限和验证机制强制加载。
```

差别在于：

- 提示词依赖模型自觉。
- 执行字依赖系统路由。
- 普通 Skill 常常是人工触发。
- 一字诀可以由自然语言自动归一化触发。
- 普通工作流容易混在长上下文里。
- 一字诀用指令堆栈逐字执行，避免权限污染。

## 当前项目里的落地位置

执行字词典：

```text
agent_skill_dictionary/programming-agent-skill-dictionary.json
```

请求重写与规则注入：

```text
agent_skill_dictionary/gateway_core.py
```

HTTP 网关：

```text
agent_skill_dictionary/gateway_server.py
```

权限和词典校验：

```text
agent_skill_dictionary/validator.py
```

## 表述边界

一字诀借鉴的是社区优秀 Skill 项目的工程思想和能力模式，不代表本项目已经内置、复制、分发或认证这些外部项目。

如果未来要正式接入某个外部 Skill、仓库或规则集，应先做：

- 许可证检查。
- 安全审查。
- 维护状态评估。
- 本地适配测试。
- 版本锁定与审计记录。
