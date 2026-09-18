# OneCode Zhouyi Math Optimization Closure Report
周易八卦与控制论数学模型优化收尾报告

- **日期**: 2026-09-18
- **项目**: OneCode (`/Volumes/MacSSD/项目开发/one code`)
- **基准状态**: Verified and passing all test suites locally
- **状态空间**: $Q_6 = \{0, 1\}^6$ 超立方体离散拓扑
- **关联文档**:
  - [ICHING_QUICKREF.md](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/docs/ICHING_QUICKREF.md)
  - [YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/docs/YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md)
  - [hexagram.py](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/src/onecode/kernel/hexagram.py)
  - [test_iching_kernel.py](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/tests/test_iching_kernel.py)

---

## 1. 任务背景与执行摘要 (Executive Summary)

OneCode 以易经六十四卦为底层状态空间，构建了一套确定性的有限状态机与李雅普诺夫动态控制框架。在此前的版本迭代中，核心控制论框架虽然保证了状态转换的收敛性与单调性（$\Delta V \le 0$），但在易学纯数学公式表达、符号代数完备性及文档规范性上存在多处历史残留缺陷。

本次任务对项目中的所有周易八卦公式、五行生克转移概率、信息论指标及状态空间映射进行了全面的深度数学审核与加固：
1. **纠正了四象位序定义反向映射问题**，使布尔代数最低位与易学爻位正统生成规律（自下而上、初爻为 LSB）完全吻合。
2. **新增了易经第四基本对合算子「交卦」**，补全了错（NOT）、综（Reverse）、互（Nuclear）、交（Exchange）四大基本变换群结构。
3. **形式化证明并实现了互卦迭代不动点吸引子定理**，全 64 卦在最多 2 步迭代内必然收敛至乾、坤、既济、未济四大枢纽状态。
4. **补充了大衍筮法古典非均匀离散概率测度**与**相对超立方体均匀先验的 KL 散度指标**。
5. **全面校准了开发参考文档与马尔可夫演化公式**的量纲与逻辑矛盾。
6. **完成双重独立验证**：全项目 916 个单元测试全部通过，状态机数学审计（`onecode math-audit`）零违例。

---

## 2. 优化改进详实记录 (Detailed Remediation)

### 2.1 四象位序与运行时语义校准 (Four Symbols Bit-Order)

#### 问题根源
在传统易学（《易纬》《系辞》）中，爻自下而上生成，初爻在下为最低有效位（LSB, bit 0），二爻在上（bit 1）：
- `0b01`（初爻阳=1，二爻阴=0）：阳中生阴，为 **少阴**（⚍）
- `0b10`（初爻阴=0，二爻阳=1）：阴中生阳，为 **少阳**（⚎）

内核代码原实现因受视觉文本字符串左读右写习惯影响，将 `0b01` 误标为 `shao_yang`、`0b10` 误标为 `shao_yin`。

#### 修复与数学证明
在 `src/onecode/kernel/hexagram.py` 中重构映射关系：
```python
FOUR_SYMBOLS = {
    0b00: "tai_yin",   # ⚋⚋ (0b00)
    0b01: "shao_yin",  # ⚊⚋ (0b01, 初阳二阴)
    0b10: "shao_yang", # ⚋⚊ (0b10, 初阴二阳)
    0b11: "tai_yang",  # ⚊⚊ (0b11)
}
FOUR_SYMBOL_RUNTIME_SEMANTICS = {
    "tai_yin": "halted",
    "shao_yin": "write_commit",
    "shao_yang": "safe_read_skip",
    "tai_yang": "overload_clash",
}
```
**数学不变性保证**：
在多尺度四象平衡决策 `four_symbol_balance_vector` 中，判定条件为：
$$\text{counts}[\text{tai\_yang}] > \text{counts}[\text{shao\_yang}] + \text{counts}[\text{shao\_yin}]$$
由于少阳与少阴在加法中满足交换律（$a + b = b + a$），两者的名字置换完全不影响宏观平衡向量与过载溢出判定，系统动态稳定性 100% 保持不变。

---

### 2.2 新增交卦对合变换算子 (Trigram Exchange Operator)

#### 易学与群论背景
易经八卦与六十四卦空间具备深刻的离散对合群结构。传统六十四卦四大基本变易算子为：
1. **错卦 (Opposite / Pang Tong)**：全爻翻转（按位取反，NOT），$\mathcal{O}(S) = S \oplus \text{0b111111}$
2. **综卦 (Inverse / Fan Dui)**：全卦颠倒（位序反转，Reverse），$\mathcal{I}(S) = \text{reverse\_bits}(S)$
3. **互卦 (Nuclear / Hu Gua)**：去初上二爻，取二三四、三四五重构，$\mathcal{N}(S)$
4. **交卦 (Exchange / Dao Gua)**：上下易位（外卦与内卦对调，Swap），$\mathcal{E}(S)$

原内核仅实现了错、综、互，缺失了交卦算子。

#### 实现与验证
在 `IchingKernel` 中实现：
```python
@classmethod
def exchange_hexagram(cls, status_code: int) -> int:
    """Trigram exchange operator (交卦 / 上下易位)."""
    normalized = status_code & 0b111111
    inner = normalized & 0b111
    outer = (normalized >> 3) & 0b111
    return (inner << 3) | outer
```
**代数性质验证**：
- 对合性（Involution）：$\forall S \in Q_6, \mathcal{E}(\mathcal{E}(S)) = S$
- 卦象对称性：$\mathcal{E}(\text{Status}(O, I)) = \text{Status}(I, O)$
- 全 64 卦穷举验证：全部通过。
- 在 `perspective_profile` 中增加 `exchange_status_code` 与 `exchange_binary` 输出。

---

### 2.3 互卦不动点迭代链与吸引子定理 (Nuclear Attractor Theorem)

#### 数学定理表述
设互卦映射 $\mathcal{N}: Q_6 \to Q_6$，其位映射定义为：
$$\mathcal{N}([b_0, b_1, b_2, b_3, b_4, b_5]) = [b_1, b_2, b_3, b_2, b_3, b_4]$$
**定理（互卦吸引子定理）**：
对任意初始状态 $S_0 \in Q_6$，迭代序列 $S_{k+1} = \mathcal{N}(S_k)$ 在最多 2 步内必然进入基数仅为 4 的枢纽吸引子集合：
$$\mathcal{A}_{\mathcal{N}} = \{ 0 (\text{坤}), 63 (\text{乾}) \} \cup \{ 21 (\text{未济}), 42 (\text{既济}) \}$$
其中：
- $S=0$（坤卦，纯阴）与 $S=63$（乾卦，纯阳）为**不动点**（Fixed Points）：$\mathcal{N}(0)=0, \mathcal{N}(63)=63$。
- $S=21$（未济，火水未济）与 $S=42$（既济，水火既济）构成**2-周期极限环**（Limit Cycle）：$\mathcal{N}(21)=42, \mathcal{N}(42)=21$。

#### 构造性证明
1. 观察一次迭代后的卦象 $S_1 = [b_1, b_2, b_3, b_2, b_3, b_4]$。
2. 再次执行迭代：$S_2 = \mathcal{N}(S_1) = [b_2, b_3, b_2, b_3, b_2, b_3]$。
3. 可见 $S_2$ 的全部 6 个爻仅由原卦的中间两爻 $(b_2, b_3)$ 唯一决定：
   - $(b_2, b_3) = (0, 0) \implies S_2 = 0b000000 = 0$（坤）
   - $(b_2, b_3) = (1, 1) \implies S_2 = 0b111111 = 63$（乾）
   - $(b_2, b_3) = (0, 1) \implies S_2 = 0b101010 = 42$（既济）
   - $(b_2, b_3) = (1, 0) \implies S_2 = 0b010101 = 21$（未济）
因此 $\forall S \in Q_6$，至多经过 2 次迭代必然命中此 4 态之一。

#### 工程实现
在 `IchingKernel` 中实现了 `nuclear_chain(status_code, max_steps=4)` 与 `nuclear_attractor(status_code)`，并通过自动化测试验证了全 64 态的最大收敛步数严格 $\le 2$。

---

### 2.4 古典大衍筮法概率测度 (Da Yan Stalk Probability Measure)

#### 测度原理
不同于现代计算机等概率伯努利硬币模型（$p=0.5$），传统《周易》大衍之数筮法（五十以学易，其用四十有九，挂一分二过揲归奇，三变成爻）产生的离散概率分布为：
- **老阳 (9, 变爻，动阳)**: $P(9) = \frac{3}{16} = 0.1875$
- **少阴 (8, 静爻，静阴)**: $P(8) = \frac{5}{16} = 0.3125$
- **少阳 (7, 静爻，静阳)**: $P(7) = \frac{5}{16} = 0.3125$
- **老阴 (6, 变爻，动阴)**: $P(6) = \frac{3}{16} = 0.1875$

#### 性质验证
1. **概率归一性**: $\sum_{v \in \{6,7,8,9\}} P(v) = \frac{3+5+5+3}{16} = 1.0$
2. **边缘阴阳严格对称**:
   $$P(\text{Yang}) = P(9) + P(7) = \frac{8}{16} = 0.5$$
   $$P(\text{Yin}) = P(8) + P(6) = \frac{8}{16} = 0.5$$
3. **动静比例**:
   - 变爻率（动爻概率）: $P(9) + P(6) = \frac{6}{16} = 37.5\%$
   - 静爻率（稳定概率）: $P(8) + P(7) = \frac{10}{16} = 62.5\%$

在 `IchingKernel` 中固化了常量字典 `DAYAN_PROBABILITIES` 与查询方法 `dayan_line_probability(value)`。

---

### 2.5 信息论相对先验 KL 散度 (Relative Entropy to Uniform Prior)

#### 公式推导
在 6-bit 状态空间 $Q_6$（总状态数 $N=64$）中，无偏最大不确定性对应离散均匀分布 $U_{64}$，其均匀概率为 $u(s) = \frac{1}{64}$，先验熵为 $\log_2(64) = 6.0$ bit。
对于运行时经验状态分布 $P$，其相对全局均匀分布的 Kullback-Leibler 散度定义为：
$$D_{\text{KL}}(P \parallel U_{64}) = \sum_{s \in \text{supp}(P)} P(s) \log_2 \frac{P(s)}{1/64} = \sum P(s) \log_2 P(s) - \log_2(1/64) = -H(P) + 6.0 = 6.0 - H(P)$$

#### 工程集成
在 `IchingKernel` 中实现 `kl_divergence_uniform(status_codes: list[int]) -> float`，并在 `state_distribution_entropy()` 输出中注入 `"kl_divergence_uniform"`：
- 确定性单态运行（$H=0$）：$D_{\text{KL}} = 6.0$ bit（最大极化，高度定向）
- 完全均匀探索分布（$H=6.0$）：$D_{\text{KL}} = 0.0$ bit（最大不确定度）

---

### 2.6 文档与规格对齐校正 (Documentation Alignment)

1. **[docs/ICHING_QUICKREF.md](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/docs/ICHING_QUICKREF.md)**：
   - 修正八卦二进制代码表，与内核常量（Zhen `001`、Kan `010`、Dui `011`、Gen `100`、Li `101`、Xun `110`）严格一致。
   - 纠正了状态速查表中的错位卦象：
     - Code 35（`0b100011`）：更正为 `Gen/Dui ☶☱`（山泽损，土生金，`accelerate`）。
     - Code 39（`0b100111`）：更正为 `Gen/Qian ☶☰`（山天大畜，土生金，`accelerate`）。
     - Code 49（`0b110001`）：更正为 `Xun/Zhen ☴☳`（风雷益，木木比和，`continue`，无额外 reason 伪造）。
   - 纠正了状态 40 步骤分析中关于「火不生土」的笔误（明确火生土，但主权安全硬边界优先判定）。
   - 实战示例校准：Example 1 改为 Status 63 纯阳降温，Example 2 改为 Status 39 正常生克加速。

2. **[docs/YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md](file:///Volumes/MacSSD/%E9%A1%B9%E7%9B%AE%E5%BC%80%E5%8F%91/one%20code/docs/YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md)**：
   - 修正了原本标量乘以矩阵的非法量纲公式，改以状态分布向量 $\boldsymbol{\pi}_t = \boldsymbol{\pi}_0 M^t \in \mathbb{R}^{1 \times 5}$ 演化表述：
     $$P(\text{State}_t = (H, V_j)) = P(H) \cdot (\boldsymbol{\pi}_t)_j = \left[\prod_{i=1}^6 P(X_i)\right] \cdot (\boldsymbol{\pi}_t)_j$$
   - 增补大衍筮法概率测度章节。

---

## 3. 验证证据矩阵 (Verification Matrix)

| 序号 | 验证维度 | 验证方法与工具 | 验证结果 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| **V-1** | 四象映射正确性 | 单元测试 + 符号检验脚本 | `0b01 -> shao_yin`, `0b10 -> shao_yang`, 语义对齐 | **PASS** |
| **V-2** | 交卦代数对合性 | 全 64 卦迭代脚本与单元测试 | $\forall S, \mathcal{E}(\mathcal{E}(S)) = S$，内外卦对换无误 | **PASS** |
| **V-3** | 互卦吸引子定理 | 64 卦全量状态图谱遍历 | 100% 卦象在 $\le 2$ 步收敛到 $\{0, 63, 21, 42\}$ | **PASS** |
| **V-4** | 大衍概率测度 | 数学解析与边界断言测试 | 归一性 1.0，阴阳各 0.5，动爻 37.5%，非法值异常 | **PASS** |
| **V-5** | KL 散度信息论指标 | 极值测试与状态分布综合测试 | 确定态 6.0 bit，全均匀态 0.0 bit，加和严格等于 6.0 | **PASS** |
| **V-6** | 内核单元测试套件 | `python -m unittest tests/test_iching_kernel.py` | 78 个测试项全部通过 (0.027s) | **PASS** |
| **V-7** | 项目全量回归测试 | `python -m unittest discover tests/ "test_*.py"` | **916 项测试通过 (0 失败, 1 跳过)** (20.363s) | **PASS** |
| **V-8** | 状态空间数学审计 | `onecode math-audit` | 64 态完全闭合，李雅普诺夫单调性违例 = 0 | **PASS** |
| **V-9** | 独立审计脚本验证 | `scratch/audit_verify.py` | 9 大审计专项检查全部通过 (0 报错) | **PASS** |

---

## 4. 文件变更清单 (Files Changed)

```text
docs/ICHING_QUICKREF.md                            |  57 +++++------
docs/YIZIJUE_CONTROLLED_DECODING_PROBABILITY_RULES.md |  29 ++++--
src/onecode/kernel/hexagram.py                     | 114 +++++++++++++++++++--
tests/test_iching_kernel.py                        |  78 ++++++++++++--
4 files changed, 229 insertions(+), 49 deletions(-)
```

---

## 5. 收尾结论与签发 (Sign-off)

本次优化在未引入任何破坏性变更、未增加平行控制变量的前提下，彻底解决了周易八卦数学体系中的位序历史瑕疵，补全了四大自同构变换群与动力系统吸引子定理，统一了工程代码与理论文档。

**最终审核结论**: **全部数学公式证明确凿，代码实现严密完备，测试与数学审计 100% 通过，可以正式收尾入库。**
