# 根字 Skill Mount 注册表

日期：2026-05-24
定位：V0.5 根字专业规范挂载层
状态：机器可读 registry、loader、网关注入和测试已落地

## 1. 核心定义

Root Skill Mount 是一字诀把社区成熟工程规范挂到 8 个根字上的机制。

```text
根字被激活
  ↓
读取 Skill Mount Registry
  ↓
加载社区参考源、可选工具、上下文挂载、硬门规则、证据要求
  ↓
注入 system rule
  ↓
由 Kernel Policy 和 Tool Guard 执行权限约束
```

这不是复制外部项目，也不是运行时自动安装 GitHub 仓库。它做的是把社区里成熟的工程模式抽象成一字诀自己的本地规范。

## 2. 落地文件

```text
agent_skill_dictionary/skill_mount_registry.json
agent_skill_dictionary/skill_mount_loader.py
tests/test_skill_mount_registry.py
agent_skill_dictionary/workflows/*.md
```

网关会在 `build_system_instruction()` 中注入：

```text
根字 Skill Mount 摘要
```

这样每个执行字不仅有词典规则、根字 workflow 和 Kernel Runtime Policy，还会加载它挂载的社区成熟规范。

## 3. 八个根字挂载关系

| 根字 | Mount | 社区参考源 | 一字诀吸收的工程精髓 |
| --- | --- | --- | --- |
| `查` | `inspect_repo_map_mount` | Aider Repo Map、SWE-agent ACI | 仓库地图、只读探索、文件行号证据 |
| `修` | `surgical_fix_mount` | SWE-agent ACI、Superpowers Debug/TDD | 最小复现、外科手术式修改、验证前不宣称完成 |
| `测` | `tdd_ci_quality_gate_mount` | pytest-cov、verification-before-completion | 真实测试命令、覆盖率、exit code 和证据哈希 |
| `卫` | `security_guard_mount` | Semgrep、OSV-Scanner、PreToolUse Guard | 依赖漏洞、安全扫描、高危命令阻断 |
| `停` | `circuit_breaker_mount` | Circuit Breaker、LangGraph interrupts | 失败阈值、熔断挂起、人工恢复 |
| `问` | `human_in_the_loop_mount` | LangGraph interrupts、PermissionRequest | 结构化澄清、人类授权、低置信度暂停 |
| `记` | `memory_bank_mount` | Claude Code memory、ADR | CLAUDE.md / Memory Bank、决策记录、长期上下文治理 |
| `总` | `handoff_compaction_mount` | Context compaction、handoff summary | 交接摘要、证据保留、下一执行字推荐 |

`造` 是 `修` 的派生字，挂载：

```text
spec_driven_build_mount
```

它用于新功能、新模块和新接口，但权限仍继承 `修` 的受限写入基因。

## 4. Registry 字段

每个 mount 至少包含：

```json
{
  "mount_name": "surgical_fix_mount",
  "purpose": "挂载系统调试、最小复现、TDD 和外科手术式修改规范。",
  "community_sources": [
    {
      "name": "SWE-agent Agent-Computer Interface",
      "pattern": "edit_feedback_and_linter_gate",
      "url": "https://swe-agent.com/0.7/background/aci/"
    }
  ],
  "optional_tools": ["read_file", "grep_code", "edit_scoped_file"],
  "context_mount": ["failing_evidence", "minimal_reproduction"],
  "hard_gates": ["没有复现或失败证据不得宣称修复"],
  "evidence": ["reproduction_result", "git_diff_patch"]
}
```

字段含义：

- `community_sources`：参考的优秀项目、工具或工程模式。
- `optional_tools`：该 mount 倾向使用的工具，不等于当前一定可用。
- `context_mount`：进入该根字时应注入的最小上下文类型。
- `hard_gates`：模型和工具层必须遵守的阻断规则。
- `evidence`：通过该状态需要的系统层证据。

## 5. 与 Kernel Policy 的分工

Skill Mount 负责回答：

```text
这个字应该参考哪些成熟工程模式？
应该加载哪些上下文？
应该遵守哪些专业硬门？
```

Kernel Policy 负责回答：

```text
这个字实际允许哪些工具？
temperature 锁到多少？
是否阻断模型转发？
必须返回哪些证据字段？
```

Tool Guard 负责回答：

```text
某个具体 tool call 是否越权？
是否包含危险命令、依赖安装或写入违规？
```

三者合起来，才是一字诀的稳定执行闭环。

## 6. 当前边界

当前 registry 是“本地规范挂载”，不是“自动执行外部工具”：

- 写入 Semgrep / OSV-Scanner 是参考源和可选工具，不代表当前运行时已经安装并调用它们。
- 写入 Aider Repo Map 是上下文策略，不代表当前已经实现完整 repo map generator。
- 写入 Claude Code memory 是记忆规范参考，不代表当前修改用户项目根目录的 `CLAUDE.md`。

后续若要从“规范挂载”升级成“工具调用”，需要逐项完成：

1. 本地依赖安装与版本锁定。
2. License 和安全审查。
3. CLI 输出解析。
4. 证据哈希落盘。
5. 失败时转 `问` 或 `停`。

## 7. 参考源

- [Aider Repository Map](https://aider.chat/docs/repomap.html)
- [SWE-agent Agent-Computer Interface](https://swe-agent.com/0.7/background/aci/)
- [Semgrep CLI](https://semgrep.dev/docs/getting-started/cli)
- [OSV-Scanner usage](https://google.github.io/osv-scanner/usage/)
- [LangGraph human-in-the-loop interrupts](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
- [Claude Code memory](https://docs.anthropic.com/en/docs/claude-code/memory)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
