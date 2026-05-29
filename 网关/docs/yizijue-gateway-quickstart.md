# 一字诀 Gateway Quickstart

一字诀 Gateway 是一个 OpenAI-compatible 反向代理。现有 Agent 只需要把 base URL 指向本地网关，网关就会在请求转发到上游模型前注入执行字规则。

当前支持：

- `GET /health`
- `POST /v1/yizijue/resolve`
- `POST /v1/yizijue/preflight-tool`
- `POST /v1/oneword/resolve`
- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /v1/messages`
- 执行计划解析，不调用上游模型
- OpenAI Chat Completions、OpenAI Responses 兼容入口、Anthropic Messages 兼容入口的请求重写
- Build Mode 下的非流式工具调用接管和常见 SSE streaming 工具调用接管
- 执行字 system rule 注入
- 参考工作流模式与专业运行逻辑注入
- 根字 Workflow 摘要注入
- 根字 Skill Mount 摘要注入
- Kernel Runtime Policy 注入
- 请求转发前按根字过滤 `tools`
- `停` 根字 HTTP 503 硬熔断
- 闭环 Macro Chain 解析
- OneWord-Agent FSM 框架原型
- 词典 temperature 策略锁定

## Run Locally

Install runtime dependencies:

```bash
python3 -m pip install -r requirements-gateway.txt
```

Start the gateway:

```bash
ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

Start the minimal V1.0 MVP gateway:

```bash
ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.minimal_gateway_server:app --host 0.0.0.0 --port 8080
```

The full gateway uses `programming-agent-skill-dictionary.json`. The minimal gateway uses:

```text
agent_skill_dictionary/oneword_dict.json
```

Minimal V1.0 MVP 行为边界：

- 8 个根字从 `oneword_dict.json` 加载 system prompt 铁律、temperature、工具白名单、阻断列表、证据字段和 `control_vector`。
- 显式根字前缀直达，例如 `查：...`。
- `[审]` 是 Phase 1 只读审查派生字，会被编译为 `[离]/查`，只保留 `read_file`、`list_directory`、`grep_code`、`git_diff` 等只读工具。
- 低置信度输入不会默认猜成 `[查]`，而是自动变卦为 `[兑]/问`，只保留 `send_user_message`、`render_ui_options`。
- `[艮]/停` 会返回 503，不转发上游模型。

Point an OpenAI-compatible agent to:

```text
http://localhost:8080/v1
```

Example agent configuration:

```text
BASE_URL=http://localhost:8080/v1
API_KEY=<same key accepted by upstream, or any value if ONEWORD_UPSTREAM_API_KEY is set>
```

## Existing Agent Integration

当前网关已经支持 OpenAI-compatible Agent。最短接入方式是让现有 Agent 的 base URL 指向：

```text
http://localhost:8080/v1
```

Anthropic-compatible `/v1/messages` adapter 已有网关入口和单元级验证。真实 Claude Code/Codex Desktop 端到端连接仍要单独做本机实测，不能只用单元测试替代。

目标形态：

```bash
export ANTHROPIC_BASE_URL=http://localhost:8080
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
claude
```

直连前必须确认客户端实际协议、streaming chunk 结构和 API key 传递方式。详细路线见 [现有 Agent 网关接入路线](existing-agent-gateway-integration.md)。

## Environment Variables

```text
ONEWORD_DICTIONARY_PATH=agent_skill_dictionary/programming-agent-skill-dictionary.json
ONEWORD_UPSTREAM_BASE_URL=https://api.openai.com/v1
ONEWORD_UPSTREAM_API_KEY=<upstream api key>
```

If `ONEWORD_UPSTREAM_API_KEY` is not set, the gateway uses `OPENAI_API_KEY`.

`ONEWORD_UPSTREAM_BASE_URL` should not include `/chat/completions`; the gateway appends that path automatically.

## Build Mode Live Loop

Build Mode is enabled explicitly:

```bash
export ONEWORD_BUILD_MODE=1
export ONEWORD_WORKSPACE_ROOT=/absolute/path/to/workspace
```

When enabled, the gateway can intercept model-emitted tool calls and execute them through the Build Mode runner instead of letting the client run them directly. Verified local paths include:

- Chat Completions `message.tool_calls`
- OpenAI Responses `output[].function_call`
- Anthropic Messages `content[].tool_use`
- common complete and split SSE tool-call chunks for OpenAI/Anthropic-style streams

Execution evidence is persisted under:

```text
<workspace>/.yizijue/build-mode-state.json
<workspace>/.yizijue/build-mode-state-<session_id>.json
```

If the request includes `session_id`, `conversation_id`, or `thread_id`, Build Mode uses a session-scoped state file. Without one, it falls back to the workspace-global state file for compatibility. State writes are protected by a per-state `.lock` file and use temporary-file plus atomic replace, so concurrent requests should not interleave read-modify-write cycles or expose half-written JSON.

Current verified behavior:

- `write_file` evidence pushes the next turn toward `001` verification tools.
- The local live smoke verifies this over real HTTP: first turn intercepts upstream `write_file` tool calls, writes into the temporary workspace, persists `next_hexagram=001`; the second turn reuses the same `session_id` and the upstream receives only `run_pytest` after state-based tool filtering; the third turn intercepts upstream `run_pytest` and returns `status=completed`, `next_hexagram=000`. It also exercises the failed verification branch, where an intercepted failing `run_pytest` returns `status=needs_fix`, `next_hexagram=110`, and soft feedback while the proxy stays on the normal response path. The persisted next-turn state follows the soft-feedback recommendation to `101`, so the following request exposes only `native_inspect_card`; when upstream calls it, the gateway returns a compact repo card and advances the next state to `111`; the next request exposes only `write_file` from the offered tool set; when upstream sends that repair write, the gateway updates the file and returns `next_hexagram=001`; the repaired verification is intercepted again and returns `status=completed`, `next_hexagram=000`.
- failed verification increments `consecutive_failures`.
- successful verification/archive resets the failure counter.
- verification clears workspace-local Python bytecode caches before execution to avoid stale `__pycache__` affecting fast repair/retest loops.
- two consecutive failed verification cycles trigger the `100` failure gate, withhold tools, and emit expert handoff evidence.
- missing workspace during streamed tool execution is soft-rewritten as `HTTP 200` instead of leaking the tool call back to the client.

Current boundary:

- Unit/integration tests cover gateway payload rewriting and stream chunk inspection.
- A real desktop client end-to-end run is still a separate acceptance test.
- State is session-scoped when clients provide a stable session identifier; otherwise it remains workspace-global.

## Resolve Only

Use this endpoint to see how the gateway compiles a natural-language request before sending anything to an upstream model:

```bash
curl -sS http://localhost:8080/v1/yizijue/resolve \
  -H 'content-type: application/json' \
  -d '{"input":"这个 bug 修一下，然后跑测试确认。"}'
```

Minimal V1.0 MVP resolve endpoint:

```bash
curl -sS http://localhost:8080/v1/oneword/resolve \
  -H 'content-type: application/json' \
  -d '{"input":"审：审查这个项目有没有风险"}'
```

Expected shape:

```json
{
  "active_code": "查",
  "requested_code": "审",
  "confidence": 1.0,
  "compile_reason": "explicit_alias_prefix",
  "hexagram": "离",
  "temperature": 0.0,
  "allowed_tools": ["native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"],
  "halt_model_forwarding": false
}
```

Low-confidence input is routed to `[兑]/问`:

```bash
curl -sS http://localhost:8080/v1/oneword/resolve \
  -H 'content-type: application/json' \
  -d '{"input":"帮我处理一下这个事情"}'
```

Expected shape:

```json
{
  "codes": ["修", "测"],
  "execution_stack": ["测", "修"],
  "active_code": "修",
  "routing_target": "debug_fix_workflow",
  "macro_chain": {
    "codes": ["查", "总"],
    "initial_active_code": "查"
  }
}
```

For a feature-development request such as `帮我实现一个新接口，写完后跑测试并记录文档。`, `macro_chain.codes` becomes:

```json
["查", "造", "测", "修", "记", "总"]
```

## Preflight Tool Check

Use this endpoint before executing a tool call:

```bash
curl -sS http://localhost:8080/v1/yizijue/preflight-tool \
  -H 'content-type: application/json' \
  -d '{"active_code":"查","tool_name":"write_file","arguments":{"path":"app.py"}}'
```

Expected shape:

```json
{
  "allowed": false,
  "active_code": "查",
  "tool": "write_file",
  "violations": [
    { "tool": "write_file", "reason": "write_forbidden" }
  ]
}
```

## OneWord-Agent FSM

Gateway 负责 OpenAI-compatible 请求重写；OneWord-Agent 是库级框架层，用 8 个根字运行可审计状态机。

本地快速查看状态轨迹：

```bash
python3 - <<'PY'
from agent_skill_dictionary.one_word_agent import OneWordAgent

agent = OneWordAgent(codebase_path="/tmp/project")
print(agent.run("这里有个 bug，跑不通了"))
PY
```

默认执行器仍主要是测试桩，但 `[查]` 状态可以通过 `enable_real_inspect=True` 做真实只读文件扫描，`[测]` 状态可以通过 `verification_command` 接入真实本地命令，`[记]` 状态可以通过 `enable_real_memory=True` 归档最近 Markdown 摘要，`[总]` 状态可以通过 `enable_real_summary=True` 生成稳定 Markdown 交接摘要。真实多步执行 endpoint 属于后续阶段。

状态切换时，OneWord-Agent 会刷新 `context["active_context"]`。这个上下文只保留原始请求、当前/最近状态、最近证据哈希、退出码、只读文件清单和文本片段摘要，不把完整历史、完整 stdout 或完整 stderr 继续传给后续状态。

示例：让 `[查]` 状态只读扫描项目结构并写入审计日志：

```bash
python3 - <<'PY'
from agent_skill_dictionary.one_word_agent import OneWordAgent

agent = OneWordAgent(
    codebase_path="/tmp/project",
    enable_real_inspect=True,
    enable_real_summary=True,
    enable_real_memory=True,
    memory_dir="/tmp/project/memory",
    audit_log_path="/tmp/project/audit.log.jsonl",
)
print(agent.run("帮我看看项目结构"))
PY
```

示例：让 `[测]` 状态运行真实验证命令并写入审计日志：

```bash
python3 - <<'PY'
from agent_skill_dictionary.one_word_agent import OneWordAgent

agent = OneWordAgent(
    codebase_path="/tmp/project",
    verification_command=["python3", "-m", "unittest", "discover", "-s", "tests"],
    audit_log_path="/tmp/project/audit.log.jsonl",
)
print(agent.run("请运行测试验证"))
PY
```

## Docker

Build:

```bash
docker build -f Dockerfile.gateway -t yizijue-gateway:0.2 .
```

Run:

```bash
docker run --rm -p 8080:8080 \
  -e ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
  yizijue-gateway:0.2
```

## Current Scope

The current gateway rewrites `/v1/chat/completions` requests by injecting the active execution character rule, root Opcode workflow excerpt, Root Skill Mount excerpt, Kernel Runtime Policy, reference workflow patterns, professional protocol, tool policy, verification policy, and model temperature from the dictionary.

The V0.4 MVP adds root tool filtering, the `停` hard halt path, deterministic Macro Chain resolution, and a library-level OneWord-Agent FSM prototype. Anthropic-compatible `/v1/messages`, streaming SSE passthrough, audit log persistence, workflow hot reload, evidence-chain delivery gates, `/v1/yizijue/run`, and hard integration with a concrete Agent tool executor should be added in later phases.

## Verify

Run local tests:

```bash
python3 -m unittest tests.test_agent_skill_dictionary tests.test_gateway_core tests.test_gateway_plan tests.test_audit tests.test_gateway_server_import tests.test_tool_guard tests.test_tool_preflight tests.test_phase2_dictionary tests.test_reference_patterns tests.test_opcode_primitives tests.test_workflow_loader tests.test_skill_mount_registry tests.test_kernel_policy tests.test_macro_chain tests.test_one_word_agent tests.test_minimal_gateway_mvp -v
```

Validate the dictionary:

```bash
python3 -m agent_skill_dictionary.validator agent_skill_dictionary/programming-agent-skill-dictionary.json
```

Expected validator output:

```text
OK
```
