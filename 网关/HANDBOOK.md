# 一字诀 · Agent 安全网关

> 给任意 AI Agent 加一层网关，省下 90%+ 的 token，并让它的每一步都可审计、可回退、可阻断。

把你的 Agent 的 base URL 指向它，剩下的不用改。它在 Agent 和大模型之间做三件事：**裁掉无用上下文、锁住危险操作、记录不可篡改的证据链**。

---

## 为什么需要它

Agent 现在不敢放进生产，原因就三个，而且每个都烧钱或烧信任：

- **token 失控**：一个"看看项目结构"的任务，原生 Agent 会反复读文件、跑命令、塞满上下文，token 轻松冲到十几万。
- **会乱来**：它可能 `rm -rf`、装依赖、改你没让它改的文件，而你事后根本说不清它干了什么。
- **没法追责**：模型说"测试通过了"，可它到底跑没跑？日志能不能信？出了事谁也对不上账。

一字诀不靠"把提示词写得更好"来解决这些，而是在网关层用**确定性规则**把 Agent 固定到可验证的轨道上。

---

## 30 秒看懂它做什么

同一个任务"帮我看看项目结构"，走不走网关的区别：

```text
直连大模型                          经过一字诀网关
────────────                       ────────────────
读文件 → 跑 ls → 跑 grep →          归一化为「查」字
再读 → 再跑 → 上下文塞满 →          → 锁定只读工具集
模型自由发挥                        → 裁掉写/删/装依赖
                                   → 注入该字的专业工作流
                                   → 全程写入审计链
```

---

## 一组真实数据

Codex CLI `gpt-5.5`，同一任务 A/B 对照（详见 `README.md` 与 `docs/gateway-rule-sync-closeout-2026-05-29.md` 的阶段记录）：

| 指标 | 直连 | 经过一字诀 | 变化 |
|---|---|---|---|
| 总 token | 183,726 | 8,736 | **降 95.2%** |
| 输入 token | 181,153 | 8,111 | 降 95.5% |
| 耗时 | 66.74s | 21.51s | **降 68%** |
| 本地命令调用 | ≥19 次 | 0 次 | 压住乱扫描 |
| 日志体积 | 142 KB | 2.9 KB | 降 97.9% |

> 这是单任务结果，不同任务波动较大。它代表的是"网关裁掉无效上下文"这件事在最理想情况下能省到什么程度，不是承诺每次都降 95%。

---

## 核心思路：一个字 = 一套专业规范

你不用学一堆配置。你告诉 Agent 要干嘛，网关先把它归一化成一个**执行字**——比如查、修、测、卫、停。每个字背后绑定五层约束：

| 层 | 作用 |
|---|---|
| 词典定义 | 固定含义、权限、模型温度、失败回退 |
| 工具白名单 | 这个字能用哪些工具，其余一律裁掉 |
| 专业工作流 | 把社区优秀 Agent 工作流的精髓写成机器规则注入 |
| 运行时策略 | 危险命令拦截、温度覆盖、熔断、证据字段 |
| 审计链 | 每步操作写入带 SHA256 的不可篡改日志 |

举例：
- **查** = 只读。想写文件？工具在进上游前就被裁掉了。
- **测** = 真实跑命令拿退出码，可选 Docker 沙箱（`--network none` 隔离）。模型不能靠嘴说"通过了"。
- **停** = HTTP 503 硬熔断，直接不转发给大模型，等人工放行令牌。

---

## 5 分钟跑起来

```bash
# 1. 装依赖
python3 -m pip install -r requirements-gateway.txt

# 2. 配置（token 用于隔离客户端，上游模型凭证只留在网关侧）
export ONEWORD_WORKSPACE_ROOT="$(pwd)"
export ONEWORD_GATEWAY_TOKEN="dev-local-token"

# 3. 启动网关
ONEWORD_UPSTREAM_API_KEY="$OPENAI_API_KEY" \
uvicorn agent_skill_dictionary.gateway_server:app --host 0.0.0.0 --port 8080
```

把任意 OpenAI-compatible Agent 的 base URL 指过来即可：

```text
http://localhost:8080/v1
```

客户端的 `OPENAI_API_KEY` 填网关 token；上游模型凭证永远不离开网关进程，也不会回传给客户端。

不想起服务？直接命令行接入：

```bash
python3 -m agent_skill_dictionary.cli resolve "查：看看项目结构"
python3 -m agent_skill_dictionary.cli run "帮我看看项目结构" --workspace .
python3 -m agent_skill_dictionary.cli run "请运行测试验证" --workspace . --use-docker
```

---

## 接入任意 Agent 的推荐循环

任何第三方 Agent 接入时遵守这套物理闭环，就能享受门禁和审计：

1. 调 `/v1/yizijue/resolve` 拿到当前执行字、工具白名单、证据要求。
2. 每次工具执行**前**调 `/v1/yizijue/preflight-tool`，按 `allowed/violations` 决定做不做。
3. 执行后提交系统 evidence——不允许用模型自然语言声称"测试通过"。
4. 用审计接口校验 JSONL hash chain，确认日志没被篡改。
5. 遇 `halted` 立即停，遇 `waiting_for_human` 把结构化选择交还人类。

支持三路协议：OpenAI Chat Completions、OpenAI Responses、Anthropic Messages。

---

## 它适合谁

| 适合 | 暂不适合 |
|---|---|
| 想给现有 Agent 加省钱 + 安全层 | 需要多节点分布式调度 |
| 本机 / 私有仓库的 Agent 实验 | 公开生产级 SLA（仍在 Beta） |
| 在意审计链、可回退、可阻断 | 需要 WebSocket 流式特性的场景 |
| 跑长任务被 token 账单劝退的人 | 不接受确定性约束、要模型完全自由发挥 |

---

## 当前状态

- 当前基线：Build Mode V2 + Kernel Runtime Policy；V0.3/V0.4 是历史演进层。
- 22 个执行字、8 个根字 Opcode 原型已落地。
- 最新验证基线：566 个单元测试通过（13 个按本地依赖条件跳过）+ 词典 validator + 编译检查。
- Build Mode V2 本地网关闭环已通过 live-smoke（三路协议）。
- 安全审计收尾已完成：鉴权 fail-closed、`/run` 工作区边界、命令白名单、控制面鉴权和坏 JSON 处理均已落地。

**诚实边界**：这是适合本机和私密 Beta 的版本。公开生产前还需固定部署环境配置、补齐真实客户端端到端验证、长任务 A/B、SLA 观测和运维手册。详细技术文档见 `README.md` 与 `docs/`。

---

## 想深入

| 我想… | 看这里 |
|---|---|
| 理解整体架构 | `docs/architecture.md` |
| 看八个根字的设计 | `docs/eight-opcode-primitives.md` |
| 接入现有 CLI Agent / Claude Code | `docs/existing-agent-gateway-integration.md` |
| 私测部署 | `PRIVATE_BETA_QUICKSTART.md` |
| 完整能力清单与细节 | `README.md` |

> 顺带一提：执行字背后那套"根字相互制衡、隐藏风险锁、生命周期轨迹"的运行时契约，灵感来自《易经》的卦象关系。它是内部实现的一套优雅约束模型——你不需要懂易经也能用，但如果好奇，`docs/yin-yang-binary-kernel.md` 在等你。
