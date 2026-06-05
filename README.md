# OneCode

> English and 中文 are maintained together in this README.
>
> 本 README 同步维护英文与中文内容，GitHub 首页可直接阅读中文说明。

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

Textual is an optional TUI dependency.

Textual 是可选 TUI 依赖。

OneCode is licensed under the Apache License, Version 2.0.

OneCode 使用 Apache License 2.0 开源协议。

## Core Ownership / 核心知识产权

OneCode Core is independently designed and implemented by the OneCode
development team. The core state machine, execution-control rules, safety
guards, evidence model, hash-chain inspection, resume logic, benchmark harness,
and shell projection contract are self-developed project assets released under
Apache License 2.0.

OneCode Core 由 OneCode 开发团队独立设计和实现。核心状态机、执行控制规则、安全护栏、证据模型、哈希链检查、恢复逻辑、基准测试框架和壳层投影契约，均为项目自研资产，并以 Apache License 2.0 发布。

The bundled Web shell is a custom OneCode integration based on LibreChat and
keeps the upstream MIT license notices. Third-party runtime, build, and UI
dependencies remain governed by their own licenses.

内置 Web 壳是基于 LibreChat 的 OneCode 定制集成，并保留上游 MIT 许可声明。第三方运行时、构建和 UI 依赖仍遵循各自许可证。

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

The benchmark harness measures:

基准测试框架衡量：

- lower invalid-action propagation / 降低无效动作传播
- higher verified task completion / 提高可验证任务完成率
- fewer unsafe writes / 减少不安全写入
- less repeated repair work / 减少重复修复
- lower token use from fewer failed retries / 通过减少失败重试降低 token 使用
- lower disk I/O from compact append-only evidence / 通过紧凑追加式证据降低磁盘 I/O
- better task quality through verifier and evidence checks / 通过验证器和证据检查提升任务质量

Verified local deterministic benchmark data is published in
[`release/BENCHMARK_RESULTS.md`](release/BENCHMARK_RESULTS.md). That benchmark
does not call a live model or external API, so token metrics are intentionally
marked as not applicable for that run.

已验证的本地确定性基准测试数据发布在
[`release/BENCHMARK_RESULTS.md`](release/BENCHMARK_RESULTS.md)。该轮基准测试不调用真实模型或外部 API，因此 token 指标在该轮数据中明确标记为不适用。

A supplemental model-backed A/B run compares Codex+LM with OneCode+LM on the
same 20 benchmark tasks. In that bounded setup, OneCode+LM matched Codex+LM on
asset completeness, exceeded it on Pass@1 and evidence completeness, and used
substantially fewer workflow tokens and wall-clock time.

另有一轮模型版补充 A/B，在相同 20 个 benchmark 任务上对比 Codex+LM 与 OneCode+LM。在这个有边界的测试设置中，OneCode+LM 在资产完整性上看齐 Codex+LM，在 Pass@1 和证据完整性上超过 Codex+LM，并显著降低工作流 token 与墙钟耗时。

### Verified A/B Snapshot / 已验证 A/B 快照

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

Boundary: this is a local deterministic execution-control benchmark. It
measures invalid-action propagation as an engineering proxy, not a live model's
raw hallucination rate.

边界说明：这是一轮本地确定性执行控制基准测试。无效动作传播率是工程代理指标，不是在线模型原始幻觉率。

### Model-Backed A/B Snapshot / 模型版 A/B 快照

| Metric / 指标 | Codex+LM | OneCode+LM | Delta / 变化 |
| --- | ---: | ---: | ---: |
| Task count / 任务数 | 20 | 20 | - |
| Passed tasks / 通过任务 | 19 | 20 | OneCode+LM +1 |
| Pass@1 | 95% | 100% | OneCode+LM +5 pp |
| Asset completeness / 资产完整性 | 100% | 100% | matched / 看齐 |
| Evidence completeness / 证据完整性 | 0% | 100% | OneCode+LM +100 pp |
| Total elapsed / 总耗时 | 701.365s | 70.398s | OneCode+LM lower |
| Total model tokens / 模型 token 总量 | 1,623,063 | 9,355 | OneCode+LM lower |

Boundary: this is not a claim that OneCode is a full Codex replacement. It shows
that when the LM is used mainly for instruction interpretation and the OneCode
kernel owns execution control, OneCode can match or exceed Codex+LM on several
measured parameters in this benchmark.

边界说明：这不是宣称 OneCode 可以完整替代 Codex。它说明当 LM 主要负责指令解释、由 OneCode 内核掌控执行控制时，OneCode 在这组 benchmark 的若干可测参数上可以看齐或超过 Codex+LM。

## Application Scenarios / 应用场景

OneCode is best suited to domains where AI output must be controllable,
auditable, and replayable before it changes files or triggers downstream
workflow steps.

OneCode 更适合那些要求 AI 输出在修改文件或触发下游流程前必须可控、可审计、可复放的领域。

- Finance operations: controlled report generation, reconciliation scripts,
  month-end close automation, policy-bound spreadsheet or ledger changes.
  财务运营：受控报表生成、对账脚本、月结自动化、受策略约束的表格或账本变更。
- Audit and assurance: evidence-preserving task execution, tamper detection,
  repeatable workpaper generation, traceable remediation workflows.
  审计与鉴证：保留证据的任务执行、篡改识别、可复放底稿生成、可追踪整改流程。
- Security engineering: guarded code changes, sandbox and approval workflows,
  unsafe write blocking, incident-response runbook execution with evidence.
  安全工程：受保护代码变更、沙箱与审批流程、不安全写入阻断、带证据链的应急响应 runbook 执行。
- Financial technology and regulated workflows: deterministic control around
  model-generated candidates, local API integration, resumable execution, and
  compact append-only evidence.
  金融科技与受监管流程：围绕模型候选输出提供确定性控制、本地 API 集成、可恢复执行和紧凑追加式证据。
- Enterprise internal tooling: local agent kernels for controlled file
  mutation, verifier-driven automation, and operator-owned deployment.
  企业内部工具：用于受控文件变更、验证器驱动自动化和使用方自主管理部署的本地 Agent 内核。

OneCode does not by itself provide legal, audit, financial, or regulatory
certification. In regulated environments it should be deployed behind
operator-owned identity, approval, logging, retention, and review controls.

OneCode 本身不提供法律、审计、金融或监管认证。在受监管环境中，应部署在使用方掌控的身份、审批、日志、留存和复核控制之后。

## Install / 安装

One-command local bootstrap:

一条命令本地安装并启动：

```bash
bash scripts/bootstrap-local.sh
```

Equivalent Make shortcut:

等价 Make 快捷命令：

```bash
make bootstrap
```

Check local service status:

检查本地服务状态：

```bash
bash scripts/status-local.sh
# or / 或
make status
```

Step-by-step preflight check:

分步部署前检查：

```bash
bash scripts/doctor-local.sh --skip-shell-deps
```

Recommended local install:

推荐本地安装方式：

```bash
bash scripts/install-local.sh
```

Then start the bundled kernel and shell:

然后启动内置内核和壳：

```bash
bash scripts/start-local.sh
```

The start script checks default ports before launching and prints the browser
URL. If a port is occupied, stop the existing process or pass custom ports.

启动脚本会在启动前检查默认端口并输出浏览器地址。如果端口被占用，停止已有进程，或传入自定义端口。

Manual kernel-only install:

手动只安装内核：

```bash
pip install -e .
```

Manual shell dependency install:

手动安装壳依赖：

```bash
cd shell/onecode-librechat
npm install
cd ../..
```

Optional conversational TUI:

可选对话式 TUI：

```bash
pip install -e .[tui]
```

Deployment guide:

部署说明：

```text
DEPLOYMENT.md
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

For complete kernel and bundled Web shell deployment steps, see
[`DEPLOYMENT.md`](DEPLOYMENT.md).

完整的内核和内置 Web 壳部署步骤见 [`DEPLOYMENT.md`](DEPLOYMENT.md)。

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
bash scripts/start-local.sh
```

Open:

打开：

```text
http://127.0.0.1:14080/c/new
```

The launcher is a foreground process. Keep that terminal open while using the
shell. If the browser reports `ERR_CONNECTION_REFUSED`, check the local service
state with:

壳启动器是前台进程。使用壳时需要保持该终端窗口运行。如果浏览器提示
`ERR_CONNECTION_REFUSED`，先检查本地服务状态：

```bash
bash scripts/status-local.sh
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
  python3 -m onecode serve --host 127.0.0.1 --port 19080
```

Discover the shell projection schema:

查看壳层投影 schema：

```bash
PYTHONPATH=src python3 -m onecode shell-schema
```

## Command Reference / 命令速查

The short module entrypoint is `python3 -m onecode`. The older explicit CLI
module form, such as `python3 -m onecode.cli doctor`, remains supported.

简写模块入口是 `python3 -m onecode`。旧的显式 CLI 模块形式仍然支持，例如 `python3 -m onecode.cli doctor`。

Run the local verifier demo:

运行本地验证器演示：

```bash
bash scripts/demo_v07.sh
```

Run the project self audit:

运行项目自审计：

```bash
onecode audit-self
```

Start the optional TUI:

启动可选 TUI：

```bash
onecode tui
```

Start a separate development copy of the LibreChat shell instead of the bundled copy:

使用独立开发版 LibreChat 壳，而不是发布包内置壳：

```bash
PYTHONPATH=src python3 -m onecode shell \
  --shell-mode librechat \
  --librechat-dir ../onecode-librechat
```

The TUI writes plain-text exports under the active workspace:

TUI 会在当前工作区写入纯文本导出：

```text
.onecode/tui-transcript.txt
.onecode/tui-last-output.txt
```

Use `/export-last` in the TUI to print the latest output path.

可在 TUI 中使用 `/export-last` 打印最近输出路径。

Run a structured task plan:

运行结构化任务计划：

```bash
PYTHONPATH=src python3 -m onecode run-plan \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan \
  --plan /tmp/onecode-demo/task-plan.json
```

Write multiple assets or resume from prior evidence:

写入多个资产，或从历史证据恢复：

```bash
PYTHONPATH=src python3 -m onecode run "write assets" \
  --workspace /tmp/onecode-demo \
  --run-id demo-multi \
  --write-text "src/a.py=a = 1\n" \
  --write-text "tests/test_a.py=def test_a():\n    assert True\n" \
  --max-write-bytes 5000000 \
  --max-trace-bytes 1000000 \
  --max-run-seconds 30

PYTHONPATH=src python3 -m onecode run "resume asset" \
  --workspace /tmp/onecode-demo \
  --run-id demo-resume \
  --resume-from demo-multi \
  --write-path src/a.py \
  --write-content "a = 1\n"
```

Generate and use a verifier policy:

生成并使用验证器策略：

```bash
PYTHONPATH=src python3 -m onecode list-verifier-presets

PYTHONPATH=src python3 -m onecode init-verifier-policy \
  --workspace /tmp/onecode-demo \
  --preset python-unittest

PYTHONPATH=src python3 -m onecode run-plan \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan-verified \
  --plan /tmp/onecode-demo/task-plan.json \
  --verifier python-unittest \
  --verifier-policy /tmp/onecode-demo/.onecode/verifier-policy.json
```

After initialization, `run-plan --verifier` reads the workspace default policy
at `.onecode/verifier-policy.json`.

初始化后，`run-plan --verifier` 会读取工作区默认策略 `.onecode/verifier-policy.json`。

Inspect evidence:

检查证据：

```bash
PYTHONPATH=src python3 -m onecode inspect \
  --workspace /tmp/onecode-demo \
  --run-id demo-plan-verified

PYTHONPATH=src python3 -m onecode list-runs \
  --workspace /tmp/onecode-demo
```

Run the math-rule audit:

运行数学规则审计：

```bash
PYTHONPATH=src python3 -m onecode math-audit
```

The audit reports the transition graph and related deterministic state checks.

该审计会报告 transition graph 以及相关确定性状态检查。

Evidence files include `evidence-chain.jsonl`, terminal `run_completed` trace
events, and guarded halt reasons such as `resource_budget_exceeded`.

证据文件包含 `evidence-chain.jsonl`、终止态 `run_completed` 追踪事件，以及 `resource_budget_exceeded` 等受控中止原因。

The Docker sandbox adapter uses defensive flags such as `--cap-drop ALL`.

Docker 沙箱适配器使用 `--cap-drop ALL` 等防御性参数。

## Safety Model / 安全模型

OneCode treats model output as a candidate, not an authority. File changes must
pass through the kernel's intent, path, evidence, and transition checks before
they are written.

OneCode 把模型输出视为候选结果，而不是执行权威。文件变更必须先通过内核的意图、路径、证据和状态转移检查。

Normal completed runs can use WAL-only relaxed evidence for low disk pressure.
Denied or halted paths retain stronger forensic evidence.

正常完成路径可以使用 WAL-only relaxed 低磁盘压力证据模式；拒绝或中止路径保留更强的取证证据。

External tool rules, project instruction files, optional runtime configuration,
and recovery hints are also treated as evidence, not authority. Public status
surfaces expose bounded metadata, status summaries, and shell projections by
default; they do not expose raw project rule content.

外部工具规则、项目指令文件、可选运行配置和恢复提示同样被视为证据，而不是执行权威。公开状态面默认只暴露受限元数据、状态摘要和壳层投影，不暴露原始项目规则内容。

## Public Release Documents / 公开发布文档

- [`release/PUBLIC_README.md`](release/PUBLIC_README.md) - public project overview / 公开项目介绍
- [`release/BENCHMARK_RESULTS.md`](release/BENCHMARK_RESULTS.md) - benchmark results / 基准测试结果
- [`release/RELEASE_NOTES.md`](release/RELEASE_NOTES.md) - release notes / 发布说明
- [`release/TERMINOLOGY.md`](release/TERMINOLOGY.md) - public terminology / 公开术语
- [`release/OPEN_SOURCE_CHECKLIST.md`](release/OPEN_SOURCE_CHECKLIST.md) - open-source readiness checklist / 开源准备检查清单

## Status / 状态

This release is suitable as a local development baseline, integration prototype,
and enterprise evaluation baseline for trusted industrial AI workflows.
Production deployment still requires an operator-owned gateway, authentication,
TLS, request-size limits, rate limiting, and environment-specific secret
management.

当前版本适合作为本地开发基线、集成原型和企业级可信工业 AI 工作流评估基线。生产部署仍需要由使用方掌控的网关、鉴权、TLS、请求大小限制、限流和环境级密钥管理。
