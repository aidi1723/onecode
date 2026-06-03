# OneCode Evidence Manifest Shell Final Closure

日期：2026-06-03
状态：最终收尾
范围：证据链 I/O 膨胀、Manifest 业务状态爆炸、二阶架构防线、壳系统控制面承接

## 1. 总结论

本轮架构问题可以收尾。

已经闭合的是 OneCode 底层安全内核在本阶段必须解决的问题：

- 证据链不能盲目全量审计。
- Manifest 不能退化成业务状态机配置中心。
- Critical/full 事件不能越过低风险聚合日志。
- Final trace 写失败不能误报 completed。
- `domain_projection` 不能通过合法字段偷渡业务图。
- Manifest metrics 不能只观测不拦截。
- Evidence write latency 和 aggregate gap 必须可观测。
- Aggregate gap 不能只停留在指标层，必须转成 repair gate。
- Metrics storm 不能通过壳系统集中拉 raw WAL。

本轮正确边界已经明确：

```text
壳系统 = 控制面、展示面、触发面
OneCode kernel = 可信事实生成、证据写入、边界校验、repair 决策
```

## 2. 已闭合问题

| 问题 | 状态 | 收口方式 |
| --- | --- | --- |
| 证据链 I/O 膨胀 | 已闭合第一阶段 | `RiskTier`、`CaptureMode`、low-risk aggregation、trace/WAL metrics。 |
| 未知事件误轻量化 | 已闭合 | Unknown event fail closed 为 `critical/full`。 |
| Critical 事件前置聚合丢失 | 已闭合 | `TraceAggregator` 在 critical/full 前 flush pending aggregate。 |
| Final trace 写失败误报 completed | 已闭合 | final critical trace failure 转为 `halted/run_exception`。 |
| Manifest 业务状态爆炸 | 已闭合第一阶段 | Manifest 只允许 bounded `domain_projection`，拒绝 workflow/rules/state machine。 |
| Projection 合法字段偷渡业务图 | 已闭合 | 总字节、单字段字节、字符集、引用数量、引用长度、引用前缀限制。 |
| Manifest metrics 只观测不拦截 | 已闭合 | total bytes 与 section bytes 超阈值拒绝写入。 |
| Evidence write latency 不可观测 | 已闭合 | trace event 写入 `write_latency_ms`，metrics 汇总 count/max/p95。 |
| Aggregate gap 不可见 | 已闭合 | `trace_evidence_metrics()` 输出 `aggregate_gap_count` 与 `max_aggregate_gap_seconds`。 |
| Aggregate gap 静默交付 | 已闭合 | `inspect_run()` 输出 `repair_required=true`、`next_action=repair`，并阻断 deliverable。 |
| 异常事件仍保持普通风险级别 | 已闭合 | failed/denied/timeout/resource/sovereignty 类事件升级为 `high/compact`。 |
| Metrics storm 默认出口 | 已闭合第一阶段 | `global_wal_metrics_summary()` 与 `GET /v1/onecode/metrics` 只返回 summary，不返回 raw entries。 |
| 壳系统直接读 raw WAL 的边界风险 | 已闭合第一阶段 | 壳系统通过 API 消费 summary、inspect、evidence，不直接扫描 WAL。 |

## 3. 已落地文档

本轮收尾文档：

- `docs/ONECODE_EVIDENCE_CHAIN_MANIFEST_BOUNDARY_CLOSURE_REPORT.md`
- `docs/ONECODE_SECOND_ORDER_ARCHITECTURE_GUARDS_CLOSURE_REPORT.md`
- `docs/ONECODE_SHELL_CONTROL_PLANE_CLOSURE_REPORT.md`
- `docs/ONECODE_EVIDENCE_MANIFEST_SHELL_FINAL_CLOSURE.md`

## 4. 已落地实现面

核心实现：

- `src/onecode/kernel/evidence_policy.py`
- `src/onecode/kernel/trace.py`
- `src/onecode/kernel/checkpoint.py`
- `src/onecode/kernel/wal.py`
- `src/onecode/kernel/runner.py`
- `src/onecode/cli.py`
- `src/onecode/web/api.py`

核心能力：

- Evidence risk tier。
- Capture mode。
- Low-risk trace aggregation。
- Critical/full write barrier。
- Trace write latency metrics。
- Trace aggregate gap metrics。
- Inspect-level aggregate gap repair gate。
- Domain projection allowlist。
- Domain projection physical density limits。
- Manifest metrics threshold rejection。
- Global WAL metrics summary。
- Web API summary-only metrics endpoint。
- Shell-facing inspect projection。

## 5. 验证证据

最终验证命令：

```text
bash scripts/verify-core.sh
```

最终验证结果：

```text
compileall: OK
Ran 193 tests in 5.853s
OK
doctor: {"status": "ok"}
```

该验证覆盖 Python 编译、核心 unittest 套件和 OneCode doctor 诊断。

## 6. 当前不阻塞收尾的后续项

以下事项属于下一阶段分布式运行时能力，不阻塞本轮收尾：

- 更细粒度 flush repair policy。
- Node-level metrics rate limit、batch window、backpressure protocol。
- Deferred artifact store。
- Multi-node trace causality。

这些能力需要调度协议、artifact store 和跨节点因果模型配合，不能仅靠壳系统或单机 inspect 完成。

## 7. 最终收尾判断

本轮可以收尾。

OneCode 已经从 PoC 级 evidence/manifest 设计，推进到具备以下特征的第一阶段生产内核：

- 关键证据完整。
- 低风险事件可聚合。
- Manifest 边界清晰。
- 合法字段无法无限膨胀。
- 指标默认输出摘要。
- 壳系统只消费可信摘要和 inspect 投影。
- 聚合时间线缺口会触发 repair gate。

后续工作应另开阶段，不再混入本轮闭环。
