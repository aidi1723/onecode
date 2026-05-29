# Gateway 与 OneCode v0.6 规则同步设计

日期: 2026-05-29
分支: `feature/gateway-iching-rule-sync`
范围: 上一层一字诀网关产品线, 面向 Claude Code / Codex / OpenAI-compatible agent / Anthropic-compatible agent

## 1. 设计结论

本阶段不做 OneCode 专属网关, 也不修改 OneCode 内核。

OneCode v0.6 是规则闭合的参考内核: 它证明了阴阳、四象、八卦、64 卦、五行和证据链可以收束到同一个 6-bit 运行状态面。上一层网关产品线已经有 OpenAI / Anthropic 入口、root-code 路由、Build Mode、preflight、PATH 哨兵、沙箱验证和状态持久化。本次同步的正确方式是新增网关规则适配层, 把这些已有能力统一投影到 OneCode v0.6 已验证的规则语义上。

核心目标:

- 保留网关现有 `查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总` 入口语义。
- 保留易经、阴阳、五行、四象、八卦和 64 卦作为必须遵循的控制语言。
- 让网关每次请求、工具调用、沙箱结果和状态持久化都输出统一的 6-bit 运行信封。
- 不复制 OneCode 的 `IchingKernel` 作为网关业务内核, 只同步它已经闭合的状态公式、证据字段和调度判定。
- 不把产品定位成编码助手, 而是定位成可控、可复现、可恢复的 agent 任务网关。

## 2. 当前网关已有基础

当前上一层网关已经具备这些能力:

- `gateway_core.py` 负责请求重写、system rule 注入、temperature 锁定、工具裁剪和 stream tool 阻断。
- `gateway_server.py` 已提供 OpenAI Chat Completions、Responses、Anthropic Messages 兼容入口。
- `kernel_policy.py` 定义 8 个根字的权限、证据字段、工具白名单和物理控制流。
- `trigram_contract.py` 定义 3-bit 根字契约、错卦、综卦、生命周期证据和隐藏意图锁。
- `build_mode_*` 模块已实现 3-bit Build Mode 状态机、沙箱验证、写入证据、归档证据、路径主权、熵衰减和五行调制雏形。
- `tool_guard.py`、`path_sentinel.py` 和本地 hook / PATH 哨兵已经覆盖部分工具执行前硬门。
- 测试已覆盖 gateway rewrite、Anthropic adapter、Build Mode tool takeover、session state、preflight 和 live smoke 脚本。

这说明网关不是从零开始。要补的是统一状态信封和规则闭合, 不是重写产品线。

## 3. 当前差距

### 3.1 规则面分散

网关当前同时存在:

- root-code policy: `kernel_policy.py`
- trigram contract: `trigram_contract.py`
- Build Mode 3-bit FSM: `build_mode_fsm.py`
- Build Mode element balancer: `build_mode_v3_balancer.py`
- gateway route matrix: `HexagramRouter`

这些模块大体方向一致, 但没有统一输出一个可审计的 6-bit 状态。结果是规则存在, 但状态证据分散。

### 3.2 只有 3-bit 行为态, 缺少 6-bit 运行态

Build Mode 的 `111 -> 001 -> 000` 等状态适合描述单个执行阶段, 但还不能完整表达:

- 外部环境面: 认证、上游模型、网络、协议、客户端、本地 hook。
- 内部资产面: 写入、patch、测试、归档、resume、证据完整性。

OneCode v0.6 的核心经验是把外卦和内卦合成:

```text
S = (outer_trigram << 3) | inner_trigram
```

网关需要保留当前 3-bit 根字作为入口, 但运行时证据要升级为 6-bit envelope。

### 3.3 证据字段尚未统一

当前网关不同层输出的字段不完全一致, 例如:

- gateway metadata 用 `active_code`, `root_opcode`, `hexagram_route`。
- Build Mode tool result 用 `hexagram`, `next_hexagram`, `consecutive_failures`。
- preflight 用 `allowed`, `violations`, `kernel_policy`。
- state file 用 build-mode 专属结构。

需要新增统一字段, 让同一次运行可以从网关入口追溯到工具调用和状态转移。

### 3.4 OneCode 的已验证修复尚未系统迁移

OneCode v0.6 已验证的经验包括:

- 低熵必须结合极性方向, 全成功不能和全失败都视为 rollback。
- `KUN/KUN = 0` 必须保留 discover 协议。
- halt / checkpoint / discover 必须决定 stop, 不能失败后继续。
- timeout、主权越界、patch 多哈希、manifest 索引和 ledger history 都要进入证据链。
- 负极化 rollback 与 timeout 可共享状态码, 但必须用 reason 区分。

网关需要同步这些规则, 否则易经规则只是入口 prompt, 没有贯穿运行时。

## 4. 可选方案

### 方案 A: 直接复制 OneCode `IchingKernel`

优点:

- 迁移最快。
- 规则行为与 OneCode 完全一致。

缺点:

- 会把 OneCode 的资产执行语义强行塞进网关。
- 容易形成 OneCode 专属网关, 违背产品边界。
- 网关已有 root-code / Build Mode 体系会被旁路或重复。

结论: 不推荐。

### 方案 B: 只补文档, 不改运行证据

优点:

- 风险最低。
- 不影响当前网关测试。

缺点:

- 无法让规则真正运行。
- 不能提升 Claude Code / Codex 接入时的任务可靠性。
- 会继续出现规则叙事与执行证据分离。

结论: 只能作为过渡, 不足以完成同步目标。

### 方案 C: 新增 Gateway Rule Adapter

优点:

- 保留网关现有产品结构和 root-code UX。
- 用适配层统一输出 6-bit status envelope。
- 可以逐步接入 gateway request、tool preflight、Build Mode result、stream guard 和 state persistence。
- 不需要复制 OneCode 内核, 但能继承它的规则闭合经验。

缺点:

- 需要梳理现有字段并补测试。
- 短期会同时存在 3-bit 根字和 6-bit envelope, 文档必须写清层级关系。

结论: 推荐。

## 5. 推荐架构

新增一个网关规则适配层, 命名建议:

```text
agent_skill_dictionary/gateway_rule_adapter.py
```

它不负责调用模型、不负责执行工具、不负责改写文件, 只负责把网关已有证据压缩成规则面:

```text
raw request / preflight / build-mode result / sandbox evidence
  -> Liangyi bits
  -> Sixiang windows
  -> outer + inner trigram
  -> 6-bit gateway_status_code
  -> transition action / reason
  -> dispatch decision
  -> evidence envelope
```

### 5.1 6-bit 运行信封

每个网关关键出口都应逐步携带:

```json
{
  "gateway_status_code": 63,
  "gateway_status_binary": "111111",
  "outer_trigram": "111",
  "inner_trigram": "111",
  "outer_plane": "environment",
  "inner_plane": "asset",
  "polarity_index": 1.0,
  "four_symbols": ["11", "11", "11"],
  "element_relation": "same",
  "transition_action": "cooldown",
  "transition_reason": "yang_overload_cooldown",
  "dispatch_decision": "continue",
  "evidence_required": [],
  "evidence_collected": {}
}
```

字段命名用 `gateway_` 前缀, 避免和 OneCode 的 `iching_` 字段混淆。

### 5.2 外卦与内卦映射

网关 6-bit 状态不替代 root-code, 而是运行时状态。

建议初始映射:

| 平面 | bit | 语义 | 阳 `1` | 阴 `0` |
| --- | --- | --- | --- | --- |
| 外卦 | b5 | sovereignty | auth/path/client hook 合规 | 主权越界或客户端不可控 |
| 外卦 | b4 | upstream | 上游协议/网络可用 | timeout / 502 / stream 断裂 |
| 外卦 | b3 | policy | 工具和模型参数已裁剪 | 策略缺失或发现规则空洞 |
| 内卦 | b2 | artifact | 资产或上下文证据存在 | 缺少目标证据 |
| 内卦 | b1 | execution | 写入/工具/测试执行成功 | 执行失败或被跳过 |
| 内卦 | b0 | time | timeout 内完成 | 超时挂起 |

这套映射保持 OneCode 的外部环境面 / 内部资产面结构, 但用网关自己的证据源。

### 5.3 常见状态映射

| 场景 | 状态 | 语义 |
| --- | --- | --- |
| 请求重写成功、工具裁剪成功、无需执行 | 正常稳定态, 可继续 |
| Build Mode 写入完成 | 内卦转阳, 下一步进入验证 |
| 验证通过并归档 | 高阳成功后 cooldown 到稳定交付 |
| upstream timeout | `KAN/ZHEN = 17` 类 checkpoint, stop |
| tool/preflight 主权越界 | `LI/KUN = 48` 类 halt, stop |
| 规则无法映射 | `KUN/KUN = 0`, discover, stop |
| 多步骤全成功低熵 | accept_positive_polarity, 不 rollback |
| 多步骤全失败低熵 | rollback_negative_polarity, reason 明确 |

### 5.4 与现有 root-code 的关系

root-code 是用户意图和工具权限入口:

```text
查 / 修 / 测 / 卫 / 停 / 问 / 记 / 总
```

6-bit envelope 是运行事实:

```text
outer environment + inner asset
```

两者不互相取代:

- `active_code=修` 表示本轮允许受控修改。
- `gateway_status_code=48` 表示本轮因主权火边界被熔断。
- `active_code=测` 表示本轮处于验证根字。
- `gateway_status_code=17` 表示上游或执行超时留下恢复种子。

这样可以保留一字诀产品的入口语言, 同时让运行证据进入 64 卦空间。

## 6. 分阶段落地

### Phase 1: 只读适配和证据输出

目标: 不改变网关行为, 只新增规则信封。

实现范围:

- 新增 `gateway_rule_adapter.py`。
- 给 `/v1/yizijue/resolve`、gateway rewrite metadata、preflight-tool response 添加可选 `gateway_rule`。
- Build Mode tool result compact metadata 中添加 `gateway_rule`。
- 不改变工具过滤、状态机、请求转发和执行行为。

测试:

- `查` 只读请求产生稳定 envelope。
- `停` 或高危 preflight 产生 halt/stop envelope。
- unknown / unmapped 产生 discover/stop envelope。
- 全成功聚合为 accept_positive_polarity。
- 全失败聚合为 rollback_negative_polarity 且 reason 明确。

### Phase 2: 规则信封接入状态持久化

目标: 让 session state 和 `.yizijue/build-mode-state*.json` 持久化规则信封。

实现范围:

- state file 保存 `gateway_status_code`, `transition_action`, `transition_reason`, `dispatch_decision`。
- stream tool takeover 和 non-stream tool takeover 统一写入 compact rule result。
- live smoke 输出增加 rule envelope 断言。

测试:

- 写入 -> 验证 -> 归档路径能完整追溯状态码。
- 失败 -> 纠错 -> 查 -> 修 -> 测路径能完整追溯状态码。
- session-scoped state 不串线。

### Phase 3: 规则面成为网关调度依据

目标: 让 halt/checkpoint/discover 的 dispatch 真正影响网关行为。

实现范围:

- `dispatch_decision=stop` 时禁止继续暴露执行工具。
- `checkpoint` 时返回可恢复证据, 不伪装成成功。
- `discover` 时进入人工规则补齐路径。
- 保留现有 Build Mode FSM, 但关键出口以 6-bit envelope 决定最终调度。

测试:

- 主权越界 stop。
- timeout checkpoint stop。
- discover stop。
- cooldown / accelerate / throttle continue。

## 7. 不做的事

本阶段明确不做:

- 不复制 OneCode 的 `IchingKernel` 到网关。
- 不把 OneCode 包装成 Claude Code/Codex 网关。
- 不开放任意 bash 或 pytest 执行。
- 不移除易经、阴阳、五行、64 卦叙事。
- 不把 root-code UX 改成纯数字状态码。
- 不一次性重构所有 `kernel_policy.py` 和 `trigram_contract.py` 重复内容。

## 8. 验收标准

阶段一完成时, 应满足:

- 网关不改变现有兼容行为, 旧测试继续通过。
- 每个关键网关响应都能输出规则信封。
- 规则信封能解释: 当前状态码、阴阳极性、四象、内外卦、转移动作、调度决策和证据来源。
- 全成功低熵不会被误判为 rollback。
- 全失败低熵不会被误判为成功。
- 主权越界、timeout、unknown rule 三类硬边界分别映射到 halt、checkpoint、discover。

阶段二完成时, 应满足:

- `.yizijue/build-mode-state*.json` 能持久化规则信封。
- live smoke 能证明 Claude/OpenAI/Responses 三类路径下状态信封一致。

阶段三完成时, 应满足:

- 网关调度最终由规则信封收束。
- root-code、tool guard、Build Mode FSM 和 state persistence 不再各自解释一套独立状态。

## 9. 后续实现计划入口

如果确认本设计, 下一步应写实施计划并按 TDD 落地:

1. 先为 `gateway_rule_adapter.py` 写失败测试。
2. 实现纯函数适配层。
3. 接入 resolve / rewrite / preflight metadata。
4. 接入 Build Mode result compact metadata。
5. 接入 state persistence。
6. 运行 gateway 相关单测和 smoke。

每一步都必须保持 OneCode 内核不变, 保持网关产品线独立。
