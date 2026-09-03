## 一字诀/大字典项目评估

**项目目标**：构建 AI Agent 的确定性中间层，将自然语言归一化为单字执行指令（如查/修/测/卫/停/问/记/总），每个字绑定固定权限、工作流、验证规则和熔断策略，通过网关层规训请求后再转发上游模型。

**核心模块**：
- **词典层**：22 个执行字 JSON 词典，含专业协议、参考工作流、继承策略
- **8 根字 Opcode**：查(离/只读)、修(震/受限写)、测(巽/验证)、卫(坎/安全)、停(艮/熔断)、问(兑/人工)、记(坤/归档)、总(乾/收束)
- **内核策略层**：工具白名单过滤、温度锁定、证据链要求
- **FSM 框架**：Compiler 归一化 → OneWordAgent 执行 → MutationEngine 状态转移
- **网关层**：OpenAI-compatible `/v1/chat/completions`、preflight 工具守卫、Macro Chain 闭环编译

**主要风险**：
- 概念过载：八卦、阴阳、Trigram 等隐喻增加认知负担
- 归一化层当前为关键词匹配，准确性有限
- 真实 LLM 执行仍为测试桩，未接入生产推理
- 物理阻断依赖外部 Agent 主动调用 preflight，无强制力
- 缺失 streaming、Anthropic adapter、审计落盘等生产必需功能

**下一步建议**：
1. 替换关键词归一化为轻量分类模型，提升意图识别准度
2. 接入真实 LLM executor，替换测试桩
3. 补齐生产缺口：SSE streaming、审计日志独立落盘、词典热加载
4. 开发 Claude Code Anthropic-compatible adapter
5. 推动工具执行层强制接入 preflight，实现真物理阻断
