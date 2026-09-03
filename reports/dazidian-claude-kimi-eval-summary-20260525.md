# Claude Code + Kimi 大字典评估结果

测试日期：2026-05-25
环境：N100
客户端：Claude Code `2.1.150`
配置工具：`cc-switch`
模型：`kimi-k2.5`
Base URL：`https://api.moonshot.cn/anthropic`

## 结果

| 指标 | 结果 |
| --- | --- |
| 任务 | 只读评估 `大字典` 项目并输出中文报告 |
| 执行结果 | 成功 |
| Exit Code | `0` |
| 执行耗时 | `144.152s` |
| 文件完整性 | `pass` |
| 报告长度 | `8574` chars |
| 质量检查 | `10/10 passed` |
| 使用工具 | `Read` x 24 |
| 危险工具 | `0`，未使用 Bash/Edit/Write |
| Input Tokens | `60861` |
| Output Tokens | `5044` |
| Cache Read Tokens | `224768` |
| Total Tokens 不含 cache read | `65905` |
| Total Tokens 含 cache read | `290673` |

## 与 Codex 直连结果对比

| 指标 | Codex + gpt-5.5 | Claude Code + Kimi |
| --- | ---: | ---: |
| 任务结果 | 成功 | 成功 |
| 质量检查 | `10/10` | `10/10` |
| 项目评分 | `73/100` | `77.5/100` |
| 文件完整性 | `pass` | `pass` |
| 执行耗时 | 未记录 | `144.152s` |
| Token 主口径 | `75,536` | `65,905` 不含 cache read |
| Token 含缓存读取 | 未记录 | `290,673` |
| 工具调用 | Codex 只读评估最终未改文件；之前 sandbox 失败后 unsandboxed | `Read` x 24，未用 Bash/Edit |
| 沙箱/权限 | Codex sandbox 在 N100 失败，最终绕过 | Claude Code 权限显式限制为 `Read/Grep/Glob/LS` |

## 判断

Claude Code + Kimi 这轮达到了测试目标：能读取真实项目、产出完整中文评估、质量检查全过、没有改盘、没有危险工具调用。和 Codex 直连相比，它的报告评分更高一些，token 主口径更低一些，但耗时有明确记录为 `144.152s`，并且存在大量 cache read tokens。

这次还不是“一字诀网关保护下的 Claude Code”测试，而是 `cc-switch` 配置 Kimi 后的 Claude Code 裸客户端只读评估。下一步若要接入一字诀，需要让 Claude Code 的 Anthropic `/v1/messages` 流量指向 N100 一字诀网关，再由网关转发到 Kimi。
