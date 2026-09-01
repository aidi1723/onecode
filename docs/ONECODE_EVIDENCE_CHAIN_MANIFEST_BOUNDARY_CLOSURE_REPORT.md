# OneCode Evidence Chain And Manifest Boundary Closure Report

日期：2026-06-02
状态：阶段收尾
范围：OneCode 证据链性能权衡 + Manifest 业务状态边界

## 1. 阶段结论

本阶段已经把两个架构风险从讨论问题推进到可验证的第一阶段实现：

1. 证据链日志不能盲目全量审计，否则低风险运行时事件会把本地集群 I/O 和 metadata 存储拖垮。
2. Manifest 不能承载复杂业务状态机，否则会从执行证据清单膨胀成业务流程配置中心。

当前 OneCode 的处理原则已经明确为：

```text
可验证交付 != 所有事件全量同步落盘
执行 Manifest != 业务状态机
```

OneCode 保留关键可信事件的完整证据，同时对低风险、重复性、可聚合的内部运行事件做轻量化记录。Manifest 保持为执行证据索引，只接收有边界的业务状态投影，不接收业务流程图、规则矩阵或分支配置。

## 2. 已关闭的问题

### 2.1 证据链与性能的权衡偏误

问题判断：成立。

如果为了 Verifiable Outcomes 对所有 API 编排、调度心跳、进度 tick、状态迁移、非突变检查都做 full evidence，同步写入压力会快速放大。风险不是“证据太多”本身，而是缺少风险分层后，把低价值事件放进了高成本写入路径。

已落地解法：

- 引入 `risk_tier`：`critical`、`high`、`medium`、`low`。
- 引入 `capture_mode`：`full`、`compact`、`aggregate`、`sampled`、`deferred`。
- 未知事件默认 fail closed：按 `critical/full` 记录。
- 关键可信事件保持 full evidence：审批、权限边界、路径守卫、物理写入、验证器结果、恢复冲突、任务完成。
- 低风险进度事件通过聚合记录降低 metadata 写入量。
- 运行结果、ledger 和 inspect 输出暴露 evidence metrics，用于观察证据字节数和事件分布。

### 2.2 Manifest 配置爆炸

问题判断：成立。

如果 OneCode 直接承载订单、审批、结算、履约、补偿、异常流转等复杂业务状态，`manifest.json` 会被迫加入大量领域字段、状态分支和转移规则。最终 Manifest 会失去“执行证据清单”的稳定职责，变成难迁移、难验证、难恢复的业务流程配置。

已落地解法：

- Manifest 增加 `manifest_schema_version`。
- Manifest 支持可选、严格边界的 `domain_projection`。
- `domain_projection` 只允许保存：
  - `schema_id`
  - `entity_id_hash`
  - `from_state`
  - `to_state`
  - `decision_id`
  - `decision_hash`
  - `evidence_refs`
- Manifest 拒绝业务流程配置类字段，例如 `transitions`、`state_machine`、`workflow`、`rules`。
- Manifest 增加 `manifest_metrics`，记录清单各部分大小和投影数量。

## 3. 当前实现形态

新增和修改的核心文件：

- `src/onecode/kernel/evidence_policy.py`
  - 定义风险分层、采集模式和默认分类策略。
- `src/onecode/kernel/trace.py`
  - Trace event 写入风险分层字段。
  - 支持低风险事件聚合。
  - 提供 trace evidence metrics。
- `src/onecode/kernel/checkpoint.py`
  - WAL entry 增加风险分层字段。
  - Manifest 增加 schema version、bounded domain projection、manifest metrics。
- `src/onecode/kernel/runner.py`
  - Runner 接入 trace aggregation。
  - full evidence 结果和 ledger 写入 trace metrics。
  - WAL-only 结果写入 global WAL metrics。
- `src/onecode/kernel/wal.py`
  - 提供 hash-chain 校验后的 global WAL evidence metrics。
- `src/onecode/cli.py`
  - `inspect` 输出 full evidence 与 WAL-only 的 evidence metrics。

对应测试覆盖：

- `tests/test_evidence_policy.py`
- `tests/test_trace.py`
- `tests/test_wal.py`
- `tests/test_checkpoint.py`
- `tests/test_runner_cli.py`
- `tests/test_inspect_cli.py`

## 4. 行为保证

当前实现建立了以下保证：

- Critical 事件不会因为性能优化被降级为 aggregate。
- 未知事件不会被轻量放行，而是按 full evidence 处理。
- Low-risk progress tick 可以聚合为 `progress_tick_aggregate`，保留 count、时间范围和 rolling digest。
- Full evidence run 的结果与 ledger 可以看到 `evidence_metrics.trace`。
- WAL-only run 的结果与 inspect summary 可以看到 `evidence_metrics.global_wal`。
- Manifest 可以记录业务状态投影，但不能记录业务状态机。
- Resume 和最终交付语义仍依赖完整关键证据，而不是 aggregate-only 或 sampled-only 信息。

## 5. 问题闭环矩阵

| 问题 | 当前状态 | 处理结果 |
| --- | --- | --- |
| 全量审计导致 I/O 和 metadata 压力 | 已闭合第一阶段 | 事件写入带 `risk_tier` 与 `capture_mode`，低风险 progress tick 已聚合。 |
| 未知事件被误轻量化 | 已闭合 | 未知事件 fail closed 为 `critical/full`。 |
| 关键可信事件被性能优化稀释 | 已闭合 | 审批、权限边界、路径守卫、物理写入、验证器、恢复冲突、最终交付保持 full evidence。 |
| Evidence 开销不可观测 | 已闭合第一阶段 | Trace 与 global WAL 均有按风险层级和采集模式分组的 metrics。 |
| Full evidence 与 WAL-only inspect 视角不一致 | 已闭合 | `inspect` 同时支持 ledger metrics 与 validated global WAL metrics。 |
| Manifest 承载业务状态机导致配置爆炸 | 已闭合第一阶段 | Manifest 只允许 bounded `domain_projection`，拒绝 workflow/rules/state machine 类字段。 |
| Manifest 大小增长不可观测 | 已闭合第一阶段 | `manifest_metrics` 记录 section size、embedded/referenced bytes 与 projection count。 |
| 异步聚合导致 critical 时间线空洞 | 已闭合第一阶段 | `TraceAggregator` 在 critical/full 事件写入前 flush pending aggregate，形成写屏障。 |
| Flush 失败后误报 completed | 已闭合第一阶段 | Final critical trace 写入失败会转为 `halted/run_exception`，不会继续返回 completed。 |
| 合法 projection 字段内偷渡业务图 | 已闭合第一阶段 | `domain_projection` 增加总大小、单字段大小、字符集、引用数量、引用长度和引用格式限制。 |
| Manifest metrics 只观测不拦截 | 已闭合第一阶段 | Manifest 写入前执行 total bytes 与 section bytes 阈值检查。 |
| Evidence write latency 不可观测 | 已闭合第一阶段 | Trace event 记录 `write_latency_ms`，trace metrics 汇总 count/max/p95。 |
| 聚合窗口缺口不可见 | 已闭合第一阶段 | Trace metrics 记录 `aggregate_gap_count` 与 `max_aggregate_gap_seconds`。 |
| 异常事件仍保持普通风险级别 | 已闭合第一阶段 | 失败、拒绝、超时类 trace event 自动升级为 `high/compact`。 |
| 多节点 metrics 直推导致观测风暴 | 已闭合第一阶段 | 新增 windowed WAL metrics summary，只输出摘要和窗口统计，不返回原始账本 entry。 |
| 大型 artifact 异步落盘和哈希引用 | 后续项 | `deferred` 已作为策略词汇保留，但完整 artifact store 未在本阶段落地。 |
| 调度器、多节点、底层 API 编排统一接入分类 | 后续项 | 当前主要覆盖 trace、WAL、runner progress tick；多节点 causality 仍需下一阶段设计。 |
| 异常触发自动升级证据密度 | 后续项 | 分类策略支持 fail closed，运行级 anomaly escalation 尚未完整实现。 |

## 6. 验收标准核对

| 验收标准 | 状态 | 证据 |
| --- | --- | --- |
| Critical trust events 保持 full evidence | 通过 | `tests/test_evidence_policy.py` 覆盖关键事件分类。 |
| Low-risk repeated transitions 可聚合 | 通过 | `tests/test_trace.py` 与 `tests/test_runner_cli.py` 覆盖 aggregate trace。 |
| Resume/final delivery 不依赖 sampled-only 或 aggregate-only | 通过 | 关键写入、恢复和 inspect 回归测试仍通过。 |
| Unknown event fail closed | 通过 | Trace 与 WAL 未知事件测试覆盖 `critical/full`。 |
| Evidence overhead 可按 tier/mode 观测 | 通过 | `trace_evidence_metrics()` 与 `global_wal_evidence_metrics()` 有测试覆盖。 |
| Manifest 保持执行证据索引 | 通过 | `domain_projection` allowlist 与 forbidden-field 测试覆盖。 |
| 复杂业务 workflow 不需要写入 Manifest 分支字段 | 通过第一阶段 | Manifest 拒绝 `transitions`、`state_machine`、`workflow`、`rules`。 |
| Critical 写入前不丢 pending aggregate | 通过第一阶段 | `tests/test_trace.py` 覆盖 critical/full write barrier。 |
| Final critical trace 写失败不能返回 completed | 通过第一阶段 | `tests/test_runner_cli.py` 覆盖 final trace failure。 |
| Domain projection 不能在合法字段内膨胀 | 通过第一阶段 | `tests/test_checkpoint.py` 覆盖字段体积、字符集、引用数量和引用格式限制。 |
| Manifest metrics 超阈值拒绝写入 | 通过第一阶段 | `tests/test_checkpoint.py` 覆盖 total bytes threshold。 |
| Evidence write latency 可观测 | 通过第一阶段 | `tests/test_trace.py` 覆盖 trace latency count/max/p95。 |
| 聚合窗口缺口可观测 | 通过第一阶段 | `tests/test_trace.py` 覆盖 aggregate gap metrics。 |
| 异常事件自动升级证据密度 | 通过第一阶段 | `tests/test_trace.py` 覆盖 anomaly escalation。 |
| Metrics 默认可按窗口摘要上报 | 通过第一阶段 | `tests/test_wal.py` 覆盖 `global_wal_metrics_summary()` 不返回原始 entries。 |
| Deferred artifact store 完整可用 | 未纳入本阶段 | 已列入下一阶段。 |
| 多节点调度 trace causality 完整可用 | 未纳入本阶段 | 已列入下一阶段。 |

## 7. 验证证据

阶段实现完成后已执行核心验证：

```text
bash scripts/verify-core.sh
compileall: OK
Ran 192 tests in 5.763s
OK
doctor: {"status": "ok"}
```

该验证覆盖 Python 编译、核心 unittest 套件和 OneCode doctor 诊断。

## 8. 当前边界

本阶段是第一阶段工程闭环，不是全部可观测性系统的最终形态。

已闭合：

- 证据采集从单一 full/wal 思路扩展为风险分层。
- 低风险重复事件已有聚合路径。
- Critical/full trace event 写入前会 flush pending aggregate，降低异步时间线空洞风险。
- Final critical trace failure 会转为 halted/run_exception，不会误报 completed。
- Evidence metrics 已进入 runner result、ledger 和 inspect。
- Trace evidence metrics 已包含 write latency count/max/p95。
- Trace evidence metrics 已包含 aggregate gap count/max gap seconds。
- 失败、拒绝、超时类 trace event 已可自动升级为 high/compact。
- Manifest 已有业务投影边界与拒绝规则。
- `domain_projection` 已有物理密度限制，阻止合法字段内的隐式业务图膨胀。
- Manifest metrics 已可作为写入前阈值拒绝条件。
- Global WAL metrics 已有窗口化 summary，适合作为多节点上报的默认摘要形态。
- 风险分类和 Manifest 边界有测试覆盖。

仍需后续增强：

- 当前聚合主要覆盖 runner progress tick，还没有覆盖所有调度器、多节点和底层 API 编排事件。
- `deferred` 大型 artifact 存储仍停留在设计约束，尚未形成完整 artifact store。
- 异常触发已有 high/compact 第一阶段升级，运行级 full escalation 仍可继续强化。
- evidence write latency 当前已有 p95/max；p50 与背压策略仍可继续增强。
- 多节点调度下的跨节点 trace causality 仍需要专门设计。

## 9. 后续建议

下一阶段建议命名为：

```text
OneCode Evidence Runtime v0.2 - Scheduler And Artifact Backpressure
```

优先级：

1. 把调度器、多节点 handoff、API 编排事件全部接入统一 evidence classification。
2. 建立 deferred artifact store，用内容哈希引用长输出、模型观察和诊断 tail。
3. 加入 evidence writer backpressure 指标，包括同步写延迟、buffer overflow、fsync 失败和聚合 flush 次数。
4. 增强 anomaly escalation：失败、超时、重试耗尽、权限边界、hash mismatch 时支持运行级 full escalation。
5. 为复杂业务状态接入外部 workflow/domain schema 示例，只向 Manifest 投影 digest 和 evidence refs。

## 10. 下一阶段架构警戒

本阶段已为以下二阶风险补上第一道防线，但接入高动态自治 Agent、多节点硬件环境或分布式 sidecar 后，仍需要把它们作为下一轮模块设计的前置约束。

### 10.1 异步时序空洞

风险：

低风险事件已经支持聚合和延迟 flush，但 critical/full 事件仍需要即时、可靠地写入 WAL 或 ledger。在断电、OOM kill、进程被强制终止时，磁盘上可能出现关键事件已落盘，而其前置低风险聚合事件仍停留在内存中的时间线空洞。

本阶段已补防线：

- `TraceAggregator` 在遇到 critical/full 事件时，会先 flush 当前 pending aggregate，再写入关键事件。
- Runner 内部编排事件已明确归类为 medium/compact，避免误用 unknown fail-closed 触发过度 flush。

后续防御要求：

- Flush 失败时不得继续声明关键动作完成。
- 恢复逻辑应能识别聚合窗口缺口，并把该运行标记为需要审计或修复。

### 10.2 Domain Projection 漂移

风险：

Manifest 已拒绝业务流程图和状态机字段，但上层开发者仍可能把复杂业务语义压缩、编码或伪装进合法字段，导致 `domain_projection` 在字段名合法的情况下发生数据密度膨胀，实质上退化为隐式业务配置。

本阶段已补防线：

- 对 `domain_projection` 增加总字节数限制。
- 对合法字符串字段增加单字段字节数限制。
- 对 `evidence_refs` 增加数量、字符串长度和允许前缀限制。
- Projection 结构继续保持 strict allowlist 的扁平结构。

后续防御要求：

- 对 `schema_id`、`decision_id`、状态字段进一步建立字符集规则。
- 将 `manifest_metrics` 纳入 validator 阈值，超过阈值时拒绝写入或降级为外部 artifact 引用。

### 10.3 Metrics Storm

风险：

`evidence_metrics` 与 `manifest_metrics` 已经让单机 inspect 具备清晰观测能力。但当 OneCode sidecar 被分发到多台边缘节点后，如果所有节点高频推送原始指标或原始账本，控制面会出现集中式 I/O 挤压，重新制造 metadata 风暴。

本阶段已补防线：

- 新增 `global_wal_metrics_summary()`，按固定时间窗口输出 summary。
- Summary 只包含计数、字节数、风险层级和采集模式分布，不包含原始 WAL entries。

后续防御要求：

- 多节点指标默认在节点本地预聚合。
- 原始账本只在 `inspect --detail` 或定向审计时按 run/node 拉取。
- 指标上报应具备速率限制、批量窗口和背压策略。
- 控制面应区分 health telemetry、evidence metrics 和 forensic ledger，避免把取证数据当作普通遥测持续推送。

## 11. 工作区说明

本阶段只收敛证据链和 Manifest 边界相关改动。当前工作区仍存在其它已修改或未跟踪文件，不属于本问题范围，未在本阶段收尾中回滚或整理。

发布或提交前建议单独做一次 git 状态清理和提交拆分，避免把无关改动混入本阶段。

## 12. 收尾判断

本阶段可以收尾。
