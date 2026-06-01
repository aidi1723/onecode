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

The table below is the release slot for measured A/B results. Do not fill it
with estimates. Only publish numbers after running the same task set against the
same model, prompt, workspace, and verification rules.

下表是发布用 A/B 实测结果位置。不要用估算填充。只有在相同任务集、模型、提示词、工作区和验证规则下完成测试后，才发布数字。

| Metric / 指标 | Baseline agent / 基线 Agent | OneCode | Delta / 变化 |
| --- | ---: | ---: | ---: |
| Invalid-action rate / 无效动作率 | TBD | TBD | TBD |
| Unsafe-write prevention / 不安全写入阻断 | TBD | TBD | TBD |
| Verified task success / 可验证任务成功率 | TBD | TBD | TBD |
| Task quality score / 任务质量分 | TBD | TBD | TBD |
| Median task time / 中位任务耗时 | TBD | TBD | TBD |
| P95 task time / P95 任务耗时 | TBD | TBD | TBD |
| Average tokens per task / 单任务平均 token | TBD | TBD | TBD |
| Total tokens per benchmark run / 单轮基准总 token | TBD | TBD | TBD |
| Evidence bytes per completed task / 单个完成任务证据字节数 | TBD | TBD | TBD |
| Resume correctness / 恢复正确性 | TBD | TBD | TBD |

## Reporting Guidance / 对外表述规范

When A/B data is available, public copy may use language like:

有 A/B 数据后，公开文案可以使用类似表述：

```text
In local benchmark tasks, OneCode reduced invalid action propagation by X%,
improved verified task completion by Y%, and reduced repeated repair token usage
by Z%.
```

```text
在本地基准任务中，OneCode 将无效动作传播降低 X%，将可验证任务完成率提高 Y%，并将重复修复 token 使用降低 Z%。
```

Do not claim hallucination, success-rate, quality, time, or token improvements
without attaching the benchmark task set, environment, model, and scoring rules.

没有附带基准任务集、环境、模型和评分规则时，不要宣称幻觉率、成功率、质量、时间或 token 改善。

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

