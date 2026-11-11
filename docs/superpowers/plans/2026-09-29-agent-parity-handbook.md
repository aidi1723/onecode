# OneCode 主流能力补齐执行手册

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while implementing. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用现有八卦运行理论做多轮控制，把通用 agent 的工具、上下文、终端、扩展和界面按阶段补上。

**Architecture:** 八卦层只消费「工具结局」，产出证据用的卦象，以及循环指令 `stop`、`model_continue`、`read_only_continue`、`verify`。新工具不得新增卦。回合数、连续失败和超时走已有的 `resource_budget_exceeded`，在卦象判断之前生效。一次性 `run_model_task` 计划模式保持不变。

**Tech Stack:** Python 3.11+，现有 `IchingKernel`、`outcome_policy`、`unittest`。

**当前进度：** 第 1 阶段的循环决策和假模型循环在本手册之后立刻实现。第 2 阶段起按本手册顺序做，每阶段都要先有失败测试。

---

## 不变量

- `classify_outcome` 仍把结局映射进 64 卦。证据里保留 `status_code`、`transition_action`、`dispatch`。
- 单次运行的 `dispatch_decision` 不变：`halt`、`checkpoint`、`discover` 仍然是 `stop`。
- 多轮循环对同一卦象另作解释，写在 `agent_cycle_decision`，不改 `dispatch_decision`：
  - `halt` → `stop`，把结果交给人。
  - `checkpoint` → `verify`，本阶段先结束循环并记下该指令。
  - `discover` → `read_only_continue`，下一轮只允许 `read_text`、`list_files`、`search_text`、`git_status`。
  - 其余且 `dispatch == continue` → `model_continue`，把工具结果交回模型。成功的乾/乾目前会落到 `cooldown`，循环指令仍是 `model_continue`。
- 一回合最多两个工具调用。写和执行在 `read_only_continue` 期间直接拒绝，原因用已有的 `permission_denied`。
- 默认最多 8 回合。用尽记为 `resource_budget_exceeded`。

## 阶段 1：多轮循环

**Files:**
- Modify: `src/onecode/kernel/hexagram.py`（`search_miss`、`path_not_found` → 坤/坤）
- Modify: `src/onecode/kernel/outcome_policy.py`
- Create: `src/onecode/kernel/agent_cycle.py`
- Test: `tests/test_agent_cycle.py`

- [x] 成功的工具结局产生 `model_continue`，转移动作保持 `cooldown`。
- [x] `search_miss` 产生 `read_only_continue`，证据动作保持 `discover`，`dispatch` 仍是 `stop`。
- [x] `permission_denied` 产生 `stop`。
- [x] `action_exception` 产生 `verify`。
- [x] 假模型先搜索再结束时，循环在两回合内完成，并且把第一轮结果放进第二轮历史。
- [x] 只读回合里出现 `write_text` 时不执行写入，循环以 `permission_denied` 停止。
- [x] 第 9 次提议之前停止，原因为 `resource_budget_exceeded`。
- [x] `tests.test_agent_cycle` 与 `tests.test_iching_kernel` 通过。不改 `run_model_task`。

## 阶段 2：找代码和改代码

**Files:** `src/onecode/kernel/execution_tools.py`，新建 `src/onecode/kernel/code_index.py`，`tests/test_execution_tools.py`

- [x] `search_text` 增加可选正则，并保留字面量默认。扫描上限沿用现有字节和文件数限制。
- [x] 新增 `glob_files` 与 Python `outline`（`ast` 取出函数和类）。找不到时报 `search_miss`。
- [x] `patch_text` 在唯一匹配失败时返回 `patch_mismatch`，不写文件。
- [x] 补丁结果附带统一 diff。按检查点里的 sha256 可以恢复上一版。

## 阶段 3：上下文和记忆

**Files:** `src/onecode/kernel/agent_cycle.py`，新建 `src/onecode/kernel/agent_memory.py`

- [x] 历史超过字符预算时，只保留任务、最近两轮工具结果和一条摘要。
- [x] `.onecode/memory.jsonl` 仅在循环指令不是 `stop` 且调用方显式确认后追加。
- [x] 续聊从该文件读回，不用运行证据冒充长期记忆。

## 阶段 4：终端和 git

**Files:** `execution_tools.py`，`sandbox.py`

- [x] `run_command` 可选流式回调，超时仍落到 `http_timeout`。
- [x] 同一工作区复用一个 Docker 容器；守护进程不可用时保持现在的本机回退。
- [x] `git_diff` 只读。`git_commit` 属于变更工具，沿用审批。

## 阶段 5：扩展和子代理

**Files:** 新建 `src/onecode/kernel/mcp_client.py`，`src/onecode/kernel/subagents.py`

- [x] MCP 工具注册进现有工具表，默认需要批准。连接失败报 `action_exception`。
- [x] 最多 3 个只读子代理。各自有回合预算和证据目录。父循环用现有 `aggregate_status` 合并状态码。

## 阶段 6：界面

**Files:** `src/onecode/web/api.py`，`src/onecode/tui/app.py`

- [x] 聊天流式在每个工具回合结束时推送事件，而不是收齐后再发一个 SSE 块。
- [x] 变更工具先返回 diff，批准后才执行。现有审批计划继续用。

## 阶段 7：可对比评测

**Files:** `benchmarks/tasks/agent/`，`src/onecode/benchmark.py`

- [x] 先加 30 个本地编码任务，记录通过率、回合数和停止原因。
- [x] 再接 SWE-bench Lite 的小子集。未接上之前，不宣称追上主流。

## 完成定义

阶段 1 到 4 的测试都通过，并且 30 个本地编码任务有一份可重复的通过率记录。阶段 5 和 6 可以在该记录出现后并行。阶段 7 的公开子集跑通之前，版本说明仍写本地内核，不写通用 agent 产品。
