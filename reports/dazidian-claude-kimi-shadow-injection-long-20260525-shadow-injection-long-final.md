**Agent Skill Dictionary 项目综合工程审计报告**

---

## 1. 项目定位、核心目标与成熟度判断

**项目定位**：Agent Skill Dictionary（ASD）是一个基于"一字诀"（单字符指令）的 AI Agent 行为控制与编排框架，旨在通过八卦状态机（Bagua State Machine）实现细粒度的权限隔离、工作流编排和上下文管理。该项目试图建立一种类似"符咒系统"的 Agent 控制协议，将复杂的多步骤任务压缩为单字 Opcode（如"查"、"评"、"修"等），并通过六十四卦的二进制爻象（101 等）映射到具体的权限向量。

**核心目标**：
- 建立标准化的 Agent 技能字典与协议契约（`build_agent_protocol_manifest`）
- 实现基于单字网关的状态机路由（`inspect_repo_map_mount`）
- 提供上下文压缩与 Path Preflight 安全校验
- 支持审计追踪（`audit.py`）和受控补丁执行（`apply_controlled_patch`）

**成熟度判断**：当前处于**Alpha 阶段（概念验证期）**。证据显示核心协议文件（`agent_protocol.py`）已定义根 Opcode 契约（第 113 行 `_root_opcode_contracts`）和排序键（第 135 行 `_root_sort_key`），但存在明显的工程缺口：测试覆盖不足（未在证据中看到测试目录）、安全硬门依赖人工审查（`tdd_scanner`提示测试不足）、且关键执行路径（`executor.py`第 80 行）直接使用 `subprocess.run` 而未显示有沙箱隔离。

---

## 2. 目录结构与核心模块分层

根据提供的文件树，项目呈现**扁平化分层**，未遵循标准 Python 包结构（缺少明显的 `tests/`、`docs/` 目录）：

**核心协议层（L0）**：
- `agent_protocol.py`：定义八卦状态机、Opcode 契约、根排序键。第 9 行的 `build_agent_protocol_manifest` 是协议入口，第 113 行的 `_root_opcode_contracts` 定义权限合约。

**网关与编排层（L1）**：
- `cli.py`：命令行入口，承担一字诀解析与初始路由。
- `context_breaker.py`：上下文压缩与分割逻辑，负责 Token 经济性管理。

**执行与审计层（L2）**：
- `executor.py`：**高风险模块**。第 5 行导入 `subprocess`，第 80 行执行 `subprocess.run`，第 91 行处理超时异常。这是本地 Runtime 越权的主要风险点。
- `audit.py`：审计日志记录，但证据中未显示其是否具备防篡改能力。
- `patch_executor.py`（通过导入推断存在）：提供 `apply_controlled_patch`，用于受控代码修改。
- `prompt_executor.py`（通过导入推断存在）：提供 `create_confirmation_ticket`，用于人工确认。

**初始化与挂载层（L3）**：
- `__init__.py`：第 10-11 行显示依赖 `patch_executor` 和 `prompt_executor`，挂载名为 `inspect_repo_map_mount`。

---

## 3. 网关、八卦状态机、工具守卫、上下文压缩、Path Preflight 的协作链路

**协作链路分析**（基于符号命名与导入关系推断）：

**Step 1 - 一字诀网关解析**：
用户输入单字符指令（如"评"）→ `cli.py` 解析 → 映射到八卦二进制爻象（如 101-INSPECT）→ 激活 `agent_protocol.py` 中的状态机。

**Step 2 - 八卦状态机路由**：
`agent_protocol.py` 第 113 行 `_root_opcode_contracts` 根据爻象（101）确定权限向量：
- `model_forward`: allowed
- `source_write`: forbidden
- `tool_execution`: read_only

**Step 3 - Path Preflight 校验**（推断存在，但未在证据中直接确认）：
在状态转移前，应检查目标路径是否在允许列表内。证据中 `inspect_repo_map_mount` 提及"硬门：禁止写入"，暗示存在 Preflight 检查。

**Step 4 - 上下文压缩**：
`context_breaker.py` 介入，执行"六十四卦"压缩策略：
- 生成 `compressed_directory_tree`
- 提取 `symbol_map`（符号地图）
- 限制 `target_file_line_refs` 只加载必要行号

**Step 5 - 工具守卫执行**：
- 若状态为 `read_only`：锁定工具权限为 `native_inspect_card`, `read_file` 等只读工具。
- 若涉及 `write_file` 或 `edit_file`：触发 `prompt_executor` 的 `create_confirmation_ticket` 人工确认。
- 危险操作（如 `subprocess.run`）：由 `audit.py` 记录，但证据显示 `executor.py` 第 80 行仍可直接执行。

**Step 6 - 审计与回退**：
根据证据中提及的"失败回退"策略：当置信度低于 0.75 时，回退到"查"状态；最大重试超限时触发 `MELT_DOWN_TO_查`。

**链路缺陷**：`executor.py` 的 `subprocess` 调用似乎位于工具守卫之外（或守卫逻辑未在提供的符号中体现），存在"守卫绕过"风险。

---

## 4. 测试覆盖与质量门禁评估

**关键缺口识别**：

**缺口 A：单元测试缺失**
证据中未显示 `tests/` 目录或测试文件，且 `tdd_scanner` 标记暗示测试驱动扫描不足。核心函数如 `_root_opcode_contracts`（第 113 行）、`build_agent_protocol_manifest`（第 9 行）缺乏可见的单元测试覆盖。

**缺口 B：集成测试缺失**
涉及 `subprocess.run`（第 80 行）的 `executor.py` 需要沙箱集成测试，但证据中无相关测试路径。

**缺口 C：状态机边界测试缺失**
八卦状态机（101, 010 等爻象）的转移矩阵未显示有自动化验证，存在状态转移死锁或未定义行为的风险。

**缺口 D：安全测试缺失**
针对 `apply_controlled_patch`（第 10 行导入）的对抗性测试（adversarial testing）未在证据中体现，补丁注入攻击向量未得到验证。

**质量门禁现状**：依赖人工审查（"硬门规则"），缺乏自动化 CI/CD 门禁。证据中提及的 " acceptable_evidence" 包含 `review_reference_hash`，但未显示自动化校验流程。

---

## 5. 安全、密钥、供应链、本地 Runtime 越权风险评估

**高风险项**：

**风险 S1：本地 Runtime 越权（Critical）**
- **位置**：`executor.py` 第 80 行 `subprocess.run`
- **证据**：第 5 行导入 `subprocess`，第 91 行捕获 `TimeoutExpired` 异常。
- **分析**：该执行点若未严格隔离，可导致任意代码执行（ACE）。虽然 `audit.py` 存在，但审计日志无法阻止首次攻击。

**风险 S2：补丁执行链注入（High）**
- **位置**：`__init__.py` 第 10 行 `apply_controlled_patch`
- **分析**：动态补丁应用是供应链攻击的高危面。证据未显示补丁签名验证或来源校验。

**风险 S3：上下文泄露（Medium）**
- **位置**：`context_breaker.py`（推断）
- **分析**：上下文压缩可能将敏感信息（如 `prompt_executor` 的 `confirmation_ticket`）意外保留在日志中。

**风险 S4：密钥管理（未确认）**
证据中未明确显示密钥管理文件（如 `.env`, `secrets.py`），但 `agent_protocol.py` 的契约系统可能涉及 API Key 权限划分。若 `executor.py` 的 `subprocess` 继承环境变量，存在密钥泄露风险。

**风险 S5：供应链污染（Medium）**
依赖 `patch_executor` 和 `prompt_executor`（第 10-11 行导入），但未显示这些模块的版本锁定或哈希校验。

---

## 6. 性能与 Token 经济性分析

**Token 消耗热点**：

**热点 T1：符号地图生成（高消耗）**
- **位置**：`inspect_repo_map_mount`
- **分析**：生成完整仓库的 `symbol_map` 和 `compressed_directory_tree` 需要一次性读取大量文件，在大型仓库中可能消耗 10k+ Token。

**已压缩点**：

**优化 C1：最小上下文规范**
证据显示系统采用"最小上下文规范"，仅加载 `target_files_list` 和 `line_refs`，而非完整文件。

**优化 C2：行号精准引用**
通过 `target_file_line_refs` 仅引用必要行号（如 `agent_protocol.py:113:def _root_opcode_contracts`），减少冗余代码块。

**优化 C3：六十四卦状态压缩**
将复杂权限向量（read/write/execute/network）压缩为 3 位二进制爻象（如 101），减少状态描述所需的 Token。

**瓶颈**：`executor.py` 的 `subprocess` 输出（第 80 行）若未限制长度，可能产生大量 stdout/stderr Token，突破上下文窗口。

---

## 7. 生产化落地风险

**风险 P1：Claude Code / Codex / Aider 兼容性**
项目设计针对特定 Agent 架构（"一字诀"），与主流工具（Claude Code、Codex CLI、Aider）的接口不兼容。证据中 `agent_protocol.py` 的 `_root_sort_key` 可能是为了排序兼容性，但未确认。

**风险 P2：配置管理缺失**
未在证据中看到 `config.py` 或 YAML/JSON 配置文件，所有配置似乎硬编码在 Python 文件中（如第 113 行的契约定义），不利于生产环境动态调整。

**风险 P3：可观测性不足**
`audit.py` 存在但证据未显示其输出格式（是否结构化日志？是否支持 OTLP？）。缺乏分布式追踪能力。

**风险 P4：单点故障**
`executor.py` 的 `subprocess` 调用若阻塞（第 91 行仅处理 Timeout），可能导致整个 Agent 实例僵死。

**风险 P5：权限模型过于复杂**
八卦状态机（64 种状态）在实际生产中难以调试，运维人员难以理解 "101-INSPECT" 与 "010-EDIT" 的区别。

---

## 8. 按优先级排序的 12 条改进路线图

**P0 - 关键安全（立即执行）**：

1. **沙箱化 Subprocess 执行**
   - **收益**：消除本地 Runtime 越权风险（S1）。
   - **风险**：可能破坏现有依赖 shell 命令的功能。
   - **验证**：在 Docker 无特权模式下运行 `executor.py` 测试套件。

2. **补丁签名验证**
   - **收益**：阻断供应链注入（S2）。
   - **风险**：增加首次补丁应用的延迟（需验签）。
   - **验证**：尝试应用未签名补丁，验证是否被 `apply_controlled_patch` 拒绝。

**P1 - 核心工程（1-2 周）**：

3. **建立测试金字塔**
   - **收益**：填补缺口 A/B，提升交付信心。
   - **风险**：初期降低开发速度。
   - **验证**：达到 80% 行覆盖率（特别是 `agent_protocol.py` 第 113 行和第 135 行）。

4. **状态机形式化验证**
   - **收益**：消除状态死锁（缺口 C）。
   - **风险**：形式化方法学习曲线陡峭。
   - **验证**：使用 TLA+ 或 Python 的 `hypothesis` 状态机测试验证所有 64 状态转移。

5. **Token 预算硬限制**
   - **收益**：防止 `subprocess` 输出淹没上下文（瓶颈 T1）。
   - **风险**：截断关键错误信息。
   - **验证**：模拟输出 100MB 日志，验证是否被压缩/截断至 4k Token。

**P2 - 架构优化（1 个月）**：

6. **配置外部化**
   - **收益**：解决生产化风险 P2，支持多环境部署。
   - **风险**：配置文件注入攻击需额外校验。
   - **验证**：通过环境变量覆盖 `agent_protocol.py` 的契约定义。

7. **增加 OpenTelemetry 追踪**
   - **收益**：解决可观测性不足（P3），追踪"一字诀"完整链路。
   - **风险**：增加约 5-10% 性能开销。
   - **验证**：在 Jaeger 中查看从"评"到 `executor.py` 第 80 行的完整调用链。

8. **兼容层开发（Claude Code Adapter）**
   - **收益**：降低落地风险 P1，接入主流生态。
   - **风险**：维护成本增加。
   - **验证**：在 Claude Code 中执行"查"指令，验证是否正确映射到 INSPECT 状态。

**P3 - 质量提升（2-3 个月）**：

9. **对抗性测试套件（Red Team）**
   - **收益**：验证上下文压缩不会泄露敏感信息（S3）。
   - **风险**：发现大量潜在漏洞，需持续修复。
   - **验证**：构造恶意 Prompt 尝试诱导 `context_breaker` 泄露 `confirmation_ticket`。

10. **权限模型简化**
    - **收益**：降低运维复杂度（P5），将 64 状态压缩为 8-16 个实用状态。
    - **风险**：破坏向后兼容性。
    - **验证**：运维人员无需查阅文档即可理解状态含义。

11. **异步执行改造**
    - **收益**：消除单点阻塞（P4），`subprocess` 改为异步。
    - **风险**：引入并发竞争条件。
    - **验证**：同时执行 100 个"查"指令，系统无僵死。

12. **供应链 SBOM 生成**
    - **收益**：应对 S5，生成软件物料清单。
    - **风险**：构建流程复杂度增加。
    - **验证**：`pip install` 前验证所有依赖哈希。

---

## 9. 多维评分表（0-100）

| 维度 | 评分 | 说明 |
|------|------|------|
| **代码质量** | 55 | 结构清晰但缺乏测试，关键路径（subprocess）硬编码。 |
| **安全性** | 35 | 存在 Critical 级 Runtime 越权风险，缺乏补丁签名。 |
| **架构设计** | 70 | 八卦状态机创新但过度复杂，模块分层合理。 |
| **测试覆盖** | 20 | 明显缺失，依赖人工审查（tdd_scanner 提示）。 |
| **性能效率** | 65 | Token 压缩机制良好，但 subprocess 可能阻塞。 |
| **生产就绪** | 30 | 缺乏配置管理、可观测性和兼容性层。 |
| **文档完整** | 50 | 有 README 和符号地图，但缺乏架构决策记录（ADR）。 |
| **供应链安全** | 40 | 动态补丁执行风险高，缺乏 SBOM。 |
| **Token 经济性** | 75 | 最小上下文规范和行号引用是亮点。 |
| **可维护性** | 45 | 单字 Opcode 简洁但调试困难，状态机晦涩。 |
| **综合评分** | **48.5** | **处于 Alpha 阶段，需重大工程投入方可生产化。** |

---

## 10. 文件/目录证据清单

**直接证据**（系统物理读取确认）：
- `README.md`：项目入口文档。
- `agent_skill_dictionary/__init__.py`：第 10 行 `from patch_executor import apply_controlled_patch`，第 11 行 `from prompt_executor import create_confirmation_ticket`。
- `agent_skill_dictionary/agent_protocol.py`：第 9 行 `def build_agent_protocol_manifest`，第 113 行 `def _root_opcode_contracts`，第 135 行 `def _root_sort_key`。
- `agent_skill_dictionary/audit.py`：审计模块存在。
- `agent_skill_dictionary/cli.py`：命令行接口。
- `agent_skill_dictionary/context_breaker.py`：上下文压缩模块。
- `agent_skill_dictionary/executor.py`：**第 5 行 `import subprocess`，第 80 行 `completed = subprocess.run(...)`，第 91 行 `except subprocess.TimeoutExpired`**。

**推断证据**（基于命名与导入关系）：
- `patch_executor.py`：由 `__init__.py` 第 10 行导入，提供受控补丁功能。
- `prompt_executor.py`：由 `__init__.py` 第 11 行导入，提供确认票据功能。
- `tdd_scanner`：由风险上下文提及，暗示测试扫描工具存在。

**缺失证据**（未在 Inspect Context 中确认，报告中已标注）：
- 测试目录（`tests/`）
- 配置文件（`config.py`, `settings.yaml`）
- 依赖锁定文件（`requirements.txt`, `poetry.lock`）
- CI/CD 配置（`.github/workflows/`）

---

**审计结论**：Agent Skill Dictionary 是一个具有创新架构（一字诀网关、八卦状态机）但工程化不足的框架。其核心风险集中在 `executor.py` 的未沙箱化 `subprocess` 调用和缺失的测试覆盖。建议立即执行 P0 级安全修复，并在完成状态机形式化验证（改进项 4）和测试覆盖（改进项 3）前，**禁止用于生产环境处理不可信输入**。