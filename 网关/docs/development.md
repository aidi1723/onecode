# 开发与验证

本文档说明一字诀网关的本地开发、测试和发布前检查。

## 环境

当前代码使用 Python 标准库实现核心逻辑。网关服务层需要额外安装：

```bash
python3 -m pip install -r requirements-gateway.txt
```

核心测试不依赖 `pytest`，使用标准库 `unittest`。

## 常用验证命令

运行全部测试：

```bash
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_gateway_plan tests.test_audit tests.test_gateway_server_import tests.test_tool_guard tests.test_tool_preflight tests.test_phase2_dictionary tests.test_reference_patterns tests.test_opcode_primitives tests.test_workflow_loader tests.test_skill_mount_registry tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent tests.test_minimal_gateway_mvp -v
```

校验词典 JSON：

```bash
python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/tmp/programming-agent-skill-dictionary.json
```

校验 schema JSON：

```bash
python3 -m json.tool schemas/agent-skill-dictionary.schema.json >/tmp/agent-skill-schema.json
```

运行词典一致性 validator：

```bash
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
```

校验 V1.0 最小词典：

```bash
python3 -m json.tool agent_skill_dictionary/oneword_dict.json >/tmp/oneword_dict.json
```

编译检查 Python：

```bash
python3 -m compileall -q agent_skill_dictionary
```

运行 HTTP 路由层测试：

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run --with-requirements requirements-gateway.txt python -m unittest tests.test_gateway_server_routes -v
```

或使用 Makefile：

```bash
make route-test
```

说明：`tests/test_gateway_server_routes.py` 依赖 FastAPI/httpx 的 TestClient。如果本机 `python3 -m unittest tests.test_gateway_server_routes -v` 显示 `fastapi test client is not installed`，不要把它当成路由层已验证；使用上面的 `uv run` 命令安装临时依赖后再跑。当前这台机器的 Homebrew Python 3.13/3.14 存在 `pyexpat` 动态库符号问题，`python3 -m pip install ...` 可能在 pip 启动阶段失败，`uv run` 是已验证的绕过方式。

启动临时真实 HTTP 网关并跑控制面 smoke：

```bash
make live-smoke
```

该命令会通过 `uv run` 临时启动 `uvicorn agent_skill_dictionary.gateway_server:app`，等待 `/health`，再调用 `scripts/http_gateway_smoke.py` 检查 `protocol / resolve / preflight / submit-evidence / build-tool / run`。默认还会启动一个本机 mock upstream，验证 `/v1/chat/completions` 代理路径能接管上游返回的 `write_file` tool call，并通过 Build Mode 写入临时 workspace。

代理路径 smoke 现在包含两轮闭环验证：

- 第一轮同 session 接管 mock upstream 返回的 `write_file` tool call，确认文件真实写入临时 workspace，并返回 `next_hexagram=001`。
- 第二轮复用同一个 `session_id` 再请求上游，确认网关从 `.yizijue/build-mode-state-<session_id>.json` 回灌状态，并把工具矩阵过滤为 `["run_pytest"]`。
- 第三轮继续复用同一个 `session_id`，mock upstream 发出 `run_pytest` tool call，确认网关接管验证动作并返回 `status=completed`、`next_hexagram=000`。
- 失败分支会额外触发一次失败的 `run_pytest` tool call，确认网关保持 `HTTP 200` 代理闭环，返回 `status=needs_fix`、`next_hexagram=110`，并附带 soft feedback，而不是把失败命令交给客户端执行或让连接断裂。状态持久化会采用 soft feedback 推荐态，下一轮同 session 回灌到 `101`，上游实际只收到 `["native_inspect_card"]`。随后 mock upstream 发出 `native_inspect_card` tool call，网关接管生成脱水资产卡，并将下一轮状态推进为 `111`；再下一轮同 session 上游实际只收到 `["write_file"]`，回到受限修复权限。最后 mock upstream 发出修复用 `write_file`，网关真实写回临时 workspace，并返回 `next_hexagram=001`，重新进入测试轨道；回修后的 `run_pytest` 再次被接管并返回 `status=completed`、`next_hexagram=000`。

沙盒测试执行前会清理 workspace 内的 `__pycache__` 与 `.pyc`，避免快速改写同名测试文件后 Python 复用旧字节码，导致回修后的真实测试误判失败。

默认使用临时 workspace，避免 Build Mode 写盘 smoke 污染项目根目录；需要指定目录时传 `python scripts/live_gateway_smoke.py --workspace /abs/path`。它会在结束时终止临时网关和 mock upstream 进程。首次运行如果依赖缓存为空，需要访问 PyPI。本机沙箱环境可能拦截 `127.0.0.1` loopback 探活；这种情况下需要在授权环境下重跑 `make live-smoke`。

## 测试覆盖

`tests/test_agent_skill_dictionary.py` 覆盖：

- 词典 validator 无错误。
- `源` 是只读并禁止依赖安装。
- `源` 和 `卫` 的路由与能力模式不同。
- `修` 超过重试次数后熔断到 `查`。
- `查 / 审 / 源 / 卫 / 隔` 都禁止写入。

`tests/test_gateway_core.py` 覆盖：

- 自然语言 `bug + 测试` 会归一化成 `修 + 测`。
- `修 + 测` 会构建成反向执行栈 `["测", "修"]`。
- OpenAI chat request 会被插入 system rule。
- `temperature` 会被执行字策略锁定。
- system rule 会注入参考工作流模式和专业运行逻辑。
- 显式前缀如 `源：...` 优先于关键词规则。
- `问 / 停 / 记 / 评 / 总` 控制意图能归一化到对应执行字。

`tests/test_gateway_plan.py` 覆盖：

- 自然语言能解析成给 Agent 或 UI 使用的执行计划。
- `源：...` 显式前缀能返回来源审计计划。

`tests/test_audit.py` 覆盖：

- 命令输出能生成 stdout、stderr 和整体证据摘要。
- 输出变化会改变证据 hash。
- 审计记录能追加写入 JSONL，并通过 `previous_sha256` 形成链式哈希。

`tests/test_executor.py` 覆盖：

- `execute_command()` 会真实运行命令并捕获 `exit_code`、`stdout` 和 `stderr`。
- 执行结果会生成 SHA-256 证据，并可追加写入审计日志。
- 非零退出码会被如实记录，不会被包装成成功。
- `cwd` 必须位于 `workspace_root` 内，防止越界执行。

`tests/test_context_breaker.py` 覆盖：

- `build_active_context()` 会把完整历史收束成当前状态可用的紧凑上下文。
- 紧凑上下文保留原始需求、最近状态、最近证据哈希、退出码、只读文件清单和文本片段摘要。
- 紧凑上下文不会携带完整 `history`、完整 stdout 或完整 stderr。

`tests/test_summary_executor.py` 覆盖：

- `summarize_active_context()` 会把紧凑上下文转换为稳定 Markdown 交接摘要。
- 摘要会生成 SHA-256 evidence，并可追加写入审计日志。

`tests/test_memory_executor.py` 覆盖：

- `archive_markdown()` 会把 Markdown 归档到指定 memory 目录。
- 归档动作会生成 SHA-256 evidence，并可追加写入审计日志。

`tests/test_tool_guard.py` 覆盖：

- 只读执行字禁止 `write_file`。
- `源` 禁止依赖安装。
- `修` 允许受限写入但禁止未批准安装依赖。
- 明显危险的 shell 命令会被拦截。

`tests/test_phase2_dictionary.py` 覆盖：

- `部 / 数 / 文 / 合 / 搜` 五个 Phase 2 执行字存在。
- 部署、数据、文档、合规、搜索意图能归一化到对应执行字。
- `合` 和 `搜` 的只读权限边界正确。

`tests/test_reference_patterns.py` 覆盖：

- 每个执行字都有 `reference_workflow_patterns`。
- 每个执行字都有 `professional_protocol`。
- `professional_protocol` 必须包含来源项目、专业步骤和硬门规则。
- `修` 绑定调试、TDD 和验证闭环。
- `设` 绑定 DESIGN.md 工作流。
- `卫` 和 `隔` 绑定安全与隔离模式。
- `问 / 停 / 记 / 评 / 总` 绑定人工确认、熔断、项目记忆、二次评估和上下文压缩模式。

`tests/test_opcode_primitives.py` 覆盖：

- 八个根字存在，并且根字指向自己。
- 22 个执行字都有 `root_opcode`、`opcode_vector`、`inheritance_policy`、`six_phase_workflow` 和 `transition_policy`。
- 关键子字继承正确的根字。
- validator 会拒绝子字放宽父字写权限。
- 网关注入根字 Opcode、六步工作流和状态转移策略。

`tests/test_workflow_loader.py` 覆盖：

- workflow registry 包含 8 个根字。
- 每个根字 workflow markdown 能被加载。
- 每个根字 workflow 都包含提示词工程来源、效率控制、精准控制、稳定控制和证据要求。
- 网关会按 `root_opcode` 注入根字 Workflow 摘要。

`tests/test_skill_mount_registry.py` 覆盖：

- Skill Mount registry 包含 8 个根字。
- 每个根字 mount 都有社区来源、硬门和证据要求。
- `查` 挂载 Aider Repo Map 和 SWE-agent ACI。
- `卫` 挂载 Semgrep 和 OSV-Scanner。
- `造` 是 `修` 的派生 mount，不是根字 mount。
- 网关会注入根字 Skill Mount 摘要。

`tests/test_kernel_policy.py` 覆盖：

- 8 个根字都有 Kernel Runtime Policy。
- 网关会注入内核行为规训。
- 网关会按根字过滤 `tools`。
- 内核策略会覆盖 `temperature`。
- `停` 会标记为禁止转发上游模型。
- 原子证据链校验会拒绝缺失字段。

`tests/test_macro_chain.py` 覆盖：

- 功能开发请求会编译为 `查 -> 造 -> 测 -> 修 -> 记 -> 总`。
- 高危安全请求会编译为 `卫 -> 停 -> 问 -> 查 -> 总`。
- `/v1/yizijue/resolve` 计划会包含 `macro_chain`。

`tests/test_one_word_agent.py` 覆盖：

- 8 个 OneWordState 到根字和卦象的映射。
- Compiler 对 bug、报错和默认调查意图的归一化。
- MutationEngine 对失败重试和三次熔断的处理。
- OneWordAgent 输出可审计 `trace` 和 `audit_log`。
- `[查]` 状态可以通过 `enable_real_inspect=True` 做真实只读文件扫描并写入审计日志。
- `[测]` 状态可以执行真实 `verification_command`，用真实退出码生成证据并写入审计日志。
- 连续失败时进入 `停`。

`tests/test_minimal_gateway_mvp.py` 覆盖：

- `oneword_dict.json` 包含 8 个根字实体配置。
- minimal gateway 会在 `查` 状态裁剪写工具。
- minimal gateway 会在 `停` 状态阻断上游模型转发。

`tests/test_gateway_server_import.py` 覆盖：

- 未安装 FastAPI 时，server import 会给出可操作的依赖安装提示。

## 本地调试核心逻辑

不启动 HTTP 服务，直接测试请求重写：

```bash
python3 - <<'PY'
from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.loader import load_dictionary

dictionary = load_dictionary("agent_skill_dictionary/programming-agent-skill-dictionary.json")
body = {
    "model": "gpt-test",
    "temperature": 0.8,
    "messages": [{"role": "user", "content": "这个 bug 修一下，然后跑测试确认。"}],
}

rewritten, metadata = rewrite_chat_completion_request(body, dictionary)
print(metadata)
print(rewritten["messages"][0]["content"])
PY
```

预期：

- `metadata["codes"]` 是 `["修", "测"]`。
- `metadata["execution_stack"]` 是 `["测", "修"]`。
- `metadata["active_code"]` 是 `修`。
- `rewritten["temperature"]` 是 `0.0`。
- system message 包含 `根字 Workflow 摘要`。
- system message 包含 `内核运行规训`。
- system message 包含 `根字 Skill Mount 摘要`。

## 调试执行计划

不调用上游模型，直接查看一句话会被编译成什么执行计划：

```bash
python3 - <<'PY'
from agent_skill_dictionary.gateway_plan import resolve_execution_plan
from agent_skill_dictionary.loader import load_dictionary

dictionary = load_dictionary("agent_skill_dictionary/programming-agent-skill-dictionary.json")
plan = resolve_execution_plan("这个 bug 修一下，然后跑测试确认。", dictionary)
print(plan)
PY
```

预期：

- `codes` 是 `["修", "测"]`。
- `execution_stack` 是 `["测", "修"]`。
- `active_code` 是 `修`。
- `routing_target` 是 `debug_fix_workflow`。
- `macro_chain` 描述复杂任务的闭环控制链。

## 生成证据摘要

系统证据摘要工具用于后续审计日志落盘：

```bash
python3 - <<'PY'
from agent_skill_dictionary.audit import build_evidence_record

record = build_evidence_record(
    command="python3 -m unittest",
    exit_code=0,
    stdout="OK\n",
    stderr="",
)
print(record)
PY
```

当前工具只生成摘要记录，不写入审计日志文件。

## 调试 OneWord-Agent FSM

OneWord-Agent 是当前 8 根字状态机框架原型。未配置真实扫描或真实命令时，默认执行器适合验证状态转移和审计轨迹：

```bash
python3 - <<'PY'
from agent_skill_dictionary.one_word_agent import OneWordAgent

agent = OneWordAgent(codebase_path="/tmp/project")
result = agent.run("这里有个 bug，跑不通了，帮我修好并验证。")
print(result)
PY
```

预期：

- `trace` 会显示根字状态轨迹。
- `audit_log` 会包含每一步的根字、卦象、允许工具和证据要求。
- `[查]` 状态可配置 `enable_real_inspect=True`，只读收集文件清单和文本片段证据。
- `[测]` 状态可配置 `verification_command`，用真实退出码和审计证据驱动状态流转。
- `[记]` 状态可配置 `enable_real_memory=True` 和 `memory_dir`，把最近的 Markdown 摘要归档到 memory 目录。
- `[总]` 状态可配置 `enable_real_summary=True`，把 `active_context` 生成稳定 Markdown 交接摘要和审计证据。
- 状态切换时会刷新 `context["active_context"]`，只保留原始请求、最近证据、退出码、只读摘要等紧凑上下文。
- 其他状态的真实生产执行器仍需要继承 `OneWordAgent` 并覆写 `execute_llm_core()`。

## 调试 Tool-Call 守卫

工具守卫可以单独调用：

```bash
python3 - <<'PY'
from agent_skill_dictionary.loader import load_dictionary, lookup_entry
from agent_skill_dictionary.tool_guard import inspect_tool_calls

dictionary = load_dictionary("agent_skill_dictionary/programming-agent-skill-dictionary.json")
entry = lookup_entry(dictionary, "查")
decision = inspect_tool_calls(entry, [{"name": "write_file", "arguments": {"path": "app.py"}}])
print(decision)
PY
```

预期：

- `allowed` 是 `False`。
- `violations[0]["reason"]` 是 `write_forbidden`。

当前 tool-call 守卫是在响应 metadata 中标注违规。要做到真实执行前物理阻断，需要把 `inspect_tool_calls()` 接到具体 Agent 的工具执行层。

执行前硬门可以直接调用：

```bash
python3 - <<'PY'
from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.tool_guard import preflight_tool_call

dictionary = load_dictionary("agent_skill_dictionary/programming-agent-skill-dictionary.json")
result = preflight_tool_call(
    dictionary,
    active_code="查",
    tool_name="write_file",
    arguments={"path": "app.py"},
)
print(result)
PY
```

如果网关已经启动，也可以通过 HTTP 调用：

```bash
curl -sS http://localhost:8080/v1/yizijue/preflight-tool \
  -H 'content-type: application/json' \
  -d '{"active_code":"查","tool_name":"write_file","arguments":{"path":"app.py"}}'
```

## 本地启动网关

```bash
ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

健康检查：

```bash
curl -sS http://localhost:8080/health
```

解析执行计划：

```bash
curl -sS http://localhost:8080/v1/yizijue/resolve \
  -H 'content-type: application/json' \
  -d '{"input":"这个 bug 修一下，然后跑测试确认。"}'
```

Agent base URL：

```text
http://localhost:8080/v1
```

## Docker

构建：

```bash
docker build -f Dockerfile.gateway -t yizijue-gateway:0.2 .
```

运行：

```bash
docker run --rm -p 8080:8080 \
  -e ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
  yizijue-gateway:0.2
```

## 修改规则

修改 `gateway_core.py` 的归一化或请求重写逻辑时：

1. 先在 `tests/test_gateway_core.py` 写失败测试。
2. 运行测试确认失败。
3. 修改实现。
4. 运行全部测试。

修改 `programming-agent-skill-dictionary.json` 时：

1. 先确认字段符合 [词典契约](dictionary-contract.md)。
2. 每个新增执行字必须补齐 `reference_workflow_patterns`。
3. 每个新增执行字必须补齐 `professional_protocol.source_projects`、`operating_logic` 和 `hard_gates`。
4. 如果新增只读、控制、安全或合规类执行字，必须在 `validator.py` 中加入权限约束。
5. 如果新增执行字会参与自然语言归一化，必须在 `tests/test_gateway_core.py` 增加命中测试。
6. 运行 JSON 解析、validator 和完整测试。

## 当前技术债

- `normalize_intent()` 还是关键词规则，不是向量检索或分类模型。
- `/v1/chat/completions` 只支持非流式请求。
- tool-call 物理阻断依赖具体 Agent 工具执行层接入 `/v1/yizijue/preflight-tool`。
- 响应侧违规标注仍然保留，用于调试和审计。
- 审计 metadata 会附加到响应里，但没有独立落盘。
- `__pycache__` 是 Python 运行测试产生的缓存，不属于业务文件。
