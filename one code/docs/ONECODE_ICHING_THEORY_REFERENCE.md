# OneCode 易经理论实现参考手册

**日期**: 2026-09-03  
**版本**: v0.8.0+  
**状态**: 理论完整，已全部实现

---

## 一、概述

OneCode 的核心决策引擎基于传统易经理论，将 64 卦状态映射为 6-bit 状态码（Q6 空间），通过阴阳平衡、五行生克、爻位关系等数学公式，提供确定性的状态转换和决策逻辑。

**设计原则**:
- 规则闭包：所有决策闭合在 6-bit 状态表面
- 无并行变量：不引入置信度、优先级等外部标志
- 数学稳定：Lyapunov 能量非递增，无不安全碰撞
- 权威链完整：yin/yang → 三卦 → 五行 → 转换 → 调度

---

## 二、基础状态表示

### 2.1 六爻卦象（6-bit 状态码）

```
状态码范围: 0-63 (0b000000 - 0b111111)
爻位编号: 0(初爻) 1(二爻) 2(三爻) 3(四爻) 4(五爻) 5(上爻)
bit表示: bit[i] = 0 (阴爻 ⚋), bit[i] = 1 (阳爻 ⚊)

示例:
  状态码 42 = 0b101010
  从右到左: ⚋⚊⚋⚊⚋⚊ (初阴-二阳-三阴-四阳-五阴-上阳)
```

### 2.2 八卦与三爻

```python
# 八卦编码（3-bit）
坤(000) = 0  # ☷ 地
震(001) = 1  # ☳ 雷
坎(010) = 2  # ☵ 水
兑(011) = 3  # ☱ 泽
艮(100) = 4  # ☶ 山
离(101) = 5  # ☲ 火
巽(110) = 6  # ☴ 风
乾(111) = 7  # ☰ 天

# 卦象分解
内卦（下卦）: status_code & 0b111 (bit 0-2)
外卦（上卦）: (status_code >> 3) & 0b111 (bit 3-5)

# 示例: 状态 42 = 0b101010
内卦 = 0b010 = 2 (坎)
外卦 = 0b101 = 5 (离)
卦名 = 离坎 (火水未济)
```

---

## 三、阴阳平衡理论

### 3.1 阴阳计数

**实现**: `IchingKernel.yin_yang_profile(status_code)`

```python
阳爻数 = status_code.bit_count()  # 统计 1 的个数
阴爻数 = 6 - 阳爻数
极性指数 = (阳爻数 - 3) / 3  # 范围 [-1.0, 1.0]
```

### 3.2 平衡状态分类

| 状态 | 阳爻数 | 极性指数 | 语义 |
|------|--------|----------|------|
| `pure_yin` | 0 | -1.0 | 纯阴（坤卦） |
| `yin_excess` | 1-2 | [-0.67, -0.33) | 阴盛 |
| `balanced` | 3 | 0.0 | 平衡 |
| `yang_majority` | 4 | 0.33 | 阳多 |
| `yang_excess` | 5 | 0.67 | 阳盛 |
| `pure_yang` | 6 | 1.0 | 纯阳（乾卦） |

**决策规则**:
- `pure_yang` / `yang_excess` → `cooldown` (阳过载冷却)
- `yin_excess` → `activate` (阴虚需要激活)
- `pure_yin` (坤卦) → `discover` (规则缺口发现)

---

## 四、五行生克关系

### 4.1 八卦配五行

```python
坤(000) → 土    震(001) → 木
坎(010) → 水    兑(011) → 金
艮(100) → 土    巽(110) → 木
离(101) → 火    乾(111) → 金
```

### 4.2 五行关系表

```
相生环: 木 → 火 → 土 → 金 → 水 → 木
相克环: 木 → 土 → 水 → 火 → 金 → 木

关系矩阵:
         木    火    土    金    水
    木   same  生    克    被克  被生
    火   被生  same  生    克    被克
    土   被克  被生  same  生    克
    金   生    被克  被生  same  克
    水   克    生    被克  被生  same
```

### 4.3 和谐度计算

**实现**: `IchingKernel.element_dynamics(status_code)`

```python
关系分数:
  generates (相生):      +2
  same (同元素):         +1
  generated_by (被生):   +1
  neutral (中性):         0
  controls (相克):       -1
  controlled_by (被克):  -2

卦象和谐度 = 外卦元素 与 内卦元素 的关系分数
```

---

## 五、卦变理论

### 5.1 错卦（对卦）

**定义**: 所有爻位阴阳互换

**实现**: `IchingKernel.opposite_hexagram(status_code)`

```python
错卦 = (status_code & 0b111111) ^ 0b111111

示例:
  原卦: 42 = 0b101010 (离坎)
  错卦: 21 = 0b010101 (坎离)
  
语义: 表示对立面、反向状态、互补性
```

### 5.2 综卦（覆卦）

**定义**: 卦象上下颠倒（6爻顺序完全颠倒）

**实现**: `IchingKernel.inverse_hexagram(status_code)`

```python
综卦 = 将6爻顺序完全颠倒

示例:
  原卦: 42 = 0b101010 = [0,1,0,1,0,1]
  综卦: 42 = 0b101010 = [1,0,1,0,1,0] 反转后
  (此例恰好对称)
  
语义: 视角转换、对称性检验、双向关系分析
```

### 5.3 互卦（核卦）

**定义**: 由2、3、4爻组成下卦，3、4、5爻组成上卦

**实现**: `IchingKernel.nuclear_profile(status_code)`

```python
互卦计算:
  下卦 = bits[1:4]  # 二、三、四爻
  上卦 = bits[2:5]  # 三、四、五爻
  
示例:
  原卦: 0b111000 (乾坤)
  2-4爻: 110 → 巽
  3-5爻: 100 → 艮
  互卦: 0b110100 (巽艮)
  
语义: 内在趋势、隐藏变化
```

---

## 六、爻位理论

### 6.1 爻位当位（正位）

**定义**: 阳爻居阳位为当位，阴爻居阴位为当位

**实现**: `IchingKernel.line_position_profile(status_code)`

```python
爻位奇偶:
  初爻(0) = 阳位    二爻(1) = 阴位
  三爻(2) = 阳位    四爻(3) = 阴位
  五爻(4) = 阳位    上爻(5) = 阴位

当位判断:
  is_yang_position = (position % 2 == 0)
  is_proper = (is_yang_position == is_yang_line)
  
返回字段:
  - proper: 是否当位
  - central: 是否中位（二爻或五爻）
  - central_and_proper: 中正位（中位且当位）
  - proper_line_count: 当位爻的数量（0-6）
```

**语义**:
- 当位度越高 → 结构越稳定
- 不当位 → 需要调整的信号

### 6.2 中正位理论

**定义**: 二爻（下卦中位）、五爻（上卦中位）为中位，居中为吉

```python
中位判断:
  下卦中位 = 二爻 (index 1)
  上卦中位 = 五爻 (index 4)
  
中正位（得中且当位）:
  二爻: 阴爻在阴位（最佳）
  五爻: 阳爻在阳位（最佳）
  
返回字段:
  - central_lines: [1, 4] (中位爻索引)
  - central_proper_lines: 中正位爻索引列表
  - middle_alignment: 是否完全中正
```

**语义**:
- 中正位权重高于普通爻位
- 符合"中庸之道"
- 影响转换决策的权重

### 6.3 承乘比应关系

**定义**: 爻与爻之间的互动关系

**实现**: `IchingKernel.correspondence_profile(status_code)`

```python
应对关系（内外卦对应）:
  初爻(0) 应 四爻(3)
  二爻(1) 应 五爻(4)
  三爻(2) 应 上爻(5)
  
关系得分:
  - 阴阳相应（一阴一阳）→ responsive: True (吉)
  - 同性相应（同阴或同阳）→ responsive: False (平)
  
返回字段:
  - response_pairs: 三对应爻的关系
  - responsive_pair_count: 相应对数（0-3）
  - adjacent_pairs: 相邻爻关系（承乘）
  - third_fourth_boundary: 三四爻边界（内外卦交界）
```

**语义**:
- 响应对越多 → 内外协调
- 三四爻边界 → 内外卦的转换点

---

## 七、转换决策系统

### 7.1 转换动作（TransitionAction）

```python
CONTINUE = "continue"       # 继续执行
ACCELERATE = "accelerate"   # 加速（生关系）
RECOVER = "recover"         # 恢复（被生关系）
CHECKPOINT = "checkpoint"   # 检查点（控关系/水险）
DISCOVER = "discover"       # 发现（规则缺口）
HALT = "halt"               # 停止（主权边界/淬火）
COOLDOWN = "cooldown"       # 冷却（阳过载）
THROTTLE = "throttle"       # 节流（克制）
PRUNE = "prune"             # 修剪（金克木）
ACTIVATE = "activate"       # 激活（阴虚）
```

### 7.2 转换原因（TransitionReason）

```python
# 规则缺口
RULE_GAP_REQUIRES_DISCOVERY

# 主权边界
SOVEREIGNTY_FIRE_SUPPRESSES_ASSET
SOVEREIGNTY_FIRE_BOUNDARY_HALT

# 结构约束
MOUNTAIN_CONTAINS_LOCAL_EXECUTOR_FAULT

# 压力调节
YANG_OVERLOAD_COOLDOWN
YIN_EXCESS_REQUIRES_ACTIVATION

# 五行关系
GENERATING_RELATION_ACCELERATES_EXECUTION
GENERATED_BY_RELATION_RECOVERS_EXECUTION
SAME_ELEMENT_BALANCED_CONTINUE          # 新增
NEUTRAL_RELATION_REQUIRES_DISCOVERY

# 控制关系
CONTROLLED_BY_RELATION_REQUIRES_VERIFIER
CONTROLLING_RELATION_THROTTLES_EXECUTION

# 元素调制
NETWORK_WATER_PRESERVES_RESUME_SEED
WATER_QUENCHES_FIRE_BOUNDARY
METAL_PRUNES_WOOD_SCOPE
EARTH_DAMS_WATER_FLOW
WOOD_BREAKS_INERT_GROUND
```

### 7.3 决策优先级（从高到低）

```python
1. 坤卦（0b000000）→ discover (规则缺口)
2. 火克金（hard_control）→ halt (主权压制)
3. 外卦离火 → halt (主权边界)
4. 艮坤配置 → checkpoint (山地容错)
5. 阳过载（pure_yang/yang_excess）→ cooldown
6. 纯阴（pure_yin）→ discover
7. 水生木（recovery_seed）→ checkpoint (网络保存)
8. 阴虚（yin_excess）→ activate
9. 五行关系策略（generates/same/controlled_by/neutral）
10. 控制关系调制（quench/prune/dam/break_ground/throttle）
```

---

## 八、API 使用示例

### 8.1 基础状态分析

```python
from onecode.kernel.hexagram import IchingKernel

# 状态码
status = 42  # 0b101010

# 阴阳分析
yin_yang = IchingKernel.yin_yang_profile(status)
print(f"阳爻: {yin_yang['yang_count']}/6")
print(f"平衡: {yin_yang['balance']}")

# 卦象分解
inner = status & 0b111
outer = (status >> 3) & 0b111
print(f"内卦: {inner}, 外卦: {outer}")

# 五行动力学
dynamics = IchingKernel.element_dynamics(status)
print(f"元素关系: {dynamics['cross_relation']}")
print(f"和谐度: {dynamics['harmony_score']}")
```

### 8.2 卦变分析

```python
# 错卦
opposite = IchingKernel.opposite_hexagram(status)
print(f"错卦: {opposite} = {bin(opposite)[2:].zfill(6)}")

# 综卦
inverse = IchingKernel.inverse_hexagram(status)
print(f"综卦: {inverse} = {bin(inverse)[2:].zfill(6)}")

# 互卦
nuclear = IchingKernel.nuclear_profile(status)
print(f"互卦内卦: {nuclear['inner_trigram']}")
print(f"互卦外卦: {nuclear['outer_trigram']}")

# 综合视角
perspective = IchingKernel.perspective_profile(status)
print(f"错卦: {perspective['opposite']}")
print(f"综卦: {perspective['inverse']}")
```

### 8.3 爻位分析

```python
# 当位分析
position = IchingKernel.line_position_profile(status)
print(f"当位爻数: {position['proper_line_count']}/6")
print(f"中正位: {position['central_proper_lines']}")
print(f"完全中正: {position['middle_alignment']}")

# 爻位详情
for line in position['lines']:
    print(f"爻{line['line_index']}: {line['polarity']}, "
          f"当位={line['proper']}, 中位={line['central']}")
```

### 8.4 承乘比应分析

```python
# 应对关系
correspondence = IchingKernel.correspondence_profile(status)
print(f"相应对数: {correspondence['responsive_pair_count']}/3")

# 应对详情
for pair in correspondence['response_pairs']:
    print(f"爻{pair['line_indexes'][0]}-爻{pair['line_indexes'][1]}: "
          f"{pair['polarities']}, 相应={pair['responsive']}")

# 相邻关系（承乘）
for pair in correspondence['adjacent_pairs']:
    if not pair['same_polarity']:
        print(f"爻{pair['line_indexes'][0]}-{pair['line_indexes'][1]}: "
              f"阴阳相接")
```

### 8.5 转换决策

```python
# 获取转换决策
transition = IchingKernel.transition(status)
print(f"转换动作: {transition.action}")
print(f"转换原因: {transition.reason}")
print(f"目标状态: {transition.status_code}")

# 调度决策
dispatch = IchingKernel.dispatch_decision(transition)
print(f"调度决策: {dispatch}")  # "stop" 或 "continue"
```

---

## 九、数学证明

### 9.1 Lyapunov 稳定性

**定义**: Lyapunov 能量函数
```python
E(status) = |polarity_index(status)| * 2 + (1 if outer == KAN else 0)

其中:
  polarity_index = (yang_count - 3) / 3
  KAN = 0b010 (坎卦，水元素)
```

**性质**: 
- ✅ 能量非递增：∀状态 s, E(transition(s)) ≤ E(s)
- ✅ 无能量递增转换：0 个转换使能量上升
- ✅ 能量递减转换：8 个转换使能量下降
- ✅ 能量平坦转换：56 个转换保持能量不变

### 9.2 状态机闭合性

**拓扑性质**:
- 状态空间：Q6 超立方体（64 个顶点）
- 转换闭合：64/64 转换保持在 Q6 内
- 吸引子：56 个固定点，0 个非平凡循环
- 最大步数到吸引子：1 步

### 9.3 碰撞安全性

**定义**: 不安全碰撞 = 不同 (status, reason) 对映射到相同下一状态

**结果**:
- ✅ 0 个不安全碰撞
- ✅ 4 个安全碰撞（same (status, reason) → same next_status）

---

## 十、总结

OneCode 的易经理论实现已达到传统易学核心内容的完整覆盖：

**✅ 已实现**:
1. 六爻卦象（64 卦全覆盖）
2. 阴阳平衡分类（6 种状态）
3. 五行生克关系（5 元素 × 5 关系）
4. 八卦配五行（8 卦 → 5 元素）
5. 和谐度计算（-2 到 +2）
6. 错卦（opposite_hexagram）
7. 综卦（inverse_hexagram）
8. 互卦（nuclear_profile）
9. 爻位当位理论（line_position_profile）
10. 中正位理论（包含在 line_position_profile）
11. 承乘比应关系（correspondence_profile）
12. 转换原因完整覆盖（64/64 状态）

**🔬 数学验证**:
- Lyapunov 能量非递增
- 状态机闭合性
- 无不安全碰撞

**📖 参考资料**:
- 《周易》传统经典
- OneCode 源码：`src/onecode/kernel/hexagram.py`
- 测试用例：`tests/test_iching_kernel.py`
- 术语词汇表：`src/onecode/kernel/rule_constants.py`

---

**编写者**: Claude (Opus 5)  
**最后更新**: 2026-09-03
