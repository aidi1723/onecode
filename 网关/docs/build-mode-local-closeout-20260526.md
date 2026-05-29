# Build Mode 本地网关闭环阶段收尾报告

日期：2026-05-26
目录：`/Users/aidi/大字典`
阶段结论：Build Mode MVP 的本地网关闭环可以阶段收尾；真实桌面客户端端到端接入尚未收尾。

## 1. 收尾结论

本阶段已经完成的是：

- 两仪、四象、八卦的运行规则已经落成可执行的 Build Mode 模块。
- `BuildModeRunner`、网关工具接管、证据门、状态文件、Soft Feedback、Repo Inspect、归档 manifest 已经形成本地闭环。
- Chat Completions、OpenAI Responses、Anthropic Messages 三路协议都已通过真实本地 HTTP 网关和 mock upstream 的 live-smoke。
- live-smoke 不再只看“请求没崩”，而是检查关键状态转移和归档硬证据。

本阶段还没有完成的是：

- 尚未完成 Codex Desktop 真实客户端端到端验证。
- 尚未完成 Claude Code 真实客户端端到端验证。
- 尚未用真实上游模型跑长周期项目构建 A/B。

因此，本阶段准确状态是：

> Build Mode MVP 本地网关闭环已通过，可以作为下一阶段真实客户端接入测试的基础版本。

## 2. 已验证范围

### 2.1 本地 HTTP 网关

验证对象：

- `agent_skill_dictionary.gateway_server`
- `/v1/chat/completions`
- `/v1/responses`
- `/v1/messages`
- Build Mode 工具执行层
- Build Mode 状态文件持久化
- mock upstream 工具调用回放

验证方式：

- 本地启动真实网关进程。
- 本地启动 mock upstream 进程。
- 通过 `scripts/live_gateway_smoke.py --proxy-tool-call` 走代理工具调用闭环。

### 2.2 三协议闭环

本轮 live-smoke 覆盖三条协议路径：

| 协议路径 | 覆盖内容 | 当前结果 |
| --- | --- | --- |
| Chat Completions | `write_file -> run_pytest -> feedback -> inspect -> repair -> archive` | 通过 |
| OpenAI Responses | function call 工具执行、工具过滤、失败修复、归档证据 | 通过 |
| Anthropic Messages | tool_use 工具执行、工具过滤、失败修复、归档证据 | 通过 |

### 2.3 核心状态链

本轮已经验证的状态链：

```text
111 乾/造
  -> scoped write 成功
  -> next_hexagram = 001

001 震/测
  -> 首次 verify 成功时 next_hexagram = 000
  -> 失败分支 failure_verify_status = needs_fix
  -> 失败分支 failure_verify_next_hexagram = 110

110 兑/纠
  -> Soft Feedback 存在
  -> post_failure_tools = ["native_inspect_card"]

101 离/查
  -> inspect_status = ok
  -> inspect_next_hexagram = 111
  -> post_inspect_tools = ["write_file"]

111 乾/修
  -> repair_status = ok
  -> repair_next_hexagram = 001
  -> repaired_file_written = true

001 震/复测
  -> post_repair_verify_status = completed
  -> post_repair_verify_next_hexagram = 000

000 坤/归
  -> manifest written
  -> manifest has repaired file
  -> manifest sha256 matches
  -> final state next_hexagram = 000
  -> consecutive_failures = 0
```

## 3. 本轮硬化点

本轮重点不是新增概念，而是压住 live-smoke 假阳性。

新增或确认的硬证据门包括：

- Responses / Anthropic 写入后下一轮工具必须过滤为 `["run_pytest"]`。
- Responses / Anthropic 初次 verify 成功必须进入 `000`。
- Responses / Anthropic 失败 verify 必须进入 `110`。
- Responses / Anthropic inspect 必须是 `inspect_status == "ok"` 且 `inspect_next_hexagram == "111"`。
- Responses / Anthropic inspect 后下一轮工具必须是 `["write_file"]`。
- Responses / Anthropic repair 必须是 `repair_status == "ok"` 且 `repair_next_hexagram == "001"`。
- Responses / Anthropic repair 后复测必须是 `completed -> 000`。
- Responses / Anthropic repair 后必须写 manifest，且 repaired file 存在、SHA256 匹配。
- 三路协议最终状态文件必须存在，且 `next_hexagram == "000"`、`consecutive_failures == 0`。

这些门禁的意义是：模型或 mock upstream 不能只返回一段“看起来成功”的文本；必须交出结构化状态和文件系统证据。

## 4. 验证命令与结果

本轮收尾前已运行以下验证：

| 命令 | 结果 |
| --- | --- |
| `python3 -m unittest tests.test_live_gateway_smoke_script -v` | 24 tests OK |
| `python3 -m compileall -q agent_skill_dictionary scripts tests` | 通过 |
| `make live-smoke` | `ok: true` |
| `make route-test` | 10 tests OK |
| 核心 Build Mode / Gateway 回归套件 | 163 tests OK |

`make live-smoke` 的关键证据包括：

| 字段 | 期望 | 实际 |
| --- | --- | --- |
| `ok` | `true` | `true` |
| `responses_repair_next_hexagram` | `001` | `001` |
| `anthropic_repair_next_hexagram` | `001` | `001` |
| `responses_post_repair_verify_next_hexagram` | `000` | `000` |
| `anthropic_post_repair_verify_next_hexagram` | `000` | `000` |
| `responses_post_repair_manifest_sha256_matches` | `true` | `true` |
| `anthropic_post_repair_manifest_sha256_matches` | `true` | `true` |
| `responses_state_next_hexagram` | `000` | `000` |
| `anthropic_state_next_hexagram` | `000` | `000` |
| `responses_state_consecutive_failures` | `0` | `0` |
| `anthropic_state_consecutive_failures` | `0` | `0` |

## 5. 当前工程状态

### 已经可视为本地闭环的部分

- Build Mode DTO 与八卦常量。
- Intent Resolver。
- Permission Matrix 与 Shadow Tool Mapping。
- Scoped Writer。
- Sandbox Runner。
- Soft Feedback。
- Archive Guard。
- Evidence-gated FSM。
- Tool Executor。
- Gateway integration。
- 三协议 live-smoke。

### 仍需真实接入验证的部分

- Codex Desktop 是否能稳定走 `/v1/responses`。
- Claude Code 是否能稳定走 `/v1/messages`。
- 真实客户端 SSE / chunk 边界是否完全兼容。
- 真实模型长任务中是否会产生 mock upstream 未覆盖的新 tool-call 形态。
- Docker / sandbox 策略在 N100、Mac、朋友机器上的一致性。

## 6. 阶段判断

可以阶段收尾：

- 文档层：三层法典已经有实现对应物。
- 本地代码层：Build Mode MVP 模块已能跑通核心闭环。
- 网关层：三协议代理工具执行已通过 live-smoke。
- 证据层：状态转移已经从“文本声称”升级为“结构化字段 + manifest + SHA256”。

不能过度宣称：

- 不能宣称真实 Codex Desktop 已完成端到端验证。
- 不能宣称真实 Claude Code 已完成端到端验证。
- 不能宣称生产级公开发布已经完成。
- 不能把历史 token 降幅直接外推到所有写盘构建任务。

## 7. 下一阶段建议

下一阶段只做真实客户端接入，不再重开底层法典：

1. Codex Desktop 指向本地网关，跑一个最小写盘项目。
2. Claude Code 指向本地网关，跑同一个最小写盘项目。
3. 记录真实客户端 SSE / tool-call 差异。
4. 如果真实客户端通过，再上 N100 容器单独部署。
5. 最后再做真实上游模型的长任务 A/B。

推荐阶段命名：

```text
Build Mode Client E2E Validation
```

推荐验收线：

```text
真实客户端 -> 本地网关 -> Build Mode Runner -> manifest/SHA256 -> 客户端收到 200 OK 软反馈或完成报告
```
