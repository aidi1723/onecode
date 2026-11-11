# OneCode v0.8.0 后续开发手册

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while implementing. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this handbook task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **后续会话开场白（直接粘贴）：**
> 按 `docs/superpowers/plans/2026-10-16-onecode-followup-development-handbook.md` 执行下一个未勾选的 Task。先写失败测试，再改业务代码。不要改已封口的控制面公式，不要把 `claims_mainstream_parity` 设为 true，不要碰密钥、同步脚本或 n100 浸泡，除非当前 Task 明确要求。

**Goal:** 把 2026-10-16 全量审计仍未关闭的工程缺口收成可逐条执行的后续开发合同，使门禁、审批、原因码和观测边界与代码现状对齐。

**Architecture:** 八卦层继续只消费工具结局，不新增卦。`classify_outcome` 仍把结局映射进现有 64 态。易经深算（动爻、承乘比应、十二消息卦、大衍、互卦、交卦）继续只进 Evidence / Trace。硬控制面（`transition`、`dispatch`、`execution_bandwidth`、`sovereignty_fire`、sandbox、verifier）禁止读取这些观测字段。本手册只修契约、门禁和文档，不扩展模型能力，不重开双机编排。

**Tech Stack:** Python 3.11+，标准库内核，现有 `unittest`、`scripts/verify.sh`、ruff (`E9,F`)、mypy（`src/`）、coverage ≥ 75%。

**依据：** 2026-10-16 项目审计与底层运行规则审查。代码现状以本手册「当前基线」一节为准；旧手册若与源码冲突，以源码和本手册为准。

**日期：** 2026-10-16
**目标版本：** v0.8.0 收口，不签发 v1.0

---

## 0. 怎么用这份手册

1. 只做下一个未勾选的 Task，做完再勾选。
2. 每个行为改动都是：失败测试 → 最小实现 → 聚焦测试绿 → 相关回归 → 勾选。
3. 一个 Phase 的全部 Task 勾选后，必须跑 `bash scripts/verify.sh`。聚焦测试绿灯不能代替门禁。
4. 函数 ≤ 160 行，类 ≤ 500 行。超限先拆，不准往 `ALLOWED_LONG_*` 加白名单。
5. 不新增第三方运行时依赖。
6. 不提交、不推送、不改 `git config`，除非操作者另外明确要求。
7. 密钥、`.env.local`、`scripts/sync_deployment.sh`、n100 浸泡、第三方渗透，全部挂起，见第 3 节。

---

## 1. 不变量（违反即停）

- 不新增卦。`classify_outcome` 只使用已有 6 个可达态：`0, 17, 32, 40, 59, 63`。软缺失并入坤/坤（0），审批/无进展并入离/坤（40）。
- `halt`、`checkpoint`、`discover` 的单次 `dispatch` 仍是 `stop`。多轮循环仍由 `agent_cycle_decision` 把 `discover` 读成 `read_only_continue`。
- 一回合最多两个工具。只读回合里的写和执行仍是 `permission_denied`。
- 默认最多 8 回合。工具输出上限 1500 字，截断必须带剩余长度。
- `register_mcp_tools` 不拉起进程。`run_verifier` 没有可用沙盒时返回 `sandbox_required`，禁止回落到宿主机 `subprocess.run`。
- 观测字段不得进入 `sandbox.py`、`verifier.py`、`execution_engine.py`、`runner.py` 的分支条件。
- `claims_mainstream_parity` 保持 `false`。
- 版本定位保持本地内核 / v0.8.0，不在本手册完成前改成 v1.0。

---

## 2. 已经封口（不要重做、不要回退）

这些能力已经落地。后续 Task 可以写回归测试锁住它们，但不要重写实现，也不要把它们重新标成待建。

| 能力 | 落点 | 说明 |
| --- | --- | --- |
| 多轮执行口审批 | `agent_cycle.py`、`cycle_approvals.py` | 高危工具先挂起，`approval_required` 并入离/坤 |
| 无进展停机 | `agent_cycle.py` | 连续两次 `search_miss` / `path_not_found` / 指纹不变 → `no_progress` |
| 429/503 可继续 | `agent_cycle_decision_for_tool` | `retryable=true` 走 `model_continue`，墙钟超时仍是 `http_timeout` |
| 截断可见 | `OUTPUT_LIMIT = 1500` | 空 `tool_calls` 不能冒充 `completed` |
| MCP 注册不拉起进程 | `mcp_client.py` | `subprocess.Popen` 推迟到批准后的执行 |
| 校验器禁止宿主机回落 | `verifier.py` | 缺配置 / 无 Docker / daemon 不可用 → `sandbox_required` |
| 人工计划拦截 | `execution_engine.py` | MCP 步骤在无 callback 时强制 `approval_required` |
| 只读观测字段 | `hexagram_profile.py` | `moving_lines`、`micro_relations`、`cycle_phase` 已存在 |
| 3.12.7 短浸泡 | 里程碑记录 | n100 上 12 分钟 / 8000 轮 RSS 22.20 MB，不在本手册重跑 |

旧手册勘误：

- `docs/superpowers/plans/2026-10-07-onecode-engineering-and-observability-handbook.md` 第 3 节仍写「这些字段目前不存在」。以源码和 `docs/ICHING_OBSERVABILITY_MAPPING.md` 为准。Task 11 会改掉这段过时表述。
- `docs/ICHING_OBSERVABILITY_MAPPING.md` 2.2 节把承/乘的拼音和字段名写反了。以 `IchingProfileMixin.micro_relations` 为准。Task 11 会改文档，不改字段名。

---

## 3. 明确挂起（本手册不实施）

| 项 | 原因 |
| --- | --- |
| OpenAI 控制台密钥轮换 / 吊销确认 | 人工操作，工程外 |
| `scripts/sync_deployment.sh` 与 n100 双机编排 | 通道已验证后由操作者暂停 |
| 4 小时浸泡与 ARM64 容器复证 | 短浸泡已记录；长跑另开任务 |
| 第三方渗透扫描 | 无外部扫描器合同 |
| 把 `claims_mainstream_parity` 设为 true | 上述项未完成前禁止 |

---

## 4. 当前基线（2026-10-16 源码事实）

后续实现必须对着这些行号和默认值工作。若实现时行号漂移，以符号名为准。

### 4.1 审批默认值分裂

```249:257:src/onecode/kernel/execution_engine.py
def execute_plan(
    ...
    require_explicit_approval: bool = False,
```

- `run_model_task` / `execute_model_plan` 默认 `True`。
- `onecode run-execution-plan`（`src/onecode/cli.py` 约 888–896 行）和 TUI `/exec-plan`（`src/onecode/tui/app.py` `_execution_plan_worker`）走默认值 `False`。
- `GuardrailConfig.require_approval_for` 默认已含 `write_text`、`patch_text`、`run_command`、`git_commit`。`should_require_approval` 对 MCP 工具也返回 True。真正漏掉的是「无 callback 且 `require_explicit_approval=False`」这条口子。
- 现有测试 `tests/test_execution_engine.py::test_cli_run_execution_plan_loads_json_and_executes_steps` 把「无批准也能写盘」写成了合同。本手册要求改写该测试。

### 4.2 `granted_approval_ids` 不能解挂

```266:301:src/onecode/kernel/agent_cycle.py
def _approval_gate(...):
    if workspace is not None:
        existing = find_pending_approval(workspace, tool_name, params)
        if existing is not None and existing["id"] not in granted:
            return _pending_result(existing, calls)
    if approve is not None and approve(tool_name, params):
        return None
    ...
    return _pending_result(record, calls)
```

当 `existing["id"] in granted` 且 `approve is None` 时，函数落到再次 `persist_pending_approval`，工具仍不执行。`resume_pending_approval` 是另一条删除 pending 文件再执行的 API，不能替代这个参数。

### 4.3 审批密钥无视 `ONECODE_HOME`

`model_config.onecode_home()` 与 `runtime_config` 都读 `ONECODE_HOME`，默认 `~/.onecode`。`cycle_approvals._get_approval_secret` 却写死 `Path.home() / ".onecode" / "approval-secret.key"`。`workspace` 参数未使用。现有 `tests/test_cycle_approvals.py` 用 `patch("pathlib.Path.home")`，会把错误实现测成绿灯。

### 4.4 中断写入清理漏掉下划线

`PathGuard.write_text` 使用 `NamedTemporaryFile(prefix=f".{target.name}.")`。CPython 的随机后缀字符集是 `abcdefghijklmnopqrstuvwxyz0123456789_`。

```13:13:src/onecode/kernel/path_guard.py
_INTERRUPTED_WRITE = re.compile(r"\A\..+\.[A-Za-z0-9]{8}\Z")
```

含 `_` 的临时文件不会被 `discard_interrupted_writes` 删除。`tests/test_path_guard.py` 目前没有这条用例。

### 4.5 原因码与软拒绝不一致

| 实际工具结局 | 产生位置 | `classify_outcome` | `agent_cycle` 软缺失集合 |
| --- | --- | --- | --- |
| `search_miss` | `SearchTextTool` | 坤/坤（0），discover | 计入 |
| `path_not_found` | 测试注入，生产 `read_text` 不产生 | 坤/坤（0） | 计入 |
| `read_target_not_file` | `ReadTextTool`：路径不存在或不是文件都走它 | 默认离/坤（40），halt | 不计入 |
| `list_target_not_found` | `ListFilesTool` | 默认离/坤（40），halt | 不计入 |

`execute_plan` 把 `ValueError` 的 `str(exc)` 直接当成 `reason`。因此读一个不存在的文件会停机，而不是 discover / `read_only_continue`。

软缺失集合散落在 `agent_cycle.py` 第 199、225、392 行和 `hexagram.py` 第 300 行，必须收成一个常量。

### 4.6 HTTPS→HTTP 同主机降级仍携带 Authorization

`StripAuthRedirectHandler` 在 `src/onecode/cli.py`、`src/onecode/kernel/model_provider.py`、`src/onecode/kernel/deepseek_distillation.py` 各有一份。只在 `req.host != new_req.host` 时剥凭证。同主机 `https://` → `http://` 会把 `Authorization` / `api-key` 带到明文。

### 4.7 校验器测试桩靠源码猜结局

`tests/test_run_plan_cli.py`、`tests/test_inspect_cli.py`、`tests/test_model_loop.py` 的 `setUp` 拦截 `onecode.kernel.sandbox.subprocess.run`，通过扫描 `-c` 脚本或测试文件是否包含 `AssertionError`、`time.sleep`、`.fail(` 来伪造结果。这会让「Docker 不可用必须 `sandbox_required`」这类测试变脆，也会让通过/失败与真实 unittest 脱节。

### 4.8 承乘文档写反

代码（不要改字段名）：

```459:462:src/onecode/kernel/hexagram_profile.py
            if lower == 0 and upper == 1:
                cheng += 1
            if lower == 1 and upper == 0:
                sheng += 1
```

文档当前把「承」标成 `sheng`、把「乘」标成 `cheng`。以代码为准。

---

## 5. 文件地图

本手册允许创建或修改的文件。不要改未列出的控制面公式文件，除非某个 Task 点名。

| 文件 | 责任 |
| --- | --- |
| `src/onecode/kernel/path_guard.py` | 中断写入正则 |
| `src/onecode/kernel/execution_engine.py` | `require_explicit_approval` 默认值 |
| `src/onecode/cli.py` | `run-execution-plan --approve`；删除本地 `StripAuthRedirectHandler` |
| `src/onecode/tui/app.py` | `/exec-plan` 无批准不得写盘 |
| `src/onecode/kernel/agent_cycle.py` | `granted_approval_ids` 解挂；使用共享软缺失集合 |
| `src/onecode/kernel/cycle_approvals.py` | `ONECODE_HOME` 审批密钥 |
| `src/onecode/kernel/hexagram.py` | `SOFT_MISS_REASONS` + `classify_outcome` |
| `src/onecode/kernel/execution_tools.py` | 不存在 vs 非文件的原因码 |
| `src/onecode/kernel/http_safety.py` | **新建**。唯一的重定向剥凭证实现 |
| `src/onecode/kernel/model_provider.py` | 改用共享 handler |
| `src/onecode/kernel/deepseek_distillation.py` | 改用共享 handler |
| `tests/sandbox_test_harness.py` | **新建**。确定性沙盒桩 |
| `tests/test_path_guard.py` | 下划线临时文件 |
| `tests/test_execution_engine.py` | 默认审批、CLI `--approve` |
| `tests/test_agent_cycle.py` | granted id 解挂、软缺失 |
| `tests/test_cycle_approvals.py` | `ONECODE_HOME` |
| `tests/test_execution_tools.py` | `path_not_found` / `read_target_not_file` |
| `tests/test_hexagram.py` 或现有 iching 测试 | 软缺失映射到状态 0 |
| `tests/test_http_safety.py` | **新建** |
| `tests/test_tui_layout.py` 或 `tests/test_tui_model_closure.py` | TUI `/exec-plan` |
| `tests/test_run_plan_cli.py`、`tests/test_inspect_cli.py`、`tests/test_model_loop.py` | 换成共享沙盒桩 |
| `docs/ICHING_OBSERVABILITY_MAPPING.md` | 承乘勘误 |
| `docs/superpowers/plans/2026-10-07-onecode-engineering-and-observability-handbook.md` | 删掉「字段不存在」 |
| `docs/INDEX.md` | 指向本手册 |
| `docs/closure/ONECODE_V08_MILESTONE_PAUSE_2026-10-08.md` | 下一阶段指向本手册 |

禁止修改：`transition`、`dispatch_decision`、`execution_bandwidth`、`sovereignty_fire` 的公式本身；`scripts/sync_deployment.sh`；任何 `.env*`。

---

## Phase 1：门禁与测试修复

先让 `scripts/verify.sh` 的质量门和校验器相关测试不再靠猜。不改产品默认审批。

### Task 1: 中断写入识别下划线后缀

**Files:**
- Modify: `src/onecode/kernel/path_guard.py`
- Test: `tests/test_path_guard.py`

- [ ] **Step 1: 写失败测试**

在 `PathGuardTests` 追加：

```python
def test_discard_interrupted_writes_removes_tempfile_suffix_with_underscore(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        leftover = workspace / "src" / ".mesh.py.abcd_ef1"
        leftover.parent.mkdir()
        leftover.write_text("partial", encoding="utf-8")
        (workspace / "src" / "mesh.py").write_text("keep\n", encoding="utf-8")
        (workspace / ".gitignore").write_text("ok\n", encoding="utf-8")

        removed = PathGuard.discard_interrupted_writes(workspace)

        self.assertEqual(removed, ["src/.mesh.py.abcd_ef1"])
        self.assertFalse(leftover.exists())
        self.assertTrue((workspace / "src" / "mesh.py").exists())
        self.assertTrue((workspace / ".gitignore").exists())
```

- [ ] **Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_path_guard.PathGuardTests.test_discard_interrupted_writes_removes_tempfile_suffix_with_underscore -v
```

Expected: FAIL，`removed` 为空，`leftover` 仍在。

- [ ] **Step 3: 最小实现**

把 `_INTERRUPTED_WRITE` 改成：

```python
_INTERRUPTED_WRITE = re.compile(r"\A\..+\.[A-Za-z0-9_]{8}\Z")
```

不要扩大到任意隐藏文件。`.gitignore`、`.env`、`.DS_Store` 不得被删。

- [ ] **Step 4: 再跑测试**

```bash
PYTHONPATH=src python -m unittest tests.test_path_guard -v
```

Expected: PASS。

---

### Task 2: 校验器沙盒桩改为真实结局

**Files:**
- Create: `tests/sandbox_test_harness.py`
- Modify: `tests/test_run_plan_cli.py`、`tests/test_inspect_cli.py`、`tests/test_model_loop.py` 的 `setUp`

- [ ] **Step 1: 写共享桩**

`tests/sandbox_test_harness.py` 必须满足：

1. 只拦截 `command[0] == "docker"`。
2. `docker version` / `docker info` / `docker inspect` / `docker create|start|kill` 返回成功的 `CompletedProcess`。
3. `docker run` 若命令里有 `unittest`：在 bind 到 `/workspace` 的宿主机目录上执行

```python
_original_subprocess_run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
    cwd=workspace_path,
    capture_output=True,
    text=True,
    check=False,
)
```

把这次真实 unittest 的 `returncode` / `stdout` / `stderr` 原样返回。

4. `docker run` 若是 `python -c`：在同一 workspace 上执行 `sys.executable -c script`，不要扫描脚本字符串。
5. 禁止出现 `"AssertionError" in script_content`、`"time.sleep" in script_content`、`".fail(" in file_content` 这类分支。
6. 非 docker 命令走原始 `subprocess.run`。

提供：

```python
def install_sandbox_docker_stub(test_case: unittest.TestCase) -> None:
    ...
```

- [ ] **Step 2: 三个测试类的 `setUp` 改为一行**

```python
def setUp(self):
    super().setUp()
    install_sandbox_docker_stub(self)
```

删除三份复制的 `_mock_subprocess_run`。

`test_cli_run_plan_verifier_halts_when_docker_missing` 和 `test_cli_run_plan_verifier_halts_when_docker_daemon_unavailable` 继续在方法内覆盖 `subprocess.run`，行为不变。

- [ ] **Step 3: 先跑会受影响的测试，确认不再靠猜**

```bash
PYTHONPATH=src python -m unittest \
  tests.test_run_plan_cli tests.test_inspect_cli tests.test_model_loop -v
```

Expected: PASS。若有测试依赖「源码含 AssertionError 就失败」，改为在工作区写入真正会失败的 `tests/test_generated.py`（例如 `self.assertEqual(1, 2)`），让宿主 unittest 产生真实失败。

- [ ] **Step 4: 清理未使用导入**

跑：

```bash
PYTHONPATH=src python -m ruff check tests/test_run_plan_cli.py tests/test_inspect_cli.py tests/test_model_loop.py
```

Expected: 无 F401/F811。不要为了过 ruff 加 `# noqa`，除非符号是 CLI 再导出。

---

### Task 3: Phase 1 门禁

- [ ] **Step 1: 跑完整门禁**

```bash
bash scripts/verify.sh
```

Expected: compileall、source-quality、ruff、mypy、unittest、coverage ≥ 75%、`onecode doctor` 全绿。

若只剩与本 Phase 无关的失败，停下来，把失败用例写进手册勘误，不要用改断言换绿灯。

---

## Phase 2：审批与控制面安全收敛

产品口默认必须显式批准。模型路径已经是 True，本 Phase 把人工计划口和多轮 granted id 补齐。

### Task 4: `execute_plan` 默认要求批准

**Files:**
- Modify: `src/onecode/kernel/execution_engine.py`
- Modify: `tests/test_execution_engine.py`
- Modify: 所有直接调用 `execute_plan(...)` 且需要真正写盘的单元测试

- [ ] **Step 1: 写失败测试**

在 `tests/test_execution_engine.py` 增加：

```python
def test_execute_plan_defaults_to_explicit_approval_for_write_text(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        plan = ExecutionPlan(
            task="default approval",
            steps=[
                ExecutionStep(
                    id="write",
                    description="create file",
                    tool_calls=[
                        ToolCallSpec(
                            tool_name="write_text",
                            params={"path": "src/mesh.py", "content": "VALUE = 1\n"},
                        )
                    ],
                )
            ],
        )

        trace = execute_plan(plan, workspace=workspace, tool_registry=default_tool_registry())

        self.assertFalse(trace.success)
        self.assertEqual(trace.step_results[0].status, "failed")
        self.assertEqual(trace.step_results[0].reason, "approval_required")
        self.assertFalse((workspace / "src" / "mesh.py").exists())
```

再增加批准后写盘：

```python
def test_execute_plan_writes_after_approval_callback(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        plan = ExecutionPlan(
            task="approved write",
            steps=[
                ExecutionStep(
                    id="write",
                    description="create file",
                    tool_calls=[
                        ToolCallSpec(
                            tool_name="write_text",
                            params={"path": "src/mesh.py", "content": "VALUE = 1\n"},
                        )
                    ],
                )
            ],
        )

        trace = execute_plan(
            plan,
            workspace=workspace,
            tool_registry=default_tool_registry(),
            approval_callback=lambda step: True,
        )

        self.assertTrue(trace.success)
        self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "VALUE = 1\n")
```

- [ ] **Step 2: 跑测试确认第一条失败**

```bash
PYTHONPATH=src python -m unittest \
  tests.FAKESECRET_e3f4g5h6i7j8k9l0m1n2 \
  tests.FAKESECRET_i3j4k5l6m7n8o9p0q1r2 -v
```

Expected: 第一条 FAIL（当前默认会写盘），第二条 PASS。

- [ ] **Step 3: 改默认值**

```python
require_explicit_approval: bool = True,
```

MCP 步骤在 `require_explicit_approval=False` 时仍须因 `has_mcp` 挂起。`test_mcp_list_tools_halts_when_no_approval_callback` 继续传 `False`，断言不变。

- [ ] **Step 4: 修复被默认值打红的内部测试**

凡是单元测试自己构造计划并期望写盘成功的，显式传入 `approval_callback=lambda step: True`。不要在 `tests/test_model_loop.py` 的 `run_model_task_wrapper` 里继续 `setdefault(..., False)` 来绕过产品默认值；模型路径本就默认 True。若某条测试要验证「调用方主动关闭」，必须在测试里写明 `require_explicit_approval=False`，并断言这是测试专用 opt-out。

- [ ] **Step 5: 回归**

```bash
PYTHONPATH=src python -m unittest tests.test_execution_engine tests.test_model_loop tests.test_web_api -v
```

Expected: PASS。

---

### Task 5: CLI / TUI 人工计划必须显式批准

**Files:**
- Modify: `src/onecode/cli.py`（`run-execution-plan` 参数与分发）
- Modify: `src/onecode/tui/app.py`（`_run_execution_plan` / `_execution_plan_worker`）
- Test: `tests/test_execution_engine.py`、`tests/test_tui_model_closure.py`

- [ ] **Step 1: 改写现有 CLI 测试**

把 `test_cli_run_execution_plan_loads_json_and_executes_steps` 拆成两条：

1. 无 `--approve`：exit code ≠ 0，JSON `success` 为 false，`step_results[0].reason == "approval_required"`，`src/mesh.py` 不存在。
2. 有 `--approve`：exit code 0，文件内容为 `VALUE = 1\n`，现有 shell_projection 断言保留。

- [ ] **Step 2: 确认无 `--approve` 的新断言当前失败**

因为现在 CLI 会直接写盘。

- [ ] **Step 3: 实现 `--approve`**

```python
run_execution_plan_parser.add_argument("--approve", action="store_true")
```

```python
trace = execute_plan(
    plan,
    workspace=Path(args.workspace),
    run_id=args.run_id,
    resume_from_run_id=args.resume_from,
    approval_callback=(lambda step: True) if args.approve else None,
)
```

不要增加环境变量或隐藏配置来跳过批准。不要默认批准。

- [ ] **Step 4: TUI**

`/exec-plan <file>` 无批准标记时调用 `execute_plan` 且 `approval_callback is None`，界面必须显示 `approval_required`，工作区无新文件。

`/exec-plan --approve <file>` 才传入 `approval_callback=lambda step: True`。

写一条 TUI 测试锁住「无 `--approve` 不写盘」。不要为了测试启动完整 Textual 驱动去改布局；优先 patch `_execution_plan_worker` 的调用参数，或直接测 worker。

- [ ] **Step 5: 回归**

```bash
PYTHONPATH=src python -m unittest \
  tests.test_execution_engine.ExecutionEngineTests \
  tests.test_tui_model_closure.TuiModelClosureTests -v
```

Expected: PASS。

---

### Task 6: `granted_approval_ids` 解挂待执行工具

**Files:**
- Modify: `src/onecode/kernel/agent_cycle.py`（`_approval_gate`）
- Test: `tests/test_agent_cycle.py`

- [ ] **Step 1: 写失败测试**

```python
def test_granted_approval_ids_executes_pending_tool_once(self):
    calls: list[tuple[str, dict]] = []

    def execute(tool_name: str, params: dict) -> dict:
        calls.append((tool_name, params))
        return {"status": "completed", "reason": None, "output": "ok"}

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        first = run_agent_cycle(
            propose=lambda history, allowed: [{"tool_name": "run_command", "params": {"argv": ["echo", "ok"]}}],
            execute=execute,
            workspace=workspace,
            max_turns=1,
        )
        self.assertEqual(first["reason"], "approval_required")
        self.assertEqual(calls, [])
        pending_id = first["pending_id"]
        self.assertTrue(pending_id)

        second = run_agent_cycle(
            propose=lambda history, allowed: [{"tool_name": "run_command", "params": {"argv": ["echo", "ok"]}}],
            execute=execute,
            workspace=workspace,
            max_turns=1,
            granted_approval_ids=frozenset({pending_id}),
        )

        self.assertEqual(calls, [("run_command", {"argv": ["echo", "ok"]})])
        self.assertNotEqual(second.get("reason"), "approval_required")
```

再写一条：错误的 id 不得执行。

```python
def test_unknown_granted_approval_id_does_not_execute(self):
    calls: list[tuple[str, dict]] = []

    def execute(tool_name: str, params: dict) -> dict:
        calls.append((tool_name, params))
        return {"status": "completed", "reason": None, "output": "ok"}

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        run_agent_cycle(
            propose=lambda history, allowed: [{"tool_name": "run_command", "params": {"argv": ["echo", "ok"]}}],
            execute=execute,
            workspace=workspace,
            max_turns=1,
        )
        again = run_agent_cycle(
            propose=lambda history, allowed: [{"tool_name": "run_command", "params": {"argv": ["echo", "ok"]}}],
            execute=execute,
            workspace=workspace,
            max_turns=1,
            granted_approval_ids=frozenset({"not-the-id"}),
        )
        self.assertEqual(calls, [])
        self.assertEqual(again["reason"], "approval_required")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src python -m unittest \
  tests.FAKESECRET_k3l4m5n6o7p8q9r0s1t2 \
  tests.FAKESECRET_i4j5k6l7m8n9o0p1q2r3 -v
```

Expected: 第一条 FAIL（第二次仍是 `approval_required`，`calls` 为空）。

- [ ] **Step 3: 最小实现**

```python
        existing = find_pending_approval(workspace, tool_name, params)
        if existing is not None:
            if existing["id"] in granted:
                return None
            return _pending_result(existing, calls)
```

`approve is not None and not approve(...)` 仍返回 `permission_denied`。`resume_pending_approval` 行为不变。只读工具仍不进门。

- [ ] **Step 4: 回归**

```bash
PYTHONPATH=src python -m unittest tests.test_agent_cycle tests.test_host_baseline tests.test_cycle_approvals -v
```

Expected: PASS。阶段 1 的高危注入（`rm -rf`、`git push --force`、写 shell 配置）仍是 0 次系统调用。

---

### Task 7: 审批密钥遵循 `ONECODE_HOME`

**Files:**
- Modify: `src/onecode/kernel/cycle_approvals.py`（`_get_approval_secret`）
- Test: `tests/test_cycle_approvals.py`

- [ ] **Step 1: 写失败测试**

```python
def test_approval_secret_uses_onecode_home_not_path_home(self):
    with TemporaryDirectory() as tmp:
        home = Path(tmp) / "unix-home"
        configured = Path(tmp) / "onecode-home"
        home.mkdir()
        configured.mkdir()
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        with patch.dict(os.environ, {"ONECODE_HOME": str(configured)}, clear=False):
            with patch("pathlib.Path.home", return_value=home):
                persist_pending_approval(workspace, "run_command", {"argv": ["echo", "1"]})

        self.assertTrue((configured / "approval-secret.key").is_file())
        self.assertEqual((configured / "approval-secret.key").stat().st_mode & 0o777, 0o600)
        self.assertFalse((home / ".onecode" / "approval-secret.key").exists())
```

需要 `import os`。

- [ ] **Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.FAKESECRET_s2t3u4v5w6x7y8z9a0b1 -v
```

Expected: FAIL，密钥落在 `Path.home()/.onecode`。

- [ ] **Step 3: 最小实现**

```python
def _get_approval_secret(workspace: Path) -> bytes:
    from onecode.kernel.model_config import onecode_home
    from onecode.kernel.checkpoint import file_lock

    root = onecode_home()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = root / "approval-secret.key"
    ...
```

删除函数体内重复的 `import secrets`（模块顶已导入）。`workspace` 保留在签名中，供 `_sign_record` 调用，但不得用来改密钥根目录。密钥长度仍是 32 字节 / 64 hex；损坏文件继续抛 `ValueError("approval secret is corrupted or unreadable")`。目录 `0o700`，文件 `0o600`。

- [ ] **Step 4: 改现有 `test_signature_and_secret_location`**

不要再 `patch("pathlib.Path.home")` 充当 `ONECODE_HOME`。改成设置 `ONECODE_HOME`，并继续断言篡改 params 后 `find_pending_approval` 返回 `None`。

- [ ] **Step 5: 回归**

```bash
PYTHONPATH=src python -m unittest tests.test_cycle_approvals tests.test_agent_cycle tests.test_host_baseline -v
```

Expected: PASS。

---

### Task 8: Phase 2 门禁

```bash
bash scripts/verify.sh
```

Expected: 全绿。`claims_mainstream_parity` 仍为 false。

---

## Phase 3：运行规则与原因码对齐

目标：生产工具真正产生的缺失原因，与 `classify_outcome`、多轮软拒绝、无进展计数使用同一集合。不新增卦。

### Task 9: 统一软缺失原因

**Files:**
- Modify: `src/onecode/kernel/hexagram.py`
- Modify: `src/onecode/kernel/agent_cycle.py`
- Modify: `src/onecode/kernel/execution_tools.py`（`ReadTextTool.execute`，必要时 `ListFilesTool` / `SearchTextTool`）
- Test: `tests/test_execution_tools.py`、`tests/test_agent_cycle.py`、`tests/test_hexagram.py` 或 `tests/test_iching_kernel.py`

共享常量（放在 `hexagram.py`，供控制和观测两侧只读引用）：

```python
SOFT_MISS_REASONS = frozenset({
    "search_miss",
    "path_not_found",
    "read_target_not_file",
    "list_target_not_found",
})
```

`classify_outcome` 把 `if reason in {"search_miss", "path_not_found"}` 改成 `if reason in cls.SOFT_MISS_REASONS`。映射仍是坤/坤（0）。

`agent_cycle.py` 第 199、225、392 行全部改成 `SOFT_MISS_REASONS`，禁止再手写集合。

- [ ] **Step 1: 写失败测试**

```python
def test_read_text_missing_path_is_path_not_found(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        with self.assertRaises(ValueError) as ctx:
            ReadTextTool().execute({"path": "missing.txt"}, workspace)
        self.assertEqual(str(ctx.exception), "path_not_found")


def test_read_text_directory_is_read_target_not_file(self):
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "src").mkdir()
        with self.assertRaises(ValueError) as ctx:
            ReadTextTool().execute({"path": "src"}, workspace)
        self.assertEqual(str(ctx.exception), "read_target_not_file")


def test_soft_miss_reasons_map_to_kun_kun(self):
    for reason in (
        "search_miss",
        "path_not_found",
        "read_target_not_file",
        "list_target_not_found",
    ):
        self.assertEqual(
            IchingKernel.classify_outcome("halted", reason),
            IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
        )
        decision = agent_cycle_decision("halted", reason)
        self.assertEqual(decision["cycle"], "read_only_continue")
        self.assertEqual(decision["status_code"], 0)
```

再写一条循环测试：连续两次 `read_text` 指向不存在文件，必须在第 3 回合前以 `no_progress` 停机，不得把 `read_target_not_file` 当成硬停。

- [ ] **Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src python -m unittest tests.test_execution_tools tests.test_agent_cycle -v
```

Expected: 缺失路径仍是 `read_target_not_file`；`classify_outcome(..., "read_target_not_file")` 仍是 40。

- [ ] **Step 3: 最小实现**

`ReadTextTool.execute`：

```python
        target = PathGuard.resolve_read_target(workspace, action["path"])
        if not target.exists():
            raise ValueError("path_not_found")
        if not target.is_file():
            raise ValueError("read_target_not_file")
```

`ListFilesTool` 保持 `list_target_not_found`，但该原因必须进入 `SOFT_MISS_REASONS`。

`execute_plan` 继续用 `str(exc)` 作为 reason，不要在引擎里再映射一层。

不要把 `sovereignty_breach`、`permission_denied`、`approval_required` 放进软缺失集合。

- [ ] **Step 4: 隔离回归**

加一条观测隔离断言（可放进现有 `tests/test_iching_observability.py`）：对上述四个 reason 计算 `moving_lines` / `micro_relations` / `cycle_phase` 前后，`IchingKernel.transition`、`dispatch_decision`、`execution_bandwidth` 的返回值必须字节级相同。这是锁红线，不是新功能。

```bash
PYTHONPATH=src python -m unittest \
  tests.test_execution_tools tests.test_agent_cycle tests.test_host_baseline tests.test_iching_observability -v
```

Expected: PASS。

---

### Task 10: 多工具回合按严重度取观察值

**Files:**
- Modify: `src/onecode/kernel/agent_cycle.py`（仅当 Step 2 证明现有逻辑会用成功掩盖失败）
- Test: `tests/test_agent_cycle.py`

严重度从高到低：

1. `permission_denied` / `approval_required` / `sovereignty_breach` / `repeated_action` / `no_progress`
2. `action_exception` / `run_exception` / `http_timeout`
3. `SOFT_MISS_REASONS`
4. `completed` 且 `reason is None`

- [ ] **Step 1: 写测试（先当回归，允许已通过）**

```python
def test_two_tool_turn_does_not_hide_later_halt_behind_earlier_success(self):
    def propose(history, allowed):
        return [
            {"tool_name": "read_text", "params": {"path": "ok.txt"}},
            {"tool_name": "run_command", "params": {"argv": ["echo", "x"]}},
        ]

    def execute(tool_name, params):
        if tool_name == "read_text":
            return {"status": "completed", "reason": None, "output": "ok"}
        return {"status": "halted", "reason": "action_exception", "output": ""}

    result = run_agent_cycle(propose=propose, execute=execute, max_turns=1)
    self.assertEqual(result["reason"], "action_exception")
    self.assertEqual(result["status"], "halted")


def test_two_tool_turn_soft_miss_then_hard_halt_is_hard_halt(self):
    def propose(history, allowed):
        return [
            {"tool_name": "read_text", "params": {"path": "missing.txt"}},
            {"tool_name": "write_text", "params": {"path": "x.py", "content": "1\n"}},
        ]

    def execute(tool_name, params):
        if tool_name == "read_text":
            return {"status": "halted", "reason": "path_not_found", "output": ""}
        raise AssertionError("write_text must not run after a hard stop in the same turn if the second call is not reached; if it is reached, return permission_denied")

    result = run_agent_cycle(propose=propose, execute=execute, max_turns=1)
    self.assertIn(result["reason"], {"path_not_found", "permission_denied", "no_progress"})
```

说明：当前实现在 `status != completed` 时立刻返回，第一条测试应当已经通过。第二条取决于软缺失是否还提前返回。不要为了「看起来更对称」强行让同一回合在软缺失后再执行写工具；只读继续属于下一回合。

- [ ] **Step 2: 跑测试**

```bash
PYTHONPATH=src python -m unittest \
  tests.FAKESECRET_y4z5a6b7c8d9e0f1g2h3 \
  tests.FAKESECRET_u2v3w4x5y6z7a8b9c0d1 -v
```

若第一条 FAIL，再改 `_run_proposal`：回合观察值取 calls 中严重度最高者，而不是 `calls[-1]`。不要改 `aggregate_status` 的位运算。

- [ ] **Step 3: 回归**

```bash
PYTHONPATH=src python -m unittest tests.test_agent_cycle tests.test_host_baseline -v
```

Expected: PASS。

---

### Task 11: Phase 3 门禁

```bash
bash scripts/verify.sh
```

Expected: 全绿。`onecode math-audit` 若在 doctor 中调用，不得因原因码集合扩大而失败。

---

## Phase 4：安全边界清洁与文档勘误

### Task 12: HTTPS→HTTP 同主机降级剥凭证

**Files:**
- Create: `src/onecode/kernel/http_safety.py`
- Modify: `src/onecode/cli.py`、`src/onecode/kernel/model_provider.py`、`src/onecode/kernel/deepseek_distillation.py`
- Create: `tests/test_http_safety.py`

- [ ] **Step 1: 写失败测试**

```python
from urllib.request import Request
from onecode.kernel.http_safety import StripAuthRedirectHandler

class HttpSafetyTests(unittest.TestCase):
    def test_strips_authorization_on_https_to_http_same_host(self):
        handler = StripAuthRedirectHandler()
        req = Request(
            "https://api.example.test/v1",
            headers={"Authorization": "Bearer secret-token", "Api-Key": "k"},
        )
        new_req = handler.redirect_request(
            req, fp=None, code=302, msg="Found", headers={}, newurl="http://api.example.test/v1"
        )
        names = {name.lower() for name in new_req.headers}
        self.assertNotIn("authorization", names)
        self.assertNotIn("api-key", names)

    def test_strips_authorization_on_host_change(self):
        handler = StripAuthRedirectHandler()
        req = Request(
            "https://api.example.test/v1",
            headers={"Authorization": "Bearer secret-token"},
        )
        new_req = handler.redirect_request(
            req, fp=None, code=302, msg="Found", headers={}, newurl="https://evil.example.test/v1"
        )
        names = {name.lower() for name in new_req.headers}
        self.assertNotIn("authorization", names)

    def test_keeps_authorization_on_https_same_host(self):
        handler = StripAuthRedirectHandler()
        req = Request(
            "https://api.example.test/v1",
            headers={"Authorization": "Bearer secret-token"},
        )
        new_req = handler.redirect_request(
            req, fp=None, code=302, msg="Found", headers={}, newurl="https://api.example.test/v2"
        )
        self.assertEqual(new_req.get_header("Authorization"), "Bearer secret-token")
```

`redirect_request` 的签名必须与 `urllib.request.HTTPRedirectHandler.redirect_request` 兼容。若 super() 在测试里因 fp=None 不好构造，改为抽纯函数：

```python
def should_strip_redirect_auth(*, old_url: str, new_url: str) -> bool:
    ...
```

测试先锁 `should_strip_redirect_auth`，handler 只调用它。这是推荐形状，避免和 urllib 内部纠缠。

- [ ] **Step 2: 跑测试确认失败**

把当前三份 handler 之一临时 import 进测试会看到同主机降级仍保留 Authorization。Expected: FAIL。

- [ ] **Step 3: 实现**

```python
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler

def should_strip_redirect_auth(*, old_url: str, new_url: str) -> bool:
    old = urlparse(old_url)
    new = urlparse(new_url)
    if (old.hostname or "").lower() != (new.hostname or "").lower():
        return True
    if (old.scheme or "").lower() == "https" and (new.scheme or "").lower() == "http":
        return True
    return False


class StripAuthRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and should_strip_redirect_auth(old_url=req.full_url, new_url=newurl):
            for key in list(new_req.headers.keys()):
                if key.lower() in {"authorization", "api-key"}:
                    del new_req.headers[key]
        return new_req
```

三个旧副本改为一行 import。禁止再复制类。

- [ ] **Step 4: 回归**

```bash
PYTHONPATH=src python -m unittest tests.test_http_safety tests.test_model_provider_contract tests.test_deepseek_distillation -v
```

Expected: PASS。

---

### Task 13: 文档与手册勘误

**Files:**
- Modify: `docs/ICHING_OBSERVABILITY_MAPPING.md`
- Modify: `docs/superpowers/plans/2026-10-07-onecode-engineering-and-observability-handbook.md`
- Modify: `docs/INDEX.md`
- Modify: `docs/closure/ONECODE_V08_MILESTONE_PAUSE_2026-10-08.md`

- [ ] **Step 1: 改承乘表述，不改代码字段**

`docs/ICHING_OBSERVABILITY_MAPPING.md` 2.2 节必须改成：

```markdown
- **承 (Cheng)**：下阴上阳（$b_i=0, b_{i+1}=1$），记录为 `cheng`。
- **乘 (Sheng)**：下阳上阴（$b_i=1, b_{i+1}=0$），记录为 `sheng`。
- **比 (Bi)**：相邻同性（$b_i = b_{i+1}$）。
- **应 (Ying)**：内外卦对应爻极性相异（$b_i \neq b_{i+3}$ 对于 $i \in \{0, 1, 2\}$）。
```

锁点：乾（63）`bi=5`、`ying=0`、`cheng=0`、`sheng=0`；既济（21）`bi=0`、`ying=3`。这些已由 `tests/test_iching_observability.py` 覆盖，不要改断言去迁就旧文档。

- [ ] **Step 2: 改 2026-10-07 手册第 3 节**

删除「`moving_lines` / `micro_relations` / `cycle_phase` currently do not exist」。改成：字段已在 `hexagram_profile.py` 落地，只进 Evidence；控制面隔离测试见 `tests/test_iching_observability.py`。浸泡与 ARM64 仍标未完成，与第 3 节挂起项一致。

- [ ] **Step 3: 核对索引与里程碑指针**

手册落盘时已写入这两处，实现时只核对链接仍指向本文件，不要删：

- `docs/INDEX.md` Quick Start 与 Development 节
- `docs/closure/ONECODE_V08_MILESTONE_PAUSE_2026-10-08.md` Next Phase 段首

- [ ] **Step 4: 全文搜索过时表述**

```bash
rg -n "currently do not exist|记录为 \`sheng\`|claims_mainstream_parity" docs
```

承乘旧表述必须清零。`claims_mainstream_parity` 仍只能出现在「保持 false」的句子里。

---

### Task 14: Phase 4 门禁

```bash
bash scripts/verify.sh
```

Expected: 全绿。

---

## Phase 5：发布前核对（不发布）

本 Phase 只做核对，不打 tag，不推 GitHub，不改版本号。

### Task 15: 发布核对清单

- [ ] `bash scripts/verify.sh` 全绿。
- [ ] `bash scripts/verify-core.sh` 全绿。
- [ ] `PYTHONPATH=src python -m unittest tests.test_web_api -v` 全绿。
- [ ] `git diff --check` 无空白错误。
- [ ] `rg -n "require_explicit_approval: bool = False" src/onecode/kernel/execution_engine.py` 无匹配。
- [ ] `rg -n "Path.home\(\) / \".onecode\"" src/onecode/kernel/cycle_approvals.py` 无匹配。
- [ ] `rg -n "AssertionError\" in script_content" tests` 无匹配。
- [ ] `rg -n "class StripAuthRedirectHandler" src` 只有 `http_safety.py` 一处。
- [ ] `claims_mainstream_parity` 仍为 false。
- [ ] 工作区无密钥、无 `.env.local` 真值被加入版本库。
- [ ] 不运行 `scripts/release-audit.sh` 的 publish 动作。
- [ ] 不更新 `CHANGELOG.md` 版本号，除非操作者要求发布。

核对比对表：

| 检查 | 期望 |
| --- | --- |
| 无批准的 `execute_plan(write_text)` | `approval_required`，无文件 |
| CLI 无 `--approve` | 同上 |
| CLI 有 `--approve` | 写盘成功 |
| granted 正确 id | 执行一次 |
| granted 错误 id | 仍挂起 |
| `ONECODE_HOME` | 密钥只出现在该目录 |
| 缺失文件 `read_text` | `path_not_found` → 状态 0 |
| 目录 `read_text` | `read_target_not_file` → 状态 0 |
| HTTPS→HTTP 同主机 | 无 Authorization |
| 中断文件 `.foo.py.abcd_ef1` | 被清理 |
| 观测字段 | 不改变 transition/dispatch/bandwidth |

---

## 6. 完成定义

本手册完成，当且仅当：

1. Phase 1–4 的全部 checkbox 已勾选。
2. Task 15 的命令与 `rg` 检查全部通过。
3. 没有把挂起项做成「已完成」。
4. 没有新增卦，没有把观测字段接到控制面。
5. `claims_mainstream_parity` 仍为 false。

完成后写一份短闭环记录到 `docs/closure/ONECODE_FOLLOWUP_HANDBOOK_CLOSURE_2026-10-16.md`（日期按实际完成日），只列：改了哪些契约、跑了哪些门禁、明确没做哪些挂起项。不要写比喻，不要写外部系统。

---

## 7. 每个后续会话的禁止事项

- 不要用改测试断言来迁就旧的不安全默认值。
- 不要在 `run_model_task_wrapper` 或其他测试助手里把产品默认值改回 False，然后声称生产口已收敛。
- 不要把 `read_target_not_file` 重新映射成 `action_exception`。
- 不要为了文档自洽去改 `cheng`/`sheng` 字段名。
- 不要在互卦落入 `{21, 42}` 时加死锁检测。
- 不要因为偏离大衍 25% 去改停机。
- 不要启动 n100 同步或 4 小时浸泡，除非操作者另开任务。
- 不要在本手册范围外重构 TUI 布局、LibreChat、YiZiJue 解码。

---

## 8. 与旧手册的关系

| 手册 | 状态 | 本手册态度 |
| --- | --- | --- |
| `2026-09-29-host-contract-handbook.md` | 阶段 1–5 主体已完成 | 回归锁，不重做 |
| `2026-10-07-onecode-engineering-and-observability-handbook.md` | 观测字段已落地；长浸泡挂起 | Task 13 勘误；浸泡保持挂起 |
| `docs/ICHING_OBSERVABILITY_MAPPING.md` | 红线有效，2.2 节有误 | Task 13 勘误 |
| `docs/closure/ONECODE_V08_MILESTONE_PAUSE_2026-10-08.md` | 边界封口记录 | 下一阶段改指向本手册 |

若旧手册与本手册冲突，执行本手册。
