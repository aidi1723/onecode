# 现有 Agent 网关接入路线

日期：2026-05-24
定位：Phase 4.5 落地路线
结论：先做中间层网关规训现有高级 Agent，再逐步演进到自研 AgentOS

## 1. 核心判断

一字诀最短见效路径不是立刻从零写一个全新 Agent，而是先作为中间层网关接入现有高级 CLI Agent。

原因很简单：

```text
现有 Agent 已经解决了文件读取、编辑、终端、Git、上下文组织等大量工程脏活。
一字诀最有价值的部分，是在它们上方增加确定性路由、权限锁、证据门和状态机。
```

因此 Phase 1 的最优路线是：

```text
用户 / CLI Agent
  ↓
一字诀 Gateway
  ↓
执行字归一化 + Kernel Policy + 工具裁剪 + 熔断
  ↓
真实上游模型
```

这条路线本质上是“网关规训现有 Agent”：不替代现有工具链，而是接管它发往模型的请求，把自由发挥改造成按字执行。

## 2. 接入分级

### 2.1 Level A：OpenAI-compatible Agent

当前项目已经支持这一层。

适用对象：

```text
任何能把 base URL 指向 OpenAI-compatible /v1/chat/completions 的 Agent、SDK 或自研工具
```

接入方式：

```text
BASE_URL=http://localhost:8080/v1
```

当前已落地能力：

- 请求进入上游模型前注入执行字规则。
- 按根字覆盖 `temperature`。
- 按根字过滤 `tools`。
- `停` 直接 HTTP 503 熔断，不转发上游模型。
- `/v1/yizijue/preflight-tool` 可在工具执行前做权限检查。

这是当前最快可运行路径。

### 2.2 Level B：Anthropic / Claude Code-compatible Agent

Claude Code 这类工具通常走 Anthropic Messages API，而不是 OpenAI Chat Completions API。Claude Code 官方 LLM gateway 文档描述了通过 `ANTHROPIC_BASE_URL` 指向 Anthropic-compatible gateway 的场景，并要求网关至少暴露 Anthropic Messages、Bedrock 或 Vertex rawPredict 其中一种 API 格式。

参考：

- [Claude Code LLM gateway configuration](https://code.claude.com/docs/en/llm-gateway)
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-usage)

目标接入方式：

```bash
export ANTHROPIC_BASE_URL=http://localhost:8080
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
claude
```

如果网关实现了 `/v1/models`，并且需要让 Claude Code 从网关发现模型，可按官方文档启用：

```bash
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
```

当前项目边界：

```text
当前 gateway_server.py 只实现 OpenAI-compatible /v1/chat/completions。
Claude Code 直连需要新增 Anthropic-compatible adapter，例如 /v1/messages、streaming、tool schema 转换和错误格式适配。
```

所以，Claude Code 是 Phase 4.5 的重点方向，但不能把当前 OpenAI-compatible 网关直接宣传成“已完整支持 Claude Code”。

### 2.3 Level C：HTTP 代理或协议桥

如果某个 Agent 不能直接设置 base URL，但能走企业代理或 HTTP proxy，可以考虑协议桥。

但这不是首选，因为：

- TLS 场景下不能稳定读取和修改 JSON payload。
- Agent 可能有非 HTTP 的本地工具执行路径。
- 代理层更难做结构化工具白名单和证据链。

只有当 base URL / SDK adapter 都不可用时，才考虑这一层。

### 2.4 Level D：自研 AgentOS

等一字诀的 8 根字、22 字词典、64 字扩展、审计日志和工具执行前硬门全部跑顺后，再考虑自研 AgentOS。

自研 AgentOS 的合理触发条件：

- 现有 CLI Agent 无法把工具执行前检查接入 `/v1/yizijue/preflight-tool`。
- 需要 Reader / Orchestrator / Writer 物理隔离。
- 需要跨 Mac Mini、x86 mini PC 或远程节点做任务调度。
- 需要把 64 字指令集作为完整运行时内核，而不是单次请求规训。

## 3. 网关能真正控制什么

当 Agent 的模型请求经过一字诀 Gateway 时，网关可以确定性控制：

- 当前执行字：自然语言先归一化成 `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总` 或派生字。
- System Prompt：注入执行字规则、根字 workflow 摘要和 Kernel Runtime Policy。
- 模型参数：覆盖 `temperature` 等确定性参数。
- 工具列表：在请求转发前删除当前根字不允许的工具。
- 熔断：`停` 状态直接拒绝转发上游模型。
- 执行前检查：通过 `/v1/yizijue/preflight-tool` 决定某个工具调用是否允许。
- 审计 metadata：响应侧标注 tool-call 违规和执行字上下文。

这就是“网关物理夺权”的工程含义：让模型在当前状态下只看到它被允许使用的工具和规则。

## 4. 网关不能单独保证什么

为了避免过度承诺，必须写清边界。

如果现有 Agent 的文件编辑、终端执行或依赖安装并不经过模型 `tools` payload，也不调用一字诀的 preflight 接口，那么网关无法物理阻断这类本地动作。

因此，完整安全闭环需要两道门：

```text
模型请求门
  Gateway 过滤 system prompt、temperature、tools 和模型调用。

工具执行门
  Agent 在执行 read/write/bash/install 前调用 /v1/yizijue/preflight-tool。
```

只接入模型请求门，可以显著降低漂移和乱规划；接入工具执行门，才能更接近真正的物理阻断。

## 5. 八字对现有 Agent 的规训方式

| 根字 | 对现有 Agent 的网关规训 | 工具执行前硬门 |
| --- | --- | --- |
| `查` | 删除写入和高风险执行工具，只保留只读调查规则 | 拦截 `write_file`、`edit_file`、危险 shell |
| `修` | 只允许受限编辑，强制最小修改和失败复现 | 检查路径范围、禁止依赖安装 |
| `测` | 只允许运行验证类工具，强制证据输出 | 捕获 stdout、stderr、exit code |
| `卫` | 强制安全审计 prompt，拒绝未授权外联和依赖 | 高危命令、License、网络、密钥检查 |
| `停` | 不转发模型请求，直接挂起 | 收回所有工具 |
| `问` | 只允许生成澄清问题或授权选项 | 等待用户结构化确认 |
| `记` | 只允许写指定知识库、ADR 或 Markdown | 限定写入目录并生成 hash |
| `总` | 只做上下文压缩和交接摘要 | 禁止业务源码写入 |

## 6. 推荐落地顺序

### Step 1：继续巩固当前 OpenAI-compatible 网关

当前已经完成：

```text
/v1/chat/completions
/v1/yizijue/resolve
/v1/yizijue/preflight-tool
Kernel Runtime Policy
Macro Chain
OneWord-Agent FSM 原型
```

这一层先稳定下来，作为所有适配器的统一内核。

### Step 2：实现 Anthropic-compatible adapter

为了接入 Claude Code，需要新增：

```text
POST /v1/messages
GET  /v1/models
SSE streaming passthrough
Anthropic tool schema -> 一字诀 tool policy
Anthropic error shape
```

这个 adapter 不应该复制一套新逻辑，而应复用：

```text
gateway_core.py
kernel_policy.py
tool_guard.py
macro_chain.py
audit.py
```

### Step 3：实现工具执行前强制接入

优先方案：

```text
现有 Agent 支持 hooks / MCP / tool wrapper
  ↓
在每次工具执行前调用 /v1/yizijue/preflight-tool
```

如果现有 Agent 不支持 hook，就需要包装它的工具层，或进入自研 AgentOS 阶段。

本地 Runtime 最小铁闸已经有 CLI 入口：

```bash
python3 -m agent_skill_dictionary.cli claude-pretool-hook \
  --active-code 查 \
  --payload-json '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt"}}'
```

它会把 Claude Code 原生工具名归一化到一字诀策略域：

| Claude Code 工具 | 一字诀工具 |
| --- | --- |
| `Read` | `read_file` |
| `LS` | `list_directory` |
| `Glob` | `list_directory` |
| `Grep` | `grep_code` |
| `Bash` | `execute_command` |
| `Edit` / `MultiEdit` | `edit_scoped_file` |
| `Write` | `write_file` |

在 `[查]` 状态下，`Read` 会被允许，`Bash`、`Edit`、`Write` 会被拒绝。这个 CLI 是接入 Claude Code `PreToolUse` hook 的最小本地判定器。真正的物理阻断必须发生在 Claude Code 执行本地工具之前；只把模型流量指向 `/v1/messages` 网关，不能阻止客户端本地 Bash 或写盘。

同时提供 PATH 级哨兵骨架：

```bash
export ONEWORD_ACTIVE_CODE=查
export PATH="/path/to/oneword-agentos-test/bin:$PATH"
```

当前 `bin/bash` 与 `bin/rm` 会在派生真实系统二进制前复用本地 Preflight。`[查]` 状态下，下面两类动作会被本地拒绝，进程返回非零退出码，原始文件不会被删除：

```bash
bash -lc 'rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt'
rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt
```

PATH 哨兵是防守纵深，不替代 Claude Code Hooks。Hook 能覆盖 Claude Code 内部工具协议，PATH 哨兵负责拦截最终落到宿主机 PATH 的常见破坏命令。两层都接入后，才是本地 Runtime 物理主权闭环。

### Step 4：把 OneWord-Agent 接入真实 executor

让 `OneWordAgent.execute_llm_core()` 不再返回测试桩，而是：

1. 读取当前状态和 KernelPolicy。
2. 通过 gateway rewrite 组织模型请求。
3. 调用真实上游模型。
4. 对工具调用做 preflight。
5. 捕获系统证据。
6. 把证据交给 MutationEngine 做状态转移。

最小闭环：

```text
查 -> 修 -> 测 -> 记 -> 总
```

### Step 5：成熟后抽出自研 AgentOS

当 adapter、preflight、audit、state machine 都稳定后，再把一字诀变成完整 AgentOS：

```text
64 字指令集
多 Agent 物理隔离
跨机器调度
长期记忆
审计日志
权限与证据中心
```

## 7. 当前项目结论

一字诀当前最应该坚持的路线是：

```text
先做 Gateway，规训现有 Agent。
再做 Anthropic adapter，接入 Claude Code。
再做工具执行前硬门，形成真正安全闭环。
最后再抽象成自研 AgentOS。
```

这样既能快速见效，又不会把早期工程量浪费在重做文件编辑、终端执行、Git 管理这些成熟工具已经做好的部分。
