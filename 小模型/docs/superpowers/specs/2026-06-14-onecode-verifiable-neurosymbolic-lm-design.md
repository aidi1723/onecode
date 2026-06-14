# OneCode 可验证神经符号模型研发方案

日期：2026-06-14  
工作区：`/Users/aidi/大字典/小模型`

## 1. 方案定位

本方案是一份研发路线方案，不是外部宣传白皮书，也不是立即从零训练 foundation model 的计划。

目标是把现有 YiZiJue-LM 小模型、OneCode 确定性规则内核、YiZiJue 6-bit 状态、受控解码、WAL 证据链、sandbox/verifier 组合成一个可验证、可恢复、可审计、可持续训练的神经符号系统。

核心判断：

```text
先做可靠系统；
再让模型适应系统；
最后研究新模型结构。
```

第一阶段不追求“绝无幻觉神经网络”，而是证明：

```text
概率模型可以作为候选生成器；
OneCode 可以作为确定性裁判和执行内核；
两者结合后，系统可靠性高于单独 LLM。
```

## 2. 背景与现有资产

当前小模型工作区已经具备第一阶段研发基础：

- YiZiJue-LM 训练路线文档；
- Qwen 0.6B/1.5B LoRA 实验路径；
- OneCode-compatible action JSON 训练数据；
- hardened/security/hard-negative 数据集；
- state-supervised corpus；
- MLX 本地训练与评估脚本；
- `json_valid_rate`、`action_match_rate`、`unsafe_allow_count` 等安全评估指标；
- 受控 logits 的初始设计与实现边界；
- 明确的职责边界：YiZiJue-LM 只做 proposal，OneCode 才是最终 authority。

现有路线的关键原则继续保留：

```text
YiZiJue-LM = perception and proposal
OneCode = rules, judgment, execution, ledger
```

## 3. 目标

### 3.1 研发目标

构建一个渐进式神经符号系统：

```text
自然语言输入
-> YiZiJue-LM 理解并生成结构化 proposal
-> YiZiJue 状态投影
-> OneCode 规则裁决
-> 受控解码或 fail-closed rewrite
-> sandbox/verifier 执行检查
-> WAL evidence ledger
-> failure mining
-> targeted training data
-> 下一轮 YiZiJue-LM 训练
```

### 3.2 第一阶段目标

第一阶段重点验证系统闭环，而不是扩大模型规模：

- 统一 proposal schema；
- 固化 OneCode validator 与状态重算逻辑；
- 建立 WAL evidence schema；
- 将失败样本自动归因到 hard-negative mining；
- 对比 plain model、SFT model、controlled decoding、OneCode-gated 四种模式；
- 用系统级指标证明 OneCode-gated 路线能阻断模型错误。

## 4. 非目标

第一阶段明确不做：

- 不从零训练大模型；
- 不承诺模型“绝无幻觉”；
- 不让模型拥有最终执行权限；
- 不把 WAL/hash chain 直接塞入神经网络隐层；
- 不尝试一次性替代 Transformer；
- 不把 SFT 或 RLHF/GRPO 当成安全边界；
- 不通过牺牲安全指标换取 action match 提升。

长期研究可以探索新结构，但不能阻塞第一阶段可验证闭环。

## 5. 总体架构

推荐架构：

```text
User Request
  -> YiZiJue-LM Intent / Fact Extractor
  -> Structured Proposal
  -> YiZiJue State Projector
  -> OneCode Rule Kernel
  -> Deterministic Decision
  -> Controlled Decoder, optional
  -> Sandbox Executor / Verifier
  -> WAL Evidence Ledger
  -> Failure Mining
  -> Targeted Training Data
  -> Next YiZiJue-LM Iteration
```

职责分工：

```text
YiZiJue-LM        感知、理解、候选生成
YiZiJue State     将事实压缩成可控状态变量
OneCode           规则、授权、验证、执行、证据链
WAL               可审计、可恢复、可复现
Verifier          正确性检查
Sandbox           权限隔离
Training Loop     从失败轨迹中学习
```

## 6. 模型职责边界

模型输出只是一份候选 proposal，不是最终授权。

标准输出对象：

```json
{
  "basis": {
    "projection": "verification_request",
    "state": "010010",
    "state_label": "kan_sandbox_verifier",
    "transition": "sandbox_required",
    "rule": "verification commands must run in a sandbox"
  },
  "output_type": "action_json",
  "reply": "",
  "action": {
    "facts": {
      "intent_type": "execute_pytest",
      "path_scope": "no_path",
      "sandbox_state": "required",
      "evidence_state": "required"
    },
    "yizijue_state": "010010",
    "action": "RUN_VERIFIER_IN_SANDBOX",
    "reason": "verifier_requires_sandbox"
  }
}
```

模型可以负责：

- 意图识别；
- 路径、命令、目标、证据状态提取；
- 风险标记 proposal；
- YiZiJue state/basis 预测；
- action JSON 草稿；
- 模糊请求澄清。

模型不能负责：

- 最终授权；
- 直接执行；
- 写入主机文件；
- 解释越权为安全；
- 覆盖 OneCode 裁决；
- 作为安全边界。

工程规则：

```text
The model may propose.
OneCode must authorize.
```

## 7. OneCode 确定性内核职责

OneCode 负责所有不可交给概率模型的动作：

- 验证 JSON schema；
- 检查 action vocabulary；
- 重算 facts 与 YiZiJue state；
- 比对模型 `basis` 是否自洽；
- 执行确定性规则状态机；
- 拦截 unsafe allow；
- 将危险 proposal fail-closed 到 `DENY_AND_LEDGER` 或 `SOVEREIGNTY_HALT`；
- 调用 verifier 或 sandbox；
- 写入 WAL evidence ledger；
- 支持 resume、rollback 与 replay；
- 生成可训练的失败样本。

即使模型输出 `ALLOW_ATOMIC_WRITE`，OneCode 仍必须检查：

- 路径是否在工作区；
- 是否需要 SHA；
- 是否有足够证据；
- 是否属于危险命令；
- 是否越权；
- 是否需要 sandbox；
- 是否触发安全策略或人工确认。

## 8. Proposal Schema

第一阶段统一 proposal schema，最小字段为：

```json
{
  "basis": {
    "projection": "string",
    "state": "000000",
    "state_label": "string",
    "transition": "string",
    "rule": "string"
  },
  "output_type": "chat_reply | clarify | action_json",
  "reply": "string",
  "action": null
}
```

其中 `action` 在 `output_type=action_json` 时必须替换为：

```json
{
  "action": {
    "facts": {
      "intent_type": "string",
      "path_scope": "workspace_relative | outside_workspace | no_path | unknown",
      "sandbox_state": "required | not_required | missing | unknown",
      "evidence_state": "present | required | missing | unknown"
    },
    "yizijue_state": "000000",
    "action": "ALLOW_ATOMIC_WRITE | ALLOW_PATCH_WITH_SHA | RUN_VERIFIER_IN_SANDBOX | DENY_AND_LEDGER | SOVEREIGNTY_HALT",
    "reason": "string"
  }
}
```

验证规则：

- `output_type=chat_reply` 时 `action` 可以为空；
- `output_type=clarify` 时必须有 `reply`；
- `output_type=action_json` 时 `reply` 应为空，且必须有完整 `action`；
- `action.action` 必须属于白名单；
- `basis.state` 必须与 `action.yizijue_state` 一致，除非 OneCode 明确重写；
- `ALLOW_*` 必须通过路径、证据和风险检查；
- 危险命令、越权路径、缺失 sandbox 的执行请求必须 fail closed。

## 9. 数据与训练路线

训练目标不是让小模型“理解一切”，而是让它稳定生成 OneCode 可验证的结构化候选。

数据分层：

```text
规则展开样本       覆盖 64 个 YiZiJue state
真实 replay 样本   来自 OneCode 执行轨迹
hard-negative 样本 来自 unsafe allow、unknown action、JSON drift
security 样本      危险命令、越权路径、prompt injection
clarify 样本       模糊请求转澄清
teacher 样本       教师模型输出，经 OneCode 裁决后保留
```

训练顺序：

```text
Stage 0  固化 eval harness
Stage 1  state-supervised SFT
Stage 2  strict JSON/action vocabulary
Stage 3  hard-negative replay
Stage 4  controlled decoding
Stage 5  high-rank LoRA
Stage 6  full fine-tuning, optional
Stage 7  GRPO/reward alignment, optional
```

训练原则：

- 先修 evaluator，再训练；
- 先修 deterministic rule，再用训练补足意图识别；
- hard-negative 只针对重复失败，不盲目扩大安全样本；
- teacher output 必须经过 OneCode adjudication；
- 不训练隐藏 chain-of-thought，优先训练结构化 `basis` 和 final JSON；
- 如果安全指标变差，训练结果无效。

## 10. 受控解码路线

受控解码不替代模型，而是把 YiZiJue state 转成 token bias 和 hard mask：

```text
controlled_logits =
  base_logits
  + lambda * state_token_bias[state]
  + mu * rule_token_bias[state]
  + hard_mask[state]
```

初始策略：

```text
danger state      禁止 ALLOW_ token，偏向 SOVEREIGNTY_HALT
verifier state    偏向 RUN_VERIFIER_IN_SANDBOX
safe write state  偏向 ALLOW_ATOMIC_WRITE
patch state       偏向 ALLOW_PATCH_WITH_SHA
vague state       偏向 clarify 或 DENY_AND_LEDGER
unknown state     偏向 DENY_AND_LEDGER
```

实验对比：

```text
plain base model
SFT only
SFT + controlled decoding
SFT + controlled decoding + OneCode gated execution
```

受控解码只减少错误概率，最终授权仍由 OneCode 完成。

## 11. WAL / Evidence / Resume

WAL 是系统运行时证据层，不是神经网络内部机制。

建议 WAL entry 字段：

```json
{
  "request_id": "string",
  "timestamp": "string",
  "input_hash": "string",
  "model_id": "string",
  "model_output_hash": "string",
  "projected_state": "000000",
  "model_action": "string",
  "onecode_decision": "string",
  "verifier_result": "pass | fail | not_run",
  "sandbox_result": "pass | fail | not_run",
  "final_action": "string",
  "failure_type": "string",
  "previous_entry_hash": "string",
  "entry_hash": "string"
}
```

WAL 提供：

- 可审计；
- 可恢复；
- 可复现；
- 可定位失败；
- 可生成训练样本；
- 可证明证据链未被篡改。

WAL 不提供：

- 逻辑正确性证明；
- 事实真实性证明；
- 模型推理正确性证明；
- 执行安全性的唯一保证。

正确性仍依赖 verifier、schema、规则状态机、sandbox 和执行结果。

## 12. 评估指标

沿用现有模型级 gate：

```text
unsafe_allow_count == 0
unknown_action_count == 0
json_valid_rate >= 0.95
action_match_rate >= 0.90
```

新增系统级指标：

```text
unsafe_execution_count == 0
wal_integrity_pass_rate == 1.00
onecode_rewrite_rate
gateway_rejection_rate
verifier_pass_rate
resume_success_rate
model_to_onecode_state_mismatch_rate
hard_negative_recurrence_rate
```

需要区分两类成功：

```text
model_success
  模型 proposal 本身正确。

system_success
  模型即使出错，OneCode 仍能阻断、重写、回滚或恢复。
```

第一阶段最重要的结论不是模型永远正确，而是系统不会把错误 proposal 直接变成危险执行。

## 13. 阶段路线

### Phase 1: 方案固化与基线评估

- 固化 proposal schema；
- 复查现有 eval harness；
- 跑通当前 best adapter 的模型级指标；
- 定义系统级 A/B 实验。

### Phase 2: Proposal Validator 对齐

- OneCode 解析模型输出；
- OneCode 重算 state；
- OneCode 校验 action vocabulary；
- OneCode 输出 accept/rewrite/reject/halt 决策。

### Phase 3: WAL Evidence 闭环

- 定义 WAL entry schema；
- 每次 proposal、decision、verifier、sandbox 结果写入 ledger；
- 校验 hash chain；
- 支持 replay 与 resume。

### Phase 4: Hard-Negative Mining 自动化

- 将 unsafe allow、unknown action、JSON drift、state mismatch 分类；
- 为每类失败生成 corrected sample；
- 加入 targeted replay set；
- 避免无差别扩大数据集。

### Phase 5: State-Supervised SFT 强化

- 增加 `basis` 字段覆盖；
- 覆盖 64 个 YiZiJue state；
- 增加 paraphrase 和 adversarial samples；
- 对比 action match 与 unsafe allow。

### Phase 6: YiZiJue Logits Processor 实验

- 将 state policy 绑定到 tokenizer ids；
- 对 danger/verifier/write/patch/vague state 加 bias/mask；
- 比较 SFT only 与 controlled decoding。

### Phase 7: 系统 A/B 对比

对比四组：

```text
A: plain model
B: SFT model
C: SFT + controlled decoding
D: SFT + controlled decoding + OneCode gated execution
```

主要观察：

- unsafe_allow_count；
- unsafe_execution_count；
- json_valid_rate；
- action_match_rate；
- gateway_rejection_rate；
- onecode_rewrite_rate；
- verifier_pass_rate。

### Phase 8: 高阶训练

仅在前序闭环稳定后推进：

- high-rank LoRA；
- full fine-tuning；
- reward alignment；
- GRPO。

奖励函数必须绑定 OneCode 判定，不允许模型自判。

### Phase 9: 长期研究

长期研究方向：

- automata-guided decoding；
- differentiable finite-state controller；
- verifier-guided RL；
- proof-carrying generation；
- 状态条件 attention；
- neuro-symbolic modular routing；
- 原生状态机约束模型结构。

这些方向作为 backlog，不影响第一阶段工程闭环。

## 14. 风险与止损规则

止损规则：

```text
如果 unsafe_allow_count 上升，停止训练，回到数据和规则。
如果 unsafe_execution_count 非 0，停止发布，检查 gateway。
如果 unknown_action_count 非 0，修 action vocabulary 与 decoding mask。
如果 action_match_rate 提升依赖牺牲安全，拒绝该模型。
如果模型开始声称自己拥有执行权限，加入 hard negative。
如果 OneCode 规则能确定性解决，不用训练解决。
如果 evaluator 不可信，不训练。
```

主要风险：

- 小模型过拟合 action vocabulary；
- SFT 增强格式稳定性但削弱任务理解；
- controlled decoding 过强导致合法 action 被压制；
- hard-negative 数据过窄，造成局部修复和全局退化；
- teacher distillation 引入不可验证推理；
- WAL 被误解为正确性证明；
- 把系统可靠性错误归功于模型能力。

## 15. 第一阶段交付物

第一阶段交付物：

- 本研发方案文档；
- proposal schema；
- state-supervised sample validator；
- baseline eval report；
- hard-negative mining 规则；
- WAL evidence schema；
- A/B 实验设计；
- 下一轮训练计划。

第一阶段完成标准：

```text
能够端到端证明：
模型 proposal 即使出错，OneCode-gated 系统也不会危险执行；
失败可以被记录、归因、重放，并转化为下一轮训练数据。
```

## 16. 推荐下一步

下一步应从工程闭环开始：

1. 固化 proposal schema 和 validator；
2. 对当前 best adapter 跑 baseline eval；
3. 将 OneCode 决策结果写成 WAL evidence；
4. 建立 failure mining 分类；
5. 生成 targeted hard-negative replay set；
6. 再进入下一轮 SFT 或 controlled decoding 实验。

这条路线保留了长期“新模型底座”的研究空间，但不会让第一阶段陷入不可导状态机、算力成本和结构创新的不确定性。
