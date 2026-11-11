# OneCode: 工业制造与生产级高安全自主智能体内核
### Industrial High-Assurance Autonomous Agent Kernel for Factory Automation & Mission-Critical Systems

OneCode 是专为**工业制造、自动化车间、连续流程控制与关键基础设施**量身打造的高安全、防篡改、极低 Token 消耗的生产级自主智能体内核（Autonomous Agent Kernel）。

不同于依赖大模型黑盒自我评判的传统编程 Agent，OneCode 将大模型推理严格收敛于**确定性控制论状态机代数（Deterministic Cybernetic Automaton）**与**物理沙箱双门禁校验器（Kernel-Isolated Dual-Gatekeeper Verifier）**之内，从系统工程层面彻底根除了代码交付幻觉与越权写盘隐患。

---

## 核心工业级特性 (Industrial Superpowers)

```
+----------------------------------------------------------------------------------------------------+
|                                    OneCode Industrial Kernel                                      |
+------------------------------------+----------------------------------+----------------------------+
| 1. 工业级最高生产安全保障          | 2. 80%+ 颠覆性 Token 节省        | 3. 工控网关与网络抖动容灾  |
| - 内核态 Verifier 独立测试门禁     | - 紧凑 Shell 状态差分投影        | - 原生 SSE 流式分块传输    |
| - Anti-Tamper 反越权防篡改拦截     | - 杜绝多轮上下文原始暴涨         | - 彻底免疫 524 原点超时    |
| - 交付幻觉物理阻断 (100%全绿准入)  | - 工业三部曲实测节省 81.1% Token | - 全抖动指数退避自愈重试   |
+------------------------------------+----------------------------------+----------------------------+
```

### 1. 工业级最高生产安全保障 (Maximum Mission-Critical Safety)
- **内核态双门禁 Verifier 沙箱 (Kernel-Isolated Dual-Gatekeeper Verifier)**：
  坚决杜绝“大模型以为自己写完了就交付”的虚假完成幻觉（Finish Hallucination）。无论模型在回答中如何声明“已完成修复”，OneCode 仅在隔离沙箱中真实执行预置单元测试套件且返回 `exit_code == 0` 时，才发放 `deliverable` 准入凭证；若测试未过，门禁强行判定 `delivery_status: blocked`，物理阻断缺陷代码流入生产环境。
- **反越权与代码防篡改防御 (Anti-Tamper Layer & Sovereign Boundary Protection)**：
  针对大模型受挫时企图在命令行中执行 `python -c "open('src.py', 'w').write(...)"` 等旁路侵入行为，OneCode 内核防火墙实时阻断非法修改（`preset_test_immutable` / `sovereignty_fire_boundary_halt`），强制所有代码修改必须走受严格审计的 `patch` 或 `write_file` 动作通道，并持续生成 SHA256 单向不可篡改审计链（`evidence-chain.jsonl`）。

### 2. 颠覆性的 Token 节省与上下文投影 (Over 80%+ Token Reduction)
- **精准 Shell 状态差分投影 (`shell_projection`)**：
  传统 Agent 会将多轮探索中海量的文件全文与执行历史无节制地滚雪球式累加，极易引发 Prompt 爆炸（单轮超 40,000 Tokens）。OneCode 采用微内核紧凑状态投影，仅向下游模型和交互壳层传递结构化的差分证据与最小必要上下文。
- **工业生产基准三部曲实测数据 (OneCode vs Claude Code v2.1.150)**：
  在物理工控节点（Intel N100 4C4T 物理机，统一 DeepSeek-V4.1-Flash 底座）上对决 **78 项严苛工业测试**：
  - **离散智能制造 (Option A - PackML / OEE)**：Claude 89.9万 Tokens vs **OneCode 13.3万 Tokens（节省 85.2%）**；
  - **连续流程安全 (Option B - TEP 化工 / ISA PID / SIL-2)**：Claude 70.5万 Tokens vs **OneCode 15.7万 Tokens（节省 77.8%）**；
  - **工业物联网网关 (Option C - Modbus TCP / 死区旋转门压缩)**：Claude 49.4万 Tokens vs **OneCode 10.8万 Tokens（节省 78.2%）**；
    - **全场景大盘汇总**：Claude Code 累计消耗 2,097,072 Tokens，OneCode 仅消耗 **397,258 Tokens**，**全流程综合节省 81.1%（净节省 1,699,814 Tokens）**，单元测试通过率两端均为 **78/78 (100.0%)**。
- **客观范围与复验说明**：
  - 上述工业三部曲数据在受控基准工作区与同一 DeepSeek-V4.1-Flash 模型底座下测得；其中在单模块/中等复杂度的明确规格实现任务（如 Option A、Option B Tasks 1–3、Option C Tasks 1–3）中，OneCode 的紧凑上下文投影实现了高通过率与显著的 Token 节约（约 78%–85% 节省）。
  - 在多模块强耦合集成任务（如 `Option B Task 4` 与 `Option C Task 4: ModbusEdgeTelemetryGateway`）的历史基线测试中，曾依赖多轮重试与人工/上下文调优才完成全绿；本次内核已合入长文件分页读取修复、静态字面量路径白名单与命令写盘追踪审计，并在洁净 Task 4 工作区对无提示单次自主运行重新进行了实时复验（`--max-turns 25`，DeepSeek-V4.1-Flash）：`terminal` 模式在 25 轮消耗 63,163 Tokens 后因反复重读跨文件规范触发 `turn_limit_exhausted`（未写入 `edge_gateway.py`）；`phased_terminal` 模式在 5+20 轮消耗 97,752 Tokens 后仅于第 25 轮生成了不完整的 `edge_gateway.py`（同样 `turn_limit_exhausted`）。因此，`OneCode` 对单模块任务具有稳定的高性价比，但在无外部提示的多模块大型集成任务上的端到端单次自主率仍受小参数/高速模型跨轮工作记忆窗口限制。

### 3. 工控网关与网络抖动容灾 (Network Jitter & Gateway Resilience)
- **原生 SSE 分块流式处理引擎 (`ONECODE_STREAM_CHAT=1`)**：
  攻克工业专网与云端网关、前置 CDN（如 Cloudflare / 阿里云 ESA）常见的 30s/100s 原点硬超时（HTTP 524 Origin Time-out），彻底消除长耗时代码规划时连接被前置网关强行掐断的问题；
- **全抖动指数退避重试 (Exponential Backoff with Full Jitter)**：
  内置工控级重试状态机，抵御边缘弱网、网卡抖动与网关瞬态重置；结合状态可恢复机制（Stateful Resumption），保证任务长程作业中断点可续、状态零丢失。

### 4. 深度适配的工控标准与行业场景
- **离散制造与包装生产线**：OMAC PackML (ISA-TR88.00.02) 17 状态自动机、TPM OEE 六大损失体系 (ISO 22400 / SEMI E10)、MTBF/MTTR 设备可靠性 KPI 计算。
- **连续化工过程与生命安全**：Tennessee Eastman Process (TEP) 反应动力学常微分方程组（ODEs）、Arrhenius 热平衡反应、ISA 工业标称 PID 无扰切换（Bumpless Transfer）与抗积分饱和（Anti-Windup）、ANSI/ISA-18.2 智能报警状态机与死区抑制、IEC 61511 SIL-2 级安全仪表系统（SIF）紧急停车（ESD）。
- **工业物联网与边缘采集**：Modbus TCP (MBAP/PDU) 报文编解码、IEEE-754 32位多字节序浮点支持（ABCD/CDAB/BADC/DCBA）、四大工业内存映像区高并发保护、绝对死区/量程百分比死区过滤、旋转门趋势压缩（Swinging Door Trending SDT）。

---

## 底层运行规则与控制论数学模型 (Cybernetic State Machine & Formulations)

OneCode 内核将系统运行状态形式化为高可靠**控制论离散状态机（Cybernetic Finite State Automaton）**，杜绝任何无法解释的黑盒玄学逻辑：

### 1. 64 状态超立方体自动机 (Boolean Hypercube Automaton $Q_6$)
系统运行空间由 6-bit 状态布尔向量严格张成：
$$s = (b_5, b_4, b_3, b_2, b_1, b_0) \in \{0, 1\}^6 \cong \mathbb{Z}_{64}$$

状态向量由两个三维子相向量构成：
- **外部环境相 (Outer Phase Vector)** $\phi_{\text{out}} = (b_5, b_4, b_3) \in \{0, 1\}^3$：表征规则契约、沙箱约束与任务调度上下文；
- **内部执行相 (Inner Phase Vector)** $\phi_{\text{in}} = (b_2, b_1, b_0) \in \{0, 1\}^3$：表征物理文件、测试结果与工具执行状态。

### 2. 李雅普诺夫系统平衡熵方程 (Lyapunov Balance & Energy Descent)
为确保多轮迭代过程收敛且不陷入死循环，内核定义系统平衡能量泛函 $V(s)$：
$$V(s) = \sum_{i=0}^5 |b_i - b_i^*|$$
其中 $b^*$ 为目标任务收敛基态（如基态 `63: 0b111111` 乾稳态）。  
系统转移算子 $\mathcal{T}: S \times \mathcal{E} \to S$ 必须严格满足李雅普诺夫渐近稳定收敛约束：
$$\Delta V(s) = V(\mathcal{T}(s, e)) - V(s) \le 0$$
当且仅当发生不可逆物理故障时，系统受控跃迁至边界阻断态（如 `40: sovereignty_fire_boundary_halt`），彻底避免无阻尼发散震荡。

### 3. 五相闭环传递矩阵 (5-Phase Transfer Matrix)
外部相 $\phi_{\text{out}}$ 与内部相 $\phi_{\text{in}}$ 的耦合作用遵循闭环反馈控制代数：
$$\mathbf{S}_{k+1} = \mathbf{M}_{\text{transfer}} \cdot \mathbf{S}_k + \mathbf{B} \cdot e_{\text{evidence}}$$
- **加速前馈 (Feedforward Acceleration)**：当内部动作与外部规格正向协同，触发加速转移（`action: accelerate`）；
- **阻尼负反馈 (Negative Feedback Damping)**：当检测到局部发散或超调，触发安全阻尼（`action: throttle`）；
- **稳态维持 (Equilibrium Preservation)**：处于平衡区间时维持稳态调度（`action: continue`）；
- **热耗散冷却 (Thermal Dissipation Cooling)**：检测到过载或轮数高频振荡，强制进入冷却区（`action: cooldown`）；
- **边界阻断 (Sovereign Boundary Halt)**：遭遇越权写盘或破坏性篡改，立即切断执行链（`action: halt`）。

### 4. 工业双门禁交付公理 (Dual-Gatekeeper Delivery Axiom)
系统交付状态 $\text{Delivery}(R)$ 遵循严格充分必要布尔条件：
$$\text{Delivery}(R) \iff \text{AssetsComplete}(R) \land \big(\text{ExitCode}(\text{Verifier}) == 0\big) \land \text{HashMatch}(\text{Workspace}) \land \text{AuditedPatchOnly}(R)$$
任何未经验证（Unverified）、未修改（Unmodified）或测试失败（Failed）的运行记录，在公理层面恒为 `blocked`。

### 5. Rule Closure Principle & Rule Discovery Protocol
- **Rule Closure Principle**: External engineering facts (`external facts are evidence, not law` — file existence, SHA-256 verification, path traversal checks, timeout errors) are sampled as physical evidence and collapsed strictly into the existing formal rule surface (`6-bit status_code`, yin-yang damping pressure, four-symbol windows, trigrams, five-element relational feedback matrices, and `IchingKernel.transition()`). Bug fixes must close inside that algebraic state surface without adding forbidden parallel control variables (`confidence_level`, `manual_priority`, `model_mood`, `retry_score`, or external policy flags).
- **Rule Discovery Protocol**: `Bug reports are rule-gap probes`. When a task encounters an unmapped runtime failure or stalled state, the fix path adds a failing regression test, collapses the physical evidence into a `6-bit status_code` / balanced five-element feedback transition, or emits a deterministic `discover` boundary transition, verified via manifest, ledger, and checkpoint evidence.

---

## 快速上手 (Quick Start)

### 1. 安装核心与可选界面
The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency.

```bash
# 安装基础控制内核与 CLI
pip install -e .

# 安装可选的富交互终端界面 (Textual TUI)
pip install -e .[tui]
```

### 2. 运行完整工程验证门禁
```bash
# 核心轻量校验门禁
bash scripts/verify-core.sh

# 全量自检套件 (包含全套严格单元测试与静态分析)
bash scripts/verify.sh

# 运行 v0.7 本地验证门禁演示工作流
bash scripts/demo_v07.sh
```

### 3. 一键环境自检 (Doctor) 与系统自审 (Self Audit)
```bash
PYTHONPATH=src python3 -m onecode doctor
PYTHONPATH=src python3 -m onecode.cli doctor
PYTHONPATH=src python3 -m onecode audit-self
PYTHONPATH=src python3 -m onecode math-audit
```
- `doctor` 内置生产级物理链路自检：`write_text`、`resume_skip`、`sovereignty_breach`、`http_timeout` 等；
- `math-audit` 为只读形式化审计，校验 64-state `transition graph`、吸引子数量、`Q6` 拓扑闭合与李雅普诺夫稳定边界。

---

## 生产模式与交互界面

### 1. 终端交互式 TUI (Terminal User Interface)
基于 Textual 构建的工业级全键盘响应式终端：
```bash
onecode tui
```
- 所有任务执行与补丁生成均穿透内核 `LogosGate`、`PathGuard` 与沙箱门禁；
- 会话转录与最终输出分别持久化至 `.onecode/tui-transcript.txt` 与 `.onecode/tui-last-output.txt`（支持在 TUI 中使用 `/export` 或 `/export-last` 导出路径）。

### 2. 本地 OpenAI 兼容网关 (LibreChat / Web UI 端点)
启动本地无外部依赖的标准 HTTP 代理桥接：
```bash
ONECODE_API_TOKEN=<local-token> python3 -m onecode serve --host 127.0.0.1 --port 19080
```
- 暴露 `/health`、`/v1/models`、`/v1/chat/completions`；
- 原生支持接入 LibreChat、Open-WebUI 等现代前端界面；
- 具备严格的恒定时间（Constant-Time）Token 鉴权防御。

### 3. 结构化任务、策略门禁与断点审计命令
```bash
# 列出内置验证预设并初始化工作区验证门禁策略
PYTHONPATH=src python3 -m onecode list-verifier-presets
PYTHONPATH=src python3 -m onecode init-verifier-policy --workspace ./my-project --preset python-unittest

# 单步受控运行与幂等断点续传
PYTHONPATH=src python3 -m onecode run "write assets" \
  --workspace ./my-project --run-id demo-run \
  --write-text "src/app.py=value = 1\n" --max-write-bytes 5000000
PYTHONPATH=src python3 -m onecode run "resume asset" \
  --workspace ./my-project --run-id demo-resume --resume-from demo-run \
  --write-text "src/app.py=value = 1\n"

# 运行受控门禁规划任务（支持 --verifier-policy 覆盖工作区默认策略）
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace ./my-project --run-id prod-task-01 --plan ./plan.json --verifier python-unittest

# 审计单次运行或列出工作区运行账本
PYTHONPATH=src python3 -m onecode inspect --workspace ./my-project --run-id prod-task-01
PYTHONPATH=src python3 -m onecode list-runs --workspace ./my-project
```
After initialization, `run-plan --verifier` reads the workspace default policy at `.onecode/verifier-policy.json` (override with `--verifier-policy`). Each run stores `manifest.json`, `ledger.json`, `evidence-chain.jsonl`, checkpoints, and terminal `run_completed` trace evidence under `<workspace>/.onecode/runs/<run-id>/`. Resource guardrails (`--max-write-bytes`, `--max-trace-bytes`, `--max-run-seconds`, etc.) reject oversized or overlong runs with `resource_budget_exceeded`. Docker sandbox execution enforces network isolation (`--network none`), CPU/memory bounds, `--pids-limit`, and `--cap-drop ALL`.

---

## 命令行快速参考 (CLI Quick Reference)

| 命令 | 用途说明 |
| :--- | :--- |
| `onecode run-model "<task>"` | 启动自主编码循环（支持 `--agent-mode terminal|phased_terminal`、`--execution-scope`、`--rollback-on-failure`、`--verifier`） |
| `onecode run "<task>"` | 执行单步受控写盘、增量补丁或命令动作（支持 `--resume-from` 断点续传） |
| `onecode run-plan --plan <json>` | 执行声明式多资产任务规划并绑定沙箱验证器与自动修复预算 |
| `onecode inspect --run-id <id>` | 检查指定运行账本与 SHA-256 不可篡改审计链（`.onecode/runs/<id>/`） |
| `onecode list-runs` | 列出当前工作区历史运行记录 |
| `onecode doctor` / `onecode math-audit` | 执行环境边界自检与控制论状态机公理审计 |
| `onecode config` / `onecode approvals` | 管理模型配置预设与人工审批队列 |
| `onecode tui` / `onecode serve` | 启动富交互终端界面或本地 OpenAI 兼容网关 |

完整参数与环境变量清单请参阅 [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)，文档总索引请参阅 [docs/INDEX.md](docs/INDEX.md)。

---

## 工业实战基准归档库 (Industrial Benchmark Portfolio)

所有评测记录、源码比对、完整 Trace 与 184 项单元测试均物理归档于测试基站：

| 归档编号 | 领域与工程场景 | 核心工业标准与组件 | 测试集通过率 | Token 节省表现 |
| :--- | :--- | :--- | :---: | :---: |
| **01~03** | 核心分布式中间件 | Saga 两阶段协调器、异步流事件总线、动态多租户 RBAC、零停机迁移引擎 | 100% (23/23) | 单轮与多轮自主通关 |
| **04** | 基础中间件 A/B 对决 | 令牌桶限流器、半开熔断器、预写日志 (WAL)、平滑加权轮询负载均衡 | 100% (25/25) | 综合节省 48.7% |
| **05** | 量化高频交易风控 | L3 限价订单薄撮合、实时投资组合 VaR/最大回撤风控、TWAP/VWAP 算法执行 | 100% (26/26) | 综合节省 64.6% |
| **06** | 智能制造离散主控 | OMAC PackML (ISA-TR88) 17状态机、TPM OEE 六大损失体系、MTBF/MTTR 引擎 | 100% (26/26) | **节省 85.2%** |
| **07** | 化工连续安全流控 | TEP 反应器 ODEs、ISA PID 无扰切换与抗饱和、ISA-18.2 智能报警、SIL-2 SIF | 100% (26/26)* | **节省 77.8%** |
| **08** | 工业物联网通信网关 | Modbus TCP (MBAP/PDU)、四区内存并发映像、绝对/相对死区、旋转门 SDT 压缩 | 基线多轮后 26/26（Task 4 单轮复测未收敛） | Task 1–3 **节省 78.2%** |
| **总计** | **8 大层级生产级全场景** | **覆盖分布式、量化金融、智能制造、化工流控、工业物联网全链路** | **基线多轮累计 184/184** | **单模块高节流，跨模块持续演进** |

> 注：`*` 表示包含断线重试或多轮迭代修复记录的基线累计结果；单次无提示自主运行边界请参见上文“客观范围与复验说明”。

---

## 开源协议与合规声明 (License)

OneCode 遵循 **GNU General Public License, Version 3 only (`GPL-3.0-only`)** 开源许可协议。任何基于 OneCode 的衍生修改与分发版本均须保持 GPL v3 开源，并提供完整对应的源码工程。
