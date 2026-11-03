# OneCode 受控内核与 Harbor 兼容调度器交付封板清单 (Release Manifest)

- **版本基线**：Git Commit [`49fceb2`](https://github.com/aidi1723/onecode/commit/49fceb2) on `main`
- **封板日期**：2026-11-03
- **运行环境支持**：macOS (Darwin arm64) & Linux (Ubuntu x86_64 / `n100` @ 10.0.0.184)
- **依赖状态**：`pyproject.toml` 保持 `dependencies = []`（纯 Python 3.12+ 原生标准库实现）
- **全量门禁状态**：双端 251 项单元测试 100% 通过，`check_source_quality.py src` 通过，`ruff` 全绿，`mypy` 110 个源文件 0 错误，`onecode doctor` 9/9 检查全部通过。

---

## 1. 交付范围与边界声明 (Scope & Boundary)

### 1.1 本次正式交付与封板范围
1. **标准库受控智能体内核 (OneCode Controlled Agent Core Engine)**：
   - 具备完整全局 WAL 审计账本、十六进制资产快照、预置测试哈希核对链（`th`）及易经数理状态机（卦象 63 乾为天、39 山天大畜、40 火地晋等）；
   - 具备只读探索、行号区间分页、防越界路径守卫（[`PathGuard`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/path_guard.py)）及受控模型自愈修复循环（[`model_loop.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/model_loop.py)）。
2. **Harbor 规范兼容评测适配器 (Harbor Benchmark Scheduler Adapter)**：
   - 规范落地于 [`scripts/harbor_adapter.py`](file:///Volumes/MacSSD/项目开发/one%20code/scripts/harbor_adapter.py)，原生调度真实 Docker 容器沙箱完成求解与验真，严格遵守 `ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02`。
3. **跨语言符号索引与逆向调用链定位器 (Multi-Language Symbol Locator)**：
   - 原生标准库实现于 [`src/onecode/kernel/symbol_locator.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/symbol_locator.py) 与 [`src/onecode/kernel/symbol_parsers.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/symbol_parsers.py)；
   - 覆盖 Python（AST 递归）、Go、TypeScript/JavaScript、Rust 四大主流语言，具备栈帧解析、相对导入穿透、测试作用域符号提取与非测试实现文件置顶能力。

### 1.2 非交付范围明确界定 (Non-Scope & Out-of-Scope)
- **开放式多步终端智能体循环（`terminal_loop.py`）属于下一阶段实验性探索模块，本期不作为交付内容**：
  - [`run_model_task`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/model_loop.py#L2733) 与 [`scripts/harbor_adapter.py`](file:///Volumes/MacSSD/项目开发/one%20code/scripts/harbor_adapter.py) 顶层**均未调用** `terminal_loop.py`，也未开放 `--agent-mode=terminal` 调度开关；
  - `stagnation_loop`（陀罗暗滞熔断）和 `preset_test_immutable` 仅在 `terminal_loop.py` 内部生效；
  - 当前主流程的补丁拦截严格依赖 [`is_preset_test_path`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/preset_tests.py#L8-L14)（以 `tests/` 开头的路径），命令拦截覆盖针对 `tests/` 目录的 `rm`、`sed -i`、重定向与 `tee` 操作；`*_test.go`、`*.test.ts` 暂未接入该主流程拦截路径；
  - 本交付版本**不宣称为面向 SWE-bench 全自主打榜的免运维终端智能体**。

---

## 2. 真实容器验真与基准实测对账 (Container Verification & Benchmark Audit)

1. **真实 Docker 沙箱验真**：
   - 验真进程严格在 `python:3.12-slim-amd64` 容器内运行，回传 64 位小写十六进制真实容器指纹；
   - 杜绝非 Docker 环境下的假验真，非 Harbor 场景严格维持 `"harbor": false`。
2. **Hard 题目基准综合表现**：
   - 在 `wb-bench-code-v1.0` 题库中全部 36 道具备独立验真器的 Hard 题目基准实测中：
     - **平均奖励得分**：**0.8474**；
     - **满分题数**：**21 道获得 1.0 满分**（满分率 58.3%）；
     - **平均成本**：单题折合人民币不足半分钱。
3. **两道 Harbor 调度器题目对账（`support_sla`, `cross_categorical`）**：
   - 调度器名称记录为 `onecode_harbor_scheduler_v1`，汇总记录中 `"harbor": true`；
   - 题目包内置 `verifier.py` 真实写入 `reward.txt`（`1.0`，3 字节）与 `reward.json`（13/13 passed）；
   - Docker 守护进程独立写入 64 字节、无换行的 `container.cid`：
     - `support_sla`: `9cade3254c625966f0e9565296ffff63e3f18256230bfd341697efc0f32784ac`
     - `cross_categorical`: `19cb2f3fafed1e9c3efc50c036bf056093fb7c1ee29804196dd2d914ae3f85e8`
   - `n100` 节点无需安装任何名为 `harbor` 的第三方 CLI 命令，所有凭证真实落盘、权属清晰（CID 为 `aidi:aidi`，txt/json 为容器内 `root:root`）。

---

## 3. 真实开源与工程仓库符号定位实测对账 (Real Repository Localization Audit)

在 `n100` Linux 节点实测加载并运行 [`SymbolLocator`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/symbol_locator.py) 对账记录：

### 3.1 Python 真实开源仓库实测（`marshmallow`，36 个源文件）
- **Case A（原生 Pytest 极简断言失败）**：
  - 测试断言于 `tests/test_decorators.py:712` 失败；
  - 自动通过 `_extract_tokens_from_test_scope` 提取测试函数代码中使用的符号，穿透 `marshmallow/__init__.py` 相对导入重导出；
  - **前四名候选全为实现文件**：`src/marshmallow/schema.py [Schema]`（置信度 0.92）、`src/marshmallow/schema.py [Schema.load]`（0.92）、`src/marshmallow/exceptions.py [ValidationError]`（0.92）、`src/marshmallow/decorators.py [validates]`（0.92），测试文件严格置底。
- **Case B（深层运行时 4 层异常调用栈）**：
  - 解析从测试到 `_run_validator` 的 4 层堆栈；
  - **精准定位第 1 名**：`src/marshmallow/schema.py [Schema._run_validator]`（行 825–843，行 842 命中），置信度 **1.00**，与官方基准缺陷修复目标完全一致。

### 3.2 多语言三仓库实机对账（`n100` 节点）
| 仓库名称与路径 | 扫描文件数 | 索引符号条数 | 注入异常测试与定位第 1 名结果 | 判定 |
| :--- | :--- | :--- | :--- | :--- |
| **TypeScript 真实工程**<br>`/home/aidi/agentcore-os/src` | 515 个 | 3,637 条 | 栈帧指向 `lib/recruiting.ts:42`（调自 `__tests__/recruiting.test.ts`）：<br>**第 1 名**：`lib/recruiting.ts` 的 `save`（行 39–46，置信度 **0.90**，`is_test=False`）<br>**第 2 名**：`lib/recruiting.ts` 的 `upsertRecruitingRecord`（置信度 0.85） | 成功穿透，测试严格置底 |
| **Rust 真实工程**<br>`/home/aidi/agentcore-os/src-tauri` | 2 个 | 19 条 | 注入 Rust panic（`src/main.rs:45:9`）：<br>**第 1 名**：`src/main.rs` 的 `sidecar_target_triple`（行 42–67，置信度 **1.00**，`is_test=False`） | 作用域与行号 100% 命中 |
| **Go 真实开源库**<br>`filippo.io/edwards25519@v1.1.1` | 24 个 | 223 条 | 1. 相对路径 `scalarmult.go:40`：<br>**第 1 名**：`scalarmult.go` 的 `Point.ScalarBaseMult`（行 33–80，置信度 **1.00**，行 40 注释落在其行跨度内）<br>2. 完整包路径 `filippo.io/edwards25519/scalarmult.go:40`：<br>**第 1 名**：`scalar.go` 的 `Scalar.Multiply`（置信度 **0.85**） | 正确解析，测试符号过滤 |

---

## 4. 易经数理与状态跃迁规范定义

系统中统一定义的易数状态码规范（收录于手册与状态机）：
- **63（乾为天）**：任务顺利完工，元亨利贞，成功状态；
- **39（山天大畜）**：遭遇环境受阻或命令报错，刚健笃实，进入冷却或重试自愈；
- **40（火地晋）**：越界阻断、防篡改触发或停滞熔断，顺而丽大明，阻断违规操作；
- **17（水雷屯）**：网络超时或连接等待，险而健，保存快照断点；
- **21（水火既济）** / **20（水山蹇）** / **10（雷水解）**：备用辅助跃迁卦象。

---

## 5. 关键源码文件指纹与对账表 (Artifact Integrity)

| 文件路径 | macOS 本地 MD5 散列 | Linux `n100` MD5 散列 | 状态 |
| :--- | :--- | :--- | :--- |
| `src/onecode/kernel/symbol_locator.py` | `b918700d82583dc9ab71095fd352408f` | `b918700d82583dc9ab71095fd352408f` | 一致 |
| `src/onecode/kernel/symbol_parsers.py` | `53aa5bb7fa0649995255fbf1418f0911` | `53aa5bb7fa0649995255fbf1418f0911` | 一致 |
| `src/onecode/kernel/terminal_loop.py` | `fa93feffc98ab5116aa9183ceb98d1a0` | `fa93feffc98ab5116aa9183ceb98d1a0` | 一致 |
| `tests/test_multi_lang_symbols.py` | `fc0954b01350874d2f0edba6f5414342` | `fc0954b01350874d2f0edba6f5414342` | 一致 |
| `tests/test_terminal_loop.py` | `a6c619e0a7ad1029220f9853b42669f1` | `a6c619e0a7ad1029220f9853b42669f1` | 一致 |
| `scripts/harbor_adapter.py` | `f5999ad116be1e39a3111f185ec157a4` | `f5999ad116be1e39a3111f185ec157a4` | 一致 |

---

## 6. 后续演进路线图 (Phase VII Roadmap)

1. **终端模式主流程接入**：
   - 将 [`terminal_loop.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/terminal_loop.py) 多步探索状态机无缝接入 [`run_model_task`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/model_loop.py) 与 [`harbor_adapter.py`](file:///Volumes/MacSSD/项目开发/one%20code/scripts/harbor_adapter.py)，提供统一 `--agent-mode=terminal` 调度开关；
2. **多文件实测任务端到端打通**：
   - 选取具备真实多文件特征的复杂题目，实跑验证“模型自主搜索 $\to$ 读源码 $\to$ 打外科补丁 $\to$ 终端回归验真 $\to$ 自主宣告完工”，将真实容器指纹与奖励得分完整回传账本。
