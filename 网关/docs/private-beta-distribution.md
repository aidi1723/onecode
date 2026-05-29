# 私密仓库分发说明

本文档说明如何把一字诀 AgentOS 分发给指定朋友部署和测试。

## 分发前维护者要做的事

1. 确认没有真实 key：

```bash
bash deploy/private_repo_release_check.sh
```

2. 提交以下内容到私密仓库：

```text
agent_skill_dictionary/
bin/
deploy/
docs/
schemas/
scripts/
tests/
.env.example
requirements-gateway.txt
README.md
Makefile
Dockerfile.gateway
```

3. 不要提交：

```text
.env
.oneword/
.venv*
reports/ 中包含私密业务内容的原始日志
任何真实 API key
```

## 测试者最短流程

```bash
git clone <private-repo-url>
cd <repo>
cp .env.example .env
```

编辑 `.env` 后启动：

```bash
bash deploy/start_gateway_background.sh
bash deploy/smoke_http.sh
```

如果安装了 Claude Code：

```bash
bash deploy/run_claude_smoke.sh
```

如果安装了 Codex CLI：

```bash
bash deploy/run_codex_smoke.sh
```

如果使用 Codex 桌面版，配置：

```text
Base URL: http://127.0.0.1:8080/v1
API Key: ONEWORD_GATEWAY_TOKEN
Model: 上游模型名
```

停止：

```bash
bash deploy/stop_gateway.sh
```

## 推荐测试任务

第一轮只测只读：

```text
查：请只读评估当前项目，输出 500 字中文简报。必须包含项目目标、核心模块、安全风险、3 条改进建议。不要修改文件，不要安装依赖，不要联网。
```

第二轮长只读：

```text
查：请对当前项目做一次深入只读综合工程审计，输出 2000 字中文报告。覆盖架构、测试、安全、性能、生产风险、优先改进路线图。不要修改文件，不要安装依赖，不要联网。
```

写盘和对抗任务必须在临时副本里跑，不允许直接在真实项目目录执行。

## 朋友回传内容

让测试者回传：

```text
.oneword/gateway.log
.oneword/claude-smoke-output.json
.oneword/claude-smoke-stderr.txt
.oneword/codex-smoke-output.jsonl
.oneword/codex-smoke-stderr.txt
终端输出截图或文本
机器系统版本、Python 版本、Claude Code 版本、Codex 版本
```

不要回传 `.env`。
