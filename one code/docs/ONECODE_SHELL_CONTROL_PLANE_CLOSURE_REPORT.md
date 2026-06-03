# OneCode Shell Control Plane Closure Report

日期：2026-06-03
状态：阶段收尾
范围：壳系统对 evidence metrics、Manifest 边界和二阶架构风险的承接能力

## 1. 结论

壳系统可以解决的是控制面问题：

- 展示 run summary。
- 展示 shell projection。
- 拉取 summary-only evidence metrics。
- 触发 inspect、resume、doctor、audit-self。
- 作为本地 UI 或 LibreChat 接入层承接用户操作。

壳系统不能替代内核解决的是可信语义问题：

- Evidence 事件分类。
- WAL/trace 写入顺序。
- Critical write barrier。
- Manifest 边界校验。
- Domain projection 物理限额。
- Artifact 内容寻址与持久化。
- Recovery repair 决策。
- 多节点 trace causality。

因此，本轮正确收口方式不是让壳系统直接读取和解释原始 WAL，而是由 OneCode kernel 生成可信摘要，由 Web API 以 summary-only 形式暴露给壳系统。

## 2. 本轮已落地

### 2.1 壳系统已有能力

当前代码中，壳系统已经具备以下基础：

- `src/onecode/kernel/shell_projection.py`
  - 将 run result 投影成壳层可显示的 `shell_projection`。
  - 输出 severity、next_action、compact_message、evidence_ref、delivery_state、resume_state。
- `src/onecode/shell_launcher.py`
  - 启动 OneCode API 与 LibreChat shell。
  - 配置 `ONECODE_API_BASE_URL` 与 `ONECODE_API_TOKEN`。
  - 提供 shell status 检查。
- `src/onecode/web/api.py`
  - 已有 project status、runs list、run inspect、run evidence、resume、doctor、audit-self 等控制面 API。

### 2.2 本轮新增能力

新增 `GET /v1/onecode/metrics`：

- 返回 workspace。
- 返回 `control_plane.scope=summary`。
- 返回 `control_plane.raw_entries_included=false`。
- 返回 `global_wal_summary`。
- 支持 `window_seconds` 请求参数。
- 默认不返回 `entries` 或 `raw_entries`。

对应实现：

- `src/onecode/web/api.py`
  - `parse_window_seconds()`
  - `handle_onecode_metrics()`
  - `GET /v1/onecode/metrics`

对应测试：

- `tests/test_web_api.py`
  - `test_onecode_metrics_endpoint_returns_control_plane_wal_summary_without_raw_entries`
  - `test_http_server_serves_onecode_metrics_endpoint`

## 3. 问题闭环判断

| 问题 | 当前状态 | 说明 |
| --- | --- | --- |
| 证据链 I/O 膨胀 | 已闭合第一阶段 | kernel 已有 risk tier、capture mode、aggregation、metrics。 |
| Manifest 业务状态爆炸 | 已闭合第一阶段 | Manifest 只允许 bounded `domain_projection`，拒绝 workflow/rules/state machine。 |
| Critical 前置低风险事件丢失 | 已闭合第一阶段 | Trace aggregator 在 critical/full 事件前 flush pending aggregate。 |
| Final trace 写失败误报 completed | 已闭合第一阶段 | final critical trace failure 会转 `halted/run_exception`。 |
| Projection 合法字段内偷渡业务图 | 已闭合第一阶段 | 字节数、字符集、引用数量、引用长度和引用前缀均有限制。 |
| Metrics storm 默认出口 | 已闭合第一阶段 | kernel 提供 windowed WAL summary，Web API 提供 summary-only `/metrics` 给壳系统。 |
| 壳系统是否能直接解决未完成项 | 部分能 | 壳系统能承接观测、展示、拉取、触发；不能承接 evidence/recovery/causality 内核语义。 |
| Flush 失败后的细粒度 repair | 未完全闭合 | 需要 kernel recovery policy，不应由壳系统判断。 |
| 聚合窗口缺口强制 repair 决策 | 已闭合第一阶段 | inspect 会把 `aggregate_gap_count > 0` 转为 `repair_required=true`、`next_action=repair`。 |
| 多节点 metrics 背压协议 | 未完全闭合 | 壳系统已有 summary pull 入口；节点级速率限制和背压仍需协议设计。 |
| Deferred artifact store | 未闭合 | 需要 kernel artifact store，不是壳系统职责。 |
| 多节点 trace causality | 未闭合 | 需要跨节点 causal id / parent id / handoff event 设计。 |

## 4. 边界原则

壳系统只消费可信内核产物，不生成可信事实。

推荐边界：

- 壳系统读取 `/v1/onecode/metrics`，展示摘要。
- 壳系统读取 `/v1/onecode/runs`，展示运行列表。
- 壳系统读取 `/v1/onecode/runs/<run_id>/inspect`，展示单次运行状态。
- 壳系统读取 `/v1/onecode/runs/<run_id>/evidence`，按需展示证据详情。
- 壳系统不直接扫描 `.onecode/global-ledger*.jsonl`。
- 壳系统不根据 raw WAL 自行做 repair。
- 壳系统不把 Manifest 扩展成业务 workflow 配置。

## 5. 收尾判断

本阶段可以收尾。

已经解决的是第一阶段架构闭环和壳系统控制面承接：

- 性能与证据链的权衡已经有分级策略。
- Manifest 与业务状态机边界已经有强约束。
- 二阶风险已有 write barrier、projection density limit、metrics summary、latency/gap/anomaly metrics。
- 聚合窗口缺口已经由 inspect gate 转为强制 repair 决策，不由壳系统自行判断。
- 壳系统已经可以通过 Web API 消费 summary-only metrics，不需要直接读取 raw WAL。

仍未完全解决的是下一阶段分布式运行时能力：

- repair policy。
- node-level metrics backpressure。
- deferred artifact store。
- multi-node trace causality。

这些问题不能靠壳系统本身彻底解决，只能由壳系统提供入口和展示，由 OneCode kernel 与调度协议继续承接。
