# 一字诀 AgentOS Private Beta 部署与测试说明

本目录用于把一字诀网关分发给指定朋友做私密部署测试。不要提交真实 API key。

## 1. 机器要求

| 项 | 要求 |
|---|---|
| OS | macOS 或 Linux |
| Python | 3.10+，建议 3.11/3.12 |
| 网络 | 能访问你的上游模型端点 |
| 客户端 | 可选：Claude Code 2.x、Codex Desktop、Codex CLI |

## 2. 快速部署

在仓库根目录执行：

```bash
cp .env.example .env
```

编辑 `.env`：

```text
ONEWORD_GATEWAY_TOKEN=给本机客户端使用的网关 token
ONEWORD_WORKSPACE_ROOT=/要测试的项目绝对路径
ONEWORD_ANTHROPIC_BASE_URL=https://你的 Anthropic-compatible endpoint/v1
ONEWORD_ANTHROPIC_API_KEY=真实上游 key
ONEWORD_ANTHROPIC_MODEL=模型名
ONEWORD_UPSTREAM_BASE_URL=https://你的 OpenAI-compatible endpoint/v1
ONEWORD_UPSTREAM_API_KEY=真实上游 key
ONEWORD_CODEX_MODEL=模型名
```

启动网关：

```bash
bash deploy/start_gateway.sh
```

健康检查：

```bash
bash deploy/smoke_http.sh
```

## 3. Claude Code 接入

生成 Claude Code settings 文件：

```bash
python3 deploy/make_claude_settings.py
```

默认输出：

```text
.oneword/claude-gateway-settings.json
```

用 Claude Code 跑短只读测试：

```bash
bash deploy/run_claude_smoke.sh
```

或者手动运行：

```bash
claude --bare \
  --settings .oneword/claude-gateway-settings.json \
  -p \
  --output-format json \
  --model "$ONEWORD_ANTHROPIC_MODEL" \
  --tools "Read,Bash" \
  --permission-mode dontAsk \
  "查：请只读评估当前项目，输出 500 字中文简报。"
```

## 4. Codex Desktop / Codex CLI 接入

如果 Codex 桌面版是独立部署、通过 API key 驱动，并支持 OpenAI-compatible Base URL，可以直接接一字诀网关。

Codex 桌面版填写：

| 字段 | 填写 |
|---|---|
| Provider | OpenAI-compatible / OpenAI |
| Base URL | `http://127.0.0.1:8080/v1` |
| API Key | `.env` 里的 `ONEWORD_GATEWAY_TOKEN` |
| Model | `.env` 里的 `ONEWORD_CODEX_MODEL` 或上游模型名 |

测试 prompt：

```text
查：请只读评估当前项目，输出 500 字中文简报。必须包含项目目标、核心模块、安全风险、3 条改进建议。不要修改文件，不要安装依赖，不要联网。
```

如果安装了 Codex CLI，可以用同一套 `.env` 跑命令行 smoke：

```bash
bash deploy/run_codex_smoke.sh
```

## 5. 验收标准

短只读 smoke 的目标：

| 指标 | 目标 |
|---|---|
| exit_code | 0 |
| 文件完整性 | 不应修改被测项目 |
| 工具调用 | 理想情况下 `Bash/Read=0` |
| 输出 | 包含项目结构、风险、建议 |
| 网关 | `/ready` 返回 `ready=true` |

## 6. 安全边界

当前 Beta 默认用于只读审计和网关能力测试。

不要在朋友机器上直接跑破坏性 prompt。需要测试写盘/修复任务时，必须先复制一份临时项目：

```bash
cp -R /path/to/project /tmp/oneword-beta-project
```

然后把 `.env` 里的 `ONEWORD_WORKSPACE_ROOT` 指向临时副本。

## 7. 常见问题

### Claude Code 没有走一字诀网关

Claude Code 可能优先读取全局 `~/.claude/settings.json`。必须使用：

```bash
--settings .oneword/claude-gateway-settings.json
```

### 网关 401

Claude settings 里的 `ANTHROPIC_API_KEY` 应该是 `ONEWORD_GATEWAY_TOKEN`，不是上游真实 key。真实 key 只放在 `.env` 的 `ONEWORD_ANTHROPIC_API_KEY`。

### 上游 502

检查：

```bash
grep ONEWORD_ANTHROPIC .env
```

确保 base URL 包含 `/v1`，且 key 有权限访问对应模型。

### Codex 桌面版没有 Base URL 设置

如果桌面版只有 API Key，没有 Base URL，就不能直接接一字诀网关。请改用 Codex CLI，或确认桌面版是否读取 `~/.codex/config.toml`。

## 8. 回传给项目维护者的数据

请让测试者回传以下文件，不要回传 `.env`：

```text
.oneword/gateway.log
.oneword/claude-smoke-output.json
.oneword/claude-smoke-stderr.txt
.oneword/codex-smoke-output.jsonl
.oneword/codex-smoke-stderr.txt
```
