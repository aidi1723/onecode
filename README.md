# OneCode — Self-Hosted Bounded Autonomous Agent Kernel (Bounded Preview)
### 自托管受控自主编码智能体内核（`v1.1.0-bounded-preview`）

OneCode is a **self-hosted, bounded-preview** autonomous coding agent kernel (`claims_mainstream_parity: false`, zero runtime third-party kernel dependencies) built for controlled code generation, automated repair, and offline validation across engineering and industrial/IIoT automation workflows — emphasizing **deterministic delivery gates, anti-tamper protection, and compact context projection**.

OneCode 是一个**自托管、受控工程预览级（Bounded Preview）**自主编码智能体内核（零第三方内核运行时依赖），面向高审计需求的研发、运维脚本与工业/IIoT 离线模块开发场景，主打**确定性测试交付门禁、反篡改防越权保护与紧凑上下文 Token 节流**。

> **Scope & Isolation Prerequisite / 适用范围与隔离前提**：OneCode is NOT an unattended enterprise monolith or a real-time PLC replacement. Full OS/network sandbox isolation (`--network none --cap-drop ALL --read-only`) **requires Docker** (`onecode doctor` reports `production_ready: true`); without Docker, `run_command` executes on the host under software guards and is restricted to **trusted local workspaces** (see [SECURITY.md](SECURITY.md)).  
> OneCode 目前处于**个人/小团队受控试点与研究预览阶段**，并非开箱即用的大型无人值守商业底座或现场 PLC 实时控制器。完整容器强隔离**须启用 Docker**；无 Docker 时命令行在宿主机运行，仅用于**可信本地工作区**（详见 [SECURITY.md](SECURITY.md)）。

---

## Core Capabilities / 核心特性

```
+----------------------------------------------------------------------------------------------------+
|                              OneCode Kernel (v1.1.0-bounded-preview)                               |
+------------------------------------+----------------------------------+----------------------------+
| 1. Bounded Execution Safety        | 2. Compact Context Projection    | 3. Gateway Jitter Resilience|
| - Kernel-isolated Verifier gate    | - Compact shell_projection diff  | - Native SSE chunked stream|
| - Anti-Tamper shell firewall       | - Prevents multi-turn context    | - Immune to HTTP 524 origin|
| - Blocks unverified code delivery  |   prompt explosion               |   gateway timeouts         |
| - Full isolation requires Docker   | - Self-tested N100 savings logs  | - Full-jitter exponential  |
| 1. 内核级硬门禁安全防线            | 2. 紧凑上下文差分与 Token 节流   |   backoff & checkpoint     |
| - 内核态独立 Verifier 测试门禁     | - 紧凑 Shell 状态差分投影        | 3. 弱网与边缘网关容灾       |
| - 反越权防篡改命令行拦截           | - 杜绝多轮上下文原始暴涨         | - 原生 SSE 流式分块传输    |
| - 物理阻断未通过测试的代码交付     | - 适用于边界清晰的受控模块任务   | - 免疫 524 超时与断线重连  |
| - 容器隔离依赖 Docker 运行时       |                                  |                            |
+------------------------------------+----------------------------------+----------------------------+
```

### 1. Bounded Execution Safety / 确定性内核安全门禁
- **Kernel-Isolated Dual-Gatekeeper Verifier**: Prevents finish hallucinations. Regardless of what the model claims in prose, OneCode only marks a run `deliverable` when the isolated test suite executes and exits with `exit_code == 0`. Otherwise delivery is blocked (`delivery_status: blocked`).  
  **内核态双门禁校验器**：彻底杜绝虚假完成幻觉。无论模型文本如何声称已完成修复，只有在测试运行器真实执行验证套件且返回 `exit_code == 0` 时才签发 `deliverable`；失败则强制判定 `delivery_status: blocked`，阻断缺陷代码交付。
- **Anti-Tamper & Sovereign Boundary Protection**: Blocks shell workarounds such as inline `python -c "open('src.py', 'w')..."` bypasses (`preset_test_immutable` / `sovereignty_fire_boundary_halt`), enforces audited `patch`/`write_file` transitions, and records a tamper-evident SHA-256 log (`evidence-chain.jsonl`). Container enforcement requires Docker (`onecode doctor` -> `production_ready: true`). Full 6-layer architecture & reproducible `18/18` self-authored regression suite: [Security Architecture](#security-architecture--adversarial-suite--安全纵深防御架构与对抗实测) · [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md).  
  **反越权防篡改保护**：实时拦截命令行旁路篡改与越界写盘，强制全部文件变更经受审计的 `patch` / `write_file` 动作通道，并持续落盘 SHA-256 不可篡改审计链（`evidence-chain.jsonl`）。完整容器强隔离依赖 Docker。6 层防御与 `18/18` 可复现对抗测试见下文[安全专章](#security-architecture--adversarial-suite--安全纵深防御架构与对抗实测)及 [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md)。

### 2. Token Reduction & Compact Context Projection / 颠覆性 Token 节省与紧凑投影
- **Structured Shell State Projection (`shell_projection`)**: Instead of appending raw file dumps and full terminal logs every turn, OneCode projects minimal structured deltas and failure evidence across turns.  
  **紧凑状态差分投影（`shell_projection`）**：用结构化差分与最小必要失败证据替代逐轮拼接海量全文，避免多轮对话上下文雪球式爆炸。
  - **Reproducible Zero-API Offline Compression Benchmark (`scripts/token_projection_benchmark.py`)**: Running `PYTHONPATH=src python3 scripts/token_projection_benchmark.py --json` locally verifies **`90.32%`** serialized UTF-8 byte reduction across 4 synthetic multi-turn workloads via `project_run_to_shell` (`56,929 B` raw -> `5,511 B` projected), and **`98.74%`** checkpoint telemetry byte reduction across 8 turns when optional symbolic telemetry is decoupled (`155,736 B` -> `1,959 B`). *(Note: uses `chars/4` heuristic token estimates over synthetic reference payloads with zero API calls; external Trilogy comparator logs remain unbundled.)*  
    **零 API 离线可复现压缩基准（`scripts/token_projection_benchmark.py`）**：本地零密钥复现脚本对 4 组多轮工业合成轨迹执行真实 `project_run_to_shell` 投影，实测将原始运行负载从 `56,929 B` 压缩至 `5,511 B`（**`-90.32%`**），同时剥离可选符号遥测后检查点体积从 `155,736 B` 降至 `1,959 B`（**`-98.74%`**）。
- **Industrial Trilogy Benchmark (OneCode vs Claude Code v2.1.150, Intel N100 4C4T, DeepSeek-V4.1-Flash, 78 tests)**:  
  **工业生产三部曲实测对比（同硬件与同一 DeepSeek-V4.1-Flash 底座，共 78 项测试）**：
  - **Discrete Manufacturing (Option A — PackML / OEE)**: Claude `899k` vs **OneCode `133k` Tokens (`-85.2%`)**  
    离散智能制造（PackML / OEE）：Claude 89.9 万 Tokens vs **OneCode 13.3 万 Tokens（节省 85.2%）**
  - **Continuous Process Safety (Option B — TEP / ISA PID / SIL-2)**: Claude `705k` vs **OneCode `157k` Tokens (`-77.8%`)**  
    连续流程安全（TEP 化工 / ISA PID / SIL-2）：Claude 70.5 万 Tokens vs **OneCode 15.7 万 Tokens（节省 77.8%）**
  - **Industrial IoT Gateway (Option C — Modbus TCP / Deadband / SDT)**: Claude `494k` vs **OneCode `108k` Tokens (`-78.2%`)**  
    工业物联网网关（Modbus TCP / 死区与旋转门压缩）：Claude 49.4 万 Tokens vs **OneCode 10.8 万 Tokens（节省 78.2%）**
  - **Total Across Self-Tested Trilogy / 三部曲自测总计**: `2,097,072` vs **`397,258` Tokens (`-81.1%` / `1,699,814` saved)**, `78/78 (100.0%)` under author-run N100 baseline sessions. *(Disclosure: baseline comparator raw logs and prompt traces are not archived in this public repo; evaluate on your own workload before treating this percentage as general parity.)*
  *(说明：三部曲 Token 节省为作者在 N100 环境下的自测统计，对照方原始运行日志未随仓库公开，请结合自身任务集实测评估，勿作同级横向榜单引用。)*

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

OneCode is positioned as a **self-hosted bounded-preview engineering and verification agent kernel** (`Self-hosted Bounded Preview`, `claims_mainstream_parity: false`) for generating, patching, verifying, and auditing scoped code/configs under deterministic gates — rather than an unattended general production monolith or a real-time PLC controller.  
OneCode 定位于**自托管受控工程预览级（Bounded Preview）开发与校验智能体内核**（在确定性门禁下完成单模块代码/配置生成、修复、沙箱验证与审计留痕），适合个人开发者与小团队受控试点及安全参考，不替代现成生产级大型底座或现场 PLC/DCS 毫秒级硬件实时控制。

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

## Security Architecture & Adversarial Suite / 安全纵深防御架构与对抗实测

Rather than trusting system-prompt instructions, OneCode enforces every security invariant in deterministic kernel Python code **before** filesystem mutation, command execution, HTTP routing, or delivery sign-off.  
OneCode 不依赖提示词层面的“口头约束”，而是在文件落盘、Shell 执行、HTTP 路由与最终交付签发**之前**，通过 6 层确定性内核机制硬性阻断越权行为与“投机作弊”路径（详见 [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md)）。

### 6 Defense-in-Depth Kernel Layers / 六层确定性内核安全防线

1. **Workspace Isolation & Secret Read Guard (`PathGuard`)**  
   Canonicalizes target paths, rejects `../` traversal, absolute paths, `\x00` null bytes, and symlink directory jailbreaks (`_reject_symlinks`); locks control-plane paths (`.git`, `.github`, `.onecode`, `pyproject.toml`, `Makefile`) and blocks model `read_file` probes on `.env`, `.env.production`, `.git/config`, and private keys (`sensitive_read_denied`).  
   **工作区隔离与密钥防泄露**：拦截路径穿越、绝对路径、空字节与软链接逃逸；锁死 `.git/.github/.onecode/pyproject.toml/Makefile` 控制面写权限，并物理拒绝模型读取 `.env` 等敏感凭据。
2. **Verifier Anti-Tamper, AST/Shadow Guard & Auto-Rollback (`preset_tests`, `TerminalSession`, `model_provider`)**  
   Protects multi-language test suites (Python / Go / TS / Rust) as immutable (`preset_test_immutable`); blocks shadow test runner injection (`unittest.py`, `pytest.py`, `conftest.py`, `sitecustomize.py`, `usercustomize.py`); statically rejects `pytest`/`unittest`/`__import__`/`os._exit` in `src/` via AST; intercepts inline `python3 -c` test-tampering commands *before* shell execution; and restores source snapshots automatically on `rollback_on_failure=True`.  
   **测试完整性保护与失败回滚**：禁止修改多语言预设单测；阻断 `unittest.py`/`sitecustomize.py` 影子注入；AST 静态查杀 `src/` 内嵌测试框架与 `os._exit(0)`；执行前预拦截 `python3 -c` 绕过写入；触发篡改立即 `halt` 并自动回滚源码快照。
3. **Scoped Capabilities & Destructive Command Firewall (`ExecutionScope`, `ExecutionGuardrails`)**  
   Enforces `READ_ONLY` / `PATCH_GUARDED` / `FULL_TERMINAL` policies (`ToolCapabilityPolicy`), blocks destructive commands including `bash -c` wrappers (`rm -rf`, `git reset --hard`, `git clean -f`, `git push --force`, `dd`, `kill -9`), validates `forbidden_tools` / resource budgets, and requires explicit human approval for external `mcp.*` tool calls.  
   **分权能力集与高危命令防火墙**：按 `READ_ONLY` / `PATCH_GUARDED` / `FULL_TERMINAL` 分级授信，拦截含 Shell 嵌套包装的高危销毁指令，并对外部 `mcp.*` 调用强制接入人工审批门禁。
4. **Isolated Delivery Gatekeeper & SHA-256 Audit Ledger (`verify_shell_write`, `wal`, `validate_evidence_chain`)**  
   Failing verification tests hard-block delivery (`delivery_status: blocked`), while `.onecode/global-ledger.jsonl` and `.onecode/runs/<id>/evidence-chain.jsonl` detect post-run workspace or audit-log tampering via SHA-256 digests (`asset_hash_mismatch`, `evidence_chain_hash_mismatch`).  
   **不可绕过交付门禁与防篡改审计链**：单测不真通过即强制 `delivery_status: blocked`；通过全局 WAL 与逐条前向哈希链对产出文件与审计日志做 SHA-256 校验，事后任何单字节篡改立即可检。
5. **Container Sandbox Hardening (`SandboxConfig.build_docker_command`)**  
   Runs isolated verification inside Docker with `--network none`, `--cap-drop ALL`, `--read-only`, `--security-opt no-new-privileges`, `--pids-limit 256`, `noexec,nosuid` `/tmp`, `PYTHONSAFEPATH=1`, `PYTHONDONTWRITEBYTECODE=1`, non-root host `--user`, and `readonly` mounts for `.git`, `.github`, `.onecode`, and `tests`.  
   **极简高强容器沙箱**：默认无外网、全能力裁撤（`--cap-drop ALL`）、只读根文件系统、防提权与进程数上限隔离，并将受保护目录以只读模式挂载。
6. **Gateway HTTP, Redirect & Deployment Boundary Security (`web.auth`, `http_safety`, `deployment_boundary`)**  
   Strips `Authorization` and `api-key` headers across HTTP cross-host redirects or HTTPS->HTTP downgrades (`StripAuthRedirectHandler`), blocks DNS-rebinding `Host` headers and cross-origin CSRF (`local_request_allowed`), refuses unauthenticated `0.0.0.0` binding (`run_server`), and rejects published sample credentials (`dev-local-token`) or permissive `0o644` token files.  
   **网关认证、重定向防泄露与部署红线**：重定向/降级自动剥离认证头；防御 DNS 重绑定与跨站 CSRF；禁止未鉴权绑定 `0.0.0.0`；拒收公开示例弱口令及权限过宽（`0o644`）的密钥文件。

### Adversarial Agent Security Benchmark (`18/18` Self-Authored Deterministic Suite) / 可复现对抗安全评测（18/18 自研拦截基准）

> **Boundary Note / 边界与证据说明**：Full OS/network containment requires Docker (`production_ready: true` via `onecode doctor`); in non-Docker `host` fallback mode, `run_command` is strictly for **trusted local workspaces** (see [SECURITY.md](SECURITY.md)). `scripts/security_benchmark.py` is a **self-authored deterministic regression benchmark** covering known attack surfaces — it demonstrates that these kernel guards actively enforce their contracts, not an external third-party penetration audit.  
> **说明**：完整系统与网络隔离依赖 Docker；无 Docker 时 `run_command` 在宿主机执行，仅限可信本地工作区使用。下方 `18/18` 套件为项目自带可复现回归红队测试（覆盖已知攻击面），不等同于第三方外部渗透审计。

Anyone can reproduce the zero-API-key red-team test suite locally against the real kernel in <0.5s:  
任何人均可零成本在本地直接运行以下对抗安全基准脚本（无需外部 LLM API Key，全部直连真实内核边界）：

```bash
# Printable Markdown adversarial benchmark report / 输出对抗评测报告
PYTHONPATH=src python3 scripts/security_benchmark.py

# Machine-readable JSON output or CI unittest suite / JSON 输出或运行单元测试套件
PYTHONPATH=src python3 scripts/security_benchmark.py --json
PYTHONPATH=src python3 -m unittest tests/test_security_suite.py -v
```

| Layer / 安全防线 | Adversarial Probes Tested / 实测攻击向量 (`SEC-01` .. `SEC-18`) | Blocked / 拦截率 | Source Suite / 对应测试 |
| :--- | :--- | :---: | :--- |
| **Workspace & Secret Boundary** | `SEC-01`..`SEC-04`: `../` traversal, abs/null-byte paths, symlink escape, `.env`/`.env.production`/`.git/config` read probe, `.git`/`.github`/`.onecode`/`pyproject.toml`/`Makefile` write | **4 / 4 (100%)** | [scripts/security_benchmark.py](scripts/security_benchmark.py) |
| **Verifier Anti-Tamper & Rollback** | `SEC-05`..`SEC-09`: Py/Go/TS/Rust test patching, shadow `unittest.py`/`sitecustomize.py` (root+nested), AST `pytest`/`__import__`/`os._exit(0)`, `python3 -c` pre-exec bypass, halt + auto rollback | **5 / 5 (100%)** | [tests/test_security_suite.py](tests/test_security_suite.py) |
| **Scoped Capabilities & Firewall** | `SEC-10`..`SEC-12`: `READ_ONLY` mutation block, `rm -rf`/`bash -c rm`/`git reset --hard`/`git push --force`/`dd`/`kill -9`, `forbidden_tools` & forced `mcp.*` human approval | **3 / 3 (100%)** | [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) |
| **Delivery Gate & Audit Chain** | `SEC-13`..`SEC-14`: failing `unittest` forces `delivery_status=blocked`; post-run file & ledger edits caught (`asset_hash_mismatch`, `evidence_chain_hash_mismatch`) | **2 / 2 (100%)** | [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) |
| **Sandbox Hardening** | `SEC-15`: validates Docker `--network none`, `--cap-drop ALL`, `--read-only`, `no-new-privileges`, `--pids-limit 256`, `PYTHONSAFEPATH=1`, RO protected mounts | **1 / 1 (100%)** | [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) |
| **Network, Auth & Boundary** | `SEC-16`..`SEC-18`: HTTP redirect/downgrade credential strip, DNS rebinding `Host` + rogue `Origin` CSRF + unauth `0.0.0.0` bind block, published default token & `0o644` file rejection | **3 / 3 (100%)** | [docs/SECURITY_ARCHITECTURE.md](docs/SECURITY_ARCHITECTURE.md) |

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

### 2. Lyapunov Energy Descent & Scope / 李雅普诺夫平衡熵与状态收敛边界
The finite 64-state Q6 `transition graph` satisfies discrete monotonicity $\Delta V(s) = V(\mathcal{T}(s)) - V(s) \le 0$ under the runtime Lyapunov energy metric:

在 64 态超立方体确定性迁移表上，每步决策满足离散非递增约束 $\Delta V(s) \le 0$（可由 `onecode math-audit` 实时验证）：
$$V(s) = \frac{|\text{yang\_count}(s) - 3|}{3} + \text{action\_penalty}(\mathcal{T}(s).\text{action}) + (1 - \text{bandwidth}(s))$$
where the composite Lyapunov energy combines:
1. **Dynamic balance penalty**: $\frac{|\text{yang\_count}(s) - 3|}{3} \in [0.0, 1.0]$, reaching minimum $0.0$ at 3-yang / 3-yin dynamic equilibrium states (`[14, 28, 49, 56]`, e.g. Xian, Heng, Kun, Jing);
2. **Action penalty**: $\text{action\_penalty}(\mathcal{T}(s).\text{action}) \in [0.0, 1.0]$, favoring non-disruptive transitions (`continue`/`recover` = 0.0, `accelerate` = 0.1, up to `halt` = 1.0);
3. **Bandwidth penalty**: $(1 - \text{bandwidth}(s)) \in [0.0, 0.67]$, rewarding maximum tool execution throughput.

Specifically, the static lookup graph contains **56 self-loop fixed points** (terminal halts or idempotent checkpoint attractors under repeated identical fault inputs) and **8 strictly energy-decreasing edges** ($\Delta V < 0$ for reversible recovery/cooldown paths); bounded runtime termination across turns is enforced orthogonally by `--max-turns`, `turn_budget`, repeat/stagnation guards, and resource budgets. Irreversible safety violations jump deterministically to boundary halts (e.g. `40: sovereignty_fire_boundary_halt`).

复合李雅普诺夫能级综合了**三阴三阳动态平衡度**（于平衡态 `[14, 28, 49, 56]` 取得最小值 $0.0$）、**动作干预阻尼代价**（稳态维持为 0.0，熔断停机为 1.0）与**执行带宽损耗**，全图 64 个确定性状态迁移严格满足 $\Delta V(s) \le 0$。静态迁移表共包含 **56 个自环不动点**与 **8 条严格降能迁移边**（$\Delta V < 0$）；多轮运行的有界终止由 `--max-turns`、`turn_budget`、重复动作阻断与配额门禁共同保证。当发生不可逆越权故障时，系统直接跃迁至硬阻断边界态（如 `40: sovereignty_fire_boundary_halt`）。

Optional classical symbolic telemetry (`packages/onecode-symbolic-audit`) is physically decoupled from `src/onecode/kernel/` and disabled unless explicitly installed and enabled (`ONECODE_SYMBOLIC_TELEMETRY=1`).

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
- **Decoupled Symbolic Telemetry (`ONECODE_SYMBOLIC_TELEMETRY`)**: Default execution paths (tool gating in `execution_engine`, checkpoint snapshots in `checkpoint`, `recovery_status` backoff, and `model_guidance` repair prompts) use pure deterministic `6-bit` state logic and plain engineering terminology (`ONECODE_SYMBOLIC_TELEMETRY` unset/`0`). Extended symbolic/observability payloads and `onecode math-audit` certificates are strictly opt-in (`ONECODE_SYMBOLIC_TELEMETRY=1`) and never alter deterministic state transitions.  
  **符号遥测解耦设计（`ONECODE_SYMBOLIC_TELEMETRY`）**：热路径工具门禁、检查点落盘、恢复退避与修复提示词默认仅输出纯工程确定性指标与状态码；扩展符号遥测字段默认关闭（按需设置 `ONECODE_SYMBOLIC_TELEMETRY=1` 开启），做到遥测皮肤与确定性内核零耦合、且不改变任何状态转移裁决。

---

## Quick Start / 快速上手

### 1. Installation / 从源码安装（包名：`onecode-kernel`）
The core kernel has no runtime third-party dependency. Textual is an optional TUI dependency. Its distribution package is named **`onecode-kernel`** (with CLI binary `onecode` and Python import namespace `onecode`) to avoid colliding with the unrelated `DeepLime/onecode` package on PyPI, and `packages/onecode-symbolic-audit` is a strictly optional companion package.

> **PyPI Warning / 包名与冲突规避**：The package `onecode` on PyPI belongs to an unrelated third-party project (`DeepLime`). This distribution declares `name = "onecode-kernel"` in `pyproject.toml`; **never run `pip install onecode`**. Always install from this repository:
> PyPI 上的 `onecode` 已被无关第三方项目占用，因此本仓库发布包名为 **`onecode-kernel`**（CLI 命令与 Python 导入名仍为 `onecode`），**请勿执行 `pip install onecode`**，请从源码目录安装：

```bash
# Core control kernel & CLI (dist: onecode-kernel, zero runtime deps) / 安装核心内核与命令行工具
pip install -e .

# Optional interactive terminal UI / 安装可选 Textual TUI
pip install -e .[tui]

# Optional decoupled symbolic audit companion package / 可选符号审计扩展包（默认无需安装）
pip install -e ./packages/onecode-symbolic-audit
```

### 2. Verification & Self-Audit / 三层分层验证与系统自审
```bash
# 1) Engineering core tests (fast gate, no symbolic companion required) / 核心工程层测试
bash scripts/verify-core.sh

# 2) Repository docs, license, SBOM & contract meta tests / 仓库元契约与文档一致性测试
bash scripts/verify-meta.sh

# 3) Optional symbolic audit companion tests & micro-benchmark / 可选符号审计伴生包测试
bash scripts/verify-symbolic.sh

# Full verification suite (tests, lint, typecheck, >=75% coverage, doctor) / 全量严格套件
bash scripts/verify.sh

# Local v0.7 verification workflow demo / 本地门禁演示工作流
bash scripts/demo_v07.sh

# Reproducible zero-API adversarial security & token compression benchmarks / 零密钥安全拦截与投影压缩基准
PYTHONPATH=src python3 scripts/security_benchmark.py
PYTHONPATH=src python3 scripts/token_projection_benchmark.py --json

# Environment diagnostics & automaton math audit / 环境自检与状态机公理审计
PYTHONPATH=src python3 -m onecode doctor
PYTHONPATH=src python3 -m onecode.cli doctor
PYTHONPATH=src python3 -m onecode audit-self
PYTHONPATH=src python3 -m onecode math-audit
```
`doctor` runs isolated physical checks (`write_text`, `resume_skip`, `sovereignty_breach`, `http_timeout`), while `math-audit` performs read-only verification of the 64-state `transition graph` (`56` self-loop fixed points, `8` energy-decreasing transitions), `Q6` closure, Lyapunov bounds, and optional `symbolic_extension` attachment status.

`doctor` 会执行物理沙箱链路自检，`math-audit` 则校验 64 态转移图闭合性（56 自环不动点 + 8 降能迁移边）、李雅普诺夫边界与可选符号扩展挂载状态。

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

> `*` Baseline cumulative records (`01–08`) reflect author-run local benchmarks (`claims_mainstream_parity: false`; baseline comparator raw logs not bundled) and include retries/tuning; see *Empirical Scope & Re-Verification Boundaries* above for clean unassisted `Task 4` limits. Curated SWE-bench evaluation snapshot ([swebench_agent_evaluation_report_v1.1.json](benchmarks/reports/swebench_agent_evaluation_report_v1.1.json)) covers **4 evaluated instances** (`4/4` non-statistical preview sample, distinct from the `official_gold_patch` smoke file [swebench-lite-subset.json](benchmarks/reports/swebench-lite-subset.json)).  
> `*` 上表（01–08）为受控单机基线累计实测统计（对照方原始日志未入库，不主张通用同级对标，洁净工作区无提示 `Task 4` 复测上限见上文）；仓库内 SWE-bench 报告归档为 **4 题自选预览子集**（详见 [swebench_agent_evaluation_report_v1.1.json](benchmarks/reports/swebench_agent_evaluation_report_v1.1.json)，不构成完整 300 题榜单结论）。

---

## Community / 社区认可与交流

- Shared with and supported by the **[LINUX DO](https://linux.do)** open-source community (`https://linux.do`). Feedback, issues, and contributions are welcome.  
  本项目保持完整开源，特别感谢并认可 **[LINUX DO](https://linux.do)** 社区在开源技术交流与社区孵化中的支持，欢迎各位佬友试用、讨论与提交共建 PR。

---

## License / 开源协议与集成边界

OneCode is licensed under the **GNU General Public License, Version 3 only (`GPL-3.0-only`)**.  
- **Copyleft Notice / 强开源传染提示**：Because `GPL-3.0-only` is a strong copyleft license, statically importing or embedding the OneCode Python kernel directly inside proprietary closed-source products requires releasing the combined derivative work under GPLv3. Proprietary teams wishing to adopt OneCode can evaluate it over external CLI / HTTP process boundaries or contact the maintainer regarding integration terms.  
  OneCode 遵循 **GNU General Public License v3 only (`GPL-3.0-only`)** 开源协议：直接将该 Python 内核嵌入闭源商业产品并分发时，会触发 GPLv3 的衍生作品开源义务；闭源集成方须通过独立进程 / HTTP 服务边界调用或就授权边界另行沟通。
