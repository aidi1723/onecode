# OneCode Release Notes / OneCode 发布说明

## Current Release Summary / 当前发布摘要

This release stabilizes OneCode as a trusted industrial AI kernel for
enterprise-grade local agent workflows. It combines a deterministic state
machine, guarded file writes, resumable execution, and low-overhead append-only
evidence.

本版本将 OneCode 稳定为面向企业级本地 Agent 工作流的可信任工业级 AI 内核，组合了确定性状态机、受保护文件写入、可恢复执行和低开销追加式证据。

This update also adds a rule-evidence absorption layer for project instruction
discovery, runtime configuration inspection, and advisory recovery status. These
inputs are exposed as bounded metadata and deterministic control summaries, not
as independent authority over the workspace.

本次更新还加入了规则证据吸收层，用于项目指令发现、运行配置检查和建议式恢复状态。这些输入以受限元数据和确定性控制摘要形式暴露，而不是成为工作区的独立执行权威。

## Ubuntu And Docker Verification - 2026-06-09 / Ubuntu 与 Docker 验证

This update validates the OneCode core path on Ubuntu 24.04 LTS with Python
3.12 and Docker available. The verified gates include `verify-core`, `doctor`,
Docker sandbox smoke, the sandbox/privacy focused tests, and the public privacy
scan.

本次更新在 Ubuntu 24.04 LTS、Python 3.12 和 Docker 可用环境下验证了 OneCode 核心路径。已验证门禁包括 `verify-core`、`doctor`、Docker sandbox smoke、沙箱/隐私聚焦测试和公开隐私扫描。

The Docker sandbox now runs containers as the host UID/GID by default on
Unix-like systems. This fixes Linux bind-mount write failures without relaxing
network, filesystem, capability, resource, evidence, or transition controls.

Docker 沙箱现在在类 Unix 系统上默认使用宿主 UID/GID 运行容器。该修复解决 Linux bind mount 写入失败问题，同时不放宽网络、文件系统、capability、资源、证据或状态转移控制。

The privacy scan also ignores Git worktree pointer metadata while continuing to
scan public source and release files for local path and private-environment
markers.

隐私扫描现在会忽略 Git worktree 指针元数据，同时继续扫描公开源码和发布文件中的本地路径及私有环境标记。

## Documentation Update - 2026-06-03 / 文档更新

This update adds the evidence-chain, Manifest-boundary, shell-control-plane,
and final closure documentation under `docs/`. It records the architectural
decisions for balancing verifiable outcomes with local I/O pressure, keeping
Manifest files out of business workflow configuration, exposing summary-only
metrics to the shell, and treating aggregate trace gaps as repair-required
inspection signals.

本次更新在 `docs/` 下新增证据链、Manifest 边界、壳系统控制面和最终收尾文档。文档记录了以下架构决策：在可验证交付与本地 I/O 压力之间做分级权衡，避免 Manifest 退化为业务流程配置，向壳系统只暴露 summary-only 指标，并把聚合 trace 时间线缺口作为需要 repair 的 inspect 信号。

Added documents:

新增文档：

- `docs/ONECODE_EVIDENCE_CHAIN_MANIFEST_BOUNDARY_CLOSURE_REPORT.md`
- `docs/ONECODE_SECOND_ORDER_ARCHITECTURE_GUARDS_CLOSURE_REPORT.md`
- `docs/ONECODE_SHELL_CONTROL_PLANE_CLOSURE_REPORT.md`
- `docs/ONECODE_EVIDENCE_MANIFEST_SHELL_FINAL_CLOSURE.md`
- `docs/superpowers/specs/2026-06-02-onecode-evidence-chain-performance-balance-design.md`
- `docs/superpowers/plans/2026-06-02-onecode-evidence-chain-manifest-boundaries.md`

`DEPLOYMENT.md` now also records that online updates must be prepared from a
separated clean publish worktree, not from the local development workspace.

`DEPLOYMENT.md` 同步记录：后续线上更新必须从独立干净发布 worktree 准备，不应直接从本地开发工作区发布。

## Core Ownership / 核心知识产权

OneCode Core is independently designed and implemented by the OneCode
development team. The state machine, execution-control rules, safety guards,
evidence model, hash-chain inspection, resume logic, benchmark harness, and
shell projection contract are self-developed project assets released under
Apache License 2.0.

OneCode Core 由 OneCode 开发团队独立设计和实现。状态机、执行控制规则、安全护栏、证据模型、哈希链检查、恢复逻辑、基准测试框架和壳层投影契约，均为项目自研资产，并以 Apache License 2.0 发布。

The bundled Web shell is a custom OneCode integration based on LibreChat and
retains upstream MIT license notices. Third-party dependencies remain governed
by their own licenses.

内置 Web 壳是基于 LibreChat 的 OneCode 定制集成，并保留上游 MIT 许可声明。第三方依赖仍遵循各自许可证。

## Highlights / 亮点

- Apache License 2.0 project licensing.
  使用 Apache License 2.0 开源协议。
- WAL-only relaxed evidence mode for normal completed runs.
  正常完成路径支持 WAL-only relaxed 轻量证据模式。
- Hash-chain validation for WAL inspection and resume paths.
  WAL 检查和恢复路径支持哈希链校验。
- Shell projection schema for stable CLI/Web/UI rendering.
  提供稳定的 shell projection schema，便于 CLI、Web 和 UI 渲染。
- Control-state projection for project context, runtime config, and recovery
  advice.
  为项目上下文、运行配置和恢复建议提供控制状态投影。
- Doctor and Web project status now surface bounded rule-evidence summaries
  without raw rule content by default.
  Doctor 和 Web 项目状态现在默认暴露受限规则证据摘要，而不暴露原始规则内容。
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

## Application Scenarios / 应用场景

OneCode is appropriate for local agent workflows that require deterministic
control, evidence preservation, and repeatable recovery before model-generated
candidates can change project files or trigger downstream actions.

OneCode 适合那些在模型候选结果修改项目文件或触发下游动作前，需要确定性控制、证据留存和可复放恢复的本地 Agent 工作流。

Representative evaluation targets include finance operations, audit and
assurance workpapers, security engineering automation, financial technology
tooling, regulated internal workflows, and enterprise development operations.

代表性评估场景包括财务运营、审计与鉴证底稿、安全工程自动化、金融科技工具、受监管内部流程和企业研发运维。

OneCode does not by itself provide legal, audit, financial, or regulatory
certification. Regulated deployments should add operator-owned identity,
approval, logging, retention, review, backup, and gateway controls.

OneCode 本身不提供法律、审计、金融或监管认证。受监管部署应增加使用方掌控的身份、审批、日志、留存、复核、备份和网关控制。

## Verification / 验证

Validated release gates:

已验证发布门禁：

```text
bash scripts/verify-core.sh
188 tests OK
doctor status: ok
```

```text
PYTHONPATH=src python3 -m unittest tests.test_sandbox tests.test_source_hygiene -v
11 tests OK
```

```text
PYTHONPATH=src python3 -m onecode sandbox-smoke
sandbox status: completed
exit_code: 0
```

```text
bash scripts/privacy-scan.sh
no findings
```

```text
PYTHONPATH=src python3 -m unittest tests.test_project_context tests.test_runtime_config tests.test_recovery_policy tests.test_doctor_cli tests.test_web_api tests.test_shell_projection -v
76 tests OK
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
- Rule-evidence summaries are metadata-first. Raw project instruction content
  remains internal unless an operator explicitly routes it into a trusted model
  prompt path.
  规则证据摘要以元数据优先。原始项目指令内容保持在内部，除非操作者明确将其送入可信模型提示路径。
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
