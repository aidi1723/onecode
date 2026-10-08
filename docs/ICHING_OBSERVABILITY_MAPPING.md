# OneCode 易经观测映射与开发手册
# I-Ching Observability Mapping & Development Guide

**版本**: v0.8.0
**更新日期**: 2026-10-08

## 1. 架构红线声明 (The Architectural Red Line)

> [!CAUTION]
> **观测隔离红线**：
> 本文列出的所有高级卦象计算（包括动爻、十二消息卦、承乘比应、大衍比例、互卦和交卦）的返回值**只能且必须只进入 Evidence 或 Trace 日志**，作为纯粹的观测指标（Observability / Telemetry）。
> 
> `sandbox.py`、`verifier.py`、`execution_engine.py` 和 `runner.py` 的内部核心控制流分支**绝对不可**读取这些高级观测指标。系统绝不能因为偏离大衍基线、或者互卦陷入震荡，而去改写执行计划、改变回滚决策或触发系统停机。

---

## 2. 易经数学公式与软件工程映射

### 2.1 动爻 (Moving Lines)

**数学定义**：
动爻表示两个状态码（上一状态与当前状态）之间的按位差异。计算两卦的异或（XOR），结果为 1 的位即为动爻。
- `moving_lines(base, current) = [i for i in range(6) if ((base XOR current) >> i) & 1]`

**软件工程层面 (Current Implementation)**：
- 严格反映在相邻两次状态更迭时，底层 6-bit 状态码发生翻转的具体位置。
- 作为 Trace 中的客观比对记录。

### 2.2 承乘比应 (Micro Relations / Cheng, Sheng, Bi, Ying)

**数学定义**：
基于六爻中相邻和对应位置的关系（$b_0$ 为初爻，自下而上计算）：
- **承 (Sheng)**：下阴上阳（$b_i=0, b_{i+1}=1$），记录为 `sheng`。
- **乘 (Cheng)**：下阳上阴（$b_i=1, b_{i+1}=0$），记录为 `cheng`。
- **比 (Bi)**：相邻同性（$b_i = b_{i+1}$）。
- **应 (Ying)**：内外卦对应爻极性相异（$b_i \neq b_{i+3}$ 对于 $i \in \{0, 1, 2\}$）。

**软件工程层面 (Current Implementation)**：
- 纯粹是对当前所处六位状态码内部结构关系的数据提取，直接由 `micro_relations` 计算并写入观测指标。

### 2.3 十二消息卦 (12 Sovereign / Tidal Hexagrams)

**数学定义**：
代表阴阳消长的十二个标准状态，按周期循环：
`["复", "临", "泰", "大壮", "夬", "乾", "姤", "遁", "否", "观", "剥", "坤"]`
- `cycle_phase(count) = SOVEREIGN_HEXAGRAMS[count % 12]`

**软件工程层面 (Current Implementation)**：
- 仅作为基于 `cycle_count`（循环次数）对 12 求模的客观计数器阶段标志。不涉及对实际系统负载高低的评估。

### 2.4 大衍比例 (Da Yan Proportions & 25% Baseline)

**数学定义**：
大衍之数生成的四象理论概率：
- 老阳（动）：3/16 (18.75%)
- 老阴（动）：1/16 (6.25%)
- 动爻总比例基线（Volatility Baseline）：**25%**

**软件工程层面 (Current Implementation)**：
- 作为理论对照基线存在于文档与日志比对中。
- **牢记红线**：即便运行日志中的状态翻转比例发生严重偏离，此指标仅作事后 Trace 观测对照，绝对不可直接阻断执行流程。

### 2.5 互卦 (Hu Gua / Mutual Hexagrams)

**数学定义**：
提取原卦内部蕴含的深层结构。丢弃初爻（$b_0$）和上爻（$b_5$）。
- 新内卦：$b_1, b_2, b_3$
- 新外卦：$b_2, b_3, b_4$
- 互卦生成定理：最多经过 2 次迭代，互卦必定落入以下数学吸引子：
  - 纯态吸引子：`{坤 0, 乾 63}`
  - 2-循环震荡吸引子：`{既济 21 ↔ 未济 42}`

**软件工程层面 (Current Implementation)**：
- 仅作为卦象状态记录。
- **警告**：不要把互卦陷入 `{既济 21 ↔ 未济 42}` 的 2-循环误判为业务逻辑死锁（Deadlock）。这是一个自然数学吸引子，属于正常规律。

### 2.6 交卦 (Jiao Gua / Intersecting Hexagrams)

**数学定义**：
内外卦位置互换。
- 原卦：$T_{out} \text{ over } T_{in}$
- 交卦：$T_{in} \text{ over } T_{out}$

**软件工程层面 (Current Implementation)**：
- 通过 `exchange_hexagram`（或类似交换逻辑）生成，仅写入卦象记录。
- 提供了一种不中断网络的“思想实验”逃生通道日志用于事后分析，不在冲突时实时改变计划。

---

## 3. 观测系统的最佳实践

为了维护 OneCode 的健壮性，请开发者在贡献代码时遵循以下准则：

1. **分离观测与控制**：始终将上述易经运算置于 `IchingProfileMixin` 或专属的记录侧，作为 Evidence 或 Trace 日志写入，确保不越权干涉主控循环（如 `run_model_task`）。
2. **不做解码先验**：不要将这些复杂的数学规律作为 LLM 结构化输出解码（如 Yizijue Logits）的先验惩罚。解码层只看合法性和基本的安全性，严禁引入互卦、大衍比例等深层逻辑进行剪枝。
3. **不做停机判定**：绝不能因为实际比例偏离大衍基线等原因而主动触发系统停机（Halt）。
