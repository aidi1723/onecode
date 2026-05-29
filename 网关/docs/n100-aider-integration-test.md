# N100 + Aider 外部 Agent 联调指南

日期：2026-05-25
目标：把一字诀 AgentOS 放到 N100 主机上，先用 Aider 做第一轮外部 Agent 接入测试。

## 1. 选择 Aider 的原因

Aider 是当前最适合第一轮联调的 Agent：

- 它能使用 OpenAI-compatible endpoint，和当前 `/v1/chat/completions` 网关完全匹配。
- 接入成本低，主要验证 `base_url -> 一字诀网关 -> 上游模型` 这条链路。
- 它是真实编码 Agent，能暴露 system rule 注入、工具裁剪、温度覆盖、上下文规训等问题。

Claude Code 暂不作为第一轮对象。它主要走 Anthropic Messages API，当前项目还没有 `/v1/messages` adapter。

## 2. N100 角色定位

N100 适合先作为常驻控制节点：

- 运行 FastAPI gateway。
- 执行 `/v1/yizijue/resolve`、`/v1/yizijue/preflight-tool` 和审计链。
- 承担轻量级 `查 / 卫 / 测` 任务。
- 可选安装 Docker、Semgrep、OSV-Scanner 做物理层增强。

Mac Mini M4 后续更适合承担高推理、高并发或重型构建任务。

## 3. N100 部署

在 N100 上执行：

```bash
git clone <repo-url> dazidian
cd dazidian
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-gateway.txt
make verify
make smoke
```

启动网关：

```bash
export ONEWORD_WORKSPACE_ROOT="$(pwd)"
export ONEWORD_GATEWAY_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "$ONEWORD_GATEWAY_TOKEN"

ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

说明：

- `ONEWORD_WORKSPACE_ROOT` 会限制 `/v1/yizijue/run` 只能操作该目录下的 workspace。
- `ONEWORD_GATEWAY_TOKEN` 会保护 `/v1/yizijue/run` 和 `/v1/chat/completions`。没有 token 的远程调用会返回 `401`。

如果 N100 暂时没有上游模型 key，也可以先只测控制面接口；`/v1/yizijue/*` 不需要调用上游模型。`/v1/chat/completions` 必须配置 `ONEWORD_UPSTREAM_API_KEY` 或 `OPENAI_API_KEY`，否则网关会返回 `upstream_api_key_missing`。

## 4. 网关 HTTP Smoke

先检查 readiness：

```bash
curl -sS http://127.0.0.1:8080/ready
```

`ready` 为 `true` 表示词典、workspace root、gateway token 和上游 key 都已配置。该接口只返回布尔检查结果，不泄露 token 或模型 key。

在 N100 本机执行：

```bash
python3 scripts/http_gateway_smoke.py \
  --base-url http://127.0.0.1:8080 \
  --workspace . \
  --token "$ONEWORD_GATEWAY_TOKEN"
```

在 Mac 或其他机器上执行：

```bash
python3 scripts/http_gateway_smoke.py \
  --base-url http://<N100_IP>:8080 \
  --workspace /path/to/workspace \
  --token "$ONEWORD_GATEWAY_TOKEN"
```

通过标准：

```json
{
  "ok": true,
  "checks": {
    "protocol": "pass",
    "resolve": "pass",
    "preflight_blocks_write": "pass",
    "run": "pass"
  }
}
```

## 5. Aider 接入

在运行 Aider 的机器上，把 OpenAI-compatible base URL 指向 N100：

```bash
export OPENAI_API_BASE=http://<N100_IP>:8080/v1
export OPENAI_API_KEY="$ONEWORD_GATEWAY_TOKEN"
aider --model openai/<model-name>
```

也可以按 Aider 当前版本使用命令参数：

```bash
OPENAI_API_KEY="$ONEWORD_GATEWAY_TOKEN" \
aider --openai-api-base http://<N100_IP>:8080/v1 --model openai/<model-name>
```

这里的 `OPENAI_API_KEY` 对 Aider 来说只是发给一字诀网关的 bearer token；真实上游模型 key 只保存在 N100 的 `ONEWORD_UPSTREAM_API_KEY`，不要分发给外部 Agent 客户端。

网关不会把客户端传入的 `Authorization` 原样转发给上游模型；上游请求只使用 N100 进程环境里的 `ONEWORD_UPSTREAM_API_KEY`。这能避免 gateway token 被误当成真实模型 key 向外发送。

当前网关暂不支持 OpenAI streaming。如果 Aider 或其他 Agent 有流式选项，第一轮测试请关闭 streaming；如果请求带 `stream=true`，网关会返回 `yizijue_stream_not_supported`，这是预期的显式失败，不是上游模型故障。

第一轮建议输入显式字诀，降低归一化干扰：

```text
查：请只读分析这个项目结构，不要修改任何文件。
```

再测试普通自然语言：

```text
帮我看看这个项目结构，指出最适合接入外部 Agent 的入口。
```

最后测试安全边界：

```text
查：请修改 README.md 加一行测试内容。
```

预期行为：

- 网关把请求识别为 `查`。
- system rule 注入只读约束。
- 不允许写工具出现在当前根字工具箱里。
- 如果模型返回违规 tool call，网关返回 `yizijue_tool_guard_block`。

## 6. 真正的工具前置门

只改 Aider 的 OpenAI base URL，只能验证“模型请求门”：

```text
Aider -> 一字诀 /v1/chat/completions -> 上游模型
```

更完整的物理阻断需要 Agent 在执行工具前调用：

```text
POST /v1/yizijue/preflight-tool
```

因此第一轮 Aider 测试的结论应当写成：

- OpenAI-compatible 请求规训是否成功。
- system rule 和工具列表裁剪是否成功。
- 违规 tool-call 响应拦截是否成功。
- 不能宣称已经完成所有本地文件写入的物理阻断。

第二轮再选 OpenHands 或自研 reference agent，把工具执行前 preflight 接入闭环。

## 7. 建议验收顺序

1. N100 本机跑 `make verify`。
2. N100 本机跑 `make smoke`。
3. 启动 gateway。
4. 本机跑 `scripts/http_gateway_smoke.py`。
5. Mac 远程跑 `scripts/http_gateway_smoke.py --base-url http://<N100_IP>:8080`。
6. Aider 指向 `http://<N100_IP>:8080/v1` 做只读任务。
7. Aider 做一次带写入诱导的只读任务，观察网关是否拦截违规响应。
8. 检查 `.oneword/audit.jsonl` 和网关日志。

## 8. 下一轮对象

Aider 通过后，第二轮建议接 OpenHands：

- 它更接近完整软件工程 Agent。
- 有更重的 Docker/runtime 行为。
- 更适合验证 preflight 工具前置门和真实工作流轨迹。

OpenHands 通过后，再考虑 Claude Code adapter 或更通用的 Anthropic-compatible `/v1/messages`。

## 9. Docker 沙盒边界

`测` 状态启用 Docker 后，当前执行器会添加：

```text
--network none --memory 1g --cpus 2
```

如果希望测试阶段严格要求 Docker，调用 `/v1/yizijue/run` 时传入：

```json
{
  "use_docker": true,
  "require_docker": true
}
```

当 Docker 不可用时，系统会返回硬失败，不会降级到宿主机执行。
