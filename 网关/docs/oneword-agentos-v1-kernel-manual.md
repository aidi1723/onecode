# 一字诀驱动 Agent Skill 词典 V1.0

官方系统内核设计手册与工程白皮书
发布日期：2026-05-24
顶层项目：字溯东方 / 大字典
内核调性：客观、确定、中立、低情绪值

## 1. 项目定位

一字诀是面向 AI Agent 的确定性行为控制中间层内核。它不追求扩大模型自由发挥，而是用执行字把自然语言意图编译成可路由、可限制、可验证的工程状态。

当前工程版本已经形成三条并行落地线：

```text
完整网关线
  programming-agent-skill-dictionary.json + gateway_server.py

最小 MVP 线
  oneword_dict.json + minimal_gateway_server.py

框架演进线
  one_word_agent.py + Macro Chain + Root Skill Mount
```

## 2. 工程目标

一字诀的目标是降低 Agent 漂移、减少重复上下文、收紧工具权限，并把交付判断交给系统证据。

工程目标：

- 意图理解与执行规训分离。
- 高频规范固化在本地词典和内核策略中。
- 当前执行字决定工具白名单，而不是让模型自由选择工具。
- 测试、构建和安全审计尽量由系统沙盒捕获证据。
- 大字典从解释型知识库演进为执行型语义基础设施。

边界声明：

```text
一字诀不能承诺绝对消灭幻觉。
它能做的是把模型自由度压缩到当前状态、当前工具、当前证据和当前回退策略之内。
```

## 3. 七层漏斗架构

```text
输入层
  接收用户请求、代码、日志和上下文

语义归一化层
  显式前缀 / 关键词 / 后续向量检索 -> 执行字

词典硬解码层
  读取 oneword_dict.json 或 programming-agent-skill-dictionary.json

Skill 挂载层
  按根字加载 Root Skill Mount 和 workflow markdown

路由分发层
  注入 system rule、锁温度、裁剪 tools

执行隔离层
  通过 preflight、沙盒或具体 Agent 工具层限制动作

验证与审计层
  捕获 exit code、stdout、stderr、coverage、hash 和审计摘要
```

## 4. 八根字内核

当前实现采用 8 个根字：

```text
查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总
```

说明：`造` 是 `修` 的派生构筑字，不是当前根字。这样可以避免把“受限写入”和“新建功能”拆成两个重叠底层原语。`乾` 在当前实现中对应 `总` 的收束、摘要和交接。

| 根字 | 卦象 | 内核含义 | 工具白名单摘要 | Skill Mount |
| --- | --- | --- | --- | --- |
| `查` | 离 | 只读探测 | `read_file / list_directory / grep_code / git_diff` | Aider Repo Map / SWE-agent ACI |
| `修` | 震 | 外科修复 | `read_file / edit_scoped_file / create_new_file` | Surgical fix / TDD |
| `测` | 巽 | 测试验证 | `run_pytest / run_npm_test / capture_coverage` | pytest-cov / CI quality gate |
| `卫` | 坎 | 安全守卫 | `dependency_security_scan / ast_vulnerability_check` | Semgrep / OSV-Scanner |
| `停` | 艮 | 熔断挂起 | none | Circuit Breaker |
| `问` | 兑 | 人机澄清 | `send_user_message / render_ui_options` | Human-in-the-loop |
| `记` | 坤 | 记忆存储 | `append_knowledge_base / write_markdown_doc / git_commit` | Claude Code memory / ADR |
| `总` | 乾 | 收束交接 | `compress_tokens` | Handoff compaction |

## 5. V1.0 最小实体词典

最小 MVP 词典已经落盘：

```text
agent_skill_dictionary/oneword_dict.json
```

它包含 8 根字的：

- `hexagram`
- `system_prompt`
- `temperature`
- `allowed_tools`
- `blocked_tools`
- `evidence_required`
- `halt_model_forwarding`

这个文件是最小网关的最高宪法。完整词典仍然是：

```text
agent_skill_dictionary/programming-agent-skill-dictionary.json
```

完整词典包含 22 个执行字、派生字、root opcode、专业协议、workflow、fallback 和 transition policy。

## 6. 最小 FastAPI 网关

最小 MVP 代码：

```text
agent_skill_dictionary/minimal_gateway_core.py
agent_skill_dictionary/minimal_gateway_server.py
tests/test_minimal_gateway_mvp.py
```

它做四件事：

1. 从用户消息编译根字。
2. 从 `oneword_dict.json` 读取该字规则。
3. 注入最小 system rule 并锁定 temperature。
4. 按工具白名单裁剪 `tools`；遇到 `停` 时阻断上游模型转发。

启动方式：

```bash
ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.minimal_gateway_server:app --host 0.0.0.0 --port 8080
```

OpenAI-compatible Agent 指向：

```text
http://localhost:8080/v1
```

## 7. 状态机与变卦

一字诀的多步执行不应交给模型自由规划，而应由状态机控制：

```text
查 -> 修 -> 测 -> 记 -> 总
卫 -> 停 -> 问 -> 查 -> 总
```

当前状态机原型：

```text
agent_skill_dictionary/one_word_agent.py
```

当前 Macro Chain：

```text
agent_skill_dictionary/macro_chain.py
```

当前 MVP 还没有把 Macro Chain 自动展开为真实多步执行 endpoint。后续目标是新增：

```text
POST /v1/yizijue/run
```

## 8. 近期工程路线

### 8.1 语义归一化

当前：

```text
显式前缀 + 关键词规则
```

后续：

```text
L1 显式前缀 / Regex
L2 本地向量检索
L3 低置信度转问
```

低置信度阈值建议：

```text
confidence < 0.75 -> 问 或 查
```

### 8.2 执行隔离

当前：

```text
请求层 tools 过滤 + preflight-tool 接口
```

后续：

```text
具体 Agent 工具层强制调用 /v1/yizijue/preflight-tool
Docker 沙盒执行测试与扫描
```

### 8.3 证据链

当前：

```text
audit.py 可生成 stdout/stderr/exit code 摘要 hash
```

后续：

```text
沙盒运行测试命令
生成 SHA-256
写入独立审计日志
证据不足转问或停
```

### 8.4 上下文断路器

当前：

```text
词典与 workflow 已声明 context_breaker_on_switch
```

后续：

```text
状态切换时裁剪对话历史
只保留原始需求、关键 diff、验证证据和当前字规则
```

## 9. 64 字扩展

64 字是 8 根字的专业变体，不推翻根字内核。

示例：

```text
查 -> 源 / 搜 / 解 / 审
修 -> 造 / 改 / 简 / 补
测 -> 验 / 覆 / 回 / 证
卫 -> 合 / 隔 / 禁 / 守
```

扩展原则：

- 子字必须继承一个根字。
- 子字可以更严格，不能放宽父字权限。
- 子字必须有独立证据要求。
- 子字必须能被 Macro Chain 组合。

## 10. 长期目标

长期形态是面向 AI 的行为基础设施：

- 汉字指令集芯片化：64 字成为 Agent 软指令集。
- 分布式矩阵调度：不同根字调度到不同本地节点。
- 跨领域扩展：编程、B2B 合规、供应链、合同、报价和数字资产生成。
- 主权防护：`卫` 和 `停` 常驻底层，限制提示词注入、供应链风险和越权工具调用。

这些目标需要在 MVP 证据链、preflight、adapter、审计日志和沙盒机制稳定后逐步推进。

## 11. 当前验证入口

```bash
python3 -m unittest tests.test_minimal_gateway_mvp -v
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_gateway_plan tests.test_audit tests.test_gateway_server_import tests.test_tool_guard tests.test_tool_preflight tests.test_phase2_dictionary tests.test_reference_patterns tests.test_opcode_primitives tests.test_workflow_loader tests.test_skill_mount_registry tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent tests.test_minimal_gateway_mvp -v
python3 -m json.tool agent_skill_dictionary/oneword_dict.json >/tmp/oneword_dict.json
python3 -m compileall -q agent_skill_dictionary
```
