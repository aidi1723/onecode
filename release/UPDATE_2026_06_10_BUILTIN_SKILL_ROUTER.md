# OneCode Update - Built-In Skill Router / OneCode 更新 - 内置 Skill 路由器

## Summary / 摘要

OneCode now includes a built-in `safe-agent-router` skill. It helps the agent
classify a task, select relevant trusted skill guidance, arrange the execution
order, and attach verifier expectations before work is reported as complete.

OneCode 现在内置 `safe-agent-router` skill。它会帮助 Agent 识别任务类型、选择相关的可信 skill 指引、安排执行顺序，并在任务完成前附带验证预期。

## What Changed / 更新内容

- Built-in skill location: `integrations/skills/safe-agent-router/`.
  内置 skill 位置：`integrations/skills/safe-agent-router/`。
- Package-bundled copy for installed OneCode runtimes.
  安装后的 OneCode 运行时会包含打包版本。
- CLI support for listing, showing, and routing built-in skills.
  CLI 支持列出、查看和路由内置 skills。
- Task packs now include capability coverage, execution order, verifier
  expectations, and a fixed safety boundary.
  任务包现在包含能力覆盖、执行顺序、验证预期和固定安全边界。

## Why It Matters / 为什么重要

OneCode can absorb strong community skill workflows into a controlled local
kernel and select the most relevant guidance for the current task. Instead of
requiring every user to know which skill to load, the router gives the agent a
structured task pack first: what capability is needed, which skill guidance is
relevant, what order to follow, and what must be verified.

OneCode 可以把优秀的社群 skill 工作流吸收到受控的本地内核中，并根据当前任务选择最相关的指引。用户不需要先知道应该加载哪个 skill，路由器会先给 Agent 一个结构化任务包：需要什么能力、哪些 skill 指引相关、应该按什么顺序执行，以及最后必须验证什么。

This lowers the barrier for new users. A beginner can describe the task in
plain language, while OneCode supplies a more professional workflow shape:
planning, execution order, safety boundary, and verification. The goal is to
help more users produce cleaner, more complete, and more polished results
without losing execution control.

这会降低新手使用门槛。用户可以直接用自然语言描述任务，OneCode 会补上更专业的工作流结构：规划、执行顺序、安全边界和验证。目标是让更多用户在不失去执行控制的前提下，产出更干净、更完整、更精致的结果。

## Safety Boundary / 安全边界

The router is advisory only. It does not grant filesystem, shell, network,
browser, connector, account, credential, deployment, or production permissions.
Host runtime policy, OneCode path guards, evidence checks, verifier gates,
approvals, and higher-priority instructions remain authoritative.

该路由器只提供建议，不授予文件系统、shell、网络、浏览器、连接器、账号、凭据、部署或生产权限。宿主运行策略、OneCode 路径护栏、证据检查、验证门禁、审批和更高优先级指令仍然是执行权威。

## Try It / 试用

```bash
onecode skills list
onecode skills show safe-agent-router
onecode skills route "update docs and run tests"
```
