# Agent Skill Dictionary 词典契约

本文档说明 `programming-agent-skill-dictionary.json` 的字段含义和维护规则。机器校验入口是：

```text
schemas/agent-skill-dictionary.schema.json
agent_skill_dictionary/validator.py
```

## 顶层结构

```json
{
  "name": "Programming Agent Skill Dictionary",
  "version": "0.3.0",
  "domain": "programming",
  "updated_at": "2026-05-24",
  "entries": []
}
```

字段含义：

- `name`：词典名称。
- `version`：词典版本，当前使用 `0.x.x` 格式。
- `domain`：词典领域，当前是 `programming`。
- `updated_at`：更新日期。
- `entries`：执行字条目数组。

## 执行字条目

每个 entry 表示一个执行字。

核心字段：

- `code`：执行字，例如 `修`、`源`、`卫`。
- `name`：英文机器名，例如 `fix`、`source`、`guard`。
- `definition`：系统写死的含义。
- `intent_examples`：用户自然语言样例。
- `reference_workflow_patterns`：该字借鉴的外部优秀 Skill / Agent workflow 模式 ID。
- `professional_protocol`：该字背后的专业运行协议。
- `bound_skill_patterns`：绑定的能力模式。
- `allowed_actions`：允许动作。
- `forbidden_actions`：禁止动作。
- `tool_policy`：工具权限。
- `runtime_environment`：运行环境策略。
- `routing_target`：路由目标。
- `model_policy`：模型策略。
- `required_steps`：执行步骤。
- `verification`：验证与证据要求。
- `fallback`：低置信度、失败和熔断回退。
- `root_opcode`：该字继承的八大根字之一。
- `opcode_vector`：根字三维控制向量。
- `inheritance_policy`：子字继承策略。
- `six_phase_workflow`：六步确定性工作流。
- `transition_policy`：成功、失败、风险时的状态转移策略。

## 参考模式与专业协议

一字诀 V0.3 的核心约束是：一个字背后必须有具体、专业、可执行的运行逻辑，并且必须继承一个底层根字 Opcode。

```json
{
  "reference_workflow_patterns": [
    "superpowers:systematic-debugging",
    "superpowers:test-driven-development",
    "superpowers:verification-before-completion"
  ],
  "professional_protocol": {
    "source_projects": [
      "obra/superpowers systematic-debugging",
      "SWE-agent issue-reproduction workflow"
    ],
    "operating_logic": [
      "先捕获真实失败日志和最小复现路径",
      "定位根因并区分配置、依赖、逻辑和环境问题",
      "只修改受影响文件，优先补充回归测试",
      "运行验证命令并记录系统层证据摘要"
    ],
    "hard_gates": [
      "没有复现或证据不得宣称修复",
      "连续失败超过重试上限必须熔断到查"
    ]
  }
}
```

字段含义：

- `reference_workflow_patterns`：机器可读的能力模式 ID，用于路由、测试和后续 workflow markdown 加载。
- `professional_protocol.source_projects`：该执行字参考的优秀项目、官方文档、论文或成熟工程实践。
- `professional_protocol.operating_logic`：进入该字后必须遵循的专业步骤。
- `professional_protocol.hard_gates`：该字的硬门槛，触发后必须阻断、追问、降级或熔断。

维护规则：

- 每个执行字都必须有 `reference_workflow_patterns`。
- 每个执行字都必须有 `professional_protocol`。
- `operating_logic` 至少 3 步。
- `hard_gates` 至少 2 条。
- 外部项目只作为能力模式参考，不代表本项目复制、分发或认证这些外部项目。

## 根字 Workflow 契约

8 个根字的专业提示词工程规范不只存在于 JSON 字段里，还被拆成独立 markdown：

```text
agent_skill_dictionary/workflow_registry.json
agent_skill_dictionary/workflows/查.md
agent_skill_dictionary/workflows/修.md
agent_skill_dictionary/workflows/测.md
agent_skill_dictionary/workflows/卫.md
agent_skill_dictionary/workflows/停.md
agent_skill_dictionary/workflows/问.md
agent_skill_dictionary/workflows/记.md
agent_skill_dictionary/workflows/总.md
```

每个 workflow 文件必须包含：

```text
Prompt Engineering Sources
Efficiency Controls
Precision Controls
Stability Controls
Evidence
```

维护规则：

- 新增根字时，必须同时新增 workflow markdown 和 registry 映射。
- 派生字不需要复制根字 workflow，但必须通过 `root_opcode` 继承。
- 子字可以增加更严格的专业协议，不能放宽根字的权限、上下文和证据要求。
- 网关会把根字 workflow 摘要注入 system rule，因此 workflow 内容要短、硬、可执行，避免写成泛泛宣言。

## 工具权限

`tool_policy` 是当前最重要的安全边界。

```json
{
  "read": "allowed",
  "write": "forbidden",
  "network": "approval_required",
  "dependency_install": "forbidden"
}
```

推荐规则：

- `查 / 审 / 源 / 卫 / 隔 / 问 / 停 / 评 / 总` 必须 `write: forbidden`。
- `合 / 搜` 必须 `write: forbidden`。
- `源` 必须 `dependency_install: forbidden`。
- `合 / 搜 / 问 / 停 / 记 / 评 / 总` 必须 `dependency_install: forbidden`。
- `修` 可以 `write: scoped_to_impact_files`，但禁止安装未批准依赖。
- `造 / 改 / 测 / 设 / 简` 的写权限必须保持受限。
- `部` 可以保留受限写权限，但高风险部署动作必须人工确认。
- `数 / 文` 可以受限写入结果文件或文档，但不能覆盖源数据或编造未验证行为。
- `记` 只能受限写入项目记忆、ADR 或文档，不允许修改业务源代码。

## 运行环境策略

```json
{
  "auto_inject_local_env": true,
  "context_breaker_on_switch": true,
  "evidence_capture": "system_sandbox",
  "audit_log_write_access": "system_only"
}
```

字段含义：

- `auto_inject_local_env`：允许网关注入本地项目环境摘要。
- `context_breaker_on_switch`：执行字切换时触发上下文预算断路器。
- `evidence_capture`：证据捕获来源，当前目标是系统沙盒。
- `audit_log_write_access`：审计日志写权限，必须是 `system_only`。

## 验证字段

```json
{
  "required": true,
  "evidence_source": "system_sandbox_stdout_stderr",
  "acceptable_evidence": ["test_output_hash"],
  "audit_fields": ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256"]
}
```

要求：

- 需要验证的执行字必须包含完整 `audit_fields`。
- 模型不能自己生成验证日志。
- 后续实现审计日志落盘时，应由系统捕获 stdout、stderr、exit code 和 hash。

## 失败回退

```json
{
  "when_confidence_below": 0.75,
  "action": "ask_clarifying_question_or_route_to_查",
  "on_max_retry_exceeded": "MELT_DOWN_TO_查",
  "on_meltdown": "revoke_write_permissions_and_emit_bug_report"
}
```

规则：

- 低置信度时应追问或回退到 `查`。
- `修` 连续失败后必须熔断到 `查`。
- 熔断后应收回写权限并生成失败报告。

## 新增执行字流程

1. 在 `programming-agent-skill-dictionary.json` 增加 entry。
2. 保持字段完整，符合 JSON Schema。
3. 如果是只读或控制类执行字，在 validator 中加入权限约束。
4. 增加测试覆盖该字的关键安全边界。
5. 运行验证命令。

```bash
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_workflow_loader tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent -v
```
