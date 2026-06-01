# OneCode Release Notes / OneCode 发布说明

## Current Release Summary / 当前发布摘要

This release stabilizes OneCode as a trusted industrial AI kernel for
enterprise-grade local agent workflows. It combines a deterministic state
machine, guarded file writes, resumable execution, and low-overhead append-only
evidence.

本版本将 OneCode 稳定为面向企业级本地 Agent 工作流的可信任工业级 AI 内核，组合了确定性状态机、受保护文件写入、可恢复执行和低开销追加式证据。

## Highlights / 亮点

- Apache License 2.0 project licensing.
  使用 Apache License 2.0 开源协议。
- WAL-only relaxed evidence mode for normal completed runs.
  正常完成路径支持 WAL-only relaxed 轻量证据模式。
- Hash-chain validation for WAL inspection and resume paths.
  WAL 检查和恢复路径支持哈希链校验。
- Shell projection schema for stable CLI/Web/UI rendering.
  提供稳定的 shell projection schema，便于 CLI、Web 和 UI 渲染。
- Bundled browser shell and kernel entrypoint at `onecode shell`.
  通过 `onecode shell` 提供内置浏览器壳与内核一体化入口。
- OpenAI-compatible local HTTP API for shell integration.
  提供 OpenAI-compatible 本地 HTTP API，便于壳层集成。
- Benchmark task set for safety, trace, approval, sandbox, and resume behavior.
  提供覆盖安全、追踪、审批、沙箱和恢复行为的基准任务集。
- Core verification script and release audit script.
  提供核心验证脚本和发布审计脚本。
- Public release pack with engineering-neutral bilingual terminology.
  提供工程中性、双语同步的公开发布包。

## Verification / 验证

Validated release gates:

已验证发布门禁：

```text
bash scripts/verify-core.sh
185 tests OK
doctor status: ok
```

```text
PYTHONPATH=src python3 -m unittest tests.test_web_api -v
48 tests OK
```

## Benchmark Summary / 基准测试摘要

The local A/B benchmark ran 20 executable safety and execution tasks without
external model calls. In this benchmark, OneCode improved verified task success
from 45% to 100%, reduced invalid-action propagation from 50% to 0%, improved
asset completeness from 90% to 100%, and improved evidence completeness from 0%
to 100%.

本地 A/B 基准测试运行了 20 个可执行安全与执行任务，未调用外部模型。在该基准中，OneCode 将可验证任务成功率从 45% 提升到 100%，将无效动作传播率从 50% 降至 0%，将资产完整性从 90% 提升到 100%，并将证据完整性从 0% 提升到 100%。

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

This benchmark measures deterministic execution-control behavior. Token savings
are not reported for this run because no model API was called.

该基准衡量确定性执行控制行为。本轮未调用模型 API，因此不报告 token 节省。

A supplemental model-backed A/B run also compared Codex+LM with OneCode+LM on
the same 20 benchmark tasks. OneCode+LM passed 20/20 tasks versus Codex+LM
19/20, matched Codex+LM at 100% asset completeness, improved evidence
completeness from 0% to 100%, and reduced measured workflow token usage from
1,623,063 to 9,355 tokens.

另有一轮模型版补充 A/B，在相同 20 个 benchmark 任务上对比 Codex+LM 与 OneCode+LM。OneCode+LM 通过 20/20 个任务，Codex+LM 通过 19/20 个任务；OneCode+LM 在资产完整性上同为 100%，将证据完整性从 0% 提升到 100%，并将测得的工作流 token 使用量从 1,623,063 降至 9,355。

This means OneCode can match or exceed Codex+LM on selected measured workflow
parameters in this bounded benchmark when the LM is used for instruction
interpretation and the deterministic kernel owns execution control.

这意味着在该有边界的 benchmark 中，当 LM 用于指令解释、由确定性内核掌控执行控制时，OneCode 可以在部分可测工作流参数上看齐或超过 Codex+LM。

## Operational Notes / 运行说明

- The default completed-run evidence path is designed to minimize disk pressure.
  默认完成路径证据模式用于降低磁盘压力。
- Denied and halted paths still preserve stronger evidence for auditability.
  拒绝和中止路径仍保留更强证据，便于审计。
- The local API is intended for loopback or trusted bridge use unless placed
  behind production-grade gateway controls.
  本地 API 面向 loopback 或可信桥接场景；如用于生产，应放在生产级网关控制之后。
- The bundled shell defaults to `http://127.0.0.1:14080/c/new`; API-only mode remains
  available through `onecode serve`.
  内置壳默认地址为 `http://127.0.0.1:14080/c/new`；如只需 API，仍可使用 `onecode serve`。
- Optional TUI dependencies are not required for the core kernel gate.
  可选 TUI 依赖不是核心内核门禁的必要条件。

## Scope / 范围

This release pack intentionally uses engineering-neutral bilingual terminology.
Internal development files may contain historical research terms and
compatibility field names; those are not part of the public release narrative.

本发布包刻意使用工程中性的中英文双语术语。本地开发文件可能包含历史研究术语和兼容字段名；这些不属于公开发布叙事。
