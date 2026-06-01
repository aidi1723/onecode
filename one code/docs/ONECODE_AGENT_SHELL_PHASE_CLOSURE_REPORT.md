# OneCode Agent Shell 阶段收尾报告

日期：2026-05-31
状态：阶段收尾
范围：OneCode 内核 + LibreChat 壳

## 1. 阶段结论

本阶段完成了 OneCode 从“本地内核原型”到“可通过成熟 Web 壳使用的本地 Agent”的关键闭环。

当前闭环为：

```text
OneCode Kernel
  -> OneCode OpenAI-compatible API
  -> LibreChat OneCode custom endpoint
  -> LibreChat Web shell
  -> OneCode Console / 项目选择 / 模型配置 / 证据面板
```

网关产品线不属于本阶段范围。本阶段没有把 OneCode 绑定到 gateway、LiteLLM、Portkey 或其它网关项目。

## 2. 当前可运行入口

OneCode API：

```text
http://127.0.0.1:18080
```

LibreChat 壳：

```text
http://127.0.0.1:14080
```

本地测试账号：

```text
Email: onecode@local.test
Password: OneCode123!
```

当前服务进程：

- `onecode-api`：监听 `127.0.0.1:18080`
- `onecode-shell`：监听 `127.0.0.1:14080`

## 3. 已完成能力

### 3.1 壳接入

- LibreChat 作为 OneCode 的 Web shell。
- 自定义端点固定为 `OneCode`。
- 默认对话模型显示为 `onecode-agent`。
- 欢迎语已改为：`OneCode：可信任的工业级 AI 内核`。
- 登录页品牌文案已改为 `one code`。
- 浏览器标签页标题为 `one code`。
- 已移除 LibreChat 羽毛 favicon、PWA 图标和欢迎页前置羽毛图标。

### 3.2 OneCode Console 产品化

左侧栏已加入 `OneCode 模型配置` 入口，可打开 OneCode Console。

Console 当前覆盖：

- `项目`：工作目录状态、Git 状态、验证策略状态、项目初始化、MCP 同步。
- `运行`：最近 run 列表、inspect、resume。
- `证据`：ledger、manifest、checkpoint 证据查看。
- `验证`：verifier preset、策略读取、初始化和覆盖。
- `诊断`：doctor 与 self-audit。
- `模型`：API endpoint、API key、模型选择、远端模型发现。

### 3.3 项目文件夹能力

- 支持从壳里选择已有项目文件夹。
- 支持新建项目文件夹。
- 支持记录最近项目。
- 支持将当前 workspace 注入 OneCode 请求 metadata。
- 支持把当前项目目录同步到 Filesystem MCP 配置。

### 3.4 模型配置能力

- 壳内可配置 API endpoint、API key、模型名。
- 支持从 OpenAI-compatible `/models` 接口发现模型列表。
- 支持保存模型配置到 OneCode 用户配置。
- 支持 API key 掩码显示。
- 支持 endpoint 容错：例如 `10.0.0.184:6780/v1` 会规范化为 `http://10.0.0.184:6780/v1`。
- 已实测模型直连普通对话可返回正常回复。

### 3.5 内核硬化

本阶段同步完成了 OneCode 内核成熟度补强：

- 并行 checkpoint manifest 竞争问题修复。
- execution plan 顶层运行结果补齐 ledger/manifest 路径。
- verifier policy 限制到预设命令。
- Web API 默认鉴权策略收紧。
- TUI 移除固定内网 endpoint 默认值。
- 模型配置持久化。
- Docker sandbox adapter 与 smoke test。
- trace event 写入。
- human approval 证据记录。
- benchmark harness 与 20 个任务定义。
- CI、LICENSE、SECURITY、CONTRIBUTING、release checklist 等开源治理基础。

版权当前按用户确认写为：

```text
Copyright (c) 2026 aidi
All rights reserved.
```

## 4. 验证证据

OneCode 内核验证：

```text
bash scripts/verify.sh
Ran 373 tests in 13.221s
OK
doctor: {"status": "ok"}
```

LibreChat 壳构建：

```text
npm run build:client
✓ built in 31.21s
```

浏览器运行时验证：

```json
{
  "title": "one code",
  "icons": [
    {
      "rel": "icon",
      "href": "data:,"
    }
  ],
  "manifest": {
    "name": "one code",
    "short_name": "one code",
    "icons": []
  }
}
```

模型配置验证：

```json
{
  "configured": true,
  "endpoint": "http://10.0.0.184:6780/v1",
  "model": "gpt-5.5",
  "api_key_configured": true
}
```

普通对话接口验证：

```text
POST /v1/chat/completions
response: "Hi! How can I help you today?"
mode: chat
```

## 5. 当前边界

本阶段可以作为 OneCode Agent Shell 的本地可用基线，但还不是正式生产发布。

已闭合：

- OneCode 与 LibreChat 壳的主链路。
- 本地登录、对话、模型配置、项目绑定、MCP workspace 同步。
- 内核运行证据、恢复、诊断、验证策略的壳层面板。
- 本地运行和浏览器烟测。

未闭合：

- 正式生产部署拓扑。
- 多用户权限治理。
- 企业级密钥托管。
- 自动化端到端浏览器回归测试全覆盖。
- 仓库工作区清理和提交编排。
- 将所有执行路径强制切入 Docker sandbox。

## 6. 工作区状态

当前本地工作区存在较多已修改和未跟踪文件，符合本阶段连续集成开发状态，但不符合直接发布状态。

发布或打包前需要：

- 清理临时目录、截图、实验数据和生成物。
- 拆分 OneCode 内核提交与 LibreChat 壳提交。
- 明确哪些 `client/dist` 产物需要纳入版本控制。
- 再跑一次完整验证。
- 根据发布目标决定是否做 tag 或 release 包。

## 7. 下一阶段建议

建议下一阶段命名为：

```text
OneCode Agent Shell v0.3 - Release Packaging
```

优先级：

1. 一键启动器：稳定启动 OneCode API + LibreChat 壳 + 本地依赖。
2. 发布清理：整理 git 状态、提交边界、版本号、变更日志。
3. 端到端测试：登录、模型配置、项目选择、MCP 同步、发起任务、查看证据。
4. 沙箱升级：将更多实际执行路径接入 Docker sandbox。
5. 部署文档：本地开发、局域网部署、单机生产预览三套说明。

## 8. 收尾判断

本阶段可以收尾。

OneCode 已具备一个可运行、可登录、可配置模型、可绑定项目文件夹、可查看内核运行证据的成熟聊天壳。下一阶段应从“继续补功能”转向“打包、清理、发布和回归自动化”。
