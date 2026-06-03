# OneCode Second-Order Architecture Guards Closure Report

日期：2026-06-02
状态：阶段收尾
范围：异步时序空洞、Domain Projection 漂移、Metrics Storm 第一阶段防线、壳系统控制面出口

## 1. 阶段结论

本阶段在已完成的证据链分层与 Manifest 边界基础上，继续补强了三个二阶架构风险：

1. 低风险 trace 聚合可能在 critical 事件前形成时间线空洞。
2. `domain_projection` 可能在合法字段内偷渡复杂业务图。
3. 多节点场景下 metrics 可能以原始账本形式集中上报，制造新的观测风暴。
4. Manifest 和 evidence metrics 需要进一步具备硬阈值与延迟观测能力。
5. 聚合窗口缺口和异常事件需要有第一阶段自动识别。

本阶段没有引入完整分布式控制面，也没有把 OneCode 扩展成 workflow engine。改动集中在现有内核边界内，建立第一道可测试、可回归的防线。

补充结论：

壳系统可以承担 metrics 的控制面展示、拉取和触发职责，但不能承担 evidence 生成、因果判断、repair 决策或 artifact 持久化职责。也就是说，壳系统可以直接使用 OneCode API 暴露的 summary-only 指标来解决观测风暴的默认出口问题；底层可信语义仍必须留在 kernel。

## 2. 已关闭的问题

### 2.1 Critical 写屏障

问题判断：成立。

低风险事件使用 aggregate 是必要的性能优化，但 critical/full 事件写入不能越过尚未 flush 的聚合事件。否则在断电、OOM kill 或进程被强制终止时，磁盘上的证据时间线会出现关键动作已记录、前置低风险状态丢失的空洞。

已落地解法：

- `TraceAggregator.record()` 遇到 `critical/full` 事件时，会先 flush 当前 pending aggregate。
- 普通 runner 内部编排事件被明确分类为 `medium/compact`，避免 unknown fail-closed 造成过度 flush。
- `run_completed` 被明确归类为 `critical/full`。
- Final critical trace 写入失败时，正常完成路径不会继续返回 `completed`，而是转为 `halted/run_exception`。

### 2.2 Domain Projection 物理限额

问题判断：成立。

Strict allowlist 能阻止显式 workflow/rules/state machine 字段进入 Manifest，但不能单独阻止上层把业务图压缩进合法字段。需要用物理密度限制补上第二道边界。

已落地解法：

- `domain_projection` 增加总字节数限制。
- 合法字符串字段增加单字段字节数限制。
- `evidence_refs` 增加数量限制。
- 单个 evidence ref 增加长度限制。
- evidence ref 只允许可信证据引用前缀：`trace:`、`wal:`、`ledger:`、`checkpoint:`、`artifact:`。
- `schema_id`、`entity_id_hash`、`from_state`、`to_state`、`decision_id`、`decision_hash` 增加保守字符集限制，拒绝控制字符和空白注入。

### 2.3 Manifest Metrics 阈值

问题判断：成立。

Manifest 虽然不嵌入业务流程图，但仍可能因为 checkpoint 索引、投影或历史记录异常膨胀而破坏本地 I/O 与 inspect 可用性。仅记录 `manifest_metrics` 不够，还需要把 metrics 变成拒绝条件。

已落地解法：

- Manifest 写入前计算 `manifest_metrics`。
- Manifest total bytes 超过阈值时拒绝写入。
- Manifest 单 section bytes 超过阈值时拒绝写入。
- 阈值拒绝发生在 manifest 落盘前，避免写入已经超界的清单。

### 2.4 Metrics Storm 摘要出口

问题判断：成立。

单机 inspect metrics 不能直接等同于多节点上报协议。如果每个边缘节点都推送原始 WAL entry 或原始账本，控制面会重新承受 metadata I/O 压力。

已落地解法：

- 新增 `global_wal_metrics_summary()`。
- Summary 按固定时间窗口聚合 WAL metrics。
- Summary 只包含 entry count、byte count、risk tier 分布、capture mode 分布。
- Summary 不返回 `entries` 或 `raw_entries`，避免默认出口携带原始账本。
- Web API 新增 `GET /v1/onecode/metrics`。
- 该端点返回 `control_plane.scope=summary` 与 `raw_entries_included=false`，供壳系统直接消费。
- `window_seconds` 支持请求侧指定，并限制在安全范围内，避免壳层传入异常窗口。

### 2.5 Evidence Write Latency

问题判断：成立。

Evidence metrics 只统计字节数和事件数不足以定位 I/O 性能问题。需要记录 trace 写入延迟，让后续 p95/max 级别的背压策略有数据来源。

已落地解法：

- `write_trace_event()` 记录单条 trace JSONL append 的 `write_latency_ms`。
- `trace_evidence_metrics()` 汇总 latency count、max、p95。
- Latency 采用固定宽度原位回填，避免为了记录延迟而重写整个 trace 文件。

### 2.6 Aggregate Gap Detection

问题判断：成立。

低风险事件聚合后，单个 aggregate 只能证明一个窗口内的状态。相邻 aggregate 窗口之间如果出现过长空白，应当被视为需要审计的 liveness gap，而不是被普通 metrics 吞掉。

已落地解法：

- `trace_evidence_metrics()` 支持 `aggregate_gap_threshold_seconds`。
- Trace metrics 扫描相邻 aggregate 的 `last_timestamp` 与 `first_timestamp`。
- 超过阈值时记录 `aggregate_gap_count`。
- 同时记录 `max_aggregate_gap_seconds`。
- `inspect_run()` 会基于 trace 文件重新计算最新 trace metrics。
- 当 `aggregate_gap_count > 0` 时，inspect 不把证据链判为 corrupt，但会输出 `repair_required=true`、`repair_reason=trace_aggregate_gap`，并覆盖为 `delivery_status=blocked`、`next_action=repair`。

### 2.7 Anomaly Escalation

问题判断：成立。

正常内部编排事件可以是 `medium/compact`，但同类事件在失败、拒绝、超时或资源预算异常时不应继续保持普通风险级别。

已落地解法：

- `TraceEvent` 在 `halted`、`denied`、`failed`、`timeout` 状态下自动升级非 critical/high 事件。
- `http_timeout`、`resource_budget_exceeded`、`sovereignty_breach` reason 触发升级。
- 升级后的事件为 `high/compact`，`classification_reason` 为 `anomaly_escalation`。

## 3. 当前实现形态

核心改动文件：

- `src/onecode/kernel/evidence_policy.py`
  - 增加 runner 内部事件分类。
  - 明确 `run_completed` 为 `critical/full`。
- `src/onecode/kernel/trace.py`
  - `TraceAggregator` 增加 critical/full write barrier。
  - Trace event 写入记录 `write_latency_ms`。
  - Trace metrics 汇总 write latency count/max/p95。
  - Trace metrics 识别 aggregate 窗口缺口。
  - Trace event 支持 anomaly escalation。
- `src/onecode/kernel/checkpoint.py`
  - `validate_domain_projection()` 增加大小、数量和引用前缀约束。
  - `validate_domain_projection()` 增加保守字符集约束。
  - `manifest_metrics` 增加阈值化拒绝。
- `src/onecode/kernel/wal.py`
  - 新增 `global_wal_metrics_summary()`。
- `src/onecode/cli.py`
  - `inspect` full summaries 刷新 trace `evidence_metrics`。
  - Trace aggregate gap 触发 inspect-level repair gate。
- `src/onecode/web/api.py`
  - 新增 `handle_onecode_metrics()`。
  - 新增 `GET /v1/onecode/metrics` summary-only 路由。

对应测试：

- `tests/test_evidence_policy.py`
- `tests/test_trace.py`
- `tests/test_checkpoint.py`
- `tests/test_wal.py`
- `tests/test_inspect_cli.py`
- `tests/test_web_api.py`

## 4. 行为保证

当前实现建立了以下保证：

- Pending aggregate 不会被 critical/full trace event 越过。
- Final critical trace 写入失败不会伪装成 completed run。
- Runner progress aggregation 不会被普通 medium/compact 编排事件拆碎。
- 未知事件仍然 fail closed 为 `critical/full`。
- `domain_projection` 不能通过超大合法字段承载隐藏业务配置。
- `evidence_refs` 不能无限增长，也不能使用任意伪装引用。
- `domain_projection` 合法字段不能包含控制字符或空白注入。
- Manifest metrics 超过硬阈值时会拒绝写入。
- Trace metrics 可以观察 write latency max/p95。
- Trace metrics 可以识别 aggregate 窗口缺口。
- Inspect 会把 aggregate 窗口缺口转换为 repair-required 决策，阻止静默交付。
- 失败、拒绝、超时类内部编排事件会自动升级到 high/compact。
- 多节点 metrics 的默认候选出口可以使用窗口化 summary，而不是原始 WAL entries。
- 壳系统可以通过 OneCode Web API 拉取 summary-only metrics，不需要也不应该直接读取 WAL raw entries。

## 5. 验收核对

| 验收项 | 状态 | 证据 |
| --- | --- | --- |
| Critical/full 事件前 flush pending aggregate | 通过 | `tests/test_trace.py` 覆盖写屏障顺序。 |
| Final critical trace 写失败不能返回 completed | 通过 | `tests/test_runner_cli.py` 覆盖 final trace failure 转 halted。 |
| Runner 内部编排不误触发过度 flush | 通过 | `tests/test_evidence_policy.py` 覆盖 medium/compact 分类。 |
| 低风险 progress tick 仍能聚合为一个 aggregate | 通过 | `tests/test_runner_cli.py` 回归仍通过。 |
| Projection 合法字段不能无限膨胀 | 通过 | `tests/test_checkpoint.py` 覆盖字段体积限制。 |
| Projection evidence refs 不能无限增长 | 通过 | `tests/test_checkpoint.py` 覆盖引用数量限制。 |
| Projection evidence refs 不能伪装成任意业务配置 | 通过 | `tests/test_checkpoint.py` 覆盖引用前缀校验。 |
| Projection 合法字段拒绝控制字符 | 通过 | `tests/test_checkpoint.py` 覆盖字符集限制。 |
| Manifest metrics 超阈值拒绝写入 | 通过 | `tests/test_checkpoint.py` 覆盖 total bytes threshold。 |
| Trace evidence metrics 包含写延迟 | 通过 | `tests/test_trace.py` 覆盖 `write_latency_ms` 汇总。 |
| Trace evidence metrics 识别聚合窗口缺口 | 通过 | `tests/test_trace.py` 覆盖 aggregate gap。 |
| 聚合窗口缺口触发强制 repair 决策 | 通过 | `tests/test_inspect_cli.py` 覆盖 inspect 输出 `repair_required` 与 `next_action=repair`。 |
| 异常事件自动升级风险等级 | 通过 | `tests/test_trace.py` 覆盖 anomaly escalation。 |
| WAL metrics 可按窗口输出摘要 | 通过 | `tests/test_wal.py` 覆盖 summary 不返回 raw entries。 |
| 壳系统可通过 API 拉取 summary-only metrics | 通过 | `tests/test_web_api.py` 覆盖 `handle_onecode_metrics()` 与 HTTP 路由。 |

## 6. 验证证据

本阶段完成后已执行核心验证：

```text
bash scripts/verify-core.sh
compileall: OK
Ran 193 tests in 5.853s
OK
doctor: {"status": "ok"}
```

该验证覆盖 Python 编译、核心 unittest 套件和 OneCode doctor 诊断。

## 7. 当前边界

已闭合：

- Critical/full trace write barrier。
- Final critical trace failure halt。
- Runner 内部事件显式分类。
- Domain projection 物理密度限制。
- Domain projection 字符集限制。
- Manifest metrics 阈值化拒绝。
- Trace write latency metrics。
- Aggregate gap metrics。
- Aggregate gap inspect repair gate。
- Trace anomaly escalation。
- WAL metrics windowed summary。
- Web API summary-only metrics endpoint。
- 对应回归测试。

仍需后续增强：

- Flush 失败后的更细粒度 repair 策略。
- 多节点 metrics 上报的速率限制、批量窗口和背压协议。壳系统当前可以消费摘要，但不替代节点级背压协议。
- 完整 deferred artifact store。
- 多节点 trace causality。

## 8. 收尾判断

本阶段可以收尾。
