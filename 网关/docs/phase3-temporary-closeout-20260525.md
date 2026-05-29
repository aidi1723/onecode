# 一字诀 AgentOS Phase 3 临时收尾总结

日期：2026-05-25
目录：`/Users/aidi/大字典`
状态：本地私测版可部署；生产公开版继续观察

## 1. 当前结论

一字诀 AgentOS 当前已经完成从“执行字词典 + 网关 MVP”到“可接 Claude Code / Codex、可审计、可裁剪、可私密分发”的阶段性闭环。

最准确的定位：

| 维度 | 当前判断 |
|---|---|
| 本机部署 | 可以 |
| 私密仓库分发 | 可以 |
| Codex CLI / Desktop 接入 | CLI 已实测，Desktop 按同端点配置测试 |
| Claude Code 接入 | 已有私测脚本和 Kimi 链路报告 |
| 公开开源 | 暂缓，建议先跑 3-5 台朋友机器 Beta |
| 生产级使用 | 暂缓，仍需 WebSocket、长周期写盘任务、更多客户端兼容验证 |

## 2. 本轮最关键数据

### Codex 本机 A/B

同一个客户端、同一个模型、同一个只读评估任务：

| 维度 | 挂一字诀网关 | 不挂一字诀直连 | 结论 |
|---|---:|---:|---|
| 客户端 | Codex CLI 0.133.0 | Codex CLI 0.133.0 | 同工具 |
| 模型 | `gpt-5.5` | `gpt-5.5` | 同模型 |
| 退出码 | 0 | 0 | 都完成 |
| 总耗时 | 21.51s | 66.74s | 提速 67.8% |
| Input Tokens | 8,111 | 181,153 | 节省 95.5% |
| Output Tokens | 625 | 2,573 | 节省 75.7% |
| 总 Token | 8,736 | 183,726 | 节省 95.2% |
| JSONL 输出大小 | 2,957 bytes | 142,489 bytes | 日志量减少 97.9% |
| 本地命令调用 | 0 | 至少 19 次 | 一字诀压住本地扫描 |
| 报告细节 | 中等 | 较高 | 直连更细，但成本高很多 |

解释：

- 一字诀组通过 `native_inspect_card` 给 Codex 注入只读资产卡，不让 Codex 自己大规模读盘。
- 直连组通过大量 `sed`、`rg`、`find`、`git status` 等本地命令获取更多细节，因此报告更细，但 token 和时间成本暴涨。
- 当前优化方向不是恢复无限读盘，而是提高 `native_inspect_card` 的信息密度。

### Claude Code / Kimi 阶段数据

| 测试 | 关键结果 |
|---|---|
| Shadow Injection 短任务 | 36,537 tokens -> 453 tokens，节省 98.76% |
| 短任务工具调用 | Bash/Read 8 次 -> 0 次 |
| Native Context Injection 长任务 | 134.486s，8,592 字符报告，12/12 检查通过 |
| PathGuard 对抗任务 | 裸跑和仅网关 fail；网关 + PATH Preflight pass |

## 3. 已经落地的能力

| 能力 | 状态 |
|---|---|
| OpenAI-compatible `/v1/chat/completions` | 已支持 |
| Anthropic-compatible `/v1/messages` | 已支持 |
| OpenAI Responses `/v1/responses` | 已支持，供 Codex 使用 |
| Responses -> Chat Completions 上游转译 | 已支持 |
| Chat 响应 -> Responses SSE 回写 | 已支持 |
| `response.completed` SSE 完成事件 | 已支持 |
| Codex 隔离 `CODEX_HOME/auth.json` 配置 | 已支持 |
| Claude Code settings 生成 | 已支持 |
| `native_inspect_card` | 已支持 |
| Claude Native Context Injection | 已支持 |
| Codex Native Context Injection | 已支持 |
| Shadow Tool Mapping | 已支持 |
| Soft Rewrite | 已支持 |
| PATH Preflight / PathGuard | 已支持并修过递归 CPU 问题 |
| 私密仓库部署脚本 | 已支持 |
| 发布前密钥扫描 | 已支持 |

## 4. 当前代码与文档入口

### 部署与私测

| 文件 | 用途 |
|---|---|
| `PRIVATE_BETA_QUICKSTART.md` | 测试者最短上手说明 |
| `deploy/README_PRIVATE_BETA.md` | 私密部署完整说明 |
| `docs/private-beta-distribution.md` | 维护者分发说明 |
| `.env.example` | 测试者本机配置模板 |
| `deploy/start_gateway_background.sh` | 后台启动网关 |
| `deploy/smoke_http.sh` | 网关 HTTP 健康检查 |
| `deploy/run_claude_smoke.sh` | Claude Code smoke |
| `deploy/run_codex_smoke.sh` | Codex CLI smoke |
| `deploy/private_repo_release_check.sh` | 发布前密钥扫描、编译、核心测试 |

### 架构与内核

| 文件 | 用途 |
|---|---|
| `README.md` | 项目总入口 |
| `docs/architecture.md` | 架构说明 |
| `docs/project-status.md` | 项目阶段状态 |
| `docs/yizijue-gateway-quickstart.md` | 网关快速开始 |
| `docs/oneword-agentos-v1-kernel-manual.md` | 内核手册 |
| `docs/yin-yang-binary-kernel.md` | 阴阳八卦二进制内核说明 |
| `docs/root-skill-mount-registry.md` | 根字 Skill Mount 注册表 |

### 测试报告

| 文件 | 用途 |
|---|---|
| `docs/agentos-test-summary-20260525.md` | 2026-05-25 阶段测试总报告 |
| `reports/dazidian-yizijue-vs-bare-comparison-20260525.md` | 一字诀 vs 裸跑对比 |
| `reports/dazidian-codex-claude-yizijue-pathguard-comparison-20260525.md` | Codex / Claude / PathGuard 对比 |
| `reports/complex-task-ab-summary.md` | 复杂任务 A/B 摘要 |
| `reports/live-agent-benchmark-secure-b2b-ledger.md` | Secure-B2B-Ledger 靶场报告 |

## 5. 私测部署最短流程

```bash
git clone <private-repo-url>
cd <repo>
cp .env.example .env
```

填写 `.env`：

```text
ONEWORD_GATEWAY_TOKEN=本机自定义网关 token
ONEWORD_WORKSPACE_ROOT=/要测试的项目绝对路径
ONEWORD_UPSTREAM_BASE_URL=https://你的 OpenAI-compatible 上游/v1
ONEWORD_UPSTREAM_API_KEY=真实上游 key
ONEWORD_CODEX_MODEL=模型名
ONEWORD_ANTHROPIC_BASE_URL=https://你的 Anthropic-compatible 上游/v1
ONEWORD_ANTHROPIC_API_KEY=真实上游 key
ONEWORD_ANTHROPIC_MODEL=模型名
```

启动和检查：

```bash
bash deploy/start_gateway_background.sh
bash deploy/smoke_http.sh
```

Codex CLI：

```bash
bash deploy/run_codex_smoke.sh
```

Claude Code：

```bash
bash deploy/run_claude_smoke.sh
```

停止：

```bash
bash deploy/stop_gateway.sh
```

## 6. 发布前检查

维护者 push 前必须跑：

```bash
bash deploy/private_repo_release_check.sh
```

本轮最新结果：

| 检查 | 结果 |
|---|---|
| 密钥扫描 | No obvious API keys found |
| Python compile | 通过 |
| 核心测试 | 40 tests OK |
| 私测发布检查 | Private beta release check passed |

额外相关回归：

| 检查 | 结果 |
|---|---|
| Codex Responses 兼容相关回归 | 通过 |
| 网关 / Auth / Core / Executor / Preflight 相关回归 | 71 tests OK |

## 7. 已知缺口

| 缺口 | 影响 | 建议 |
|---|---|---|
| Codex 会先尝试 WebSocket `/v1/responses` | 会多几秒 403 回退成本 | 后续补 WebSocket 或找配置禁用 |
| `native_inspect_card` 信息密度不如直连大扫描 | 报告细节略少 | 扩展到 3000-5000 字，加入测试摘要、模块拓扑、风险热点 |
| 长周期写盘任务仍需更多验证 | 生产修复能力未完全证明 | 用临时副本跑 10-50 轮修复/测试任务 |
| PATH Preflight 是环境级拦截 | 长期维护成本高 | 后续升级 hooks / runner / 更硬隔离 |
| 多客户端矩阵还不够 | 私测机器差异未知 | 先跑 3-5 台 Mac/Linux 私测 |

## 8. 临时收尾判断

当前项目可以进入“本地私测部署 + 私密仓库分发”阶段。

不要把它宣传为生产完成版。更准确的说法是：

> 一字诀 AgentOS 已经证明它能在 Codex / Claude Code 真实客户端链路中显著降低 token、减少本地工具调用、提升安全可控性，并完成只读审计类任务。下一阶段重点是提高 native context 信息密度、补齐 WebSocket、验证多轮写盘任务和跨机器稳定性。
