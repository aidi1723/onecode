# 当前项目中文评估报告

## 1. 项目目标和当前形态判断

当前目录是一个混合型项目，包含两条主线：

- **一字诀 AgentOS / Agent Skill Gateway**：用“单字执行码”把自然语言请求规训为确定性执行状态，并通过网关、词典、Kernel Policy、工具守卫、FSM、审计证据链来约束 Agent 行为。
- **大字典 / 字溯东方数据资产**：提供汉字基础库、新华基础层、lookup 索引、复核队列和数据录入规范。

当前形态不是单纯研究文档，也不是完整生产级 AgentOS，而是：

> **可运行 MVP + 较完整架构原型 + 较大规模数据资产 + 测试覆盖较多的工程样机。**

它已经具备较多实装代码：FastAPI 网关、OpenAI-compatible `/v1/chat/completions`、Anthropic-compatible `/v1/messages`、`/v1/yizijue/run`、执行计划解析、preflight 工具检查、FSM runner、真实只读扫描/安全扫描/受控 patch/测试执行/摘要归档等模块。

但它仍存在明显的产品化缺口：包管理不完整、依赖未锁定、运行模式复杂、文档与代码状态有少量不一致、Agent 工具层强制接入还未形成完整闭环。

## 2. 目录结构、核心模块、数据资产、脚本和文档质量

### 目录结构

项目顶层结构清晰：

```text
agent_skill_dictionary/  一字诀核心 Python 包
data/                    大字典与汉字基础数据
docs/                    架构、开发、交付、白皮书文档
schemas/                 JSON Schema
scripts/                 smoke、benchmark、集成脚本
tests/                   单元测试、路由测试、fixture、golden cases
reports/                 benchmark 报告
```

优点：

- 模块边界基本清楚。
- `agent_skill_dictionary/` 按 gateway、policy、executor、loader、validator、runner 拆分。
- `data/` 有 manifest、schema、lookup、CSV/JSON 双格式。
- `tests/` 文件数量多，覆盖多个核心路径。

问题：

- 顶层没有 `pyproject.toml`、`setup.py`、锁文件或正式包元数据。
- `requirements-gateway.txt` 只覆盖网关依赖，不覆盖测试、benchmark、fixture 所需依赖。
- 顶层存在 `.DS_Store`、`1.png`、`2.jpeg`、`3.jpeg`、`封面.png`、`.docx`，资产用途未纳入 manifest。
- 不是 Git 仓库，无法从当前目录判断提交历史、分支策略、发布标签。

### 核心模块

主要核心模块包括：

- `gateway_server.py`：FastAPI 网关，包含 `/health`、`/ready`、`/v1/yizijue/resolve`、`/v1/yizijue/preflight-tool`、`/v1/yizijue/run`、`/v1/chat/completions`、`/v1/messages`。
- `gateway_core.py`：执行字归一化、请求重写、system rule 注入、工具过滤、stream chunk 检查。
- `kernel_policy.py`：8 根字运行时策略，定义 allowed tools、blocked tools、temperature、熔断。
- `one_word_agent.py`：OneWord FSM，状态转移、trace、audit log。
- `runner.py`：端到端任务入口，会生成 `.oneword/audit.jsonl` 等运行产物。
- `tool_guard.py`：工具调用前/后权限判断。
- `executor.py`：命令执行，支持 Docker 只读沙箱模式。
- `patch_executor.py`：受控 patch 写入，要求已有文件提供 `expected_sha256`。
- `guard_executor.py`：正则安全扫描和 Semgrep/OSV 外部扫描接入。
- `tool_executor_registry.py`：注册工具执行器。

整体代码组织较务实，但部分模块职责偏重，尤其 `gateway_server.py` 聚合了认证、路由、上游转发、stream 检查、readiness、workspace 校验等逻辑，后续维护压力会增加。

### 数据资产

`data/agent-dictionary-manifest.json` 显示当前大字典基础层：

- `entry_count`: 500
- 主数据：`xinhua-base-entries.json`
- 索引：`xinhua-base-lookup.json`
- CSV：`xinhua-base-entries.csv`
- 有 review queue、review tags、variant、pinyin、radical 等索引维度。

数据文档质量较好，明确说明现代义项是基于《新华字典》释义体系整理的项目改写，不是逐字引用。这对版权和来源表达是加分项。

风险：

- 大量 `hanzi-lifecycle-combined-*` 文件并存，版本关系不够直观。
- 数据质量是否全量通过 schema 与 lookup 同步无法确认，因为本次按约束未执行验证命令。
- 数据资产和 AgentOS 代码共享仓库，但产品边界仍偏混杂。

### 脚本

`scripts/` 包含：

- `smoke_test.py`
- `http_gateway_smoke.py`
- `real_model_ab_benchmark.py`
- `live_agent_benchmark.py`
- `golden_matrix.py`
- `cyber_dice_ab_report.py`
- shell setup/smoke 脚本

脚本覆盖研发、集成和 benchmark 场景，但生产级封装不足：缺少统一 CLI、依赖声明、环境变量模板、可重复 benchmark 配置。

### 文档质量

文档数量充足，覆盖：

- 架构说明
- 开发说明
- 网关 quickstart
- kernel manual
- whitepaper
- delivery test plan
- project status
- root skill mount
- opcode primitives

主要问题是**文档有轻微状态漂移**。例如 `docs/project-status.md` 前部说 `/v1/yizijue/run` 已落地，后部“当前边界”又写“尚未提供 `/v1/yizijue/run` 多步执行 endpoint”。代码中实际已存在该 endpoint。

## 3. 架构成熟度、可维护性、测试完备度、运行/交付风险

### 架构成熟度

架构方向明确，抽象层次完整：

```text
自然语言
-> 执行字归一化
-> 词典
-> 根字 Kernel Policy
-> workflow / skill mount 注入
-> gateway request rewrite
-> tool preflight / response guard
-> FSM runner / executor / audit
```

成熟点：

- 8 根字策略固化，有工具白名单和熔断机制。
- 词典 schema 和 validator 存在。
- preflight-tool 与 response-side guard 都有实现。
- OpenAI 和 Anthropic 两种兼容入口都已有代码。
- runner 具备真实执行器，不只是 prompt 包装。

不成熟点：

- 归一化仍主要依赖关键词规则，复杂意图路由容易误判。
- 多步 AgentOS 仍是框架式 FSM，未完全打通模型 tool-call 执行、回传、再生成的真实循环。
- stream 检查基于字符串 signature，容易漏检变形 tool use。
- 工具执行 registry 与 gateway 尚未形成严格统一的授权执行链。
- 没有插件/包发布结构，部署更多依赖手工环境变量。

### 可维护性

代码可读性总体尚可，函数命名明确，测试辅助较多。

主要维护风险：

- `gateway_server.py` 过大，建议拆分 auth、routes、upstream、readiness、stream guard。
- `KEYWORD_RULES` 硬编码在 `gateway_core.py`，后续扩展会导致规则难治理。
- 字典、workflow、skill mount、kernel policy 多处定义同一概念，存在同步漂移风险。
- 没有类型检查、lint、coverage 配置。
- 没有正式版本发布流程。

### 测试完备度

`tests/` 下约 62 个测试文件，覆盖面明显强于普通 MVP。已看到测试覆盖：

- gateway core
- gateway auth
- gateway routes
- runner
- tool guard
- kernel policy
- one_word_agent
- validator
- benchmark scripts
- golden cases

限制：

- 本次按用户硬性约束未执行测试，因此不能确认当前测试是否全部通过。
- 缺少覆盖率报告。
- 集成测试多依赖 mock，真实上游、真实 stream、真实工具执行链风险仍需专项验证。
- 缺少 fuzz/property-based 测试来验证路径逃逸、命令解析、tool schema 变体。

### 运行/交付风险

主要风险：

- 没有 `pyproject.toml` 或锁文件，环境复现风险高。
- `Dockerfile.gateway` 会安装未锁定版本依赖：`fastapi>=0.115`、`httpx>=0.27`、`uvicorn[standard]>=0.30`，供应链变动可能导致行为漂移。
- `runner.py` 会写 `.oneword` 产物；这对产品是合理行为，但 CLI 文档需要醒目标明。
- `/ready` 对生产状态有帮助，但生产部署仍缺少健康检查策略、日志策略、反向代理建议、限流策略。
- 当前目录不是 Git 仓库，交付审计缺少版本可追溯性。

## 4. 安全风险、隐私/密钥风险、供应链风险

### 安全优点

- `gateway_server.py` 不把客户端 `Authorization` 直接转发给上游，而是使用网关侧 `ONEWORD_UPSTREAM_API_KEY`。
- 支持 `ONEWORD_GATEWAY_TOKEN`。
- 支持 workspace root 限制：`ONEWORD_WORKSPACE_ROOT`。
- `patch_executor.py` 对已有文件要求 `expected_sha256`，能降低误覆盖风险。
- `executor.py` 支持 Docker 只读、无网络、低权限用户、资源限制。
- `guard_executor.py` 有危险命令、curl pipe shell、密钥模式扫描。
- `submit-evidence` 限制 stdout/stderr 最大长度。

### 安全问题

1. **preflight 默认不强制鉴权**  
   `/v1/yizijue/preflight-tool` 只有设置 `ONEWORD_PROTECT_PREFLIGHT` 才强保护。生产环境建议默认保护。

2. **危险命令判断偏弱**  
   `tool_guard.py` 只匹配 `rm -rf`、`sudo `、`chmod -R 777`、`curl `、`wget `、`git reset --hard` 等固定 marker。绕过方式很多，例如变量拼接、`python -c`、`find -delete`、`dd`、`mkfs`、shell alias、base64 decode 后执行。

3. **stream tool guard 是字符串扫描**  
   对 SSE chunk 做 signature 检查，能挡住简单情况，但不是协议级 AST 解析。

4. **`execute_command` 本地模式仍可执行任意 command list**  
   虽然调用点有限，但只要上层传入未充分验证的命令，就可能产生高风险行为。生产建议默认强制 Docker 或受限命令 allowlist。

5. **供应链未锁定**  
   `requirements-gateway.txt` 使用下限版本，没有 hash pinning；Docker build 会拉取最新兼容版本。

6. **缺少安全响应策略**  
   有 guard 和 halt，但没有完整审计日志轮转、敏感字段脱敏策略、密钥泄露事件处理流程。

### 密钥风险

我用只读搜索检查了 `api_key/secret/token/password/sk-/OPENAI_API_KEY/ANTHROPIC_API_KEY` 等关键词。未看到真实生产密钥，主要是测试 token、文档示例和环境变量名。

需要注意：

- 文档中有 `dev-local-token` 示例，应明确仅限本地。
- benchmark 脚本有密钥环境变量读取逻辑，但测试中已有 redaction 检查，这是正向信号。

## 5. UI/产品体验风险

当前项目没有明显前端 UI 应用，产品形态主要是：

- 文档产品
- API 网关
- CLI runner
- 数据字典文件接口

体验风险：

- 对新用户入口偏多：`gateway_server.py`、`minimal_gateway_server.py`、`runner.py`、`reference_agent_adapter.py`、多个 quickstart 和 delivery plan，容易不知道该从哪条路径开始。
- README 很长，适合技术评审，但不适合首次接入者快速判断“我该运行哪三个命令”。
- 没有 OpenAPI 示例导出或 Postman/HTTPie collection。
- 错误响应结构已有雏形，但需要统一错误码文档。
- 大字典数据目前更像本地数据包，没有查询 UI 或稳定 CLI。

## 6. 与“一字诀 AgentOS / 大字典”目标的匹配度

### 一字诀 AgentOS 匹配度：较高，但仍是 MVP 到 Beta 之间

匹配点：

- “一个字加载一套专业运行逻辑”的核心理念已经代码化。
- 8 根字 Kernel Policy 已落地。
- gateway request rewrite、tool filtering、halt、preflight、audit、FSM 都已存在。
- 文档、schema、测试能支撑研究展示和早期集成。

缺口：

- 真实 AgentOS 的核心是“模型规划 -> 工具执行 -> 证据回传 -> 状态迁移 -> 再规划”的闭环。目前 runner 有执行器，gateway 有规训，但两者尚未完全合并成强制物理闭环。
- 当前 tool guard 更像策略层和检测层，不是不可绕过的执行沙箱。
- 上游模型、客户端 Agent、工具执行器之间的协议边界仍需产品化。

### 大字典匹配度：中高，但数据治理还需加强

匹配点：

- 500 字基础层、lookup、manifest、录入标准、复核标签已经形成数据产品雏形。
- 明确“非逐字引用”的版权表达。
- 数据字段支持字形、字义、音韵、现代释义、复核状态。

缺口：

- 历史层仍有大量 pending/review 语义。
- 多版本 lifecycle 文件并存，用户难以识别权威版本。
- 缺少数据构建脚本、校验报告、变更日志、质量指标面板。

## 7. 最优先的 10 条改进建议

1. **建立正式 Python 包与依赖锁定**  
   增加 `pyproject.toml`，拆分 `dev/test/gateway/benchmark` extras，生成锁文件或 hash-pinned requirements。

2. **把 gateway、runner、tool executor 合成强制闭环**  
   确保所有模型 tool call 必须经过 `/preflight-tool` 和 `execute_registered_tool`，执行结果必须写 audit，再进入下一轮模型。

3. **默认保护所有控制面接口**  
   `/preflight-tool`、`/resolve`、`/protocol`、`/ready` 至少区分 public/private 模式；生产默认要求 token。

4. **升级命令安全模型**  
   从字符串 marker 改为命令 allowlist + shell 禁用 + AST/argv 级解析；本地执行默认禁用，验证默认 Docker 或 sandbox。

5. **拆分 `gateway_server.py`**  
   建议拆成 `auth.py`、`routes.py`、`upstream_openai.py`、`upstream_anthropic.py`、`readiness.py`、`stream_guard.py`，降低单文件复杂度。

6. **统一状态文档，修正文档漂移**  
   以代码为准更新 `docs/project-status.md`，明确 `/v1/yizijue/run` 已存在，但真实多轮 LLM-tool 闭环仍未完整生产化。

7. **补充 CI 基线**  
   固定运行：unit tests、compileall、schema validate、json.tool、coverage、security scan、Docker build smoke。

8. **为大字典建立数据构建与质量报告**  
   提供 `make data-validate`、lookup 重建脚本、数据差异报告、review queue 统计、权威 latest 指针。

9. **增加协议级 stream parser 测试**  
   对 OpenAI/Anthropic SSE chunk 做结构化解析，不只靠字符串 signature；增加变形 tool use、跨 chunk、unicode escape 测试。

10. **补齐产品接入层**  
   输出 OpenAPI 文档、curl 示例集合、最小 CLI、错误码表、生产部署模板、环境变量 `.env.example`。

## 8. 多维评分表

| 维度 | 分数 | 评估 |
| --- | ---: | --- |
| 架构 | 78 | 核心抽象完整，AgentOS 思路清晰，但闭环执行和模块拆分还未成熟 |
| 代码质量 | 72 | 可读性尚好，测试较多，但包结构、类型检查、职责拆分不足 |
| 测试 | 76 | 测试文件多，覆盖面广；本次未执行，且真实集成/安全绕过测试不足 |
| 文档 | 82 | 文档丰富，解释力强；存在状态漂移和入口过多问题 |
| 可运行性 | 64 | 有 Makefile、Dockerfile、runner、quickstart；缺少锁文件和正式包元数据 |
| 安全 | 68 | 有 token、workspace、guard、Docker 沙箱雏形；默认保护和命令安全仍不足 |
| 产品完成度 | 61 | MVP 可展示，API/CLI 可用；生产接入、错误码、部署、UI/查询体验不足 |
| 商业/研究价值 | 84 | “字驱动 Agent 规训”有差异化，数据资产也有价值；需证明真实效率和安全收益 |

**综合评分：73 / 100**

## 9. 实际检查过的文件或目录证据

实际列目录/读取过的主要证据包括：

- `README.md`
- `Makefile`
- `Dockerfile.gateway`
- `requirements-gateway.txt`
- `pytest.ini`
- `agent_skill_dictionary/gateway_server.py`
- `agent_skill_dictionary/gateway_core.py`
- `agent_skill_dictionary/kernel_policy.py`
- `agent_skill_dictionary/tool_guard.py`
- `agent_skill_dictionary/tool_executor_registry.py`
- `agent_skill_dictionary/one_word_agent.py`
- `agent_skill_dictionary/runner.py`
- `agent_skill_dictionary/executor.py`
- `agent_skill_dictionary/patch_executor.py`
- `agent_skill_dictionary/guard_executor.py`
- `agent_skill_dictionary/validator.py`
- `agent_skill_dictionary/loader.py`
- `agent_skill_dictionary/oneword_dict.json`
- `agent_skill_dictionary/programming-agent-skill-dictionary.json`
- `agent_skill_dictionary/guard_policy.json`
- `agent_skill_dictionary/workflows/`
- `data/agent-dictionary-manifest.json`
- `data/DATA_ENTRY_STANDARD.md`
- `data/AGENT_DICTIONARY_API.md`
- `data/xinhua-base-entries.json`
- `data/xinhua-base-lookup.json`
- `data/xinhua-base-entries.csv`
- `schemas/agent-skill-dictionary.schema.json`
- `schemas/guard-policy.schema.json`
- `docs/architecture.md`
- `docs/project-status.md`
- `docs/development.md`
- `docs/yizijue-gateway-quickstart.md`
- `docs/oneword-agentos-v1-kernel-manual.md`
- `docs/delivery-test-plan.md`
- `tests/test_gateway_server_routes.py`
- `tests/test_runner.py`
- `tests/test_gateway_auth.py`
- `tests/test_gateway_core.py`
- `tests/test_tool_guard.py`
- `tests/test_kernel_policy.py`
- `tests/test_one_word_agent.py`
- `scripts/smoke_test.py`
- `scripts/http_gateway_smoke.py`
- `scripts/real_model_ab_benchmark.py`
- `scripts/live_agent_benchmark.py`
- `reports/complex-task-ab-summary.md`
- `reports/live-agent-benchmark-secure-b2b-ledger.md`

本次严格按约束未修改文件、未安装依赖、未联网、未运行测试或项目命令。