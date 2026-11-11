# OneCode — Industrial High-Assurance Autonomous Agent Kernel
### 工业制造与生产级高安全自主智能体内核

OneCode is a production-grade autonomous coding and control agent kernel built for **industrial automation, factory execution, continuous process control, and mission-critical infrastructure**, engineered for strict safety enforcement, tamper resistance, and low token overhead.

OneCode 是专为**工业制造、自动化车间、连续流程控制与关键基础设施**打造的高安全、防篡改、极低 Token 消耗的生产级自主智能体内核（Autonomous Agent Kernel）。

Unlike agents that rely on an LLM's self-reported completion, OneCode constrains model inference within a **Deterministic Cybernetic Finite-State Automaton** and a **Kernel-Isolated Dual-Gatekeeper Verifier**, eliminating false delivery claims and unauthorized disk writes at the systems level.

不同于依赖大模型自我评判的传统编码 Agent，OneCode 将模型推理严格收敛在**确定性控制论状态机**与**内核态双门禁校验器**之内，从系统工程层面根除“未通过验证即交付”的幻觉以及命令行越权写盘隐患。

---

## Core Capabilities / 核心工业级特性

```
+----------------------------------------------------------------------------------------------------+
|                                    OneCode Industrial Kernel                                      |
+------------------------------------+----------------------------------+----------------------------+
| 1. Mission-Critical Safety         | 2. 80%+ Token Reduction          | 3. Gateway Jitter Resilience|
| - Kernel-isolated Verifier gate    | - Compact shell_projection diff  | - Native SSE chunked stream|
| - Anti-Tamper shell firewall       | - Prevents multi-turn context    | - Immune to HTTP 524 origin|
| - Blocks unverified code delivery  |   prompt explosion               |   gateway timeouts         |
|                                    | - 81.1% saved in trilogy runs    | - Full-jitter exponential  |
| 1. 工业级最高生产安全保障          | 2. 80%+ 颠覆性 Token 节省        |   backoff & checkpoint     |
| - 内核态独立 Verifier 测试门禁     | - 紧凑 Shell 状态差分投影        | 3. 工控网关与网络抖动容灾  |
| - 反越权防篡改命令行拦截           | - 杜绝多轮上下文原始暴涨         | - 原生 SSE 流式分块传输    |
| - 物理阻断未通过测试的代码交付     | - 工业三部曲基准实测节省 81.1%   | - 免疫 524 超时与断线重连  |
+------------------------------------+----------------------------------+----------------------------+
```

### 1. Mission-Critical Production Safety / 工业级最高生产安全保障
- **Kernel-Isolated Dual-Gatekeeper Verifier**: Prevents finish hallucinations. Regardless of what the model claims in prose, OneCode only marks a run `deliverable` when the isolated test suite executes and exits with `exit_code == 0`. Otherwise delivery is blocked (`delivery_status: blocked`).  
  **内核态双门禁校验器**：彻底杜绝虚假完成幻觉。无论模型文本如何声称已完成修复，只有在隔离沙箱中真实执行验证套件且返回 `exit_code == 0` 时才签发 `deliverable`；失败则强制判定 `delivery_status: blocked`，阻断缺陷代码交付。
- **Anti-Tamper & Sovereign Boundary Protection**: Blocks shell workarounds such as inline `python -c "open('src.py', 'w')..."` bypasses (`preset_test_immutable` / `sovereignty_fire_boundary_halt`), enforces audited `patch`/`write_file` transitions, and records a tamper-evident SHA-256 log (`evidence-chain.jsonl`).  
  **反越权防篡改保护**：实时拦截命令行旁路篡改与越界写盘，强制全部文件变更经受审计的 `patch` / `write_file` 动作通道，并持续落盘 SHA-256 不可篡改审计链（`evidence-chain.jsonl`）。

### 2. Token Reduction & Compact Context Projection / 颠覆性 Token 节省与紧凑投影
- **Structured Shell State Projection (`shell_projection`)**: Instead of appending raw file dumps and full terminal logs every turn, OneCode projects minimal structured deltas and failure evidence across turns.  
  **紧凑状态差分投影（`shell_projection`）**：用结构化差分与最小必要失败证据替代逐轮拼接海量全文，避免多轮对话上下文雪球式爆炸。
- **Industrial Trilogy Benchmark (OneCode vs Claude Code v2.1.150, Intel N100 4C4T, DeepSeek-V4.1-Flash, 78 tests)**:  
  **工业生产三部曲实测对比（同硬件与同一 DeepSeek-V4.1-Flash 底座，共 78 项测试）**：
  - **Discrete Manufacturing (Option A — PackML / OEE)**: Claude `899k` vs **OneCode `133k` Tokens (`-85.2%`)**  
    离散智能制造（PackML / OEE）：Claude 89.9 万 Tokens vs **OneCode 13.3 万 Tokens（节省 85.2%）**
  - **Continuous Process Safety (Option B — TEP / ISA PID / SIL-2)**: Claude `705k` vs **OneCode `157k` Tokens (`-77.8%`)**  
    连续流程安全（TEP 化工 / ISA PID / SIL-2）：Claude 70.5 万 Tokens vs **OneCode 15.7 万 Tokens（节省 77.8%）**
  - **Industrial IoT Gateway (Option C — Modbus TCP / Deadband / SDT)**: Claude `494k` vs **OneCode `108k` Tokens (`-78.2%`)**  
    工业物联网网关（Modbus TCP / 死区与旋转门压缩）：Claude 49.4 万 Tokens vs **OneCode 10.8 万 Tokens（节省 78.2%）**
  - **Total Across Trilogy / 三部曲总计**: `2,097,072` vs **`397,258` Tokens (`-81.1%` / `1,699,814` saved)**, `78/78 (100.0%)` under baseline runs.

- **Empirical Scope & Re-Verification Boundaries / 客观适用边界与复验说明**:
  - The 78%–85% savings above were measured in controlled workspaces on single-module or well-scoped specifications (`Option A`, `Option B Tasks 1–3`, `Option C Tasks 1–3`).  
    上述 78%–85% 节省数据是在受控工作区、单模块及边界清晰的中等复杂度任务下测得。
  - On tightly coupled multi-module integration (`Option B Task 4` and `Option C Task 4: ModbusEdgeTelemetryGateway`), baseline green completion required multi-round tuning/retries. In clean unassisted post-fix re-tests (`--max-turns 25`, `DeepSeek-V4.1-Flash`), `terminal` hit `turn_limit_exhausted` at 25 turns (`63,163` tokens, no `edge_gateway.py` written), and `phased_terminal` hit `turn_limit_exhausted` after `5+20` turns (`97,752` tokens, incomplete `edge_gateway.py`). Thus OneCode achieves high efficiency on scoped modules, while unassisted single-shot integration on large multi-file systems remains bounded by compact-model working memory.  
    在强耦合跨模块集成任务（`Option B Task 4`、`Option C Task 4: ModbusEdgeTelemetryGateway`）的历史全绿记录中曾依赖多轮调优与重试；内核补丁后在洁净工作区进行无提示单次复验（`--max-turns 25`、`DeepSeek-V4.1-Flash`），`terminal` 模式 25 轮消耗 `63,163` Tokens 后触发 `turn_limit_exhausted`（未写入 `edge_gateway.py`），`phased_terminal` 模式在 `5+20` 轮消耗 `97,752` Tokens 后仅在末轮生成不完整实现。因此 OneCode 在单模块交付上具备稳定高性价比，而无提示大型跨文件一次通关率仍受限于小参数模型跨轮工作记忆窗口。

### 3. Industrial Gateway & Network Jitter Resilience / 工控网关与网络抖动容灾
- **Native SSE Chunked Streaming (`ONECODE_STREAM_CHAT=1`)**: Prevents 30s/100s origin proxy timeouts (such as HTTP 524 behind CDNs or industrial gateways) during long model reasoning turns.  
  **原生 SSE 流式引擎**：有效避免长程推理请求被前置网关或 CDN（如 HTTP 524 Origin Time-out）强行中断。
- **Exponential Backoff with Full Jitter & Checkpoint Resume**: Handles transient NIC/gateway resets with stateful resume (`--resume-from`) so intermediate artifacts are preserved without redundant rewrites.  
  **全抖动指数退避与断点续传**：内置容错重试状态机并结合断点续传（`--resume-from`），降低弱网丢包导致的进度丢失。

### 4. Supported Industrial Domains & Standards / 覆盖的工业场景与规范
- **Discrete Manufacturing / 离散制造**：OMAC PackML (`ISA-TR88.00.02`) 17-state machine, TPM OEE (`ISO 22400` / `SEMI E10`), MTBF/MTTR KPIs.
- **Process Safety / 化工流程安全**：Tennessee Eastman Process (TEP) ODEs, Arrhenius thermal balance, ISA PID Bumpless Transfer & Anti-Windup, `ANSI/ISA-18.2` alarm management, `IEC 61511` SIL-2 SIF/ESD.
- **IIoT Edge Telemetry / 工业物联网采集**：Modbus TCP (MBAP/PDU), multi-order IEEE-754 floats (`ABCD`/`CDAB`/`BADC`/`DCBA`), concurrent 4-area register maps, absolute/percentage deadband & Swinging Door Trending (SDT).

---

## Application Scenarios & Roadmap / 适用场景与后续演进

OneCode is positioned as a **high-assurance engineering and controlled-delivery agent kernel for industrial & production environments** (generating, patching, verifying, and auditing code/configs under deterministic gates), rather than replacing on-line hardware controllers for millisecond-level hard real-time execution.  
OneCode 定位于**工业与生产环境下的高安全工程开发与受控交付内核**（在确定性门禁下完成代码/配置生成、修复、沙箱验证与审计留痕），而非直接替代现场 PLC/DCS 硬件承担毫秒级硬实时在线控制。

### Ready for Controlled Production Workflows / 当前已可直接胜任的场景
- **Module-Level Industrial & IIoT Engineering (`--verifier` gated) / 工业与物联网模块级研发与修复**：  
  Well-scoped discrete-manufacturing logic (PackML / OEE), continuous process & safety simulation modules (TEP / ISA PID / SIL-2 logic), and edge gateway protocol/codec modules (Modbus TCP, deadband, SDT), delivering strict test-backed acceptance (`exit_code == 0`) with 78%–85% token savings.  
  边界清晰的离散制造逻辑（PackML / OEE）、流程安全算法仿真（TEP / ISA PID / SIL-2 逻辑）以及边缘网关编解码/死区压缩模块，在配齐测试门禁后可强制验证通过才准予交付，同时实现 78%–85% Token 节流。
- **High-Audit, Tamper-Resistant Engineering & DevOps / 高审计、防篡改的受控研发与变更运维**：  
  FinTech risk components, distributed middleware, and infrastructure scripts running inside Docker isolation (`--network none`, `--cap-drop ALL`, `--pids-limit`, `resource_budget_exceeded`), producing immutable SHA-256 `evidence-chain.jsonl`, `manifest.json`, and `ledger.json` with `--rollback-on-failure` and `--resume-from`.  
  适用于金融风控、分布式中间件及关键运维变更脚本；配合 Docker 隔离沙箱、写盘与耗时预算拦截及防篡改哈希链，实现每次变更可审计、失败可回滚、中断可续传。
- **Low-Resource Edge Nodes & Unstable Gateways / 低算力边缘节点与弱网/网关代理环境**：  
  Zero third-party kernel dependencies suit compact edge servers (e.g., Intel N100 class), while native SSE chunked streaming (`ONECODE_STREAM_CHAT=1`) and full-jitter exponential backoff mitigate gateway 524 timeouts and transient link jitter.  
  纯 Python 核心零第三方运行时依赖，适应轻量工控节点；原生 SSE 流式引擎与全抖动指数退避有效抵御跨网关 524 超时与链路抖动。
- **Internal Workbench & Web Shell Backend / 企业内部平台与前端工作台执行后端**：  
  Embeddable via `onecode serve` (OpenAI-compatible bridge with constant-time token auth for LibreChat / Open-WebUI) or `onecode tui`.  
  可通过 `onecode serve`（恒定时间 Token 鉴权的 OpenAI 兼容网关）或 `onecode tui` 接入企业现有研发门户与自动化流水线。

### Under Active Development (Roadmap) / 后续陆续完善与演进方向
- **Unassisted Single-Shot Refactoring Across Large Multi-Module Systems / 超大型跨模块系统的无提示端到端自主通关**：  
  As shown in clean `Task 4` (`ModbusEdgeTelemetryGateway`) re-verification, tightly coupled multi-file synthesis without external task decomposition remains constrained by compact-model cross-turn working memory. Ongoing development targets structured multi-file symbol anchoring, stronger staged planning, and higher single-shot convergence across complex architectures (currently recommended: decompose via `run-plan` + per-module verifier policies + `approvals`).  
  正如洁净 `Task 4`（`ModbusEdgeTelemetryGateway`）复测所展现的边界，强耦合多文件在无拆解提示下的单次端到端生成仍受限于轻量模型跨轮工作记忆；后续将持续完善跨模块符号锚点记忆、多阶段自动规划拆解与复杂系统收敛能力（当前生产建议采用 `run-plan` 分模块规划 + `approvals` 审批）。
- **Broader Production Sandbox Hardening & Industrial Commissioning Integrations / 更深层的生产环境加固与现场投产闭环集成**：  
  Deterministic hard real-time PLC/DCS execution remains outside the LLM agent runtime scope; OneCode generates and verifies engineering artifacts offline before human sign-off and bench commissioning, while broader `deployment_boundary` hardening, additional industrial protocol presets, and enterprise governance integrations continue to roll out in subsequent releases.  
  现场产线毫秒级硬实时闭环仍属于专业实时控制系统职责，OneCode 负责上线前的开发、离线回归验证与审计签发；更完善的 `deployment_boundary` 生产加固工具链、更多工业协议校验预设与企业治理集成正在后续版本中陆续完善开发中。

---

## Cybernetic State Machine & Formal Rules / 底层运行规则与数学模型

OneCode formalizes execution governance as a **Deterministic Finite-State Automaton**, avoiding unexplainable heuristic black boxes.  
OneCode 将调度治理形式化为**确定性控制论有限状态自动机**，避免不可解释的启发式黑盒控制。

### 1. 64-State Boolean Hypercube Automaton ($Q_6$) / 64 状态超立方体自动机
System state is spanned by a 6-bit boolean vector:  
系统运行状态由 6-bit 布尔向量严格张成：
$$s = (b_5, b_4, b_3, b_2, b_1, b_0) \in \{0, 1\}^6 \cong \mathbb{Z}_{64}$$
- **Outer Phase Vector ($\phi_{\text{out}} = (b_5, b_4, b_3)$)**: Contract rules, sandbox constraints, and scheduling context. （外部规则契约与沙箱上下文相）
- **Inner Phase Vector ($\phi_{\text{in}} = (b_2, b_1, b_0)$)**: Physical file state, verifier outcomes, and tool execution telemetry. （内部文件资产与测试执行遥测相）

### 2. Lyapunov Energy Descent / 李雅普诺夫平衡熵收敛
To prevent unbounded retry oscillation, the kernel evaluates state energy $V(s)$ against the target fixed point $b^*$ (e.g. `63: 0b111111`):  
为保证多轮迭代收敛、杜绝死循环震荡，内核定义平衡能量泛函 $V(s)$ 并约束每步转移 $\mathcal{T}: S \times \mathcal{E} \to S$：
$$V(s) = \sum_{i=0}^5 |b_i - b_i^*|, \qquad \Delta V(s) = V(\mathcal{T}(s, e)) - V(s) \le 0$$
Irreversible safety violations jump deterministically to boundary halts (e.g. `40: sovereignty_fire_boundary_halt`).  
当发生不可逆越权故障时，系统直接跃迁至硬阻断边界态（如 `40: sovereignty_fire_boundary_halt`）。

### 3. 5-Phase Closed-Loop Transfer / 五相闭环反馈调度
$$\mathbf{S}_{k+1} = \mathbf{M}_{\text{transfer}} \cdot \mathbf{S}_k + \mathbf{B} \cdot e_{\text{evidence}}$$
- `accelerate` (Feedforward / 前馈加速) · `throttle` (Damping / 负反馈阻尼) · `continue` (Equilibrium / 稳态维持) · `cooldown` (Dissipation / 过载冷却) · `halt` (Sovereign stop / 边界熔断)

### 4. Dual-Gatekeeper Delivery Axiom / 工业双门禁交付公理
$$\text{Delivery}(R) \iff \text{AssetsComplete}(R) \land \big(\text{ExitCode}(\text{Verifier}) == 0\big) \land \text{HashMatch}(\text{Workspace}) \land \text{AuditedPatchOnly}(R)$$

### 5. Rule Closure Principle & Rule Discovery Protocol / 规则闭合原则与发现协议
- **Rule Closure Principle**: External engineering facts (`external facts are evidence, not law` — file existence, SHA-256 verification, path traversal checks, timeout errors) are sampled as physical evidence and collapsed strictly into the existing formal rule surface (`6-bit status_code`, yin-yang damping pressure, four-symbol windows, trigrams, five-element relational feedback matrices, and `IchingKernel.transition()`). Bug fixes must close inside that algebraic state surface without adding forbidden parallel control variables (`confidence_level`, `manual_priority`, `model_mood`, `retry_score`, or external policy flags).  
  **规则闭合原则**：外部工程事实仅作为物证输入（`external facts are evidence, not law`），必须收敛映射至统一的 `6-bit status_code`、双极阻尼压力与五相传递矩阵代数状态面，严禁引入平行的经验打分控制变量。
- **Rule Discovery Protocol**: `Bug reports are rule-gap probes`. When a task encounters an unmapped runtime failure or stalled state, the fix path adds a failing regression test, collapses the physical evidence into a `6-bit status_code` / balanced five-element feedback transition, or emits a deterministic `discover` boundary transition, verified via manifest, ledger, and checkpoint evidence.  
  **规则发现协议**：缺陷报告视为规则缺口探针；新增回归测试后将物证塌缩至确定性状态转移或 `discover` 边界，并由 manifest、账本与检查点共同校验闭环。

---

## Quick Start / 快速上手

### 1. Installation / 安装核心与可选界面
The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency.  
核心内核零第三方运行时依赖；Textual 为可选终端界面依赖：

```bash
# Core control kernel & CLI / 安装核心内核与命令行工具
pip install -e .

# Optional interactive terminal UI / 安装可选 Textual TUI
pip install -e .[tui]
```

### 2. Verification & Self-Audit / 全量验证与系统自审
```bash
# Core fast verification / 核心轻量验证门禁
bash scripts/verify-core.sh

# Full verification suite (tests, lint, typecheck) / 全量严格套件
bash scripts/verify.sh

# Local v0.7 verification workflow demo / 本地门禁演示工作流
bash scripts/demo_v07.sh

# Environment diagnostics & automaton math audit / 环境自检与状态机公理审计
PYTHONPATH=src python3 -m onecode doctor
PYTHONPATH=src python3 -m onecode.cli doctor
PYTHONPATH=src python3 -m onecode audit-self
PYTHONPATH=src python3 -m onecode math-audit
```
`doctor` runs isolated physical checks (`write_text`, `resume_skip`, `sovereignty_breach`, `http_timeout`), while `math-audit` performs read-only verification of the 64-state `transition graph`, attractor count, `Q6` closure, and Lyapunov bounds.  
`doctor` 会执行物理沙箱链路自检，`math-audit` 则校验 64 态转移图闭合性与李雅普诺夫边界。

---

## Production Modes & CLI / 生产模式与核心命令

### 1. Interactive TUI & Local OpenAI-Compatible Server / 交互式终端与本地网关
```bash
# Launch keyboard-driven Textual TUI / 启动交互式 TUI
onecode tui

# Launch loopback OpenAI-compatible HTTP gateway / 启动本地兼容网关 (/health, /v1/models, /v1/chat/completions)
ONECODE_API_TOKEN=<local-token> python3 -m onecode serve --host 127.0.0.1 --port 19080
```
TUI sessions persist transcripts to `.onecode/tui-transcript.txt` and last output to `.onecode/tui-last-output.txt` (export via `/export` or `/export-last`). The HTTP gateway enforces constant-time bearer-token authentication.  
TUI 自动将对话转录写入 `.onecode/tui-transcript.txt` 与 `.onecode/tui-last-output.txt`（支持 `/export`、`/export-last` 导出）；本地网关支持直接接入 LibreChat / Open-WebUI，采用恒定时间 Token 鉴权。

### 2. Verifier Policy, Bounded Runs & Ledger Audit / 策略门禁、断点续传与账本审计
```bash
# List presets and initialize workspace policy / 初始化工作区验证门禁策略
PYTHONPATH=src python3 -m onecode list-verifier-presets
PYTHONPATH=src python3 -m onecode init-verifier-policy --workspace ./my-project --preset python-unittest

# Single-step run & idempotent resume / 单步受控写入与幂等断点续传
PYTHONPATH=src python3 -m onecode run "write assets" \
  --workspace ./my-project --run-id demo-run \
  --write-text "src/app.py=value = 1\n" --max-write-bytes 5000000
PYTHONPATH=src python3 -m onecode run "resume asset" \
  --workspace ./my-project --run-id demo-resume --resume-from demo-run \
  --write-text "src/app.py=value = 1\n"

# Execute declarative plan with verifier policy / 运行受控规划与沙箱校验
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace ./my-project --run-id prod-task-01 --plan ./plan.json --verifier python-unittest

# Inspect run ledger & list runs / 审计运行账本与哈希链
PYTHONPATH=src python3 -m onecode inspect --workspace ./my-project --run-id prod-task-01
PYTHONPATH=src python3 -m onecode list-runs --workspace ./my-project
```
After initialization, `run-plan --verifier` reads the workspace default policy at `.onecode/verifier-policy.json` (override with `--verifier-policy`). Each run stores `manifest.json`, `ledger.json`, `evidence-chain.jsonl`, checkpoints, and terminal `run_completed` trace evidence under `<workspace>/.onecode/runs/<run-id>/`. Resource guardrails (`--max-write-bytes`, `--max-trace-bytes`, `--max-run-seconds`, etc.) reject oversized or overlong runs with `resource_budget_exceeded`. Docker sandbox execution enforces network isolation (`--network none`), CPU/memory bounds, `--pids-limit`, and `--cap-drop ALL`.

### 3. CLI Quick Reference / 命令行快速参考

| Command / 命令 | Purpose / 用途说明 |
| :--- | :--- |
| `onecode run-model "<task>"` | Autonomous coding loop (`--agent-mode terminal\|phased_terminal`, `--execution-scope`, `--rollback-on-failure`, `--verifier`) / 自主编码求解循环 |
| `onecode run "<task>"` | Single-step write/patch/command with `--resume-from` checkpointing / 单步受控动作与断点续传 |
| `onecode run-plan --plan <json>` | Declarative multi-asset plan with sandbox verifier & repair budget / 声明式规划与沙箱门禁 |
| `onecode inspect --run-id <id>` | Verify run ledger and SHA-256 `evidence-chain.jsonl` / 审计账本与不可篡改链 |
| `onecode list-runs` | List workspace run history / 列出工作区运行记录 |
| `onecode doctor` / `math-audit` | Runtime boundary checks & automaton invariants / 环境自检与数学审计 |
| `onecode config` / `approvals` | Model presets & human approval queue / 模型配置与人工审批队列 |
| `onecode tui` / `serve` | Terminal UI or local OpenAI-compatible HTTP bridge / 终端界面或本地网关 |

Full options & environment variables: [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) · Documentation index: [docs/INDEX.md](docs/INDEX.md)  
完整参数与环境变量见 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)，文档总索引见 [docs/INDEX.md](docs/INDEX.md)。

---

## Industrial Benchmark Portfolio / 工业实战基准归档汇总

| ID | Domain / 领域场景 | Standards & Components / 核心标准与组件 | Baseline Pass / 通过率 | Token Efficiency / Token 表现 |
| :--- | :--- | :--- | :---: | :---: |
| **01–03** | Distributed Middleware / 核心分布式 | Saga coordinator, async event bus, dynamic RBAC, zero-downtime migration | 100% (23/23) | Single & multi-turn green / 自主通关 |
| **04** | Infrastructure A/B / 基础中间件对决 | Token bucket limiter, half-open circuit breaker, WAL, weighted LB | 100% (25/25) | **-48.7%** vs baseline |
| **05** | Quant & Risk / 量化高频与风控 | L3 order book matching, portfolio VaR / drawdown, TWAP/VWAP execution | 100% (26/26) | **-64.6%** vs baseline |
| **06** | Discrete Manufacturing / 离散主控 | OMAC PackML (`ISA-TR88`) 17-state, TPM OEE 6-loss, MTBF/MTTR | 100% (26/26) | **-85.2%** (`899k` -> `133k`) |
| **07** | Chemical Safety / 化工连续安全 | TEP ODEs, ISA PID anti-windup, `ISA-18.2` alarm, `IEC 61511` SIL-2 SIF | 100% (26/26)* | **-77.8%** (`705k` -> `157k`) |
| **08** | IIoT Gateway / 工业物联网网关 | Modbus TCP (MBAP/PDU), 4-zone concurrent map, deadband, SDT | 26/26* (Task 4 boundary noted) | Tasks 1–3 **-78.2%** (`494k` -> `108k`) |
| **Total** | **8 Production Tiers / 全场景** | **Distributed, Quant, Discrete Mfg, Process Safety, IIoT** | **184/184 (baseline)** | High single-module savings; multi-module evolving |

> `*` Baseline cumulative records include network retries and multi-round tuning; see *Empirical Scope & Re-Verification Boundaries* above for live unassisted `Task 4` results.  
> `*` 基线累计记录包含断线重试与多轮迭代调优；洁净工作区无提示 `Task 4` 实时复测边界见上文“客观适用边界与复验说明”。

---

## Community / 社区认可与交流

- Shared with and supported by the **[LINUX DO](https://linux.do)** open-source community (`https://linux.do`). Feedback, issues, and contributions are welcome.  
  本项目保持完整开源，特别感谢并认可 **[LINUX DO](https://linux.do)** 社区在开源技术交流与社区孵化中的支持，欢迎各位佬友试用、讨论与提交共建 PR。

---

## License / 开源协议

OneCode is licensed under the **GNU General Public License, Version 3 only (`GPL-3.0-only`)**.  
OneCode 遵循 **GNU General Public License v3 only (`GPL-3.0-only`)** 开源协议，衍生与分发版本须保持开源并提供对应完整源码。
