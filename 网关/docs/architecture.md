# 一字诀架构说明

一字诀网关是放在用户 / Agent 和上游大模型 API 之间的中间层。它不替代模型，也不替代 Agent，而是在请求进入模型前做一次确定性规训。

## 目标

把自然语言的模糊输入变成系统可执行、可限制、可验证的执行计划。

```text
用户输入
  ↓
一字诀网关
  ↓
执行字归一化
  ↓
查词典
  ↓
注入规则与权限
  ↓
转发到上游模型
  ↓
返回给原 Agent
```

## 核心模块

### 1. 词典层

文件：

```text
agent_skill_dictionary/programming-agent-skill-dictionary.json
schemas/agent-skill-dictionary.schema.json
```

词典定义每个执行字的含义、意图样例、参考工作流、专业运行协议、绑定 Skill、允许动作、禁止动作、工具权限、验证要求和失败回退。

其中两个字段是 V0.2 的核心：

- `reference_workflow_patterns`：机器可读的参考模式，例如 `superpowers:test-driven-development`、`openai-agents:tool-guardrail`、`langgraph:human-in-the-loop`。
- `professional_protocol`：该字背后的专业运行逻辑，包含参考来源、执行步骤和硬门规则。

V0.3 又补上根字继承字段：

- `root_opcode`：该字继承的 8 个根字之一。
- `opcode_vector`：权限、上下文和证据三维控制向量。
- `six_phase_workflow`：该字的六步确定性工作流。
- `transition_policy`：成功、失败、风险时的状态转移。

### 2. 根字 Workflow 层

文件：

```text
agent_skill_dictionary/workflow_registry.json
agent_skill_dictionary/workflow_loader.py
agent_skill_dictionary/workflows/*.md
```

8 个根字 `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总` 各自有独立 workflow markdown。每个 workflow 都必须写明：

```text
Prompt Engineering Sources
Efficiency Controls
Precision Controls
Stability Controls
Evidence
```

这层的意义是把“一个字背后的专业提示词工程和规范”从词典字段中拆出来，变成可加载、可测试、可审计的根字工作流。

### 3. Kernel Runtime Policy 层

文件：

```text
agent_skill_dictionary/kernel_policy.py
```

这层把 8 个根字变成运行时内核策略。每个根字有三项控制铁律：

- 工具权限锁：根字只下放允许工具，网关在请求转发前过滤 `tools`。
- 内核行为规训：根字注入硬 System Prompt，并覆盖 `temperature`。
- 原子证据链：根字声明必须返回的证据字段，供后续审计和交付门使用。

当前 8 个根字策略：

| 根字 | 卦象 | 运行时含义 | 关键动作 |
| --- | --- | --- | --- |
| `查` | 离 | 只读探索内核 | 只允许读文件、列目录、代码检索、diff |
| `修` | 震 | 外科手术动作内核 | 只允许读、检索、受限编辑和撤销 |
| `测` | 巽 | 验证内核 | 只允许运行测试、构建和 mock 数据 |
| `卫` | 坎 | 风险合规隔离内核 | 只允许安全扫描和只读审计 |
| `停` | 艮 | 状态冻结熔断内核 | 收回所有工具，HTTP 503 阻断上游模型转发 |
| `问` | 兑 | 人机协同内核 | 只允许发用户消息和渲染选择 |
| `记` | 坤 | 知识持久化存储内核 | 只允许写知识库或 Markdown 文档 |
| `总` | 乾 | 上下文收束内核 | 只允许读取和状态摘要 |

说明：`造` 仍然是 `修` 的派生字，不作为当前 8 根字之一。这样保留 “八字为骨、六十四为展” 的架构克制。

### 4. Root Skill Mount 层

文件：

```text
agent_skill_dictionary/skill_mount_registry.json
agent_skill_dictionary/skill_mount_loader.py
docs/root-skill-mount-registry.md
tests/test_skill_mount_registry.py
```

这层把社区成熟工程规范挂载到 8 个根字上。它不是自动安装外部项目，而是把外部优秀实践抽象成本地可加载规则：

| 根字 | Mount | 参考规范 |
| --- | --- | --- |
| `查` | `inspect_repo_map_mount` | Aider Repo Map、SWE-agent ACI |
| `修` | `surgical_fix_mount` | SWE-agent ACI、systematic debugging、TDD |
| `测` | `tdd_ci_quality_gate_mount` | pytest-cov、verification-before-completion |
| `卫` | `security_guard_mount` | Semgrep、OSV-Scanner、PreToolUse Guard |
| `停` | `circuit_breaker_mount` | Circuit Breaker、LangGraph interrupt |
| `问` | `human_in_the_loop_mount` | LangGraph interrupts、PermissionRequest |
| `记` | `memory_bank_mount` | Claude Code memory、ADR |
| `总` | `handoff_compaction_mount` | context compaction、handoff summary |

网关会把当前执行字对应的 Skill Mount 摘要注入 system rule。`造` 作为 `修` 的派生字，挂载 `spec_driven_build_mount`，但仍继承 `修` 的受限写入边界。

### 5. 闭环 Macro Chain 层

文件：

```text
agent_skill_dictionary/macro_chain.py
```

Macro Chain 层把复杂任务编译成确定性根字链。它不让模型自由规划，而是根据规则模板输出闭环控制序列。

当前内置两个典型闭环：

```text
功能开发闭环: 查 -> 造 -> 测 -> 修 -> 记 -> 总
安全熔断闭环: 卫 -> 停 -> 问 -> 查 -> 总
```

其中 `造` 是 `修` 的派生字，进入运行时仍继承 `修` 的 Kernel Runtime Policy。Macro Chain 的作用是给前端、调度器或后续 AgentOS 执行器一个稳定的任务骨架；当前 `/v1/yizijue/resolve` 会返回该链路，但 `/v1/chat/completions` 仍按当前 active execution code 执行单步请求重写。

### 6. OneWord-Agent FSM 框架层

文件：

```text
agent_skill_dictionary/one_word_agent.py
docs/oneword-agent-framework.md
tests/test_one_word_agent.py
```

这层把 8 个根字升级成可测试的有限状态机框架。它不替代网关，而是给后续 AgentOS 多步执行器提供一个稳定运行模型：

```text
Compiler
  把用户自然语言编译成初始根字状态。

OneWordAgent
  每一步加载当前根字的 Kernel Runtime Policy，记录 trace 和 audit_log。

MutationEngine
  根据执行证据决定下一状态：测失败转修，重试超限转停，需要人类时转问，完成后转总。
```

状态映射：

| 卦象 | 根字 | 框架状态 |
| --- | --- | --- |
| 离 | `查` | 只读调查 |
| 震 | `修` | 外科修复 |
| 巽 | `测` | 验证测试 |
| 坎 | `卫` | 安全防护 |
| 艮 | `停` | 熔断挂起 |
| 兑 | `问` | 澄清授权 |
| 坤 | `记` | 记忆归档 |
| 乾 | `总` | 收束交接 |

当前 OneWord-Agent 还是框架原型：默认 `execute_llm_core()` 是测试桩，真实 LLM、真实工具和沙盒证据需要后续 executor adapter 接入。它的价值是先固定“Agent 必须沿 8 字状态轨迹运行”的框架边界。

### 7. 归一化层

文件：

```text
agent_skill_dictionary/gateway_core.py
```

当前实现是关键词规则归一化。用户直接输入 `修：...`、`源：...` 这类显式前缀时，显式执行字优先。

示例：

```text
这个 bug 修一下，然后跑测试确认。
```

归一化结果：

```text
修 + 测
```

### 8. 指令堆栈层

文件：

```text
agent_skill_dictionary/execution-stack-policy.md
```

多字任务不会混成一个大 Prompt，而是按执行顺序压栈。

```text
修 + 测
```

堆栈：

```text
["测", "修"]
```

栈顶 `修` 先执行。后续阶段应在每个执行字切换时重新加载权限和最小上下文。

### 9. 请求重写层

文件：

```text
agent_skill_dictionary/gateway_core.py
```

`rewrite_chat_completion_request()` 会：

- 读取最新 user message。
- 归一化执行字。
- 构建指令堆栈。
- 选择当前 active execution code。
- 注入 system message。
- 注入参考工作流模式和专业运行逻辑。
- 按 `root_opcode` 加载根字 workflow markdown 摘要并注入 system message。
- 按执行字加载 Root Skill Mount 摘要并注入 system message。
- 按根字加载 Kernel Runtime Policy，注入内核运行规训。
- 用内核策略覆盖 `temperature`，并过滤不属于当前根字的 `tools`。
- 返回 metadata，便于审计和调试。

### 10. Tool-Call 守卫层

文件：

```text
agent_skill_dictionary/tool_guard.py
```

当前守卫会检查上游响应中的 `tool_calls`，并根据 active execution code 的 `tool_policy` 标注是否违规。

已覆盖的违规类型：

- 只读执行字调用 `write_file`、`edit_file`、`apply_patch` 等写入工具。
- 禁止安装依赖的执行字调用 `install_dependency`、`pip_install`、`npm_install` 等工具。
- 任意执行字调用包含明显高风险片段的 shell 命令，例如 `rm -rf`、`sudo`、`git reset --hard`。

当前守卫是在响应 metadata 中标注违规：

```json
{
  "yizijue_gateway": {
    "tool_guard": {
      "allowed": false,
      "violations": [
        { "tool": "write_file", "reason": "write_forbidden" }
      ]
    },
    "blocked": true
  }
}
```

这已经能让上层 Agent 或调试 UI 识别违规工具调用。

执行前硬门接口：

```text
POST /v1/yizijue/preflight-tool
```

请求：

```json
{
  "active_code": "查",
  "tool_name": "write_file",
  "arguments": { "path": "app.py" }
}
```

响应：

```json
{
  "allowed": false,
  "active_code": "查",
  "tool": "write_file",
  "violations": [
    { "tool": "write_file", "reason": "write_forbidden" }
  ]
}
```

当具体 Agent 工具执行层在执行前调用这个接口，并在 `allowed: false` 时拒绝执行，就能完成物理阻断。

### 11. HTTP 网关层

文件：

```text
agent_skill_dictionary/gateway_server.py
```

当前支持：

```text
GET  /health
POST /v1/yizijue/resolve
POST /v1/yizijue/preflight-tool
POST /v1/chat/completions
```

`/v1/yizijue/resolve` 只做解析，不调用上游模型。它用于调试一句话会被归一化成哪些执行字、指令堆栈是什么、当前 active code 是什么、会加载哪些权限，以及复杂任务会被编译成哪条 Macro Chain。

`/v1/yizijue/preflight-tool` 在工具真正执行前检查权限。Agent 工具层可以把 `active_code`、`tool_name` 和 `arguments` 发给网关，网关返回 `allowed` 和违规原因。

`/v1/chat/completions` 接收 OpenAI-compatible 请求，调用核心重写逻辑，再转发到 `ONEWORD_UPSTREAM_BASE_URL`。

### 12. 现有 Agent 适配层

文件：

```text
docs/existing-agent-gateway-integration.md
```

一字诀的首选落地路线不是立刻重写一个完整 Agent，而是先接入现有高级 CLI Agent：

```text
现有 Agent
  ↓
一字诀 Gateway
  ↓
上游模型
```

当前已支持 OpenAI-compatible Agent：只要能把 base URL 指到 `http://localhost:8080/v1`，就可以使用当前 `/v1/chat/completions` 网关。

Claude Code 等 Anthropic-compatible Agent 是下一步重点，但需要新增 adapter：

```text
POST /v1/messages
GET  /v1/models
streaming passthrough
Anthropic tool schema 转换
Anthropic error shape
```

这层的原则是复用当前 `gateway_core.py`、`kernel_policy.py`、`tool_guard.py` 和 `audit.py`，不再复制一套规则。

## 请求生命周期

1. Agent 把请求发到 `http://localhost:8080/v1/chat/completions`。
2. 网关读取 request body。
3. 网关从最后一条 user message 中识别执行字。
4. 网关按执行字查本地 JSON 词典。
5. 网关解析根字，加载根字 workflow 摘要和 Kernel Runtime Policy。
6. 网关注入 system rule，包括执行字、根字 workflow、Root Skill Mount 和 Kernel Runtime Policy。
7. 网关锁定 temperature，并过滤 `tools`。
8. 如果根字是 `停`，网关返回 HTTP 503，不转发上游模型。
9. 否则网关把重写后的请求转发给上游模型。
10. 网关检查响应里的 tool calls。
11. 网关把上游响应返回给 Agent，并附带 `yizijue_gateway` metadata。

## 调试解析生命周期

1. 开发者把自然语言发到 `/v1/yizijue/resolve`。
2. 网关调用 `resolve_execution_plan()`。
3. 网关返回 `codes`、`execution_stack`、`active_code`、`routing_target`、`tool_policy` 和 `verification`。
4. 这个接口不读取 API key，不调用上游模型，适合用于调试、前端展示和接入测试。

## 当前 MVP 边界

当前版本已经有确定性请求重写，但还没有实现以下能力：

- streaming SSE passthrough。
- Anthropic-compatible `/v1/messages` adapter。
- 未接入具体 Agent 工具执行层时，tool-call 物理阻断不会自动发生。
- OneWord-Agent 还没有真实 executor adapter 和 `/v1/yizijue/run` 多步执行 endpoint。
- 审计日志落盘。
- SHA-256 证据文件落盘。
- 词典热加载。
- API key 多租户管理。

这些能力不影响当前 MVP 验证“自然语言到执行字到请求规训”的主链路。
