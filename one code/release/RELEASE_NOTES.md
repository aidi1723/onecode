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

## Operational Notes / 运行说明

- The default completed-run evidence path is designed to minimize disk pressure.
  默认完成路径证据模式用于降低磁盘压力。
- Denied and halted paths still preserve stronger evidence for auditability.
  拒绝和中止路径仍保留更强证据，便于审计。
- The local API is intended for loopback or trusted bridge use unless placed
  behind production-grade gateway controls.
  本地 API 面向 loopback 或可信桥接场景；如用于生产，应放在生产级网关控制之后。
- Optional TUI dependencies are not required for the core kernel gate.
  可选 TUI 依赖不是核心内核门禁的必要条件。

## Scope / 范围

This release pack intentionally uses engineering-neutral bilingual terminology.
Internal development files may contain historical research terms and
compatibility field names; those are not part of the public release narrative.

本发布包刻意使用工程中性的中英文双语术语。本地开发文件可能包含历史研究术语和兼容字段名；这些不属于公开发布叙事。

