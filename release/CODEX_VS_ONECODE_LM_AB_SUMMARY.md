# Codex+LM vs OneCode+LM A/B Summary / Codex+LM 与 OneCode+LM A/B 摘要

This supplemental report compares two model-backed workflows over the same 20
local OneCode benchmark tasks.

本文档记录一轮补充 A/B：在相同 20 个 OneCode 本地 benchmark 任务上，对比两个都接入 LM 的工作流。

## Run Boundary / 运行边界

- Codex+LM arm: real `codex exec --json` calls through Codex CLI.
  Codex+LM 组：通过 Codex CLI 真实调用 `codex exec --json`。
- OneCode+LM arm: LM first converts each benchmark task into a compact OneCode
  instruction; OneCode then executes, halts, denies, records evidence, and
  scores through the deterministic kernel.
  OneCode+LM 组：LM 先把每个 benchmark 任务转成紧凑 OneCode 指令；随后由 OneCode 确定性内核执行、中止、拒绝、留痕和评分。
- Same task set: 20 benchmark definitions under `benchmarks/tasks`.
  同一任务集：`benchmarks/tasks` 下的 20 个 benchmark 定义。
- Token counts are model-token counts reported by each runner.
  token 数为各 runner 暴露的模型 token 统计。
- Wall-clock time includes toolchain overhead, not only raw model inference.
  墙钟耗时包含工具链开销，不只是纯模型推理耗时。

Raw JSON report:

原始 JSON 报告：

```text
release/CODEX_VS_ONECODE_LM_AB_REPORT.json
```

## Result Matrix / 结果矩阵

| Metric / 指标 | Codex+LM | OneCode+LM | Delta / 变化 |
| --- | ---: | ---: | ---: |
| Task count / 任务数 | 20 | 20 | - |
| Passed tasks / 通过任务 | 19 | 20 | OneCode+LM +1 |
| Pass@1 | 95% | 100% | OneCode+LM +5 pp |
| Invalid-state failures / 无效状态失败 | 0 | 0 | 0 |
| Asset completeness / 资产完整性 | 100% | 100% | 0 |
| Evidence completeness / 证据完整性 | 0% | 100% | OneCode+LM +100 pp |
| Total elapsed / 总耗时 | 701.365s | 70.398s | OneCode+LM -630.967s |
| Avg elapsed per task / 单任务平均耗时 | 35.068s | 3.520s | OneCode+LM lower |
| Total model tokens / 模型 token 总量 | 1,623,063 | 9,355 | OneCode+LM -1,613,708 |
| Avg model tokens per task / 单任务平均模型 token | 81,153.15 | 467.75 | OneCode+LM lower |

## Failure Notes / 失败项说明

Codex+LM failed one task:

Codex+LM 失败 1 个任务：

- `list-runs-after-execution`
- Failure: `missing wal evidence`
- 失败原因：缺少 WAL 证据。

OneCode+LM passed all 20 tasks.

OneCode+LM 通过全部 20 个任务。

## Interpretation / 解读

This run is a more direct model-backed comparison than the previous local-kernel
benchmark. Both arms used an LM. The main OneCode advantage came from shrinking
the model's responsibility to instruction interpretation, then letting the
deterministic kernel handle execution, refusal, evidence, and scoring.

这轮比之前的本地内核测试更接近“模型版”对比：两组都使用 LM。OneCode 的主要优势来自把模型职责压缩为“指令解释”，再由确定性内核负责执行、拒绝、留痕和评分。

The token reduction should be interpreted as workflow-token reduction for this
benchmark setup. It does not mean OneCode eliminates model usage; OneCode+LM
still consumed 9,355 model tokens in this run.

token 下降应理解为本 benchmark 设置下的工作流 token 下降，不代表 OneCode 不使用模型；本轮 OneCode+LM 仍消耗了 9,355 个模型 token。
