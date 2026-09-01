# OneCode Benchmark Results / OneCode 基准测试结果

OneCode is not a general-purpose autonomous assistant. It is a deterministic
execution kernel for reducing model error propagation in local coding workflows.

OneCode 不是全能型自主助手，而是一个确定性执行内核，用于降低本地代码工作流中的模型错误扩散。

This document records the public benchmark metrics used to evaluate safety,
task success, task quality, runtime overhead, and token efficiency.

本文档记录公开基准测试指标，用于评估安全性、任务成功率、任务质量、运行时开销和 token 效率。

## Verified Gates / 已验证门禁

The current release has the following verified local gates:

当前版本已经通过以下本地门禁：

| Gate / 门禁 | Result / 结果 |
| --- | --- |
| Core verification / 核心验证 | 185 tests OK |
| Doctor smoke check / Doctor 冒烟检查 | status: ok |
| Web API focused suite / Web API 聚焦测试 | 48 tests OK |
| Benchmark task definitions / 基准任务定义 | 20 executable local tasks |
| Local A/B benchmark / 本地 A/B 基准测试 | 20 tasks completed |
| Release audit / 发布审计 | no tracked changes, no untracked release candidates |
| License / 协议 | Apache License 2.0 |

## Metric Definitions / 指标定义

| Metric / 指标 | Meaning / 含义 | Measurement / 测量方式 |
| --- | --- | --- |
| Invalid-action rate / 无效动作率 | Model output references invalid tools, invalid schemas, unsafe paths, or unsupported execution modes. / 模型输出引用无效工具、无效 schema、不安全路径或不支持的执行模式。 | Count invalid candidate actions over total task attempts. / 无效候选动作数除以总任务尝试数。 |
| Unsafe-write prevention / 不安全写入阻断 | Candidate writes that are blocked before mutating protected or out-of-scope files. / 在修改受保护或越界文件前被阻断的候选写入。 | Count blocked unsafe writes over unsafe write attempts. / 被阻断的不安全写入数除以不安全写入尝试数。 |
| Verified task success / 可验证任务成功率 | Tasks that complete and satisfy expected file, verifier, or evidence assertions. / 完成且满足文件、验证器或证据断言的任务。 | Count verified completions over total tasks. / 可验证完成数除以总任务数。 |
| Task quality score / 任务质量分 | Weighted score for correct file content, no extra writes, verifier success, evidence completeness, and resume correctness. / 文件内容正确、无额外写入、验证成功、证据完整和恢复正确性的加权分。 | Benchmark scorer output. / 基准测试评分器输出。 |
| Repair-loop reduction / 修复循环减少 | Reduction in repeated correction attempts needed to reach a verified result. / 达到可验证结果所需重复修复次数的下降。 | Baseline retry count compared with OneCode retry count. / 对比 Baseline 与 OneCode 的重试次数。 |
| Time saved / 时间节省 | Wall-clock reduction from fewer failed retries and deterministic resume skips. / 通过减少失败重试和确定性恢复跳过带来的墙钟时间下降。 | Median and P95 task duration comparison. / 对比中位数和 P95 任务耗时。 |
| Token saved / token 节省 | Token reduction from fewer repair prompts, repeated context, and failed follow-up attempts. / 通过减少修复提示、重复上下文和失败追问带来的 token 下降。 | Total prompt plus completion tokens per benchmark run. / 每轮基准测试的 prompt + completion token 总量。 |
| Evidence overhead / 证据开销 | Disk bytes written for run evidence. / 运行证据写入的磁盘字节数。 | Full evidence versus WAL-only relaxed evidence size. / 对比 full evidence 与 WAL-only relaxed 证据大小。 |
| Resume correctness / 恢复正确性 | Correct skip, apply, halt, or tamper response when re-running a task. / 重新运行任务时正确跳过、应用、中止或识别篡改。 | Resume benchmark assertions. / 恢复基准测试断言。 |

## A/B Result Matrix / A/B 结果矩阵

The table below records the local deterministic A/B benchmark run. It compares a
minimal baseline runner with OneCode's guarded execution kernel over the same 20
local tasks. This run did not call an external model API, so token metrics are
marked not applicable.

下表记录本地确定性 A/B 基准测试结果。它在相同 20 个本地任务上，对比最小 baseline runner 与 OneCode 受控执行内核。本轮未调用外部模型 API，因此 token 指标标记为不适用。

| Metric / 指标 | Baseline agent / 基线 Agent | OneCode | Delta / 变化 |
| --- | ---: | ---: | ---: |
| Task count / 任务数 | 20 | 20 | - |
| Passed tasks / 通过任务 | 9 | 20 | +11 |
| Verified task success / 可验证任务成功率 | 45% | 100% | +55 pp |
| Invalid-action propagation proxy / 无效动作传播代理率 | 50% | 0% | -50 pp |
| Asset completeness / 资产完整性 | 90% | 100% | +10 pp |
| Evidence completeness / 证据完整性 | 0% | 100% | +100 pp |
| A/B run wall-clock / A/B 本地总耗时 | 0.066s total | 0.066s total | local combined run |
| Average tokens per task / 单任务平均 token | N/A | N/A | no model call |
| Total tokens per benchmark run / 单轮基准总 token | N/A | N/A | no model call |
| Evidence bytes in workspace / 工作区证据字节数 | 0 B | 1,287,464 B | audit evidence generated |
| Resume correctness / 恢复正确性 | failed tamper-halt case | passed tested resume cases | improved |

## Failed Baseline Tasks / Baseline 失败任务

Baseline failed 11 of the 20 tasks:

Baseline 在 20 个任务中失败 11 个：

- `approval-recorded`
- `http-timeout-halt`
- `invalid-intent-denied`
- `list-runs-after-execution`
- `refuse-absolute-path`
- `refuse-git-directory-write`
- `refuse-github-workflow-write`
- `refuse-workspace-escape`
- `resume-modified-asset-halt`
- `sandbox-command-constructed`
- `trace-event-recorded`

The failures were concentrated in denied/halted status handling, evidence
generation, approval records, trace records, sandbox command construction, and
tamper-aware resume behavior.

失败集中在拒绝/中止状态处理、证据生成、审批记录、追踪记录、沙箱命令构造和篡改感知恢复行为上。

## OneCode Result / OneCode 结果

OneCode passed all 20 benchmark tasks:

OneCode 通过全部 20 个基准任务：

```text
pass_at_1: 1.0
hallucination_failures: 0
hallucination_rate: 0.0
asset_completeness: 1.0
evidence_completeness: 1.0
```

## Result Boundaries / 结果边界

This run measures local deterministic execution-control behavior. The
invalid-action propagation metric is an engineering proxy for hallucination
propagation, not a direct measurement of a live model's raw hallucination rate.

本轮衡量本地确定性执行控制行为。无效动作传播指标是幻觉传播的工程代理指标，不是对在线模型原始幻觉率的直接测量。

Token savings are not reported because no external or local model API was used
in this benchmark run. A model-backed A/B run must use the same model, prompts,
workspace fixtures, and scoring rules before publishing token-savings claims.

由于本轮未使用外部或本地模型 API，因此不报告 token 节省。发布 token 节省结论前，必须使用相同模型、提示词、工作区 fixture 和评分规则运行模型版 A/B 测试。

## Reporting Guidance / 对外表述规范

For this local deterministic benchmark, public copy may use language like:

针对本地确定性基准测试，公开文案可以使用类似表述：

```text
In 20 local safety and execution benchmark tasks, OneCode improved verified task
success from 45% to 100%, reduced invalid-action propagation from 50% to 0%,
and improved evidence completeness from 0% to 100%.
```

```text
在 20 个本地安全与执行基准任务中，OneCode 将可验证任务成功率从 45% 提升到 100%，将无效动作传播率从 50% 降至 0%，并将证据完整性从 0% 提升到 100%。
```

Do not claim live-model hallucination, time, or token improvements without
attaching the benchmark task set, environment, model, and scoring rules.

没有附带基准任务集、环境、模型和评分规则时，不要宣称在线模型幻觉率、时间或 token 改善。

## Current Positioning / 当前定位

OneCode should be described as:

OneCode 应描述为：

```text
a trusted industrial AI kernel for enterprise-grade local agent workflows
```

```text
面向企业级本地 Agent 工作流的可信任工业级 AI 内核
```

It should not be described as:

不应描述为：

```text
a fully autonomous general-purpose assistant
```

```text
全能型自主助手
```
