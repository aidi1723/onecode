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

## Files / 文件

- `PUBLIC_README.md` - concise public project overview / 简明公开项目介绍
- `TERMINOLOGY.md` - public terminology mapping and terms to avoid in release copy / 公开术语映射和发布文案规约
- `RELEASE_NOTES.md` - current release summary written with engineering terms / 当前发布说明
- `BENCHMARK_RESULTS.md` - benchmark metric definitions and verified result slots / 基准测试指标定义和结果占位
- `OPEN_SOURCE_CHECKLIST.md` - final open-source readiness checklist / 最终开源准备检查清单
