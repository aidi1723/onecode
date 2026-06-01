# OneCode

OneCode is a trusted industrial AI kernel for enterprise-grade local agent
workflows. It reduces model error propagation by turning model outputs into
candidates that must pass deterministic state, safety, evidence, and recovery
checks before they can affect project files.

OneCode 是面向企业级本地 Agent 工作流的可信任工业级 AI 内核。它把大模型输出视为候选结果，必须经过确定性状态、安全、证据和恢复检查后，才能影响项目文件，从而降低模型错误扩散。

OneCode is not a general-purpose autonomous assistant. It is a controllable
execution kernel for guarded file changes, deterministic state transitions,
append-only run evidence, and resumable task execution.

OneCode 不是全能型自主助手，而是一个可控执行内核，聚焦受保护文件变更、确定性状态转移、追加式运行证据和可恢复任务执行。

The core kernel has no runtime third-party dependency. Optional shells and UI
layers can connect through the CLI or the local OpenAI-compatible HTTP API.

核心内核运行时不依赖第三方库。可选壳层和 UI 可以通过 CLI 或本地 OpenAI-compatible HTTP API 接入。

OneCode is licensed under the Apache License, Version 2.0.

OneCode 使用 Apache License 2.0 开源协议。

## Core Capabilities / 核心能力

- Guarded workspace writes through a path and intent gate.
  通过路径与意图门控保护工作区写入。
- Deterministic 6-bit state profile for every run outcome.
  为每次运行结果生成确定性的 6-bit 状态画像。
- Append-only WAL evidence with hash-chain validation.
  通过追加式 WAL 证据和哈希链校验提供可追溯记录。
- Stateful resume logic for completed, skipped, halted, and tampered runs.
  对完成、跳过、中止和篡改场景提供状态化恢复逻辑。
- Shell projection contract for CLI, Web API, and UI adapters.
  为 CLI、Web API 和 UI 适配器提供稳定的壳层投影契约。
- Local doctor and release verification scripts.
  提供本地 doctor 与发布验证脚本。
- Benchmark harness for rule, safety, sandbox, approval, and trace coverage.
  提供覆盖规则、安全、沙箱、审批和追踪的基准测试框架。
- Model-independent control layer for OpenAI-compatible, local, or third-party
  candidate generators.
  提供模型无关的控制层，可接入 OpenAI-compatible、本地或第三方候选生成器。
- Low-disk-pressure evidence mode for normal completed runs.
  为正常完成路径提供低磁盘压力证据模式。

## Why It Matters / 为什么重要

Large models can propose useful edits, but they can also hallucinate tools,
paths, schemas, permissions, and completion status. OneCode inserts a
deterministic control layer between the model and the workspace.

大模型可以提出有用修改，但也可能幻觉工具、路径、schema、权限和完成状态。OneCode 在模型和工作区之间加入确定性控制层。

The target benefits measured by the benchmark harness are:

基准测试框架重点衡量以下收益：

- lower invalid-action propagation / 降低无效动作传播
- higher verified task completion / 提高可验证任务完成率
- fewer unsafe writes / 减少不安全写入
- less repeated repair work / 减少重复修复
- lower token use from fewer failed retries / 通过减少失败重试降低 token 使用
- lower disk I/O from compact append-only evidence / 通过紧凑追加式证据降低磁盘 I/O
- better task quality through verifier and evidence checks / 通过验证器和证据检查提升任务质量

In a supplemental model-backed A/B run on the same 20 benchmark tasks, OneCode+LM
matched Codex+LM on asset completeness, exceeded Codex+LM on Pass@1 and evidence
completeness, and used substantially fewer workflow tokens and wall-clock time.
This is a bounded benchmark result, not a claim that OneCode is a full
general-purpose Codex replacement.

在相同 20 个 benchmark 任务的模型版补充 A/B 中，OneCode+LM 在资产完整性上看齐 Codex+LM，在 Pass@1 和证据完整性上超过 Codex+LM，并显著降低工作流 token 与墙钟耗时。这是有边界的基准测试结果，不是宣称 OneCode 可以完整替代通用 Codex。

## Install / 安装

```bash
pip install -e .
```

Optional conversational TUI:

可选对话式 TUI：

```bash
pip install -e .[tui]
```

## Verify / 验证

Fast core gate:

快速核心门禁：

```bash
bash scripts/verify-core.sh
```

Full local gate:

完整本地门禁：

```bash
bash scripts/verify.sh
```

## Run / 运行

Doctor smoke check:

Doctor 冒烟检查：

```bash
PYTHONPATH=src python3 -m onecode doctor
```

Run a guarded file write:

运行一次受保护文件写入：

```bash
PYTHONPATH=src python3 -m onecode run \
  --workspace . \
  --intent write_text \
  --path demo.txt \
  --content "hello OneCode"
```

Start the bundled shell and kernel:

启动内置壳和内核：

```bash
cd shell/onecode-librechat
npm install
cd ../..
PYTHONPATH=src python3 -m onecode shell
```

Open:

打开：

```text
http://127.0.0.1:14080/c/new
```

Default local preview login:

默认本地预览账号：

```text
Email: onecode@local.test
Password: OneCode123!
```

Start API-only mode:

只启动 API：

```bash
PYTHONPATH=src ONECODE_API_TOKEN=dev-local-token \
  python3 -m onecode serve --host 127.0.0.1 --port 8080
```

Discover the shell projection schema:

查看壳层投影 schema：

```bash
PYTHONPATH=src python3 -m onecode shell-schema
```

## Safety Model / 安全模型

OneCode treats model output as a candidate, not an authority. File changes must
pass through the kernel's intent, path, evidence, and transition checks before
they are written.

OneCode 把模型输出视为候选结果，而不是执行权威。文件变更必须先通过内核的意图、路径、证据和状态转移检查。

Normal completed runs can use WAL-only relaxed evidence for low disk pressure.
Denied or halted paths retain stronger forensic evidence.

正常完成路径可以使用 WAL-only relaxed 低磁盘压力证据模式；拒绝或中止路径保留更强的取证证据。

## Status / 状态

This release is suitable as a local development baseline, integration prototype,
and enterprise evaluation baseline for trusted industrial AI workflows.
Production deployment still requires an operator-owned gateway, authentication,
TLS, request-size limits, rate limiting, and environment-specific secret
management.

当前版本适合作为本地开发基线、集成原型和企业级可信工业 AI 工作流评估基线。生产部署仍需要由使用方掌控的网关、鉴权、TLS、请求大小限制、限流和环境级密钥管理。
