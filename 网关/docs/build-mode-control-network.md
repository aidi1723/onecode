# Build Mode 控制网络与主权边界

日期：2026-05-26
定位：Build Mode 的交互网络、主权边界和平衡阀说明
状态：规则文档；当前代码已完成本地 runner 与工具接管入口，尚未完成真实模型自动 tool-call 循环

## 1. 核心结论

Build Mode 不是线性脚本，而是一个由硬证据驱动的离散状态网络。

线性链路是最小闭环：

```text
乾 111 -> 震 001 -> 坤 000 -> 总
```

真实运行网络还必须包含反馈、阻断、隔离和回流：

```text
震 001 -> 兑 110 -> 离 101 -> 乾 111
任意状态 -> 艮 100 -> 兑 110 -> 离 101
未知风险 -> 坎 010 -> 兑 110 / 艮 100
纯文本 -> 巽 011 -> 结束 / 乾 111
```

系统不靠模型自觉收敛，而靠路径、退出码、哈希、DTO 和工具参数触发状态迁移。

## 2. 八卦交互网络

### 2.1 乾与震：创造复杂度守恒

`乾 111` 释放 scoped 写入能力，产生真实文件变化。写入越多、依赖越复杂，后续 `震 001` 的验证成本越高。

工程规则：

- `乾` 必须输出 `WriteEvidence`。
- `WriteEvidence.changed_files` 为空时不得进入 `震`。
- `震` 的 timeout 和失败计数由 `乾` 的变更规模间接影响。
- `震` 失败后不能把完整日志塞回模型，只能转 `兑`。

当前代码落点：

- `agent_skill_dictionary/build_mode_writer.py`
- `agent_skill_dictionary/build_mode_sandbox.py`
- `agent_skill_dictionary/build_mode_runner.py`
- `agent_skill_dictionary/build_mode_tool_executor.py`

### 2.2 艮与兑：硬阻断与软连续

`艮 100` 负责物理拒绝，`兑 110` 负责协议连续。两者必须配对，否则外部 Agent 客户端会因为 403、126、500 或协议错误直接崩溃。

工程规则：

- 危险动作必须先生成 `ViolationEvidence`。
- `ViolationEvidence` 不能直接暴露给客户端作为崩溃式错误。
- `兑` 将阻断转换为 `HTTP 200`、`stderr=""`、结构化反馈文本。
- SSE / chunked 响应必须保持客户端期望的外壳，只改写内容文本。

当前代码落点：

- `agent_skill_dictionary/build_mode_feedback.py`
- `agent_skill_dictionary/build_mode_tool_executor.py`
- `agent_skill_dictionary/gateway_server.py`

### 2.3 离与巽：上下文脱水与零工具快轨

`离 101` 是带证据的只读上下文注入，`巽 011` 是无工具纯文本推理。它们共同控制模型“看见什么”和“不能碰什么”。

工程规则：

- `离` 阶段只能给 repo card、line refs、失败摘要。
- `离` / `巽` 不开放写盘和执行工具。
- 当只读状态中出现明确写盘意图，必须重新经 `intent_resolver` 升到 `乾`，不能偷偷放权。
- 当测试失败后进入 `离`，上下文应是短卡片，不是原始 stdout 洪流。

当前代码落点：

- `agent_skill_dictionary/build_mode_intent.py`
- `agent_skill_dictionary/build_mode_permissions.py`
- `agent_skill_dictionary/build_mode_runner.py`

### 2.4 坎与艮：未知风险缓冲与不可恢复熔断

`坎 010` 处理未知、模糊、高频震荡的 I/O 意图；`艮 100` 处理明确危险。坎是观察缓冲，艮是硬停。

工程规则：

- 未知工具不能默认放行。
- 未知 I/O 先映射为 `shadow_buffer` 或停。
- 只要出现密钥路径、系统路径、破坏性命令，立即绕过坎，直接进艮。

当前代码落点：

- `agent_skill_dictionary/build_mode_permissions.py`
- `agent_skill_dictionary/build_mode_fsm.py`
- `agent_skill_dictionary/build_mode_tool_executor.py`

### 2.5 坤与总：物理归档与人类交接分离

`坤 000` 负责物理资产证据，V1 `总` 负责人类可读摘要。两者不能混为一谈。

工程规则：

- 没有 `ArchiveEvidence`，不能声称完成。
- `manifest.json` 和 SHA256 是完成证据。
- `总` 的摘要只能引用证据，不能替代证据。
- `lockdown` 不是默认行为。默认 `audit_only`，只记录 manifest/hash。

当前代码落点：

- `agent_skill_dictionary/build_mode_archive.py`
- `agent_skill_dictionary/build_mode_runner.py`

## 3. 三条主权红线

### 3.1 文件系统主权

硬边界：

```text
Path(target).resolve() 必须位于 Path(workspace_root).resolve() 内部
```

执行规则：

- `../`、绝对路径逃逸、敏感目录访问必须返回 `ViolationEvidence`。
- 路径检查必须使用真实路径解析，不能使用字符串前缀拼接。
- 写入只允许发生在 workspace scope 内。

当前代码：

- `safe_write()` 使用 `Path.resolve()` 和 parent 检查。

### 3.2 进程主权

硬边界：

```text
测试和构建应进入 sandbox_runner；高安全模式要求 Docker
```

执行规则：

- `run_pytest` 等测试命令不直接穿透到宿主机裸执行。
- 当前本地 MVP 可 `use_docker=False` 作为开发降级，但证据必须记录。
- 生产/高安全测试应开启 Docker 要求。

当前代码：

- `run_isolated_test()` 复用 `executor.execute_command()`，支持 Docker 参数。

### 3.3 记忆主权

硬边界：

```text
离 / 巽 状态下 tools 必须为空或仅保留 native_inspect_card
```

执行规则：

- 失败日志必须先经 `兑` 压缩，再经 `离` 注入。
- 原始海量 stdout 不进入下一轮模型上下文。
- 模型不能用“我看过了/我测过了”替代证据。

当前代码：

- `filter_tools_schema()` 对 `011` 清空工具，对 `101` 只保留 `native_inspect_card`。

## 4. 平衡阀

### 4.1 Failure Counter Gate

默认规则：

```text
consecutive_failures >= 2 -> 艮 100
timeout/OOM -> 艮 100
```

用途：

- 防止模型在乾/震之间无限烧 token。
- 防止测试死循环和依赖安装失控。
- 把失败转化为可审计的停机现场。

当前代码状态：

- `build_mode_fsm.next_hexagram()` 支持 `consecutive_failures >= 2` 转 `艮`。
- `BuildModeRunner` 当前只实现单轮失败路径，尚未实现多轮自动重试计数器。

### 4.2 Memory Cleanliness Ratio

目标规则：

```text
下一轮上下文只保留需求、changed_files、exit_code、line_refs、repo_card
```

用途：

- 控制 token。
- 降低日志洪流导致的注意力漂移。
- 让模型只围绕可修复证据行动。

当前代码状态：

- `BuildModeRunner` 已在失败路径返回 `repo_card`。
- 网关尚未把 `repo_card` 自动注入真实模型下一轮请求。

## 5. 当前实现状态

已完成并验证：

| 能力 | 状态 |
| --- | --- |
| DTO 与证据门 | 已实现 |
| Intent Resolver | 已实现 |
| Permission Matrix | 已实现 |
| Shadow Tool Mapping | 已实现 |
| Scoped Writer | 已实现 |
| Sandbox Evidence Wrapper | 已实现 |
| Soft Feedback / SSE payload | 已实现 |
| Archive Guard | 已实现 |
| Evidence FSM | 已实现 |
| BuildModeRunner 本地闭环 | 已实现 |
| `/v1/yizijue/build-tool` 控制面入口 | 已实现 |

验证结果：

```text
Build Mode 聚焦测试：41 tests OK
网关/认证关键回归：40 tests OK，其中 FastAPI route tests 在缺少 test client 环境下 skip
compileall：OK
```

尚未完成：

| 能力 | 状态 |
| --- | --- |
| 从真实模型响应中自动提取 tool-call 并执行 build-tool | 未完成 |
| 将 build-tool 的 Evidence 自动注入下一轮模型上下文 | 未完成 |
| 多轮自动 retry counter | 未完成 |
| 真实 Codex / Claude 端到端项目构建复测 | 未完成 |
| 生产级 Docker 安全策略全覆盖 | 未完成 |

## 6. 下一步工程动作

下一步不应再改法典，而应打通真实模型循环：

1. 在 OpenAI Responses / Chat / Anthropic Messages 响应侧识别可接管工具调用。
2. 将可接管工具调用转发到 `build_tool_payload()`。
3. 将返回的 `WriteEvidence`、`SandboxEvidence`、`FeedbackEvidence`、`ArchiveEvidence` 写入会话状态。
4. 在下一轮请求中注入 repo card 或完成摘要。
5. 再进行真实 Codex / Claude 项目构建 A/B。

完成这五步后，Build Mode 才能称为真实 Agent 流量闭环。
