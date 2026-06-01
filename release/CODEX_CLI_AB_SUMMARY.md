# Codex CLI vs OneCode A/B Summary / Codex CLI 与 OneCode A/B 摘要

This report records a real local A/B run between Codex CLI and the OneCode
local deterministic kernel.

本文档记录一次真实本地 A/B：Codex CLI 对比 OneCode 本地确定性内核。

## Run Boundary / 运行边界

- Codex CLI arm: real `codex exec --json` calls.
  Codex CLI 组：真实调用 `codex exec --json`。
- OneCode arm: local deterministic kernel runner over the same benchmark task
  definitions.
  OneCode 组：使用相同 benchmark 任务定义，运行本地确定性内核。
- OneCode did not call a model provider in this run.
  本轮 OneCode 未调用模型提供商。
- Therefore OneCode model-token usage is `0` for this benchmark.
  因此本轮 OneCode 的模型 token 消耗为 `0`。

Raw JSON report:

原始 JSON 报告：

```text
release/CODEX_CLI_AB_REPORT.json
```

## Result Matrix / 结果矩阵

| Metric / 指标 | Codex CLI | OneCode | Delta / 变化 |
| --- | ---: | ---: | ---: |
| Task count / 任务数 | 20 | 20 | - |
| Passed tasks / 通过任务 | 19 | 20 | OneCode +1 |
| Pass@1 | 95% | 100% | OneCode +5 pp |
| Invalid-state failures / 无效状态失败 | 0 | 0 | 0 |
| Asset completeness / 资产完整性 | 100% | 100% | 0 |
| Evidence completeness / 证据完整性 | 0% | 100% | OneCode +100 pp |
| Total elapsed / 总耗时 | 718.858s | 0.0566s | OneCode -718.801s |
| Avg elapsed per task / 单任务平均耗时 | 35.943s | 0.00283s | OneCode lower |
| Total model tokens / 模型 token 总量 | 1,513,270 | 0 | OneCode -1,513,270 |
| Avg model tokens per task / 单任务平均模型 token | 75,663.5 | 0 | OneCode -75,663.5 |

## Codex CLI Failed Task / Codex CLI 失败任务

- `list-runs-after-execution`
- Failure: `missing wal evidence`
- 失败原因：缺少 WAL 证据。

## Interpretation / 解读

Codex CLI showed strong task execution ability in this benchmark, passing 19 of
20 tasks and producing all requested file assets.

Codex CLI 在本轮测试中表现出很强的任务执行能力，20 个任务通过 19 个，并生成了全部请求的文件资产。

OneCode's advantage in this run came from deterministic local control,
evidence, resume, and audit behavior rather than from model reasoning.

OneCode 本轮优势来自确定性本地控制、证据、恢复和审计机制，而不是模型推理能力。

Token comparison in this run means model-token usage, not all internal CPU work.
Because OneCode did not call a model provider, its model-token usage is zero.

本轮 token 对比指的是模型 token 消耗，不代表所有 CPU 内部计算。由于 OneCode 本轮未调用模型提供商，因此模型 token 消耗为零。
