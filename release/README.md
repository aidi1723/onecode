# OneCode Public Release Pack / OneCode 公开发布包

This directory contains public-facing release material for OneCode.

本目录存放 OneCode 的公开发布材料。

It is intentionally separate from the local development documentation. The
development tree may keep internal research names, historical terms, and
experimental notes. Public release files describe OneCode with neutral
engineering terminology so users can evaluate it as a deterministic local agent
kernel for trusted industrial AI workflows.

本目录与本地开发文档刻意分离。本地开发树可以保留内部研究命名、历史术语和实验记录；公开发布文件使用通用工程术语，让用户把 OneCode 理解为面向可信工业级 AI 工作流的确定性本地 Agent 内核。

Use this directory when preparing:

准备以下内容时使用本目录：

- GitHub release descriptions / GitHub Release 描述
- package registry descriptions / 包注册平台描述
- public project pages / 公开项目页
- external technical summaries / 外部技术摘要
- third-party integration briefs / 第三方集成说明

Do not treat this directory as the source of runtime behavior. The source of
truth for implementation remains `src/`, `tests/`, and the normal project
documentation.

不要把本目录当作运行行为的事实来源。实现事实仍以 `src/`、`tests/` 和常规项目文档为准。

## Workspace Boundary / 工作区边界

The local development workspace and the open-source synchronization workspace
are separate systems. Local development may happen in a dirty worktree with
experiments, generated assets, and private research files. GitHub publication
must be prepared from a clean worktree based on `origin/main`, such as
`<onecode-open-source-sync-worktree>`.

本机开发工作区和开源同步工作区是两套系统。本机开发可以发生在包含实验改动、生成资产和私有研究文件的脏工作区中；GitHub 发布必须从基于 `origin/main` 的干净 worktree 准备，例如 `<onecode-open-source-sync-worktree>`。

Before publishing, run `git status --short --branch` and the release audit in
the open-source synchronization worktree, not in the local development tree.

发布前应在开源同步 worktree 中运行 `git status --short --branch` 和 release audit，而不是在本机开发树中直接发布。

## Files / 文件

- `PUBLIC_README.md` - concise public project overview / 简明公开项目介绍
- `../DEPLOYMENT.md` - kernel and bundled Web shell deployment guide / 内核和内置 Web 壳部署说明
- `TERMINOLOGY.md` - public terminology mapping and terms to avoid in release copy / 公开术语映射和发布文案规约
- `RELEASE_NOTES.md` - current release summary written with engineering terms / 当前发布说明
- `UPDATE_2026_06_05.md` - GitHub release copy for the rule-evidence update / 规则证据更新的 GitHub Release 文案
- `BENCHMARK_RESULTS.md` - benchmark metric definitions and verified result slots / 基准测试指标定义和结果占位
- `CODEX_CLI_AB_SUMMARY.md` - supplemental Codex CLI vs OneCode A/B summary / Codex CLI 与 OneCode 补充 A/B 摘要
- `CODEX_CLI_AB_REPORT.json` - sanitized machine-readable supplemental A/B report / 已脱敏的补充 A/B 机器可读报告
- `CODEX_VS_ONECODE_LM_AB_SUMMARY.md` - supplemental Codex+LM vs OneCode+LM A/B summary / Codex+LM 与 OneCode+LM 补充 A/B 摘要
- `CODEX_VS_ONECODE_LM_AB_REPORT.json` - sanitized machine-readable model-backed A/B report / 已脱敏的模型版 A/B 机器可读报告
- `OPEN_SOURCE_CHECKLIST.md` - final open-source readiness checklist / 最终开源准备检查清单
