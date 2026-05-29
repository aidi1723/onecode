# 社区优秀 Skill 与 Agent Workflow 调研 2026

本文档记录一字诀当前参考的社区优秀 Skill、Agent workflow、设计系统、安全守卫和多 Agent 编排项目。它的作用不是复制外部仓库，而是把成熟工作流抽象成一字诀的 `reference_workflow_patterns`。

核心原则：

```text
外部优秀项目 / 文档 / 论文
  ↓
抽象为能力模式
  ↓
写入 reference_workflow_patterns
  ↓
绑定到执行字
  ↓
由网关注入和工具守卫执行
```

## 1. Skill 标准与生态

### Claude Agent Skills

来源：

- [Claude Docs: Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)
- [Claude Code SDK Skills](https://code.claude.com/docs/en/agent-sdk/skills)

可吸收的精髓：

- Skill 是文件系统里的 `SKILL.md` 能力包。
- 元数据用于触发，完整内容按需加载。
- 适合把专业流程变成可复用能力。

对应一字诀模式：

```text
skill:filesystem-skill
skill:on-demand-loading
skill:metadata-trigger
```

对应执行字：

```text
全部执行字
```

### OpenAI Skills

来源：

- [openai/skills](https://github.com/openai/skills)

可吸收的精髓：

- Skill 是可分发、可安装、可复用的能力目录。
- 一个能力可以包含说明、脚本和资源。
- 适合把一字诀的字典能力进一步封装成可安装 Skill。

对应一字诀模式：

```text
skill:portable-capability
skill:script-backed-skill
skill:codex-compatible
```

对应执行字：

```text
文 / 造 / 测 / 源 / 卫
```

### Vercel Agent Skills 与 Skills CLI

来源：

- [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
- [vercel-labs/skills](https://github.com/vercel-labs/skills)

可吸收的精髓：

- React、Next.js、Web Design、部署等能力可以被拆成细粒度 Skill。
- Skill 可以通过 CLI 搜索、安装、更新和移除。
- Skill 需要清楚说明触发场景、工作方式、脚本和输出格式。

对应一字诀模式：

```text
frontend:react-best-practices
design:web-design-guidelines
deploy:claimable-deploy
skill:package-manager
```

对应执行字：

```text
设 / 部 / 文 / 搜
```

### 社区 Skill 聚合与索引

来源：

- [Awesome Agent Skills](https://www.awesomeskills.dev/)
- [GetBindu/awesome-claude-code-and-skills](https://github.com/GetBindu/awesome-claude-code-and-skills)
- [subinium/awesome-claude-code](https://github.com/subinium/awesome-claude-code)
- [VoltAgent/awesome-agent-skills](https://repodepot.quetzals.ai/repo/VoltAgent/awesome-agent-skills)

可吸收的精髓：

- Skill 生态正在变成类似包管理器和市场的形态。
- 搜索、筛选、安装和验证 Skill 本身会成为 Agent 基础设施。
- 一字诀不应把外部 Skill 写死，而应保留“能力模式 + 可替换来源”的结构。

对应一字诀模式：

```text
skill:registry
skill:curated-index
skill:installable-capability
```

对应执行字：

```text
搜 / 源 / 合
```

## 2. 工程闭环与开发流程

### obra/superpowers

来源：

- [obra/superpowers](https://github.com/obra/superpowers)

可吸收的精髓：

- 从构思、需求澄清、写 Spec、写计划，到 TDD、子代理执行、Review、验证收尾，形成硬性闭环。
- 不让 Agent 直接跳到代码，先建立设计、计划和验证。
- 强调验证前不宣称完成。

对应一字诀模式：

```text
superpowers:brainstorming
superpowers:writing-plans
superpowers:systematic-debugging
superpowers:test-driven-development
superpowers:verification-before-completion
```

对应执行字：

```text
造 / 修 / 测 / 审 / 文
```

### Claude Code Hooks

来源：

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)

可吸收的精髓：

- `PreToolUse` 可以在工具调用前阻断。
- `PostToolUse` 可以做格式化、验证和审计。
- `PermissionRequest` 可以把高风险动作交给人类或其他系统裁决。

对应一字诀模式：

```text
hooks:pre-tool-use
hooks:post-tool-use
hooks:permission-request
```

对应执行字：

```text
卫 / 源 / 合 / 部 / 停
```

当前落地：

```text
POST /v1/yizijue/preflight-tool
```

这个接口就是一字诀版的执行前硬门。

### Claude Code Advanced Patterns

来源：

- [Claude Code Advanced Patterns: Subagents, MCP, and Scaling to Real Codebases](https://resources.anthropic.com/hubfs/Claude%20Code%20Advanced%20Patterns_%20Subagents%2C%20MCP%2C%20and%20Scaling%20to%20Real%20Codebases.pdf)

可吸收的精髓：

- 子代理适合拆分复杂任务。
- MCP 适合把外部工具和数据接入 Agent。
- GitHub Actions 和远程工作流适合进入 CI/CD。

对应一字诀模式：

```text
multi-agent:subagent-delegation
mcp:tool-integration
devops:github-actions-agent
```

对应执行字：

```text
隔 / 部 / 搜 / 数
```

## 3. 设计系统与 UI

### DESIGN.md / awesome-design-md

来源：

- [VoltAgent/awesome-design-md](https://github.com/voltagent/awesome-design-md)
- [DESIGN.md 官方库](https://designmd.app/)
- [Better Stack: DESIGN.md guide](https://betterstack.com/community/guides/ai/design-md-ai/)

可吸收的精髓：

- 用 Markdown 把颜色、字体、组件、布局、动效和品牌气质写成 AI 可读设计系统。
- 把 UI 生成从“凭感觉”变成“按设计规范执行”。
- 设计规则应放进项目根或可检索上下文里，避免每次重新解释。

对应一字诀模式：

```text
design-md-ui
design:design-system-consistency
design:responsive-accessibility-check
design:brand-token-grounding
```

对应执行字：

```text
设 / 审 / 文
```

### Vercel Web Design Guidelines

来源：

- [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)

可吸收的精髓：

- UI 审查可以拆成 accessibility、focus states、forms、animation、typography、images、performance、navigation、theming、touch、i18n 等规则。
- 一字诀里 `设` 不只是“变好看”，而是加载成体系的 UI 审查与实现规则。

对应一字诀模式：

```text
design:web-design-guidelines
frontend:accessibility-check
frontend:performance-review
```

对应执行字：

```text
设 / 审 / 测
```

## 4. 安全、防护与权限

### Claude Permission Modes

来源：

- [Claude Code Permission Modes](https://code.claude.com/docs/en/permission-modes)

可吸收的精髓：

- 不同任务需要不同权限模式。
- 高风险模式只能在隔离环境中使用。
- 权限不应该完全交给模型自由判断。

对应一字诀模式：

```text
security:permission-mode
security:least-privilege
security:human-approval-gate
```

对应执行字：

```text
卫 / 隔 / 部 / 合
```

### Agent Runtime Guardrails

来源：

- [AgentSteer](https://agentsteer.ai/)
- [GYRD](https://gyrd.ai/)
- [Destructive Command Guard](https://github.com/Dicklesworthstone/destructive_command_guard)
- [Railguard](https://www.railguard.tech/)
- [OpenClaw Guardrails](https://aport.io/openclaw)

可吸收的精髓：

- 工具调用必须在执行前检查。
- 高危命令、路径越界、凭证读取、依赖安装、删除文件等行为应该可阻断。
- 最好保留本地审计记录。

对应一字诀模式：

```text
security:permission-whitelist
security:dangerous-action-blocking
security:dependency-approval
security:path-fencing
security:audit-log
```

对应执行字：

```text
卫 / 源 / 合 / 停
```

当前落地：

```text
agent_skill_dictionary/tool_guard.py
POST /v1/yizijue/preflight-tool
```

### LlamaFirewall 与 Symbolic Guardrails

来源：

- [LlamaFirewall paper](https://arxiv.org/abs/2505.03574)
- [Symbolic Guardrails for Domain-Specific Agents](https://arxiv.org/abs/2604.15579)

可吸收的精髓：

- Agent 安全不应只靠提示词。
- 需要模型外的规则、静态分析、符号约束和最后防线。
- 对领域 Agent 来说，符号化规则可以提升安全和一致性。

对应一字诀模式：

```text
security:symbolic-guardrails
security:final-layer-defense
security:code-shield
```

对应执行字：

```text
卫 / 合 / 源 / 隔
```

## 5. 多 Agent 与上下文管理

### Claude Code Design Space

来源：

- [Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems](https://arxiv.org/abs/2604.14228)

可吸收的精髓：

- Agent 系统真正复杂的部分在模型外：权限、上下文压缩、hooks、skills、MCP、子代理、工作树隔离和会话存储。
- 一字诀应该重点做模型外确定性控制，而不只是提示词。

对应一字诀模式：

```text
agent-system:permission-layer
agent-system:context-compaction
agent-system:hooks-skills-mcp
multi-agent:worktree-isolation
```

对应执行字：

```text
隔 / 查 / 总 / 卫
```

### 社区多 Agent 工作流

来源：

- [awesome-claude-code-workflows](https://github.com/ithiria894/awesome-claude-code-workflows)
- [VoltAgent awesome Claude Code subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)

可吸收的精髓：

- 复杂任务适合拆给专业代理。
- 安全、性能、架构、代码审查可以由不同代理并行处理。
- 编排层不应直接持有所有上下文和权限。

对应一字诀模式：

```text
multi-agent:reader-orchestrator-writer
multi-agent:parallel-review
multi-agent:specialist-subagents
```

对应执行字：

```text
隔 / 审 / 卫 / 部
```


## 6. 官方 Agent 框架与工具协议

### OpenAI Agents SDK

来源：

- [OpenAI Agents SDK: Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI Agents SDK: Tools](https://openai.github.io/openai-agents-python/tools/)
- [OpenAI Agents SDK: Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK: Tracing](https://openai.github.io/openai-agents-python/tracing/)

可吸收的精髓：

- Guardrail 不是“提醒模型注意安全”，而是输入、输出、工具调用前后的程序化检查。
- Handoff 把任务交给更合适的 Agent，适合一字诀的路由目标。
- Tracing 提供执行轨迹，是证据链和审计日志的基础。

对应一字诀模式：

```text
openai-agents:input-guardrail
openai-agents:output-guardrail
openai-agents:tool-guardrail
openai-agents:handoff
openai-agents:tracing
```

对应执行字：

```text
卫 / 评 / 隔 / 停 / 总
```

### LangGraph / LangChain Agent 工作流

来源：

- [LangGraph Interrupts / Human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Multi-agent Concepts](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)

可吸收的精髓：

- 长流程 Agent 需要可暂停、可恢复、可人工审批的状态机。
- 人类审批不应该是聊天层面的“顺便问一句”，而应成为图里的明确节点。
- 多 Agent 协作应通过状态图和消息边界传递，而不是把所有上下文混在一个 Prompt。

对应一字诀模式：

```text
langgraph:human-in-the-loop
langgraph:interrupt
langgraph:resume
langgraph:state-graph
langgraph:multi-agent-routing
```

对应执行字：

```text
问 / 停 / 隔 / 总 / 评
```

### MCP: Model Context Protocol

来源：

- [MCP Tools Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP Resources Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
- [MCP Prompts Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

可吸收的精髓：

- Tools、Resources、Prompts 是三类不同能力，不应混用。
- 工具输入输出要验证、限权、超时和记录。
- 客户端应在敏感操作前展示工具输入并请求确认。

对应一字诀模式：

```text
mcp:tools
mcp:resources
mcp:prompts
mcp:tool-input-validation
mcp:auditability
```

对应执行字：

```text
卫 / 源 / 隔 / 搜 / 数
```

### SWE-agent / Agent Computer Interface

来源：

- [SWE-agent](https://github.com/SWE-agent/SWE-agent)
- [Agent Computer Interface concept](https://swe-agent.com/latest/)

可吸收的精髓：

- 编码 Agent 的质量很大程度取决于它看到和操作系统的接口，而不只是模型本身。
- 修复问题要围绕 issue、复现、编辑、测试和提交这条窄路径。
- 工具接口越清晰，Agent 越少走偏。

对应一字诀模式：

```text
swe-agent:issue-reproduction
swe-agent:agent-computer-interface
swe-agent:test-before-claim
```

对应执行字：

```text
查 / 修 / 测 / 审
```

## 7. 社区 Skill 仓库扫描结果

本轮通过 GitHub 搜索和公开文档扫描，得到几个值得持续跟踪的方向：

- `TerminalSkills/skills`：跨 Claude Code、Codex、Gemini CLI、Cursor 的开放 Skill 库，说明 `SKILL.md` 正在成为跨 Agent 能力包格式。
- `trailofbits/skills`：安全研究、漏洞检测和审计类 Claude Code Skills，适合作为 `卫 / 源 / 审 / 合` 的安全能力参考。
- `vercel-labs/agent-skills` 与 `vercel-labs/skills`：把前端、部署和设计工作流 Skill 化，适合作为 `设 / 部 / 文` 的参考。
- `obra/superpowers` 及其衍生仓库：把 brainstorming、spec、plan、TDD、review、verification 串成闭环，适合作为 `造 / 修 / 测 / 审 / 总` 的核心参考。
- `awesome-claude-code`、`awesome-agent-skills`、`awesome-claude-code-and-skills`：适合作为未来 `搜` 字的 Skill 发现索引来源。
- `skill-lint`、`skillmark`、`agent-skills-authoring` 一类项目：说明 Skill 本身也需要 lint、评分、验证和发布质量门，适合未来扩展 `评 / 源 / 合`。

这些仓库的价值不是被复制进一字诀，而是沉淀成下面三层：

```text
项目/文档来源 -> reference_workflow_patterns -> professional_protocol -> 网关注入和工具守卫
```

## 8. 新增控制字映射

| 执行字 | 专业含义 | 主要参考工作流 | 解决的问题 |
| --- | --- | --- | --- |
| `问` | 澄清与人工确认 | superpowers brainstorming、LangGraph human-in-the-loop、permission request | 低置信度时不瞎猜 |
| `停` | 熔断与暂停 | OpenAI guardrail tripwire、Claude PermissionRequest、LangGraph interrupt | 失败过多或高风险时收权 |
| `记` | 项目记忆与 ADR | Claude Code memory、AGENTS.md、ADR | 稳定复用项目规则 |
| `评` | 二次评估与反方审查 | Guardrail evaluation、code review、red-team review | 防止一次输出自证正确 |
| `总` | 上下文压缩与交接 | Context management、handoff summary、verification discipline | 长任务不漂移、不丢证据 |

## 9. 研究结论

一字诀的核心不是“发明一套孤立提示词”，而是把社区已经验证过的优秀 Agent 工作流压缩成可执行控制码。

当前最成熟、最值得吸收的工作流方向是：

- Skill 标准化：来自 Claude Skills、OpenAI Skills、Vercel Skills。
- 工程闭环：来自 superpowers、TDD、verification-first 工作流。
- UI 设计规训：来自 DESIGN.md 与 Vercel web design guidelines。
- 安全守卫：来自 hooks、permission modes、runtime guardrails、symbolic guardrails。
- 多 Agent 编排：来自 Claude Code subagents、MCP、Reader / Orchestrator / Writer 模式。
- 上下文治理：来自 Claude Code 设计空间中的 compaction、permission、session 和 worktree 隔离思想。

这些方向已经被映射到当前词典字段：

```text
reference_workflow_patterns
professional_protocol
bound_skill_patterns
tool_policy
runtime_environment
verification
fallback
```

## 10. 下一步建议

新增控制字 `问 / 停 / 记 / 评 / 总` 已进入词典；V0.3 又补上八大 Opcode 继承字段，并已为 `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总` 落地 workflow markdown、workflow loader 和网关注入。下一步应继续补执行器、审计日志落盘和更细的安全解析。

优先加强以下工程能力：

- 把更多派生字的 `reference_workflow_patterns` 映射到更细的可加载 workflow markdown。
- 为 `卫` 接入更细的 shell command parser。
- 为 `设` 支持项目级 `DESIGN.md` 检测。
- 为 `部` 增加发布前 checklist。
- 为 `合` 增加 License 文件和依赖清单扫描。

## 11. 重要边界

本文档列出的项目和论文是能力模式参考，不代表本项目已经复制、内置、认证或分发这些外部项目。

正式接入任何外部 Skill 或仓库前，必须做：

- License 检查。
- 安全审查。
- 维护状态评估。
- 本地适配测试。
- 版本锁定。
- 审计记录。
