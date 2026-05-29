# 一字诀 Agent Skill Gateway

一字诀是一个面向 AI Agent 的确定性中间层。它把用户自然语言先归一化成一个或多个“执行字”，再从本地词典读取该字对应的 Skill、权限、工作流、验证规则和失败回退策略，最后把规训后的请求转发给 OpenAI-compatible 上游模型。

## 临时收尾与私测入口

当前阶段总结见：

```text
docs/build-mode-local-closeout-20260526.md
docs/phase3-temporary-closeout-20260525.md
```

## Build Mode V2

Build Mode V2 的本地网关闭环已经通过。当前已验证范围是：真实本地 HTTP 网关 + mock upstream，覆盖 Chat Completions、OpenAI Responses、Anthropic Messages 三路协议，并检查 `111 -> 001 -> 110 -> 101 -> 111 -> 001 -> 000` 的结构化证据链、状态文件、manifest 和 SHA256。

尚未完成的是 Codex Desktop / Claude Code 真实客户端端到端验证。最新边界见：

- `docs/build-mode-local-closeout-20260526.md`

设计与实施文档见：

- `docs/build-mode-kernel-rules.md`
- `docs/hexagram-rules.md`
- `docs/build-mode-mvp-implementation-plan.md`
- `docs/build-mode-control-network.md`

私测部署优先阅读：

```text
PRIVATE_BETA_QUICKSTART.md
deploy/README_PRIVATE_BETA.md
docs/private-beta-distribution.md
```

本轮关键结论：Codex CLI `gpt-5.5` 同任务 A/B 中，一字诀把总 token 从 `183,726` 降到 `8,736`，耗时从 `66.74s` 降到 `21.51s`，本地命令调用从至少 `19` 次降到 `0`。当前适合本机与私密仓库 Beta 测试，公开生产版仍需继续验证。

这个项目当前有两条线：

- `data/`：字溯东方 / 大字典的汉字知识库数据。
- `agent_skill_dictionary/`：一字诀 Agent Skill 词典与网关内核。

两条线共享仓库但版本边界分开处理：`data/` 的主验收是 JSON/CSV 数据契约、lookup 同步和复核队列一致性；`agent_skill_dictionary/` 的主验收是网关权限、词典 validator、单元测试和 Python 编译检查。发布网关时不要把数据扩库状态当作网关功能完成证据；扩库时也不要把网关测试通过当作数据质量复核。

## 当前能力

- 支持编程与工作流执行字：`查 / 解 / 修 / 造 / 改 / 测 / 审 / 设 / 源 / 卫 / 隔 / 简 / 部 / 数 / 文 / 合 / 搜 / 问 / 停 / 记 / 评 / 总`。
- 支持自然语言到执行字的关键词归一化。
- 支持多字任务的指令堆栈，例如 `修 + 测` 会压栈为 `["测", "修"]`，先执行 `修`。
- 支持 OpenAI-compatible `/v1/chat/completions` 网关入口。
- 支持 V1.0 最小 MVP 词典 `oneword_dict.json` 和 minimal FastAPI 代理骨架。
- 支持 `/v1/yizijue/resolve` 执行计划解析入口，不调用上游模型。
- 支持 `/v1/yizijue/protocol` 通用 Agent 接入协议自描述，不绑定 Claude Code 或任何单一客户端。
- 支持参考外部 Agent 适配器：`reference_agent_adapter` 会按 `resolve -> preflight-tool -> execute -> submit-evidence` 的物理闭环运行，用来验证任意第三方 Agent 接入前必须遵守的工具门禁与证据回传规则。
- 支持按执行字注入 system rule，并按词典锁定 `temperature`。
- 支持每个执行字绑定 `reference_workflow_patterns` 和 `professional_protocol`，把社区优秀 Skill / Agent workflow 的执行精髓写成机器可加载规则。
- 支持 8 个根字加载独立 workflow markdown：每个根字都包含提示词工程来源、效率控制、精准控制、稳定控制和证据要求。
- 支持 Root Skill Mount Registry：8 个根字挂载 Aider Repo Map、SWE-agent、pytest-cov、Semgrep、OSV-Scanner、LangGraph、Claude Code memory 等成熟社区规范的工程精髓。
- 支持网关按 `root_opcode` 注入根字 Workflow 摘要，让派生字继承一套专业、稳定、可审计的执行规范。
- 支持 Kernel Runtime Policy：8 个根字分别拥有工具权限锁、内核行为规训、温度覆盖和原子证据链要求。
- 支持请求进入上游模型前按根字过滤 `tools`；`停` 会触发 HTTP 503 硬熔断，不继续转发上游模型。
- 支持闭环 Macro Chain 编译：复杂需求可被解析为 `查 -> 造 -> 测 -> 修 -> 记 -> 总` 或 `卫 -> 停 -> 问 -> 查 -> 总` 等确定性根字链。
- 支持 OneWord-Agent FSM 框架原型：把任务运行成 8 个根字之间的可审计状态轨迹。
- 明确现有 Agent 接入路线：先规训 OpenAI-compatible Agent，再通过 Anthropic-compatible adapter 接入 Claude Code，最后再演进自研 AgentOS。
- 支持响应侧 tool-call 守卫标注，识别写文件、安装依赖和高风险 shell 命令。
- 支持 `/v1/yizijue/preflight-tool` 执行前工具检查接口。
- 支持系统证据摘要工具，为后续审计日志落盘打底。
- 支持 `/v1/chat/completions` 对 `stream=true` 返回明确拒绝，避免外部 Agent 误以为流式代理已经可用。
- 支持本地 validator，检查只读字、审计字段、熔断规则和 `源` 的依赖安装禁用规则。
- 支持真实 OneWord-Agent 执行器：`查` 工作区只读扫描、`修` 受控补丁写入、`测` 真实命令验证、`卫` 策略化安全扫描、`停` 熔断快照、`问` 人工确认票据、`记` 归档、`总` 交付摘要。
- 支持端到端运行入口：`python3 -m agent_skill_dictionary.runner` 和 `/v1/yizijue/run` 会返回 trace、审计日志路径和交付产物。
- 支持阴阳八卦运行时契约：错卦制衡、综卦换位、互卦隐藏风险锁和六爻式生命周期均已进入 `trigram_contract.py`、网关解析元数据和状态转移审计。

## 当前阶段

当前版本主线是 `V0.3`，并已开始进入 `V0.4 Kernel Runtime Policy + OneWord-Agent FSM`。第二阶段已完成，八大 Opcode 原型、根字 workflow 加载、内核运行策略 MVP 和状态机框架原型已落地。

第二阶段完成的定义：

- 22 个执行字已经写入词典。
- 每个执行字都有 `reference_workflow_patterns`。
- 每个执行字都有 `professional_protocol`，包含参考来源、专业步骤和硬门规则。
- 网关会把执行字的参考工作流、专业运行逻辑和根字 workflow 摘要注入 system rule。
- 网关会把根字 Kernel Runtime Policy 注入 system rule，并在请求转发前过滤不属于当前根字的工具。
- 工具守卫支持响应侧标注和 `/v1/yizijue/preflight-tool` 执行前检查。
- 本地测试、词典 validator 和 Python 编译检查作为当前验证基线。

第三阶段核心已经落地：8 个根字的专业协议已拆成可加载 workflow 文件，并接入 workflow loader 与网关注入。V0.4 进一步补上 Kernel Runtime Policy、Macro Chain 和 OneWord-Agent FSM 框架原型。后续仍需要继续完善上下文预算加载策略、审计日志落盘、workflow 热加载和具体 Agent 工具执行层的强制接入。

V0.3 已经把 `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总` 八个根字落成底层 Opcode 原型，并让现有 22 个字继承这些根字。64 字只作为未来扩展，不进入当前行动范围。

## 核心设计：一个字背后一套专业规范

一字诀里的“字”不是短提示词，也不是口号。每个字背后至少有五层约束：

- 词典定义：固定含义、权限、模型参数、失败回退和验证要求。
- 根字 Opcode：规定这个字继承哪一种底层行为边界，例如只读、受限写入、验证、安全、熔断、澄清、记忆或收束。
- Workflow markdown：记录该根字参考的优秀提示词工程和 Agent 工作流思想，并写清效率、精准、稳定和证据控制。
- Kernel Runtime Policy：把工具白名单、危险拦截、温度覆盖、熔断和证据字段写成运行时代码。
- 网关注入：运行时把当前字和根字 workflow 摘要写入 system rule。
- 工具守卫：在工具调用前后检查写入、依赖安装和高风险 shell 命令。

所以，一字诀追求的不是让模型“自己理解一个字”，而是让系统用一个字加载一套专业运行逻辑。它不能承诺绝对零幻觉，但能显著减少自由发挥空间，把 Agent 固定到可验证、可回退、可审计的轨道上。

## 项目结构

```text
agent_skill_dictionary/
  gateway_core.py                         # 一字诀归一化、堆栈、请求重写核心
  gateway_plan.py                         # 自然语言到执行计划的解析输出
  gateway_server.py                       # FastAPI /v1/chat/completions 网关
  agent_protocol.py                       # 通用 Agent 接入协议 manifest
  reference_agent_adapter.py              # 外部 Agent 参考适配器：preflight 后执行，执行后提交证据
  cli.py                                  # 本地 Agent 控制面 CLI
  minimal_gateway_server.py               # V1.0 最小 FastAPI 反向代理骨架
  minimal_gateway_core.py                 # V1.0 最小词典重写与工具裁剪核心
  one_word_agent.py                       # OneWord-Agent 8 根字有限状态机框架原型
  audit.py                                # 系统证据摘要工具
  runner.py                               # 端到端 OneWord-Agent 任务运行入口
  inspect_executor.py                     # 查：只读工作区扫描
  patch_executor.py                       # 修：受控补丁写入
  executor.py                             # 测：真实命令执行与退出码证据
  guard_executor.py                       # 卫：策略化安全扫描
  halt_executor.py                        # 停：熔断快照
  prompt_executor.py                      # 问：人工确认票据
  memory_executor.py                      # 记：摘要归档
  summary_executor.py                     # 总：交付摘要
  trigram_contract.py                     # 阴阳八卦运行时契约：错卦、综卦、互卦、六爻生命周期
  kernel_policy.py                        # 8 根字内核运行策略：工具锁、温度、证据链、熔断
  macro_chain.py                          # 复杂任务到闭环根字链的确定性编译器
  tool_guard.py                           # tool-call 权限检查
  loader.py                               # 词典加载与按字查询
  validator.py                            # 词典一致性校验
  workflow_loader.py                       # 根字 workflow markdown 加载
  skill_mount_loader.py                    # 根字 Skill Mount 注册表加载
  workflow_registry.json                   # 8 个根字到 workflow 文件的映射
  skill_mount_registry.json                # 8 个根字到社区成熟规范挂载的映射
  oneword_dict.json                       # V1.0 MVP 8 根字最高宪法实体词典
  guard_policy.json                       # 卫：安全扫描策略
  workflows/                               # 8 个根字的专业提示词工程规范
  programming-agent-skill-dictionary.json # 编程域执行字词典，含参考工作流和专业运行协议
  execution-stack-policy.md               # 指令堆栈策略

schemas/
  agent-skill-dictionary.schema.json      # 词典 JSON Schema
  guard-policy.schema.json                # Guard Policy JSON Schema

tests/
  test_agent_skill_dictionary.py          # 词典校验测试
  test_gateway_core.py                    # 网关核心测试
  test_agent_protocol.py                  # 通用 Agent 接入协议测试
  test_agent_cli.py                       # 本地 Agent 控制面 CLI 测试
  test_kernel_policy.py                   # 8 根字内核运行策略测试
  test_macro_chain.py                     # 闭环 Macro Chain 编译测试
  test_one_word_agent.py                  # OneWord-Agent FSM 状态转移与审计轨迹测试
  test_trigram_contract.py                # 阴阳八卦运行时契约测试
  test_workflow_loader.py                 # 根字 workflow 加载与网关注入测试
  test_skill_mount_registry.py            # 根字 Skill Mount 注册表与网关注入测试
  test_minimal_gateway_mvp.py             # V1.0 最小网关与 oneword_dict 测试

docs/
  architecture.md                         # 架构说明
  community-skill-inspirations.md         # 社区优秀 Skill 思想映射
  community-skill-research-2026.md        # 社区 Skill 与 Agent workflow 调研
  dictionary-contract.md                  # 词典契约
  eight-opcode-primitives.md              # 八个根字 / Opcode 原型架构
  oneword-agent-framework.md              # OneWord-Agent FSM 框架层说明
  root-skill-mount-registry.md            # 8 根字挂载社区成熟规范的注册表说明
  oneword-agentos-v1-kernel-manual.md     # V1.0 官方内核设计手册与工程白皮书
  existing-agent-gateway-integration.md   # 现有 CLI Agent / Claude Code 网关接入路线
  development.md                          # 开发与验证
  project-status.md                       # 当前阶段状态与边界
  v0.3-action-framework.md                # V0.3 行动框架
  yizijue-gateway-quickstart.md           # 网关运行说明
  one-character-agent-workflow-whitepaper.md
```

## 快速运行

验证本地内核：

```bash
make verify
```

运行交付 smoke test：

```bash
make smoke
```

运行端到端本地任务：

```bash
python3 -m agent_skill_dictionary.runner "帮我看看项目结构" --workspace .
```

输出是 JSON，包含：

- `status`：`completed`、`halted` 或 `waiting_for_human`
- `trace`：根字状态轨迹，例如 `["查", "总"]`
- `audit_log_path`：不可变审计日志路径
- `artifacts`：摘要、记忆归档、熔断快照、人工确认票据、变更文件等交付产物

或分别运行：

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core -v
python3 -m unittest tests.test_workflow_loader tests.test_skill_mount_registry tests.test_opcode_primitives tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent tests.test_minimal_gateway_mvp -v
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
```

启动网关：

```bash
python3 -m pip install -r requirements-gateway.txt
export ONEWORD_WORKSPACE_ROOT="$(pwd)"
export ONEWORD_GATEWAY_TOKEN="dev-local-token"

ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

把兼容 OpenAI API 的 Agent 的 base URL 指向：

```text
http://localhost:8080/v1
```

如果设置了 `ONEWORD_GATEWAY_TOKEN`，外部 Agent 的 `OPENAI_API_KEY` 应填写该 gateway token；真实上游模型 key 只放在网关侧的 `ONEWORD_UPSTREAM_API_KEY`。
网关不会把客户端传入的 `Authorization` 转发给上游；上游鉴权只使用网关进程环境里的真实 key。
没有配置上游 key 时，控制面 `/v1/yizijue/*` 仍可测试，但 `/v1/chat/completions` 会返回 `upstream_api_key_missing`。

也可以直接调用端到端执行接口：

```bash
curl -sS http://localhost:8080/v1/yizijue/run \
  -H 'content-type: application/json' \
  -H "authorization: Bearer $ONEWORD_GATEWAY_TOKEN" \
  -d '{"input":"帮我看看项目结构","workspace":"."}'
```

验证“外部 Agent 接入”物理闭环：

```bash
python3 -m agent_skill_dictionary.reference_agent_adapter \
  "查：看看项目结构" \
  --base-url http://localhost:8080 \
  --workspace . \
  --token "$ONEWORD_GATEWAY_TOKEN"
```

该适配器会先调用 `/v1/yizijue/resolve` 编译根字，再在每个工具动作前调用 `/v1/yizijue/preflight-tool`。只有网关允许后才会执行本地工具，执行结果随后通过 `/v1/yizijue/submit-evidence` 写入审计链。

查看通用 Agent 接入协议：

```bash
curl -sS http://localhost:8080/ready
curl -sS http://localhost:8080/v1/yizijue/protocol
```

不启动 HTTP 服务时，也可以让任意 Agent 通过本地 CLI 接入：

```bash
python3 -m agent_skill_dictionary.cli protocol
python3 -m agent_skill_dictionary.cli doctor
python3 -m agent_skill_dictionary.cli resolve "查：看看项目结构"
python3 -m agent_skill_dictionary.cli preflight --active-code 查 --tool-name write_file --arguments-json '{"path":"app.py"}'
python3 -m agent_skill_dictionary.cli run "帮我看看项目结构" --workspace .
python3 -m agent_skill_dictionary.cli run "请运行测试验证" --workspace . --use-docker
python3 -m agent_skill_dictionary.cli run "检查是否有供应链风险" --workspace . --enable-external-scanners
python3 -m agent_skill_dictionary.cli audit --path .oneword/audit.jsonl
```

任意 Agent 的推荐接入循环：

1. 调用 `/v1/yizijue/resolve` 获取当前根字、卦码、工具白名单和证据要求。
2. 每次工具执行前调用 `/v1/yizijue/preflight-tool`，按 `allowed/violations` 决定是否执行。
3. 执行后提交或保留系统 evidence，不允许用模型自然语言声明测试通过。
4. 用 `audit` 或 `verify_audit_chain()` 校验 JSONL hash chain，确认日志未被篡改。
5. 遇到 `halted` 立即停止，遇到 `waiting_for_human` 把结构化选择交给人类。

## 推荐阅读顺序

1. [架构说明](docs/architecture.md)
2. [项目状态](docs/project-status.md)
3. [更新日记](docs/update-diary.md)
4. [交付测试计划](docs/delivery-test-plan.md)
5. [阴阳二进制内核](docs/yin-yang-binary-kernel.md)
6. [八个根字 / Opcode 原型架构](docs/eight-opcode-primitives.md)
7. [OneWord-Agent FSM 框架](docs/oneword-agent-framework.md)
8. [根字 Skill Mount 注册表](docs/root-skill-mount-registry.md)
9. [V1.0 官方内核设计手册](docs/oneword-agentos-v1-kernel-manual.md)
10. [现有 Agent 网关接入路线](docs/existing-agent-gateway-integration.md)
11. [V0.3 行动框架](docs/v0.3-action-framework.md)
12. [社区优秀 Skill 思想映射](docs/community-skill-inspirations.md)
13. [社区优秀 Skill 与 Agent Workflow 调研](docs/community-skill-research-2026.md)
14. [网关快速启动](docs/yizijue-gateway-quickstart.md)
15. [N100 + Aider 外部 Agent 联调指南](docs/n100-aider-integration-test.md)
16. [词典契约](docs/dictionary-contract.md)
17. [开发与验证](docs/development.md)
18. [V0.3 白皮书](docs/one-character-agent-workflow-whitepaper.md)

## 当前边界

当前版本已经达到可交付 MVP：8 个根字都有可测试的内核策略，OneWord-Agent 具备真实执行、审计证据、交付产物、端到端运行入口和通用 Agent 接入协议。Build Mode V2 本地网关闭环也已经通过 live-smoke，三路协议均能完成写入、验证、失败修复、上下文检查和归档证据链。`测` 已支持可选 Docker 沙盒执行，默认加 `--network none --memory 1g --cpus 2`，并支持 `require_docker` 防止误降级到宿主机；`卫` 已支持可选 Semgrep / OSV-Scanner 外部扫描器接入；缺少本地二进制时会稳定降级。

仍未覆盖的生产增强项是真实 Codex Desktop / Claude Code 客户端端到端验证、真实上游模型长任务 A/B、WebSocket 兼容、多节点调度和词典热加载。真正完整的物理阻断仍需要具体 Agent 在执行工具前调用 `/v1/yizijue/preflight-tool`，或统一接入本项目网关。
