# OneCode 下一步开发计划手册：受控范围收口与智能体能力演进

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven development (`先写失败测试 -> 最小实现 -> 聚焦测试绿 -> 全量门禁 bash scripts/verify.sh -> 勾选`) while implementing. Steps use checkbox (`- [ ]`) syntax for tracking. Commit or push only when the operator explicitly asks.
>
> **后续会话：** 这份手册的九项任务已经记在 `e61a4b6` 和 `47cccdf`。不要把已经勾完的 Task 再实现一遍。`claims_mainstream_parity` 保持 `false`。

**Goal:** 记录已经落地的三阶段改动：预置测试防篡改、本地哈希账本复核、只读分页、补丁的有限归一化、双阶段校验、可配置修复次数，以及默认仍为 `strict` 的审批模式。

**Architecture:**
- **Phase I（受控范围收口）**：壳层继续作为编排器（Conductor），一次批准只写一个文件，不拉长单次运行循环，不新增卦象，不修改 `IchingKernel.classify_outcome`。
- **Phase II（感知与编辑底座）**：扩展只读工具的分页行区间能力与探索容忍度，为补丁引擎引入行尾空白归一化与定位反馈，解决大文件“看不全、改不准”的物理瓶颈。
- **Phase III（多轮自愈与分级自治）**：修复次数由 `max_repair_attempts` 传入。`run_model_task` 的默认值是 `0`，聊天路径传入 `1`。校验失败的控制原因仍是 `verifier_failed`，卦象仍是离/坤（40）。`classify_outcome` 没有把中间重试改成坎/震（17）。`scoped_auto` 是显式选项，聊天路径不传它，默认保持 `strict`。

**Tech Stack:** Python 3.11+，零第三方核心运行时依赖（标准库内核），`unittest`、`bash scripts/verify.sh`、ruff (`E9,F`)、mypy (`src/`)、coverage $\ge 75\%$。验收主机为开启 Docker 的 `n100`；本地无 Docker 的 Mac 负责日常单测门禁。

**依据：**
- [`docs/closure/ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md`](ONECODE_CONTROLLED_SCOPE_PLAN_2026-10-22.md)
- [`docs/closure/ONECODE_LONG_TASK_PLAN_2026-10-21.md`](ONECODE_LONG_TASK_PLAN_2026-10-21.md)
- [`docs/closure/ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md`](ONECODE_CONDUCTOR_CLOSEOUT_2026-10-22.md)
- 2026-10-23 项目全量代码、运行逻辑与主流 Agent 差距审计报告

**日期：** 2026-10-23  
**当前版本：** v1.0.0（Tag `v1.0.0` 保持在 `dd51424`，Tag `v0.8.0` 保持在 `e1adb3c`）

---

## 0. 怎么用这份手册

1. **严格按序推进**：必须先完成 **Phase I（Task 1 ~ Task 3）** 的全部收口与 `n100` 验收，才允许进入 **Phase II** 与 **Phase III**。
2. **TDD 铁律**：每个 Task 必须严格遵循：`编写失败测试 -> 运行确认 FAIL -> 编写最小业务代码 -> 聚焦测试 PASS -> 运行 bash scripts/verify.sh 全量门禁 -> 勾选 Task`。
3. **代码规模红线**：新增或修改的函数必须 $\le 160$ 行，类必须 $\le 500$ 行（由 `scripts/check_source_quality.py src` 强制检查），严禁向 `ALLOWED_LONG_*` 添加豁免白名单。
4. **依赖红线**：核心内核严禁引入任何第三方运行时依赖（`pyproject.toml` 的 `dependencies` 必须保持 `[]`）。
5. **版本与提交纪律**：未经操作者明确要求，不执行 `git commit`、不执行 `git push`、不移动已有 Git Tag、不在仓库或日志中落盘任何真实 API 密钥。

---

## 1. 核心不变量与分阶段边界（违反即停）

### 1.1 全局永久不变量（所有 Phase 均不可突破）
- **状态空间闭合**：始终维持 6-bit 易经 64 卦状态空间（$Q_6 = \{0..63\}$），不新增第 65 个状态，不引入脱离卦象体系的隐藏控制流分支。
- **主权路径防线**：`PathGuard` 始终拦截路径穿越（`..`）、软链接逃逸、以及对 `.git`、`.github`、`.onecode`、`.env*` 和根配置文件的未授权写入。
- **沙盒硬隔离**：`ONECODE_RUN_COMMAND_SANDBOX=auto` 在无 Docker 时必须返回 `sandbox_required`，严禁静默回退到宿主机执行命令；`scripts/verify.sh` 中严禁硬编码写入 `ONECODE_RUN_COMMAND_SANDBOX=host`。
- **账本密码学完整性**：`.onecode/global-ledger.jsonl` 始终保持 `prev` + `SHA-256` 链式校验与 `fcntl.flock` 跨进程文件锁。
- **测试防作弊铁律**：任何任务执行前已存在的预置测试文件（`tests/**/*.py`），模型严禁修改或删除；一旦预置测试哈希发生变化，交付立即阻断。

### 1.2 Phase I 专属封口约束（在 Phase I 收口前严禁改动）
- 不修改 [`IchingKernel.classify_outcome`](../src/onecode/kernel/hexagram.py#L323)。
- 单次运行内仅限 **1 次**补丁修复（`repair_prompt`）；补丁失配或纯补丁校验失败仅开 **1 次**整文件重写审批（`_offer_complete_rewrite`）；再次失败即刻停在离/坤（40）。
- 补丁保持字节级精确唯一匹配，在 Phase I 内不启用模糊匹配。
- Docker 沙盒保持 `--network none`。
- `agent_cycle.py` 默认保持 `max_turns = 8`、每回合最多 `2` 个工具、只读子代理上限 `3`。
- `claims_mainstream_parity` 保持 `false`，模型通道 `User-Agent` 保持 `onecode/0.8`。

---

## 2. 当前代码基线（2026-10-23 源码事实）

实现后续 Task 时，以此处的符号与行号为准：

1. **命令沙盒与自审**：
   - [`src/onecode/kernel/execution_tools.py`](../src/onecode/kernel/execution_tools.py)：`auto` 模式无 Docker 时返回 `(1, "", "sandbox_required")`。步骤原因仍可能记成 `action_exception`，payload 的 `stderr` 是 `sandbox_required`。
   - [`src/onecode/self_audit.py`](../src/onecode/self_audit.py)：缺少可选依赖 `textual` 时，`tui_bootstrap` 记录 `skipped_reason: textual_not_installed` 并视为通过。
   - [`tests/test_verify_script.py`](../tests/test_verify_script.py)：`test_demo_v07_script_runs_with_current_interpreter` 按当次校验结果分支判断 `completed / deliverable` 或 `halted / blocked`。
   - [`tests/test_rule_parallel_tasks.py`](../tests/test_rule_parallel_tasks.py) 与 [`tests/test_rule_action_tasks.py`](../tests/test_rule_action_tasks.py)：在显式 `host` 或 Docker 可用时断言命令落下文件；否则断言文件没有落下。
2. **计划校验器**：[`validate_model_plan`](../src/onecode/kernel/model_provider.py) 对 `assets` 和 `patches` 调用 `is_preset_test_path`。路径先把 `\` 换成 `/`，去掉前导 `./`，再 `casefold()`。`tests`、`tests/`、`Tests/test_pay.py` 都会拒绝。
3. **壳层写校验**：[`verify_shell_write`](../src/onecode/web/api.py) 在沙盒前比较预置测试哈希。哈希变了就返回 `verifier_failed`，`delivery_status="blocked"`，`preset_tests_changed=True`，并且不运行被改过的测试。聊天路径传入 `max_repair_attempts=1`，不传 `approval_mode`，因此审批保持 `strict`。
4. **全局账本**：[`global_wal_entry`](../src/onecode/kernel/checkpoint.py) 把预置测试哈希写成按正斜杠路径排序的 `th`。[`ledger_matches_workspace`](../src/onecode/kernel/run_inspection.py) 对照磁盘，分别返回 `preset_test_hash_mismatch`、`asset_hash_mismatch`，或沿用链校验错误。`preset_test_hashes` 使用 `as_posix()`，跳过 `__pycache__`。

---

## Phase I：受控范围收口路线（Controlled-Scope Closure）

> **目标**：在不触碰任何已封口控制规则的前提下，锁死“预置测试不可被模型篡改”与“账本可二次复核工作区文件哈希”两条防线。

### Task 1：收口工作区审计改动与无 Docker 命令规则测试（已完成）

**Files:**
- Modified: `src/onecode/kernel/execution_tools.py`
- Modified: `src/onecode/self_audit.py`
- Modified: `src/onecode/tui/app.py`
- Modified: `tests/test_execution_tools_fallback.py`
- Modified: `tests/test_self_audit_cli.py`
- Modified: `tests/test_verify_script.py`
- Modified: `tests/test_version.py`
- Modified: `tests/test_rule_parallel_tasks.py`
- Modified: `tests/test_rule_action_tasks.py`

- [x] **Step 1: 拆分 `test_rule_parallel_tasks.py` 与 `test_rule_action_tasks.py` 的 `host_mode` 断言**
- [x] **Step 2: 运行聚焦测试确认在无 `ONECODE_RUN_COMMAND_SANDBOX` 变量时通过（12 tests OK）**
- [x] **Step 3: 运行单次显式 `ONECODE_RUN_COMMAND_SANDBOX=host` 核对（2 tests OK）**
- [x] **Step 4: 运行全量门禁 `bash scripts/verify.sh`（当时 1271 tests，1 skipped，coverage 86%，doctor `ok`）**
- [x] **Step 5: 已随 `e61a4b6` 提交，并由 `47cccdf` 记录。没有按建议信息单独提交。**

---

### Task 2：预置测试防篡改拦截（Slice 2 — 本地已完成）

**Goal:** 严禁模型计划写入或修补 `tests/` 目录下的文件；在审批通过后、沙盒运行前记录预置测试 SHA-256 快照，一旦发现预置测试被改动，立即以现有 `verifier_failed`（卦象 40）阻断交付，且不再执行被篡改的测试。

**Files:**
- Create: `src/onecode/kernel/preset_tests.py`
- Modify: `src/onecode/kernel/model_provider.py` (`validate_model_plan`)
- Modify: `src/onecode/web/api.py` (`verify_shell_write`, `handle_onecode_plan_approval`)
- Create: `tests/test_preset_tests.py`

- [x] **Step 1: 编写失败测试 `tests/test_preset_tests.py`**
  包含以下 4 个核心测试场景：
  1. `test_preset_test_hash_changes_when_the_file_changes`：验证 `preset_test_hashes(root)` 扫描 `tests/**/*.py`（跳过 `__pycache__`），键名为 `.as_posix()` 正斜杠相对路径，文件内容变化时哈希改变。
  2. `test_a_plan_that_writes_under_tests_is_invalid`：验证 `validate_model_plan` 对 `tests/test_fee.py`、`Tests/test_pay.py`、`tests\test_win.py`、`tests` 无论是 `assets` 还是 `patches` 均抛出含 `"tests/"` 的 `ValueError`。
  3. `test_preset_test_mismatch_uses_the_existing_verifier_halt`：验证 `IchingKernel.classify_outcome("halted", "verifier_failed")` 仍严格等于 `compute_status(LI, KUN)` (40)。
  4. `test_verify_shell_write_blocks_delivery_when_preset_test_changes_without_running_verifier`：验证当传入的 `before` 快照与当前磁盘 `preset_test_hashes(workspace)` 不一致时，`verify_shell_write` 直接返回 `status="halted"`, `reason="verifier_failed"`, `delivery_status="blocked"`, `preset_tests_changed=True`，且不调用 `run_verifier`。

- [x] **Step 2: 运行新测试确认 FAIL**
  ```bash
  PYTHONPATH=src .venv/bin/python -m unittest tests.test_preset_tests -q
  ```

- [x] **Step 3: 实现 `src/onecode/kernel/preset_tests.py` 与拦截逻辑**
  1. 在 `src/onecode/kernel/preset_tests.py` 中实现：
     - `is_preset_test_path(path: str) -> bool`：先将 `\` 替换为 `/`，去掉前导 `./`，再 `.casefold()`；若等于 `"tests"` 或以 `"tests/"` 开头则返回 `True`。
     - `preset_test_hashes(workspace_root: Path) -> dict[str, str]`：`tests/` 不存在时返回 `{}`；否则遍历 `sorted(rglob("*.py"))`，跳过 `__pycache__`，键名使用 `relative_to(workspace).as_posix()`。
  2. 在 `src/onecode/kernel/model_provider.py:validate_model_plan` 中，对每个 `asset.path` 和 `patch.path` 检查 `is_preset_test_path(path)`，命中则 `raise ValueError(f"paths under tests/ are protected: {path}")`。
  3. 在 `src/onecode/web/api.py` 中：
     - `handle_onecode_plan_approval` 在调用 `execute_model_plan` **之前**记录 `before_tests = preset_test_hashes(workspace)`，传入 `verify_shell_write(result, workspace, before_tests=before_tests)`；
     - `verify_shell_write` 发现 `before_tests is not None and preset_test_hashes(workspace) != before_tests` 时，不运行沙盒，直接返回阻断字典；若一致且校验通过，将 `result["preset_test_hashes"] = before_tests` 挂到结果上供 Task 3 入账。

- [x] **Step 4: 运行聚焦测试与全量门禁**
  ```bash
  PYTHONPATH=src .venv/bin/python -m unittest tests.test_preset_tests tests.test_web_api tests.test_model_loop -q
  bash scripts/verify.sh
  ```

- [x] **Step 5: 已随 `e61a4b6` 提交，并由 `47cccdf` 记录。没有按建议信息单独提交。**

---

### Task 3：全局账本记录并二次复核预置测试哈希（已完成并在 n100 实体验收）

**Goal:** 在全局账本 `.onecode/global-ledger.jsonl` 的交付记录中写入预置测试路径与 SHA-256（字段 `th`），并提供 `ledger_matches_workspace(workspace)` 供事后随时与磁盘文件比对。

**Files:**
- Modify: `src/onecode/kernel/checkpoint.py` (`compact_completed_ledger_result`, `global_wal_entry`)
- Modify: `src/onecode/kernel/run_inspection.py` (`ledger_matches_workspace`)
- Modify: `src/onecode/web/api.py`（确保聊天/审批完成写账本时透传 `preset_test_hashes`）
- Modify: `tests/test_wal.py`

- [x] **Step 1: 在 `tests/test_wal.py` 中编写失败测试**
  1. `test_global_wal_entry_records_preset_test_hashes`：验证 `global_wal_entry` 将 `preset_test_hashes` 编码为按路径正斜杠排序的 `entry["th"] = [{"p": "tests/test_fee.py", "s": "abc"}]`，并忽略非 `tests/` 或非 `.py` 路径。
  2. `test_ledger_matches_workspace_detects_tampered_preset_test_and_intact_workspace`：
     - 写入一条含 `th` 与 `as` 的全局 WAL 记录；
     - 文件未改动时，`ledger_matches_workspace(workspace)` 返回 `None`；
     - 篡改 `tests/test_fee.py` 后，返回 `"preset_test_hash_mismatch"`；
     - 篡改 `src/fee.py` 后，返回 `"asset_hash_mismatch"`；
     - 篡改账本中的 `hash` 字段后，返回 `"global_wal_chain_hash_mismatch"`。

- [x] **Step 2: 运行聚焦测试确认 FAIL**
  ```bash
  PYTHONPATH=src .venv/bin/python -m unittest tests.test_wal -q
  ```

- [x] **Step 3: 实现账本 `th` 字段写入与 `ledger_matches_workspace` 核对函数**
  1. 在 `src/onecode/kernel/checkpoint.py` 中：
     - 确保 `compact_completed_ledger_result` 保留 `preset_test_hashes`；
     - 在 `global_wal_entry` 中，当 `result.get("preset_test_hashes")` 为非空 `dict` 时，过滤出以 `tests/` 开头且以 `.py` 结尾的键，按正斜杠路径排序生成 `entry["th"] = [{"p": k, "s": v} for k, v in sorted(...)]`。
  2. 在 `src/onecode/kernel/run_inspection.py` 中实现 `ledger_matches_workspace(workspace: Path) -> str | None`：
     - 调用 `read_validated_global_wal_entries(workspace)`（捕获链校验异常并映射为 `"global_wal_chain_prev_mismatch"` 或 `"global_wal_chain_hash_mismatch"`）；
     - 找到最后一条含 `th` 或 `as` 的记录，逐一计算 `workspace / item["p"]` 的当前 SHA-256；
     - 若 `th` 中文件缺失或哈希不符，返回 `"preset_test_hash_mismatch"`；若 `as` 中文件缺失或哈希不符，返回 `"asset_hash_mismatch"`；全部一致返回 `None`。

- [x] **Step 4: 本地单测覆盖账本 `th` 与 `ledger_matches_workspace`**
  1. [x] Mac 上 `bash scripts/verify.sh`：`Ran 1293 tests`，`OK (skipped=1)`，覆盖率 86%，doctor `ok`。跳过项是 `test_global_onecode_command_points_to_project_entrypoint`。
  2. [x] 2026-10-23 把当前 `src/`、`tests/`、`scripts/` 同步到 n100 后，`bash scripts/verify.sh` 为 `Ran 1293 tests`，`OK (skipped=2)`，覆盖率 86%，doctor `ok`，`production_ready: true`。多出的跳过项是未挂载 distilled dataset 的 `test_four_known_leaks_remain_pytest_rules`。
  3. `test_e2e_n100.py` 不在仓库里。四项端到端结果不记入本手册。

- [x] **Step 5: 已随 `e61a4b6` 提交，并由 `47cccdf` 记录。没有按建议信息单独提交。**

---

## Phase II：智能体感知与编辑底座升级（Agent Perception & Editing Foundation）

> **准入条件**：Phase I（Task 1 ~ 3）全部勾选关闭，且经操作者明确授权开启 Phase II。
> **架构原则**：解决当前模型在大中型代码库中“看不全文件、搜两次未命中就熔断、打补丁因空格差异失败”的三大工程卡点。不改变 64 卦状态定义。

### Task 4：为 `ReadTextTool` 增加行号区间分页与行号前缀标注

**Problem:** 当前 [`ReadTextTool`](../src/onecode/kernel/execution_tools.py#L108-L143) 只支持从文件开头读取 `max_bytes` / `max_lines`，且在 `agent_cycle.py` 中被截断为 1,500 字符。对于 500 行的代码文件，模型永远无法看到第 100~350 行的内容，导致无法定位 Bug 或编写精确补丁。

**Files:**
- Modify: `src/onecode/kernel/execution_tools.py` (`ReadTextTool`)
- Modify: `src/onecode/kernel/model_provider.py` (`MODEL_TOOL_CONTRACTS["read_text"]`)
- Modify: `tests/test_execution_tools.py`

- [x] **Step 1: 在 `tests/test_execution_tools.py` 编写失败测试**
  - 测试传入 `start_line=10, end_line=20` 时，只返回第 10~20 行（含边界，1-indexed），并返回 `start_line`、`end_line`、`total_lines` 元数据；
  - 测试传入 `line_numbers=True` 时，每行带 `{lineno}: ` 前缀；
  - 测试未传 `start_line` / `end_line` 时，100% 保持现有返回格式与向后兼容性。

- [x] **Step 2: 实现分页读取逻辑并通过 `bash scripts/verify.sh`**

---

### Task 5：解耦“只读探索未命中”与“写操作无进展”并扩容观察窗口

**Problem:** 当前 [`agent_cycle.py`](../src/onecode/kernel/agent_cycle.py#L145) 中，只要 `search_text` 或 `glob_files` 连续 2 次未搜到结果（`miss_streak >= 2`），立即触发 `no_progress`（卦象 40）强制停机。而在真实代码库探索中，换 3~4 个关键词搜索是正常定位过程。

**Files:**
- Modify: `src/onecode/kernel/agent_cycle.py`
- Modify: `tests/test_agent_cycle.py`

- [x] **Step 1: 在 `tests/test_agent_cycle.py` 编写失败测试**
  - 测试当模型在 `READ_ONLY_TOOLS` 下使用**不同查询参数**连续发生 3 次 `search_miss`、第 4 次命中目标文件时，循环能够继续完成，不被第 2 次 `search_miss` 提前杀死；
  - 测试当模型使用**完全相同的参数**重复调用或连续达到 `max_read_misses`（默认可配，對齐现有单测默认值为 2，长任务模式可配为 6）时，依然准确触发 `repeated_action` 或 `no_progress` 停机；
  - 支持在 `run_agent_cycle` 中传入可配置的 `output_limit: int = OUTPUT_LIMIT`（默认 1,500 保持兼容，智能体模式下可传 `8,000`）。

- [x] **Step 2: 实现参数化探索配额并通过 `bash scripts/verify.sh`**

---

### Task 6：升级补丁引擎 `patching.py`（行尾空白归一化 + 失配上下文定位反馈）

**Problem:** 当前 [`patching.py:apply_patch_preview`](../src/onecode/kernel/patching.py#L42-L64) 仅做 `original.count(intent.search_block)`。模型生成的 `search_block` 只要多一个或少一个行尾空格，就会报 `patch_search_not_found`。此外，[`patching.py`](../src/onecode/kernel/patching.py#L116-L117) 第 117 行存在一行冗余的重复 `return` 语句。

**Files:**
- Modify: `src/onecode/kernel/patching.py`
- Modify: `tests/test_patching.py`（或相关补丁测试文件）

- [x] **Step 1: 编写失败测试**
  - 测试清理 `patching.py` 第 117 行重复 `return`；
  - 测试当精确匹配数为 0 时，尝试对原文件与 `search_block` 进行逐行 `.rstrip(" \t")` 归一化匹配：若归一化后在文件中**唯一匹配 1 处**，则安全应用替换并保持原文件换行符；若匹配 0 处或多处，仍严格抛出 `patch_search_not_found` 或 `patch_search_ambiguous`；
  - 新增辅助函数 `find_closest_patch_context(workspace_root: Path, path: str, search_block: str, context_lines: int = 15) -> dict[str, Any]`：当补丁失配时，利用 `difflib.SequenceMatcher` 找出原文件中最相似的行区间及带行号源码片段，供修复提示词精准定位，避免对大文件盲目发起整文件重写。

- [x] **Step 2: 实现归一化唯一匹配与失配上下文提取，通过 `bash scripts/verify.sh`**

---

## Phase III：多轮受控 ReAct 循环与靶向自愈（Multi-Turn ReAct & Self-Healing）

> **准入条件**：Phase II 全部通过门禁，且操作者决定开启长程智能体能力验证。
> **架构原则**：修复预算由调用方传入。聊天路径仍是 1 次。最终校验失败仍是 `verifier_failed`，离/坤（40）。中间重试没有新的坎/震（17）分支。预置测试快照继续挡住改测试通过。`scoped_auto` 只在显式传入时生效。

### Task 7：支持靶向测试执行（Targeted Unittest Runner）与全量守门双阶段校验

**Goal:** 在多步调试期间，允许沙盒先只运行与改动相关的测试模块（如 `python3 -m unittest tests.test_pay`），秒级返回报错堆栈；待靶向测试通过后，再自动执行全量 `unittest discover -s tests` 守门。

**Files:**
- Modify: `src/onecode/kernel/verifier.py`
- Modify: `src/onecode/web/api.py` (`verify_shell_write`)
- Modify: `tests/test_verifier.py`

- [x] **Step 1: 编写靶向测试校验与回退全量校验的单元测试**
- [x] **Step 2: 实现双阶段沙盒校验器并通过 `bash scripts/verify.sh`**

---

### Task 8：在壳层与模型循环中引入可配置的阶梯式修复预算（Multi-Attempt Patch Repair）

**Goal:** `run_model_task` 的 `max_repair_attempts` 默认是 `0`。聊天路径传入 `1`。调用方传入更大的值时，循环可以按这个次数继续补丁修复。失败原因仍是 `verifier_failed`。修复提示可以带上 `find_closest_patch_context` 和校验输出尾部。

**Files:**
- Modify: `src/onecode/kernel/model_loop.py`
- Modify: `src/onecode/web/api.py`
- Modify: `tests/test_model_loop.py`

- [x] **Step 1: 编写失败测试**
  - 默认 `max_repair_attempts=0` 时不进入修复循环；聊天路径传入 `1`。
  - 调用方传入大于 `1` 的值时，下一次修复可以看到上一轮的源码切片和校验尾部。最终失败仍是 `verifier_failed`，离/坤（40）。成功交付仍走原来的完成卦象。没有把重试改成坎/震（17）。
- [x] **Step 2: 实现阶梯式修复闭环并通过 `bash scripts/verify.sh`**

---

### Task 9：分级审批策略（`strict` vs `scoped_auto`）与真实公开基准端到端验收

**Goal:** 默认 `strict` 仍要求写入批准。显式 `scoped_auto` 时，`src/` 下的写入和补丁可以不再要求批准；`git_commit`、`run_command`、`mcp.*`，以及 `src/` 以外的路径仍要求批准。聊天路径没有传入 `approval_mode`。仓库里没有 SWE-bench Lite 的实跑记录。

**Files:**
- Modify: `src/onecode/kernel/approval_plans.py`
- Modify: `src/onecode/web/api.py`
- Test: `tests/test_approval_plans.py`

- [x] **Step 1: 编写 `strict`（默认）与 `scoped_auto` 审批边界测试**
- [x] **Step 2: 实现分级审批策略并通过本地 `bash scripts/verify.sh`**
- [x] **Step 3: 单元测试覆盖 `strict` 与 `scoped_auto`。`test_e2e_n100.py` 不在仓库中，本步不记录四项端到端结果。**

---

## 3. 演进里程碑总览表

| 阶段 | 编号 | 核心任务 | 关键产出文件 | 状态 |
| :---: | :---: | :--- | :--- | :--- |
| **Phase I** | **Task 1** | 审计改动收口与无 Docker 命令测试分支 | `test_rule_parallel_tasks.py`, `test_rule_action_tasks.py` | ✅ 已完成 |
| **Phase I** | **Task 2** | 预置测试防篡改拦截（计划拒绝 + 校验前哈希比对） | `preset_tests.py`, `model_provider.py`, `web/api.py` | ✅ 已完成 |
| **Phase I** | **Task 3** | 全局账本写入预置测试哈希 `th` 与事后复核函数 | `checkpoint.py`, `run_inspection.py`, `test_wal.py` | ✅ 单测已在仓库中 |
| **Phase II** | **Task 4** | `ReadTextTool` 行区间分页读取与行号标注 | `execution_tools.py`, `model_provider.py` | ✅ 已完成 |
| **Phase II** | **Task 5** | 探索期只读未命中解耦与观察窗口可配扩容 | `agent_cycle.py`, `test_agent_cycle.py` | ✅ 已完成 |
| **Phase II** | **Task 6** | 补丁唯一匹配时的行尾空白归一化、首行缩进前缀保留，以及失配上下文 | `patching.py`, `test_patching.py` | ✅ 已完成 |
| **Phase III** | **Task 7** | 靶向单测快速验证 + 全量回归双阶段沙盒校验 | `verifier.py`, `web/api.py` | ✅ 已完成 |
| **Phase III** | **Task 8** | 可配置补丁修复次数；聊天路径传入 1；失败仍是 `verifier_failed` | `model_loop.py`, `web/api.py` | ✅ 已完成 |
| **Phase III** | **Task 9** | `strict` 为默认；`scoped_auto` 为显式选项 | `approval_plans.py` | ✅ 单测已在仓库中 |
