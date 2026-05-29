# 一字诀项目状态

日期：2026-05-26
当前版本：可交付 MVP，V0.5 Production Hardening 准备阶段
当前阶段：8 个根字内核策略、真实执行器、审计证据链、端到端 CLI/API 运行入口已落地；Build Mode V2 本地网关闭环已通过

## 一句话结论

一字诀已经从“执行字词典 + 网关 MVP”升级为“可运行、可验证、可审计的 OneWord-Agent 交付版 MVP”。

当前项目可以证明：

- 用户自然语言可以被归一化成执行字。
- 执行字可以加载固定权限、验证、熔断、专业运行逻辑、根字 workflow 摘要和 Kernel Runtime Policy。
- 网关可以把这些规则注入 OpenAI-compatible chat request，并提供工具执行前检查接口。
- OneWord-Agent 可以把 8 个根字作为有限状态机运行，输出可审计的 trace、audit_log 和交付产物。
- CLI 和 `/v1/yizijue/run` 已可执行端到端本地任务。
- Build Mode V2 已经在真实本地 HTTP 网关 + mock upstream 环境中跑通三协议工具接管闭环；真实 Codex Desktop / Claude Code 客户端端到端验证仍在下一阶段。

## 阶段状态

| 阶段 | 名称 | 状态 | 当前结论 |
| --- | --- | --- | --- |
| Phase 1 | 静态执行字词典 | 已完成 | Schema、词典、loader、validator、基础测试已落地 |
| Phase 2 | 编程域最小闭环 | 已完成 | 22 个执行字、专业协议、网关注入、preflight 工具守卫、测试验证已落地 |
| Phase 3 | 八大 Opcode 与可加载 workflow | 已完成核心闭环 | 八大 Opcode、继承字段、validator、8 个根字 workflow markdown、workflow loader 和网关注入已落地 |
| Phase 4 | Kernel Runtime Policy、Skill Mount、强权限护栏与 FSM 框架 | 已完成核心闭环 | 已有根字工具过滤、温度覆盖、内核规训注入、Root Skill Mount 注入、`停` HTTP 503 熔断、preflight API、响应侧标注、OneWord-Agent 状态机和 Build Mode 证据门 |
| Phase 4.5 | 现有 Agent 网关接入 | 本地网关闭环已通过 | Chat Completions、OpenAI Responses、Anthropic Messages 三路协议已通过本地 HTTP 网关 + mock upstream；真实 Codex Desktop / Claude Code 客户端验证待做 |
| Phase 4.6 | V1.0 最小 MVP 网关 | 已完成骨架 | `oneword_dict.json`、minimal gateway core/server 和测试已落地 |
| Phase 5 | 审计日志、证据落盘与热加载 | 部分完成 | Build Mode 状态文件、manifest/SHA256、audit JSONL 已落地；词典热加载和生产级多节点审计仍待做 |

## V0.3 已完成内容

### 1. 执行字体系

当前词典包含 22 个执行字：

```text
查 / 解 / 修 / 造 / 改 / 测 / 审 / 设 / 源 / 卫 / 隔 / 简 / 部 / 数 / 文 / 合 / 搜 / 问 / 停 / 记 / 评 / 总
```

其中：

- `查 / 解 / 审 / 源 / 卫 / 隔 / 合 / 搜 / 问 / 停 / 评 / 总` 是只读或控制类执行字。
- `修 / 造 / 改 / 测 / 设 / 简 / 部 / 数 / 文 / 记` 允许受限写入或受限产物生成。
- `停` 是高优先级熔断字。
- `问` 是低置信度澄清字。
- `评` 是二次评估和反方审查字。
- `总` 是上下文压缩和交接摘要字。
- `记` 是项目记忆、ADR 和稳定规则记录字。

### 2. 专业运行协议

每个执行字都必须包含：

```text
reference_workflow_patterns
professional_protocol.source_projects
professional_protocol.operating_logic
professional_protocol.hard_gates
```

这意味着一个字背后不是普通提示词，而是具体的专业工作流。例如：

```text
修 = 系统调试 + 最小复现 + TDD + 外科手术式修改 + 验证证据
卫 = 权限白名单 + 危险动作阻断 + 依赖审批 + 工具调用前硬门
设 = DESIGN.md + 设计系统一致性 + 响应式/可访问性检查
隔 = Reader / Orchestrator / Writer 分权隔离
停 = Guardrail tripwire + interrupt/resume + 人工确认
```

### 3. 根字 Workflow 质量契约

8 个根字已经拆成独立 workflow 文件：

```text
agent_skill_dictionary/workflows/查.md
agent_skill_dictionary/workflows/修.md
agent_skill_dictionary/workflows/测.md
agent_skill_dictionary/workflows/卫.md
agent_skill_dictionary/workflows/停.md
agent_skill_dictionary/workflows/问.md
agent_skill_dictionary/workflows/记.md
agent_skill_dictionary/workflows/总.md
```

每个根字 workflow 都包含：

```text
Prompt Engineering Sources
Root Skill Mount
Efficiency Controls
Precision Controls
Stability Controls
Evidence
```

这保证每个根字背后都是一套专业提示词工程和执行规范，而不是一段临时 prompt。它们吸收的是社区优秀项目和成熟工作流的模式，例如 systematic debugging、TDD、verification-before-completion、PreToolUse guard、Human-in-the-loop、ADR、context compaction 和 handoff summary。

### 3.1 Root Skill Mount 注册表

已落地文件：

```text
agent_skill_dictionary/skill_mount_registry.json
agent_skill_dictionary/skill_mount_loader.py
tests/test_skill_mount_registry.py
docs/root-skill-mount-registry.md
```

当前 8 个根字已经挂载社区成熟规范：

```text
查 -> Aider Repo Map / SWE-agent ACI
修 -> SWE-agent ACI / systematic debugging / TDD
测 -> pytest-cov / verification-before-completion
卫 -> Semgrep / OSV-Scanner / PreToolUse Guard
停 -> Circuit Breaker / LangGraph interrupt
问 -> LangGraph HITL / PermissionRequest
记 -> Claude Code memory / ADR
总 -> context compaction / handoff summary
```

这些是本地规范挂载，不等于当前运行时已经安装并调用全部外部工具。后续要升级为真实工具调用，需要逐项做版本锁定、安全审查、CLI 输出解析和证据落盘。

### 4. 网关能力

当前网关支持：

- `GET /health`
- `POST /v1/yizijue/resolve`
- `POST /v1/yizijue/preflight-tool`
- `POST /v1/chat/completions`

已落地能力：

- OpenAI-compatible 请求重写。
- 执行字 system rule 注入。
- 根字 workflow markdown 摘要注入。
- Root Skill Mount 摘要注入。
- Kernel Runtime Policy 注入。
- 闭环 Macro Chain 解析。
- 请求转发前按根字过滤 `tools`。
- `停` 根字触发 HTTP 503 熔断，不转发上游模型。
- `temperature` 按词典强制锁定。
- 多字任务指令堆栈。
- 响应侧 tool-call 违规标注。
- 执行前工具检查接口。

### 5. OneWord-Agent FSM 框架原型

已落地文件：

```text
agent_skill_dictionary/one_word_agent.py
tests/test_one_word_agent.py
docs/oneword-agent-framework.md
```

当前能力：

- 8 个根字与卦象状态映射。
- `Compiler` 根据用户输入选择初始状态。
- `MutationEngine` 根据 `ok`、`risk`、`needs_human` 和重试次数转移状态。
- `OneWordAgent` 输出 `trace` 和 `audit_log`。
- 连续失败超过上限进入 `停`。

当前边界：

- 默认 `execute_llm_core()` 是测试桩。
- 尚未接入真实 LLM、真实工具、沙盒运行和证据落盘。
- 尚未提供 `/v1/yizijue/run` 多步执行 endpoint。

### 6. 现有 Agent 接入路线

已落地文档：

```text
docs/existing-agent-gateway-integration.md
```

当前判断：

- 先用网关规训现有 Agent，避免重做文件编辑、终端执行和 Git 管理。
- 当前代码已支持 OpenAI-compatible Agent 接入。
- Claude Code 是下一步重点，但直连需要 Anthropic-compatible `/v1/messages` adapter、streaming 和 tool schema 适配。
- 真正的物理阻断还需要现有 Agent 的工具执行层调用 `/v1/yizijue/preflight-tool`。

### 7. V1.0 最小 MVP 网关

已落地文件：

```text
agent_skill_dictionary/oneword_dict.json
agent_skill_dictionary/minimal_gateway_core.py
agent_skill_dictionary/minimal_gateway_server.py
tests/test_minimal_gateway_mvp.py
docs/oneword-agentos-v1-kernel-manual.md
```

当前能力：

- 8 根字最高宪法实体词典。
- 根据用户消息编译根字。
- 注入最小 system rule。
- 锁定 temperature。
- 按根字白名单裁剪 `tools`。
- `停` 阻断上游模型转发。

当前定位：

```text
minimal_gateway_server.py 用于 Phase 1 教学和 Hello World MVP。
gateway_server.py 仍是功能更完整的主网关。
```

## 当前边界

Build Mode V2 已经从设计文档推进到本地 MVP 闭环。当前已落地模块包括：

- `agent_skill_dictionary/build_mode_types.py`
- `agent_skill_dictionary/build_mode_intent.py`
- `agent_skill_dictionary/build_mode_permissions.py`
- `agent_skill_dictionary/build_mode_writer.py`
- `agent_skill_dictionary/build_mode_sandbox.py`
- `agent_skill_dictionary/build_mode_feedback.py`
- `agent_skill_dictionary/build_mode_archive.py`
- `agent_skill_dictionary/build_mode_fsm.py`
- `agent_skill_dictionary/build_mode_tool_executor.py`
- `agent_skill_dictionary/build_mode_runner.py`

当前已验证：

- `111 -> 001 -> 110 -> 101 -> 111 -> 001 -> 000` 状态链。
- Chat Completions、OpenAI Responses、Anthropic Messages 三路协议的本地网关工具接管。
- 失败修复后的 `repair_next_hexagram == "001"`。
- 修复复测后的 `post_repair_verify_next_hexagram == "000"`。
- 归档 manifest 写入、repaired file 存在、SHA256 匹配。
- 三路协议最终状态文件进入 `000`，且 `consecutive_failures == 0`。

最新阶段收尾见：

- `docs/build-mode-local-closeout-20260526.md`

仍未完成：

- Codex Desktop 真实客户端端到端验证。
- Claude Code 真实客户端端到端验证。
- 真实上游模型长任务 A/B。
- WebSocket 兼容。
- 词典热加载。
- 更细的 shell command AST/parser 级安全分析。
- 多租户 API key 管理。

## 第三阶段建议目标

下一阶段应继续推进：

```text
8 个根字 Opcode 与 workflow 已固化
下一步把 workflow 热加载、审计日志落盘和具体 Agent 工具层强制接入补齐
```

V0.3 架构方向：

- 8 个根字：`查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总`。
- 现有 22 个字全部继承其中一个根字。
- 子字可以更严格，不能放宽父字权限。
- 64 字只是未来扩展，不进入当前交付范围。

已完成交付物：

- `docs/eight-opcode-primitives.md`
- `docs/v0.3-action-framework.md`
- `docs/existing-agent-gateway-integration.md`
- `root_opcode` 字段
- `opcode_vector` 字段
- `inheritance_policy` 字段
- `six_phase_workflow` 字段
- `transition_policy` 字段
- `agent_skill_dictionary/workflow_registry.json`
- `agent_skill_dictionary/workflow_loader.py`
- `agent_skill_dictionary/skill_mount_loader.py`
- `agent_skill_dictionary/kernel_policy.py`
- `agent_skill_dictionary/macro_chain.py`
- `agent_skill_dictionary/workflows/查.md`
- `agent_skill_dictionary/workflows/修.md`
- `agent_skill_dictionary/workflows/测.md`
- `agent_skill_dictionary/workflows/卫.md`
- `agent_skill_dictionary/workflows/停.md`
- `agent_skill_dictionary/workflows/问.md`
- `agent_skill_dictionary/workflows/记.md`
- `agent_skill_dictionary/workflows/总.md`
- `agent_skill_dictionary/skill_mount_registry.json`
- workflow loader 单测
- skill mount registry 单测
- workflow 摘要网关注入
- skill mount 摘要网关注入
- kernel policy 单测
- macro chain 单测
- OneWord-Agent FSM 单测
- OneWord-Agent FSM 框架文档
- 现有 Agent / Claude Code 网关接入路线文档
- 根字 Skill Mount 注册表文档
- 内核规训注入、工具过滤和 `停` 熔断
- 功能开发闭环与安全熔断闭环解析

后续交付物：

- workflow 注入预算策略进一步细化。
- workflow 缺失时的 validator 错误。
- 审计日志独立落盘。
- 具体 Agent 工具执行层强制调用 `/v1/yizijue/preflight-tool`。
- 证据链校验接入交付门：证据不足时自动转 `问` 或 `停`。
- Anthropic-compatible adapter：支持 Claude Code 通过 `ANTHROPIC_BASE_URL` 指向一字诀网关。

这样一字诀会从“词典里写清楚”进入“运行时按字加载专业流程”的下一层。

## 验证基线

V0.3/V0.4 当前完成状态的验证命令是：

```bash
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_gateway_plan tests.test_audit tests.test_gateway_server_import tests.test_tool_guard tests.test_tool_preflight tests.test_phase2_dictionary tests.test_reference_patterns tests.test_opcode_primitives tests.test_workflow_loader tests.test_skill_mount_registry tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent tests.test_minimal_gateway_mvp -v
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
python3 -m json.tool agent_skill_dictionary/oneword_dict.json >/tmp/oneword_dict.json
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
python3 -m compileall -q agent_skill_dictionary
```

当前通过标准：

```text
完整 unittest 通过
validator OK
compileall OK
```
