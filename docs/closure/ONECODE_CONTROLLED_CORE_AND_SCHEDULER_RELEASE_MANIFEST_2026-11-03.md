# OneCode v1.1 受控内核与终端模式交付封板清单 (Release Manifest v1.1)

- **版本基线**：P0 整改提交 [`1805702`](https://github.com/aidi1723/onecode/commit/1805702) 与 Stage 2 中转目录提交 [`63c94f8`](https://github.com/aidi1723/onecode/commit/63c94f8) 之后的交付工作区。本封板加上解释器单行命令的事前拦截、全工作区标准库影子审计、求解循环只跑可见的 `tests/`，以及内核容器把 `container.cid` 放在中转目录外面。
- **封板日期**：2026-11-03
- **运行环境支持**：macOS (Darwin arm64) & Linux (Ubuntu x86_64 / `n100` @ `<test-node-ip>`)
- **依赖状态**：`pyproject.toml` 保持 `dependencies = []`（纯 Python 3.11+ 原生标准库实现，推荐 Python 3.12+，无外部第三方运行时依赖）
- **全量门禁状态**：本地 1,565 项测试通过、跳过 1 项，用时 50.6 秒。n100 上 1,565 项通过、跳过 2 项，用时 250.8 秒。`check_source_quality.py` 通过，`ruff` 全绿，`mypy` 检查 `src/` 110 个源文件 0 错误。

---

## 1. 交付范围与边界声明 (Scope & Boundary)

### 1.1 本次正式交付与封板范围
1. **标准库受控智能体内核 (OneCode Controlled Agent Core Engine)**：
   - 具备完整全局 WAL 审计账本、十六进制资产快照、预置测试哈希核对链（`th`）及易经数理状态机（卦象 63 乾为天、39 山天大畜、40 火地晋等）；
   - 具备只读探索、行号区间分页、防越界路径守卫（[`PathGuard`](../../src/onecode/kernel/path_guard.py)）及受控模型自愈修复循环（[`model_loop.py`](../../src/onecode/kernel/model_loop.py)）。
2. **开放式全自主终端智能体循环 (Autonomous Terminal Agent Loop)**：
   - 规范实现于 [`src/onecode/kernel/terminal_loop.py`](../../src/onecode/kernel/terminal_loop.py)，由 [`run_model_task`](../../src/onecode/kernel/model_loop.py) 统一调度驱动（`--agent-mode terminal` / `agent_mode="terminal"`）；
   - 具备 `command`、`read_file`、`patch`、`finish` 四项基础动作交互能力；
   - 观察结果预算保障：stdout、stderr、output 均截断至 4,000 字符；
   - **终端循环三道防御闸门**：
     1) 同一条失败命令会先执行两次，第三次相同请求在执行前停下，状态记录为 `halted`，原因记为 `stagnation_loop`；
     2) 同一文件、同一行区间的读取，第三次相同请求停下，原因同样记为 `stagnation_loop`；
     3) `require_modification` 默认开启（`True`），在还没有一次成功的 patch 时，`finish` 会返回 `unmodified_workspace`，易数卦象码记为 39（山天大畜），会话继续进行；成功的 `finish` 记为 63（乾为天）；
   - **沙箱断链自愈机制**：[`src/onecode/kernel/sandbox.py`](../../src/onecode/kernel/sandbox.py) 在 `docker exec` 输出中捕获到 `possible container breakout detected` 时，自动执行 `docker rm -f` 销毁旧容器并重新创建重试一次。
3. **跨语言测试防篡改与命令过滤体系 (Multi-Language Anti-Tamper System)**：
   - 原生标准库判定器 [`is_any_test_path`](../../src/onecode/kernel/symbol_locator.py#L57) 识别 `tests/`、`test/`、`spec/`、`__tests__/`、文件名中的 `.test.` 和 `.spec.`，以及 `_test.go`、`_test.rs`、`_test.py`、`_test.js`、`_test.ts`、`_spec.rb`、`_test.rb` 和 `test_*.rb`；
   - 终端补丁拦截全面纳管上述测试文件，严禁修改测试断言；
   - 危险命令拦截复合正则与参数词元深度拦截 `rm`、`unlink`、`truncate`、`shred`、`sed -i`、重定向（`>`、`>>`）、`tee`、`cp`、`mv`；
   - 严格保证合法只读命令（`cat`、`head`）与常规测试运行命令（`pytest`、`go test`、`cargo test`、`npm test`）零误报放行。
4. **跨语言符号索引与逆向调用链定位器 (Multi-Language Symbol Locator)**：
   - 原生标准库实现于 [`src/onecode/kernel/symbol_locator.py`](../../src/onecode/kernel/symbol_locator.py) 与 [`src/onecode/kernel/symbol_parsers.py`](../../src/onecode/kernel/symbol_parsers.py)；
   - 覆盖 Python（AST 递归）、Go、TypeScript/JavaScript、Rust 四大语言，具备栈帧解析、相对导入穿透、测试作用域符号提取与非测试实现文件置顶能力。
5. **Harbor 规范兼容评测适配器与独立调度器 (Harbor Harness Scheduler & Adapter)**：
   - 规范落地于 [`scripts/harbor_adapter.py`](../../scripts/harbor_adapter.py) 与 [`scripts/harbor_scheduler.py`](../../scripts/harbor_scheduler.py)；
   - 严格遵循 `ONECODE_HARBOR_INTEGRATION_CONTRACT_2026-11-02`，实现 Stage 1（Agent 求解）与 Stage 2（Docker 原生容器验真）权责彻底分离。
6. **SWE-bench 预测集导出适配器与基准统合 (SWE-bench Predictions Adapter & WorkBuddy Suite)**：
   - 规范落地于 [`scripts/swebench_adapter.py`](../../scripts/swebench_adapter.py)，原生将工作区 git diff 提取并写成带 `instance_id` 与 `model_patch` 的 `predictions.jsonl`，随附 4 项单元测试（含 dry-run）；
   - WorkBuddy 综合评测脚本 [`scripts/bench_workbuddy.py`](../../scripts/bench_workbuddy.py) 全面统合 `--agent-mode {classic,terminal}` 开关。

### 1.2 边界与非交付范围明确界定 (Non-Scope & Boundary)
- **非“零漏洞”声明**：`pyproject.toml` 的 `dependencies = []` 保持为空，消除了第三方包引入的外部供应链依赖风险，但这绝不代表自身业务代码与边界处理存在“零漏洞”；
- **非“SWE-bench 已可打榜”声明**：适配器能导出符合格式规范的 `predictions.jsonl`，但不代表 SWE-bench 官方打榜工作已经完成；官方 500 题的大规模 Docker 镜像拉取、环境构建与评测跑分**不在此次封板范围内**，当前仓库内亦不包含官方 500 题的评测日志；
- **测试后缀覆盖**：Ruby 同时识别 RSpec 的 `_spec.rb`、`.spec.`，以及 Minitest 风格的 `_test.rb` 与 `test_*.rb`；
- **模型接口约束**：智能体执行依赖外部 OpenAI 兼容协议的模型接口，需宿主提供有效 API Key 与对应算力端点。
- **求解与评分分离**：求解循环只运行工作区里可见的 `tests/`。隐藏验真留在 Stage 2 和任务结束后的 `run_host_verifier`。命令文本里点名测试路径的 `python -c`、`perl -pi`、`node -e`、`ruby -e` 在执行前拦截。没有写出测试路径的脚本仍会先执行，执行后由测试文件哈希回滚并在本轮会话内保持熔断。

---

## 2. 真实容器验真与基准实测对账 (Container Verification & Benchmark Audit)

1. **真实 Docker 沙箱验真**：
   - 验真进程严格在 `python:3.12-slim-amd64` 容器内运行，回传 64 位小写十六进制真实容器指纹；
   - 杜绝非 Docker 环境下的假验真，非 Harbor 场景严格维持 `"harbor": false`。
2. **WorkBuddy 36 道 Hard 题目基准表现**：
   - 在 `wb-bench-code-v1.0` 题库中全部 36 道具备独立验真器的 Hard 题目基准实测中：
     - **平均奖励得分**：**0.8474**；
     - **满分题数**：**21 道获得 1.0 满分**（满分率 58.3%）。
3. **Harbor 独立调度器终端模式实机实测（`--agent-mode terminal`）**：
   - 评测目录：`<EVAL_WORKSPACE>/harbor-scheduler-eval-terminal`
   - 调度器名称：`onecode_harbor_scheduler_v1`，汇总记录 `"harbor": true`
   - **两道 Hard 题目实测指标与产物凭证对账表**：

| 评测任务 | 智能体动作轨迹 | Stage 1 耗时 | Stage 2 验真耗时 | 容器指纹 (`container.cid`) | 奖励文本 (`reward.txt`) | 断言通过率 (`reward.json`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`data_reporting-hard-support_sla`** | 6 步（find $\to$ 读 smoke $\to$ patch $\to$ CLI 参数错误借卦象 39 自愈 $\to$ 重测 $\to$ finish） | 46.59s | 1.43s | `438282cf865b90c801cb113dccdc15ea63e03e01125f58a7ffed084f8b4c5187` | `1.0` (3 字节) | **13/13 (100%)** |
| **`feature_pipeline-hard-cross_categorical`** | 4 步（精准 patch $\to$ 运行 CLI $\to$ 行内打印验证 $\to$ finish） | 25.21s | 1.43s | `2255af6aa306decc9ae63be1b3747873295f2555a880f243f0c64c243255f0bb` | `1.0` (3 字节) | **13/13 (100%)** |

- **综合表现**：通过率 **2/2（100%）**，平均得分 **1.0000**，断言通过率 **26/26（100%）**；
- **防伪与权属**：`container.cid` 由 Docker CLI 在宿主侧生成。正式 `log_dir` 不挂进容器。容器内 `/log_dir` 绑定到正式目录同级的宿主中转目录，容器以 `--rm` 退出后中转文件仍在。调度器核对退出码、`tests_passed` / `tests_total` 和 `tests` 数组，再写入正式的 `reward.txt` 与 `reward.json`。退出码非 0 却给出正分、满分缺少正的断言计数，或 `tests` 数组为空、与计数不一致时，正式奖励记 0.0。求解阶段不把隐藏验真器路径写入工作区。这不覆盖宿主 root 或内核级逃逸。

---

## 3. 真实开源与工程仓库符号定位实测对账 (Real Repository Localization Audit)

在 `n100` Linux 节点实测加载并运行 [`SymbolLocator`](../../src/onecode/kernel/symbol_locator.py) 对账记录：

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
| **TypeScript 真实工程**<br>`<EXTERNAL_PROJECT>/src` | 515 个 | 3,637 条 | 栈帧指向 `lib/recruiting.ts:42`（调自 `__tests__/recruiting.test.ts`）：<br>**第 1 名**：`lib/recruiting.ts` 的 `save`（行 39–46，置信度 **0.90**，`is_test=False`）<br>**第 2 名**：`lib/recruiting.ts` 的 `upsertRecruitingRecord`（置信度 0.85） | 成功穿透，测试严格置底 |
| **Rust 真实工程**<br>`<EXTERNAL_PROJECT>/src-tauri` | 2 个 | 19 条 | 注入 Rust panic（`src/main.rs:45:9`）：<br>**第 1 名**：`src/main.rs` 的 `sidecar_target_triple`（行 42–67，置信度 **1.00**，`is_test=False`） | 作用域与行号 100% 命中 |
| **Go 真实开源库**<br>`filippo.io/edwards25519@v1.1.1` | 24 个 | 223 条 | 1. 相对路径 `scalarmult.go:40`：<br>**第 1 名**：`scalarmult.go` 的 `Point.ScalarBaseMult`（行 33–80，置信度 **1.00**，行 40 注释落在其行跨度内）<br>2. 完整包路径 `filippo.io/edwards25519/scalarmult.go:40`：<br>**第 1 名**：`scalar.go` 的 `Scalar.Multiply`（置信度 **0.85**） | 正确解析，测试符号过滤 |

---

## 4. 易经数理与状态跃迁规范定义

系统中统一定义的易数状态码规范（收录于手册与状态机）：
- **63（乾为天）**：任务顺利完工，元亨利贞，成功状态（如 `finish` 成功完工）；
- **39（山天大畜）**：遭遇环境受阻、未修改代码提前完结拦截或命令报错，刚健笃实，进入冷却或重试自愈；
- **40（火地晋）**：越界阻断、防篡改触发或停滞熔断，顺而丽大明，阻断违规操作；
- **17（水雷屯）**：网络超时或连接等待，险而健，保存快照断点；
- **21（水火既济）** / **20（水山蹇）** / **10（雷水解）**：备用辅助跃迁卦象。

---

## 5. 关键源码文件指纹与对账表 (Artifact Integrity)

| 文件路径 | macOS 本地 MD5 散列 | Linux `n100` MD5 散列 | 对账状态 |
| :--- | :--- | :--- | :---: |
| [`src/onecode/kernel/model_loop.py`](../../src/onecode/kernel/model_loop.py) | `19dd606efd76527e4eaf8c7bf5492a61` | `19dd606efd76527e4eaf8c7bf5492a61` | 一致 |
| [`src/onecode/kernel/terminal_loop.py`](../../src/onecode/kernel/terminal_loop.py) | `3f9160a4da8bef07a419a4065aa286e7` | `3f9160a4da8bef07a419a4065aa286e7` | 一致 |
| [`src/onecode/kernel/symbol_locator.py`](../../src/onecode/kernel/symbol_locator.py) | `b1b5da100b77b8ff9a015052b4a1bee0` | `b1b5da100b77b8ff9a015052b4a1bee0` | 一致 |
| [`src/onecode/kernel/symbol_parsers.py`](../../src/onecode/kernel/symbol_parsers.py) | `53aa5bb7fa0649995255fbf1418f0911` | `53aa5bb7fa0649995255fbf1418f0911` | 一致 |
| [`scripts/harbor_adapter.py`](../../scripts/harbor_adapter.py) | `be46384312736a7a858775da7845bc9d` | `be46384312736a7a858775da7845bc9d` | 一致 |
| [`scripts/harbor_scheduler.py`](../../scripts/harbor_scheduler.py) | `3f8824b23d0c98bc9126e54f28014f6f` | `3f8824b23d0c98bc9126e54f28014f6f` | 一致 |
| [`scripts/bench_workbuddy.py`](../../scripts/bench_workbuddy.py) | `b191cf9db21d75f527c7f2253cfdc811` | `b191cf9db21d75f527c7f2253cfdc811` | 一致 |
| [`scripts/swebench_adapter.py`](../../scripts/swebench_adapter.py) | `9d01105b95e82689c2b888277708393e` | `9d01105b95e82689c2b888277708393e` | 一致 |

---

## 6. 终审封板与交付结论 (Final Delivery Sign-Off)

在已经完成实机实测与严格对账的技术边界内，OneCode v1.1 作为**标准库受控智能体内核**正式封板交付：
1. **纯标准库受控内核**：零外部第三方依赖，周易六十四卦状态机控制流，全局 WAL 事务账本；
2. **两道 Hard 题目的真实容器对账**：`support_sla` 与 `cross_categorical` 阶段 2 奖励 1.0、断言 13/13 全过、Docker 64 字节 CID 属主 `runner:runner`、容器奖励属主 `root:root`；
3. **多语言符号定位实测样本**：Python AST 递归解析（`marshmallow` 实测第 1 名命中缺陷修复点）、Go/TS/Rust 多语言符号索引与跨栈帧调用链溯源；
4. **预测文件导出器**：[`scripts/swebench_adapter.py`](../../scripts/swebench_adapter.py) 支持按标准格式输出 `predictions.jsonl`（随附 4 项测试含 dry-run）。

**明确说明**：官方 500 题的大规模镜像拉取和跑分评测不在此版封板交付范围内。系统在已对账范围内指标真实、权属清晰、状态一致，**正式作为受控内核交付封板！**
