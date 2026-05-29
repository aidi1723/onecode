# 一字诀 AgentOS 私测快速开始

这份说明给私密仓库测试者使用。真实 API key 只写入本机 `.env`，不要提交。

## 1. 初始化

```bash
git clone <private-repo-url>
cd <repo>
cp .env.example .env
```

编辑 `.env`，至少填写：

```text
ONEWORD_GATEWAY_TOKEN=本机自定义网关 token
ONEWORD_WORKSPACE_ROOT=/要测试的项目绝对路径
ONEWORD_ANTHROPIC_BASE_URL=https://你的上游/v1
ONEWORD_ANTHROPIC_API_KEY=<upstream-api-key>
ONEWORD_ANTHROPIC_MODEL=模型名
ONEWORD_UPSTREAM_BASE_URL=https://你的 OpenAI-compatible 上游/v1
ONEWORD_UPSTREAM_API_KEY=<upstream-api-key>
ONEWORD_CODEX_MODEL=模型名
```

## 2. 启动网关

```bash
bash deploy/start_gateway_background.sh
```

检查网关：

```bash
bash deploy/smoke_http.sh
```

## 3. Claude Code 测试

确保本机已安装 Claude Code：

```bash
claude --version
```

运行短只读测试：

```bash
bash deploy/run_claude_smoke.sh
```

结果文件：

```text
.oneword/claude-smoke-output.json
.oneword/claude-smoke-stderr.txt
.oneword/gateway.log
```

## 4. Codex Desktop / Codex CLI 测试

Codex 桌面版如果支持 OpenAI-compatible Base URL，填写：

```text
Base URL: http://127.0.0.1:8080/v1
API Key: .env 里的 ONEWORD_GATEWAY_TOKEN
Model: .env 里的 ONEWORD_CODEX_MODEL
```

测试 prompt：

```text
查：请只读评估当前项目，输出 500 字中文简报。必须包含项目目标、核心模块、安全风险、3 条改进建议。不要修改文件，不要安装依赖，不要联网。
```

如果安装了 Codex CLI，也可以跑：

```bash
bash deploy/run_codex_smoke.sh
```

输出文件：

```text
.oneword/codex-smoke-output.jsonl
.oneword/codex-smoke-stderr.txt
```

## 5. 停止网关

```bash
bash deploy/stop_gateway.sh
```

## 6. 发布前检查

维护者在 push 前运行：

```bash
bash deploy/private_repo_release_check.sh
```

完整说明见：

```text
deploy/README_PRIVATE_BETA.md
docs/private-beta-distribution.md
docs/gateway-security-audit-closeout-2026-05-29.md
```
