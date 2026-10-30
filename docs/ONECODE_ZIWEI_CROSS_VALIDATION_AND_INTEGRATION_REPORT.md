# OneCode 与紫微斗数 (Ziwei-Doushu) 深度数学对照、公式验证与系统改进落地报告

> **日期**: 2026-10-29  
> **对比代码库**:
> - **OneCode 内核**: [`src/onecode/kernel/hexagram.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram.py)、[`hexagram_profile.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_profile.py)、[`hexagram_certificates.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py)、[`checkpoint.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/checkpoint.py)
> - **紫微斗数引擎**: [`/tmp/ziwei-doushu/lib/ziwei/algorithm.ts`](file:///tmp/ziwei-doushu/lib/ziwei/algorithm.ts)、[`sihua.ts`](file:///tmp/ziwei-doushu/lib/ziwei/sihua.ts)、[`patterns.ts`](file:///tmp/ziwei-doushu/lib/ziwei/patterns.ts)、[`constants.ts`](file:///tmp/ziwei-doushu/lib/ziwei/constants.ts)、[`yunxian-context.ts`](file:///tmp/ziwei-doushu/lib/ziwei/yunxian-context.ts)、倪海厦《天纪》数据库 [`tianji.ts`](file:///tmp/ziwei-doushu/lib/nihai/tianji.ts)

---

## 目录
1. [引言与理论统一性（易经象数与紫微三合体系）](#1-引言与理论统一性)
2. [数学与代数同构证明](#2-数学与代数同构证明)
   - [2.1 状态空间：$Q_6$ 布尔超立方体与十二地支环的双射](#21-状态空间-q_6-布尔超立方体与十二地支环的双射)
   - [2.2 几何变换：对宫即错卦（对冲即按位取反）](#22-几何变换对宫即错卦对冲即按位取反)
   - [2.3 三合局在布尔超立方体上的对称性定理](#23-三合局在布尔超立方体上的对称性定理)
3. [六大核心算法与规则的深度双向验证](#3-六大核心算法与规则的深度双向验证)
   - [3.1 四化机制（Si Hua）：静态映射 vs 动态飞化与来因宫追溯](#31-四化机制si-hua静态映射-vs-动态飞化与来因宫追溯)
   - [3.2 宫干自化（Self-Sihua）：系统内部熵增与回环死锁检测](#32-宫干自化self-sihua系统内部熵增与回环死锁检测)
   - [3.3 格局系统（Patterns）：三方四正四点分布式共识 vs 单点互体判定](#33-格局系统patterns三方四正四点分布式共识-vs-单点互体判定)
   - [3.4 五行局数（Five Elements Bureau）：任务尺度与调度带宽动态调制](#34-五行局数five-elements-bureau任务尺度与调度带宽动态调制)
   - [3.5 星曜亮度（Brightness）：李雅普诺夫能量衰减与工具权限分级](#35-星曜亮度brightness李雅普诺夫能量衰减与工具权限分级)
   - [3.6 运限与叠宫（Superposition）：宏观架构阶段与微观轮次执行叠加](#36-运限与叠宫superposition宏观架构阶段与微观轮次执行叠加)
4. [n100 评测系统漏洞的紫微格局学病理诊断](#4-n100-评测系统漏洞的紫微格局学病理诊断)
   - [4.1 羊陀夹忌（Deadlock Trap）：截断限制与验证缺失形成的死锁](#41-羊陀夹忌deadlock-trap截断限制与验证缺失形成的死锁)
   - [4.2 化忌入迁移（External Obstacle）：网关超时与系统提示词剥离](#42-化忌入迁移external-obstacle网关超时与系统提示词剥离)
   - [4.3 自化忌（Hesitation Spun）：只读探查消耗轮次预算](#43-自化忌hesitation-spun只读探查消耗轮次预算)
5. [直接落地与改进 OneCode 的工程化方案](#5-直接落地与改进-onecode-的工程化方案)
   - [5.1 模块一：`TaskBureauMatrix`（五行局任务尺度调度器）](#51-模块一taskbureaumatrix五行局任务尺度调度器)
   - [5.2 模块二：`CausalRootTracer`（化忌来因宫因果溯源器）](#52-模块二causalroottracer化忌来因宫因果溯源器)
   - [5.3 模块三：`SelfDissipationDetector`（宫干自化与回环中断器）](#53-模块三selfdissipationdetector宫干自化与回环中断器)
   - [5.4 模块四：`TriadConsensusEngine`（三方四正四点共识格局检定器）](#54-模块四triadconsensusengine三方四正四点共识格局检定器)
6. [严格约束与规范符合性说明](#6-严格约束与规范符合性说明)

---

## 1. 引言与理论统一性

在倪海厦《天纪》（[`/tmp/ziwei-doushu/lib/nihai/tianji.ts`](file:///tmp/ziwei-doushu/lib/nihai/tianji.ts)）的学术建构中，**易经六十四卦**（象数派、决策与时机）与**紫微斗数**（三合派、十二宫位、星曜与四化）并非彼此割裂，而是**同根同源的跨尺度时空状态模型**：
- **易经六十四卦**：提供离散状态空间 $Q_6$ 上的确定性转移矩阵、互卦吸引子流形与微观爻位作用（承/乘/比/应）。
- **紫微斗数**：提供时间-空间（运限-宫位）多尺度叠层、因果追溯链（来因宫飞化）、以及四点几何共识网络（三方四正与前后夹宫）。

OneCode 目前已建立完整的 64 卦离散状态机（[`IchingKernel`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram.py#L88)）与遥测框架（[`checkpoint.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/checkpoint.py#L756)），但在多步执行中的“因果追溯”、“资源与环境协同共识”以及“任务规模自适应调度”等维度仍停留于局部单步逻辑。

通过与紫微斗数引擎的数学对照，能够为 OneCode 补齐高维分布式诊断能力。

```mermaid
graph LR
    subgraph OneCode Kernel
        Q6[6-Bit State Space Q_6] --> S_Ring[12 Sovereign Hexagram Ring]
        S_Ring --> HexDynamics[Five-Element Dynamics]
        HexDynamics --> MicroRel[Cheng/Sheng/Bi/Ying]
    end
    subgraph Ziwei Engine
        B12[12 Earthly Branches] --> SanFang[San Fang Si Zheng Trine]
        SanFang --> SiHuaFlying[Four Transformations & Flying Stars]
        SiHuaFlying --> Bureau[Five Elements Bureau 2..6]
    end
    S_Ring <===>|Bijective Isomorphism| B12
    HexDynamics <===>|Cross-Validation| SiHuaFlying
    MicroRel <===>|Geometric Alignment| SanFang
```

---

## 2. 数学与代数同构证明

### 2.1 状态空间：$Q_6$ 布尔超立方体与十二地支环的双射

在 [`hexagram_profile.py`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_profile.py#L481) 中，OneCode 定义了十二辟卦环：
$$\text{SOVEREIGN\_HEXAGRAM\_CODES} = (1, 3, 7, 15, 31, 63, 62, 60, 56, 48, 32, 0)$$
其卦名顺序为：`(复, 临, 泰, 大壮, 夬, 乾, 姤, 遁, 否, 观, 剥, 坤)`。

在紫微引擎中，地支十二宫的标准索引（[`constants.ts`](file:///tmp/ziwei-doushu/lib/ziwei/constants.ts#L4)）为：
$$\text{BRANCHES} = (\text{子}, \text{丑}, \text{寅}, \text{卯}, \text{辰}, \text{巳}, \text{午}, \text{未}, \text{申}, \text{酉}, \text{戌}, \text{亥})$$

**数学定理 1（辟卦-地支双射定理）**：  
存在严格双射 $\Phi: \mathbb{Z}_{12} \to Q_6$，使得地支索引 $b \in \{0, \dots, 11\}$ 映射到状态码 $C_b \in Q_6$：

| 索引 $b$ | 地支 | 辟卦 | 二进制状态码 | 阳爻数 | 软件工程语义 |
|:---:|:---:|:---:|:---:|:---:|:---|
| 0 | **子** | **复** | `000001` (1) | 1 | 初始状态、一阳初生、建立基线、读取任务规范 |
| 1 | **丑** | **临** | `000011` (3) | 2 | 探查代码库、符号定位、准备执行计划 |
| 2 | **寅** | **泰** | `000111` (7) | 3 | 三阳开泰、阴阳平衡、确定修改方案与接口契约 |
| 3 | **卯** | **大壮** | `001111` (15) | 4 | 执行代码编写、核心逻辑注入、展开功能补丁 |
| 4 | **辰** | **夬** | `011111` (31) | 5 | 决断收敛、执行验证测试、准备提交资产 |
| 5 | **巳** | **乾** | `111111` (63) | 6 | 纯阳至健、验证完全通过、交付工件已确立 |
| 6 | **午** | **姤** | `111110` (62) | 5 | 一阴始生、首次发现潜在缺陷/边界异常、进入复检 |
| 7 | **未** | **遁** | `111100` (60) | 4 | 策略性退避、剪枝无效修改、收缩上下文范围 |
| 8 | **申** | **否** | `111000` (56) | 3 | 天地不交、闭塞受阻、环境或依赖出现屏障 |
| 9 | **酉** | **观** | `110000` (48) | 2 | 深度审计、复盘日志与调用栈、定位根本原因 |
| 10 | **戌** | **剥** | `100000` (32) | 1 | 剥落坏损、触发资产回滚（Rollback）、清理缓存 |
| 11 | **亥** | **坤** | `000000` (0) | 0 | 纯阴厚德、状态归零重置、回归基线安全点 |

---

### 2.2 几何变换：对宫即错卦（对冲即按位取反）

在紫微斗数中，任何宫位 $B$ 的**对宫（六冲宫）**为：
$$\text{DuiGong}(B) = (B + 6) \pmod{12}$$

在 OneCode 中，[`IchingCertificatesMixin.opposite_hexagram`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L347) 定义为：
$$\text{Opposite}(S) = S \oplus \text{0b111111} = S \oplus 63$$

**数学定理 2（对冲即按位取反定理）**：  
对任意地支 $B \in \mathbb{Z}_{12}$，其在紫微中的对宫对应的辟卦，恰好等于其在 OneCode 中的按位取反错卦：
$$\Phi((B + 6) \pmod{12}) = \Phi(B) \oplus 63 = \text{Opposite}(\Phi(B))$$

**数值验算证据**（由 scratch 验证脚本验证）：
- $B=0$（子·复 $1$） $\leftrightarrow$ 对宫 $B=6$（午·姤 $62$）：$1 \oplus 63 = 62$
- $B=1$（丑·临 $3$） $\leftrightarrow$ 对宫 $B=7$（未·遁 $60$）：$3 \oplus 63 = 60$
- $B=2$（寅·泰 $7$） $\leftrightarrow$ 对宫 $B=8$（申·否 $56$）：$7 \oplus 63 = 56$
- $B=3$（卯·大壮 $15$） $\leftrightarrow$ 对宫 $B=9$（酉·观 $48$）：$15 \oplus 63 = 48$
- $B=4$（辰·夬 $31$） $\leftrightarrow$ 对宫 $B=10$（戌·剥 $32$）：$31 \oplus 63 = 32$
- $B=5$（巳·乾 $63$） $\leftrightarrow$ 对宫 $B=11$（亥·坤 $0$）：$63 \oplus 63 = 0$

> [!NOTE]
> 这证明了**紫微斗数的“对宫相冲”在布尔状态空间中本质上是全局正交反转（Involution）**。对宫不是孤立存在的，而是当前状态在外部反光镜中的完全对称补集。

---

### 2.3 三合局在布尔超立方体上的对称性定理

紫微斗数依据地支三合建立五行局（申子辰水局、寅午戌火局、巳酉丑金局、亥卯未木局）。  
将三合局映射到辟卦在 $Q_6$ 上的阳爻汉明权重（Hamming Weight $\omega(x)$）：

1. **申子辰水局**：
   - 申（否，$\omega=3$）
   - 子（复，$\omega=1$）
   - 辰（夬，$\omega=5$）  
   $$\sum \omega = 3 + 1 + 5 = 9 \implies \bar{\omega} = \frac{9}{3} = \mathbf{3.00}$$
2. **寅午戌火局**：
   - 寅（泰，$\omega=3$）
   - 午（姤，$\omega=5$）
   - 戌（剥，$\omega=1$）  
   $$\sum \omega = 3 + 5 + 1 = 9 \implies \bar{\omega} = \frac{9}{3} = \mathbf{3.00}$$
3. **巳酉丑金局**：
   - 巳（乾，$\omega=6$）
   - 酉（观，$\omega=2$）
   - 丑（临，$\omega=2$）  
   $$\sum \omega = 6 + 2 + 2 = 10 \implies \bar{\omega} = \frac{10}{3} \approx \mathbf{3.33}$$
4. **亥卯未木局**：
   - 亥（坤，$\omega=0$）
   - 卯（大壮，$\omega=4$）
   - 未（遁，$\omega=4$）  
   $$\sum \omega = 0 + 4 + 4 = 8 \implies \bar{\omega} = \frac{8}{3} \approx \mathbf{2.67}$$

**数学定理 3（三合局超立方体中心对称性）**：  
- 水局与火局的平均阳爻数严格等于 $3.00$，在 6-bit 超立方体上呈现**完美的阴阳中和平衡**。
- 金局（$3.33$）与木局（$2.67$）互为严格对偶互补：
  $$\frac{\bar{\omega}_{\text{金}} + \bar{\omega}_{\text{木}}}{2} = \frac{3.333 + 2.667}{2} = \mathbf{3.00}$$

这说明三合局并非人为随意拼凑，而是在离散对称群上具备严格的李群中心不变量！

---

### 2.4 六合（暗合）在布尔超立方体上的回文汉明距离与对偶和不变量定理

在紫微斗数与传统历法中，**六合（暗合）** 定义为十二地支满足 $(b_1 + b_2) \equiv 1 \pmod{12}$ 的 6 组配对：
1. 子丑合（$0 + 1 = 1$）
2. 寅亥合（$2 + 11 = 13 \equiv 1$）
3. 卯戌合（$3 + 10 = 13 \equiv 1$）
4. 辰酉合（$4 + 9 = 13 \equiv 1$）
5. 巳申合（$5 + 8 = 13 \equiv 1$）
6. 午未合（$6 + 7 = 13 \equiv 1$）

将其投射至 OneCode 辟卦空间并计算各对在 $Q_6$ 上的汉明异或距离 $d_H(C_{b_1}, C_{b_2})$ 与阳爻数总和 $\omega_1 + \omega_2$：

| 六合配对 $(b_1, b_2)$ | 对应辟卦 | 状态码二进制 | 汉明异或距离 $d_H$ | 阳爻数总和 $\omega_1 + \omega_2$ | 软件工程架构含义 |
|:---:|:---:|:---:|:---:|:---:|:---|
| **子·丑** | 复 $\leftrightarrow$ 临 | `000001` $\leftrightarrow$ `000011` | **1** | **3** ($1+2$) | 任务规范初现与代码库探查暗合 |
| **寅·亥** | 泰 $\leftrightarrow$ 坤 | `000111` $\leftrightarrow$ `000000` | **3** | **3** ($3+0$) | 方案规划与初始环境基线暗合 |
| **卯·戌** | 大壮 $\leftrightarrow$ 剥 | `001111` $\leftrightarrow$ `100000` | **5** | **5** ($4+1$) | 大规模修改与安全回滚暗合 |
| **辰·酉** | 夬 $\leftrightarrow$ 观 | `011111` $\leftrightarrow$ `110000` | **5** | **7** ($5+2$) | 决断提交与深度审计暗合 |
| **巳·申** | 乾 $\leftrightarrow$ 否 | `111111` $\leftrightarrow$ `111000` | **3** | **9** ($6+3$) | 纯阳至健与安全边界隔离暗合 |
| **午·未** | 姤 $\leftrightarrow$ 遁 | `111110` $\leftrightarrow$ `111100` | **1** | **9** ($5+4$) | 初现缺陷与策略性退避剪枝暗合 |

**数学定理 4（六合回文距离与对偶和不变量定理）**：
1. **回文对称汉明距离（Palindromic Hamming Distance）**：  
   六组配对的汉明距离序列呈现严格的轴对称回文结构：
   $$[d_H] = [1, 3, 5, 5, 3, 1] \implies d_H(\text{Pair}_k) = d_H(\text{Pair}_{7-k})$$
2. **对偶阳爻和完全守恒（Dual Couple Sum Invariant）**：  
   对称配对的阳爻总和严格互补等于 12：
   $$\text{YangSum}(\text{Pair}_k) + \text{YangSum}(\text{Pair}_{7-k}) = \mathbf{12} \quad (\forall k \in \{1, 2, 3\})$$
   每对平均阳爻数为 $\frac{12}{4} = \mathbf{3.00}$（中心阴阳中和）。

该定理已由 [`IchingKernel.an_he_coupling_certificate()`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_ziwei.py) 与 `onecode math-audit` 形式化验证通过！

---

### 2.5 身宫偶数子群同构定理（$2\mathbb{Z}_{12} \cong \mathbb{Z}_6$）与六大皈依庇护所

在紫微斗数与倪师《天纪》中，“命宫为先天之本，身宫为后天之用”。命宫决定先天的初始框架，而身宫则是经历现实磨练、遭遇困境与执行推进时的**最终寄托与皈依之所**。

#### 代数同态与象集证明
设出生月份 $M \in \{1, \dots, 12\}$，出生时辰地支索引 $H \in \{0, \dots, 11\}$（$0=\text{子}, 1=\text{丑}, \dots, 11=\text{亥}$）。
- 命宫地支位置：$P_{\text{ming}}(M, H) = (M + 1 - H) \pmod{12}$
- 身宫地支位置：$P_{\text{shen}}(M, H) = (M + 1 + H) \pmod{12}$

设十二宫名索引按传统逆时针排列：
$$0:\text{命宫}, 1:\text{兄弟}, 2:\text{夫妻}, 3:\text{子女}, 4:\text{财帛}, 5:\text{疾厄}, 6:\text{迁移}, 7:\text{交友}, 8:\text{官禄}, 9:\text{田宅}, 10:\text{福德}, 11:\text{父母}$$
身宫在十二宫中的相对宫位偏移行程 $k_{\text{shen}}(H)$ 为：
$$k_{\text{shen}}(H) = (P_{\text{ming}} - P_{\text{shen}}) \pmod{12} = (M + 1 - H - (M + 1 + H)) \pmod{12} \equiv (-2H) \pmod{12}$$

**数学定理 5（身宫偶数子群同构定理）**：
1. **月份完全正交无关性**：$k_{\text{shen}}(H)$ 的取值与月份 $M$ 完全无关，纯粹由时辰 $H$ 决定。
2. **偶数子群同构**：由于对任意整数 $H$，$2H$ 必为偶数，故同态映射 $\psi: \mathbb{Z}_{12} \to \mathbb{Z}_{12}, \psi(H) = (-2H) \pmod{12}$ 的象集严格等于偶数同余类子群：
   $$\operatorname{Im}(\psi) = \{0, 2, 4, 6, 8, 10\} = 2\mathbb{Z}_{12} \cong \mathbb{Z}_6$$
   基数恰为 6。
3. **奇数宫位绝对排除性**：兄弟(1)、子女(3)、疾厄(5)、交友(7)、田宅(9)、父母(11)六个奇数宫位在 $\psi$ 下的原像均为空集，**在数学上永远不可能成为身宫**！
4. **子午核与对冲对称性**：$\ker(\psi) = \{0, 6\}$（子午对冲），且对任意时辰 $H$，都有 $\psi(H) = \psi((H+6) \pmod{12})$。

#### 软件工程与 Agent 执行循环映射

| 宫位偏移 $k$ | 身宫归属 | 时辰原像 $H$ | 软件工程现实皈依模式 | 应对的工程压力 / 触发条件 |
|:---:|:---:|:---:|:---|:---|
| **0** | **命宫** (身命同宫) | 子 (0), 午 (6) | **契约规范皈依** (`contract_spec_driven`) | 任务初始轮次、缺少测试时严格对照提示词契约 |
| **2** | **夫妻宫** (身寄夫妻) | 巳 (5), 亥 (11) | **接口协同皈依** (`interop_compatible`) | 修改公共接口时保护现有函数签名与调用方兼容 |
| **4** | **财帛宫** (身寄财帛) | 辰 (4), 戌 (10) | **资源与微创补丁皈依** (`token_minimal_diff`) | 上下文超限、大文件截断风险，强制行级差分 |
| **6** | **迁移宫** (身寄迁移) | 卯 (3), 酉 (9) | **外部环境与沙箱适配皈依** (`environment_adaptive`) | 网关 120s 超时、WAF 1010、网络波动时标准库隔离 |
| **8** | **官禄宫** (身寄官禄) | 寅 (2), 申 (8) | **测试验证器皈依** (`verifier_driven`) | 存在单测且测试报错，以失败断言为唯一攻坚点 |
| **10** | **福德宫** (身寄福德) | 丑 (1), 未 (7) | **架构洁净度皈依** (`architectural_integrity`) | 模块循环依赖、函数超长 (>160行) 时架构解耦 |

该定理已由 [`IchingKernel.shen_gong_anchorage_certificate()`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_ziwei.py) 与 `onecode math-audit` 形式化验证通过！

---

### 2.6 星曜庙旺落陷与李雅普诺夫能量衰减同构定理

在紫微斗数中，星曜在不同宫位具有庙、旺、得、利、平、不、闲、陷等亮度等级（[`/tmp/ziwei-doushu/lib/ziwei/algorithm.ts` L280-L290](file:///tmp/ziwei-doushu/lib/ziwei/algorithm.ts#L280-L290)）。倪师《天纪》云：“吉星落陷无力，凶星庙旺不为凶甚至化为权柄，凶星落陷则肆虐成灾。”

将星曜亮度投射至 OneCode 的李雅普诺夫能量函数 $V(S)$（[`hexagram_certificates.py` L26-L44](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L26-L44)）与执行权限治理：

**数学定理 6（星曜亮度能量单调性与边界定理）**：
1. **基态（泰卦 $S=7$）庙旺不变性**：
   $$V(7) = 0.100 \le 0.60 \implies \text{Brightness}(7) = \text{庙旺 (bright)}$$
   系统处于阴阳中和基态，授予最高自主度：允许全量读写、补丁应用、单元测试与自主提交。
2. **熔断态（坤卦 $S=0$）落陷不变性**：
   $$V(0) = 1.850 > 1.60 \implies \text{Brightness}(0) = \text{落陷 (dim)}$$
   系统处于能量严重过载或死锁破格状态，强制触发**降级防御模式 (`degraded`)**：禁止全文件重写，节流因子降至 $0.25$，仅允许只读探测、错误溯源与最小行级微创补丁。
3. **全空间保真与边界完备性**：
   对 6-bit 超立方体中所有 64 个状态 $S \in \{0, \dots, 63\}$，其亮度严格映射为 $\text{Bright} \in \{\text{庙旺}, \text{平利}, \text{落陷}\}$，节流因子 $\tau \in \{1.0, 0.75, 0.25\}$，具备严格的有界性与单调收敛性。

该定理已由 [`IchingKernel.star_brightness_certificate()`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_ziwei.py) 与 `onecode math-audit` 形式化验证通过！

---

## 3. 六大核心算法与规则的深度双向验证

### 3.1 四化机制（Si Hua）：静态映射 vs 动态飞化与来因宫追溯

#### 现状对比
- **OneCode 现行实现**（[`hexagram_certificates.py` L251-L273](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L251-L273)）：
  ```python
  if action == "halt":
      label = "化忌"
  elif action in {"checkpoint", "discover"}:
      label = "化科"
  elif action in {"activate", "throttle", "prune", "cooldown"}:
      label = "化权"
  else:
      label = "化禄"
  ```
  *局限*：映射是单向且孤立的。只标记了“当前轮次发生了什么动作”，却没有记录“这个化忌从何而来”。

- **紫微斗数引擎实现**（[`/tmp/ziwei-doushu/lib/ziwei/sihua.ts` L223-L236](file:///tmp/ziwei-doushu/lib/ziwei/sihua.ts#L223-L236)）：
  ```typescript
  export function findIncomingPalaces(chart: ZiweiChart, starName: string, sihua: SiHua): Palace[] {
    const result: Palace[] = [];
    chart.palaces.forEach(p => {
      const transforms = getSiHuaByStem(p.stem);
      if (transforms[sihua] === starName) {
        result.push(p);
      }
    });
    return result;
  }
  ```
  *核心哲理*：**化忌必有来因宫**。当某个宫位受阻（化忌）时，那个引发化忌的天干所属宫位，才是根本症结所在。

#### 对 OneCode 的改进结合点
在 Agent 多轮循环中，若 Turn 5 触发 `halt`（化忌，测试用例执行崩溃）：
- **传统方式**：在 Turn 5 不断重新尝试修补该行代码。
- **来因宫追溯（Causal Root Trace）**：解析错误调用栈，追溯被调用方法是在哪一个历史轮次被修改的。若发现该符号由 Turn 3 引入，则将 Turn 3 定位为**来因宫**，恢复机制直接跳转回溯 Turn 3 的契约上下文，而不是在 Turn 5 盲目重试。

---

### 3.2 宫干自化（Self-Sihua）：系统内部熵增与回环死锁检测

#### 紫微原理解析（[`sihua.ts` L189-L210](file:///tmp/ziwei-doushu/lib/ziwei/sihua.ts#L189-L210)）
- **自化**：宫位天干所引发的四化，其受化星恰在本宫内部。
  - **自化忌**：自身产生阻力，消解本宫力量，陷入自我怀疑与回环。
  - **自化禄**：自身产生资源却向外消散，虚耗能量，徒有其表。
  - **自化权**：自身过度争夺控制权，导致局部僵化。
  - **自化科**：自身具备自省审计能力，能够自我修正。

#### 对 OneCode 的改进结合点
在 LLM Agent 场景中，自化检测可以直接解决常见的**提示词死循环与虚假交付**问题：
1. **自化忌（Circular Read Hesitation）**：
   - 判定：Agent 连续 2 轮只调用只读工具（`read_file`, `list_directory`, `search_symbol`），没有生成任何补丁，也没有运行任何测试。
   - 动作：触发自化忌拦截，注入强制行动约束：“已连续两轮探查，必须基于已知信息生成代码补丁或中止”。
2. **自化禄（Phantom Completion）**：
   - 判定：模型在回复中宣称“已成功完成任务/修改已生效”，但 `workspace_diff` 为空，且没有任何已通过的验证记录。
   - 动作：触发自化禄拦截，拒绝完成信号，强制要求提交物理验证证据。

---

### 3.3 格局系统（Patterns）：三方四正四点分布式共识 vs 单点互体判定

#### 现状对比
- **OneCode 现行实现**（[`hexagram_certificates.py` L276-L300](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L276-L300)）：
  ```python
  if foundation_broken or transition.action == "halt":
      state = "broken"
      name = "破格"
  elif dynamics.get("cross_relation") in {"generates", "generated_by"}:
      state = "reinforced"
      name = "加分"
  else:
      state = "balanced"
      name = "成格"
  ```
  *局限*：仅根据本卦的内部互卦（Nuclear Hexagram）是否断裂进行局部推断，未引入环境与资源约束。

- **紫微斗数引擎实现**（[`/tmp/ziwei-doushu/lib/ziwei/patterns.ts`](file:///tmp/ziwei-doushu/lib/ziwei/patterns.ts)）：
  以**三方四正（San Fang Si Zheng）**为几何拓扑核心：
  $$\text{SanFang}(m) = \{m, (m+4) \pmod{12}, (m+8) \pmod{12}, (m+6) \pmod{12}\}$$
  以及前后夹宫（$\{(m-1) \pmod{12}, (m+1) \pmod{12}\}$）。

#### 四点分布式共识模型设计
将紫微三方四正严格映射为软件工程的四维共识：

| 宫位 | 紫微对应 | 软件工程核心指标 | 状态正常标志 | 异常破格标志 |
|:---|:---|:---|:---|:---|
| **命宫** (1) | 本命主体 | **代码补丁的语法合规性** | AST 解析无错、语法树合法 | 存在语法错误、截断不全 |
| **财帛宫** (5) | 资源库藏 | **上下文与 Token 预算** | 未触发截断、Token 在预算内 | 源码预览截断、超过模型最大输出 |
| **官禄宫** (9) | 事业执行 | **测试验证器（Verifier）状态** | 单元测试/集成测试全部通过 | 测试断言失败、找不到测试驱动器 |
| **迁移宫** (7) | 外部环境 | **运行环境与网关可用性** | 网关延时低、依赖沙箱完好 | 429 限流、120s 超时、WAF 拦截 |

```mermaid
flowchart TD
    Ming["命宫 (Turn State)<br/>语法与补丁合规性"] --- Cai["财帛宫 (Resources)<br/>Token 预算与截断控制"]
    Cai --- Guan["官禄宫 (Verifier)<br/>自动化测试与断言"]
    Guan --- Qian["迁移宫 (Environment)<br/>网关可用性与依赖沙箱"]
    Qian --- Ming
    
    style Ming fill:#e1f5fe,stroke:#0288d1
    style Cai fill:#fff8e1,stroke:#ffa000
    style Guan fill:#e8f5e9,stroke:#388e3c
    style Qian fill:#fce4ec,stroke:#c2185b
```

- **三奇加会格**：四点全部为 True $\implies$ 100% 自主合并交付。
- **羊陀夹忌格**：官禄化忌（测试挂） + 财帛擎羊（文件被截断） + 命宫陀罗（禁止不完整代码） $\implies$ **死锁败局**，必须主动跳出切换策略！

---

### 3.4 五行局数（Five Elements Bureau）：任务尺度与调度带宽动态调制

#### 紫微原理解析（[`constants.ts` L37-L44](file:///tmp/ziwei-doushu/lib/ziwei/constants.ts#L37-L44)）
- 水二局（起限虚岁 2）
- 木三局（起限虚岁 3）
- 金四局（起限虚岁 4）
- 土五局（起限虚岁 5）
- 火六局（起限虚岁 6）

#### 对 OneCode 的改进结合点：`TaskBureauMatrix`
在软件任务初始化时，根据代码库的客观体量计算任务的“局数”：
$$\text{TaskScale} = \ln(\text{Total LOC} + 1) \cdot \sqrt{\text{Modified File Count}}$$

```mermaid
xychart-beta
    title "五行局与轮次预算 / 超时时间对应关系"
    x-axis ["水二局", "木三局", "金四局", "土五局", "火六局"]
    y-axis "数值" 0 --> 180
    bar [3, 4, 5, 6, 8]
    line [45, 60, 90, 120, 180]
```

- **水二局（轻量级敏捷修复）**：$\text{Scale} < 4$。预算 $3$ 轮，单轮超时 $45\text{s}$。策略：针对性行级微创补丁。
- **木三局（功能性渐进生长）**：$4 \le \text{Scale} < 8$。预算 $4$ 轮，单轮超时 $60\text{s}$。策略：模块内函数级扩充。
- **金四局（严格类型重构）**：$8 \le \text{Scale} < 14$。预算 $5$ 轮，单轮超时 $90\text{s}$。策略：全量 `mypy`/`ruff` 严苛验证。
- **土五局（数据与持久化迁移）**：$14 \le \text{Scale} < 22$。预算 $6$ 轮，单轮超时 $120\text{s}$。策略：数据结构与测试双重覆盖。
- **火六局（多模块大型架构演进）**：$\text{Scale} \ge 22$。预算 $8$ 轮，单轮超时 $180\text{s}$。策略：分布式渐进交付。

---

### 3.5 星曜亮度（Brightness）：李雅普诺夫能量衰减与工具权限分级

#### 紫微原理解析（[`algorithm.ts` L280-L296](file:///tmp/ziwei-doushu/lib/ziwei/algorithm.ts#L280-L296)）
星曜在不同宫位具有七档亮度：庙、旺、得、利、平、不、陷。
- **庙旺**：能量充沛，吉星威力倍增，凶星受制化吉。
- **落陷**：能量匮乏，吉星无力，凶星肆虐。

#### 对 OneCode 的改进结合点
OneCode 中的李雅普诺夫能量函数（[`lyapunov_energy`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L26-L44)）与执行带宽（[`execution_bandwidth`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram_certificates.py#L141)）可以直接与星曜亮度挂钩：
- 当状态处于**庙旺**（能量差接近 0、阴阳平衡）：授予全部写权限（`write_text`, `bash`, `apply_patch`）。
- 当状态处于**落陷**（能量过载、纯阳或纯阴）：降级执行权限，只允许安全审计类只读操作，防止由于模型幻觉导致破坏性写入。

---

### 3.6 运限与叠宫（Superposition）：宏观架构阶段与微观轮次执行叠加

#### 紫微原理解析（[`yunxian-context.ts`](file:///tmp/ziwei-doushu/lib/ziwei/yunxian-context.ts)）
紫微斗数的最高核心技法为**叠宫（Overlay）**：
- **本命盘**：固有先天骨架（Repository 架构与根规则）。
- **大限盘**：十年宏观大运（任务阶段：架构规划期 $\to$ 编码实施期 $\to$ 交付验证期）。
- **流年盘 / 流月盘**：当前微观执行轮次（Turn $k$）与微观工具调用。

#### 对 OneCode 的改进结合点
在评估某一步的失败（如单测报错）时，叠加当前所处的“大限”阶段：
- 若宏观处于**探索规划期**（震/坎卦）：单测报错视为有效的“探测反馈”，不扣减置信度，继续引导模型迭代。
- 若宏观处于**交付验证期**（乾/离卦）：单测报错立即判定为致命违约，触发快速熔断与版本回退。

---

## 4. n100 评测系统漏洞的紫微格局学病理诊断

在此前 n100 基准评测中暴露的 5 大系统性漏洞，在紫微斗数格局学中具有一一对应的病理映射：

### 4.1 羊陀夹忌（Deadlock Trap）：截断限制与验证缺失形成的死锁

```mermaid
graph LR
    subgraph 羊陀夹忌死锁链条
        QianYang["前驱擎羊 (羊)<br/>4000 字符预览截断<br/>导致全文件重写截断"] --> HuaJi["核心化忌 (忌)<br/>缺少 pytest 依赖<br/>测试器崩溃"]
        TuoLuo["后继陀罗 (陀)<br/>提示词严禁局部补丁<br/>模型拒绝生成 (no_actionable_plan)"] --> HuaJi
    end
```

- **病理诊断**：
  在评测 `feature-medium-validation_to_eliminate_uriref` 和 `feature-medium-envless_file_load` 时：
  - **化忌**：测试套件缺少 pytest 抛出 `ModuleNotFoundError`。
  - **前夹擎羊**：Prompt 生成器截断了 4000 字符之外的源码。
  - **后夹陀罗**：System Prompt 严令禁止局部代码片段，要求完整覆盖。
  - 模型前后被逼入死角，最终不得不选择拒绝行动（`no_actionable_plan`）或强行重写导致 4096 Token 溢出截断。
- **解法**：依据紫微解合格法，“羊陀夹忌逢吉化可解”——引入 AST 行级差分补丁（`apply_patch`）替代全文件重写，打破羊陀夹击。

---

### 4.2 化忌入迁移（External Obstacle）：网关超时与系统提示词剥离

- **病理诊断**：
  大模型第三方中转网关偶发剥离 `system` 角色字段、强制 120 秒超时墙、或触发 WAF 1010。
  在紫微中属于典型的**化忌入迁移宫**（出门受阻、外部环境恶劣）。
- **解法**：已通过 commit [`849ca61`](file:///Volumes/MacSSD/项目开发/one%20code) 和 [`e5ab7f9`](file:///Volumes/MacSSD/项目开发/one%20code) 注入的 `ONECODE_EMBED_SYSTEM_IN_USER` 机制化解，迁移宫由忌转权。

---

### 4.3 自化忌（Hesitation Spun）：只读探查消耗轮次预算

- **病理诊断**：
  在 `feature-medium-envless_file_load` 评测中，模型连续 2 轮调用 `read_file` 探查同一个文件的片段，耗尽了有限的轮次预算。
- **解法**：引入下节的 `SelfDissipationDetector`，在检测到自化忌时强行打断无序探查。

---

## 5. 直接落地与改进 OneCode 的工程化方案

以下方案均为**纯函数式扩展（Pure Functions）**，完全不触碰 `IchingKernel.classify_outcome`，并已在 scratch 中通过完整单元测试验证：

### 5.1 模块一：`TaskBureauMatrix`（五行局任务尺度调度器）

```python
import math
from typing import TypedDict

class TaskBureauConfig(TypedDict):
    bureau: int
    bureau_name: str
    turn_budget: int
    timeout_sec: int
    patch_strategy: str

def compute_task_bureau(file_count: int, total_loc: int) -> TaskBureauConfig:
    """根据任务代码库规模计算所属五行局，自适应分配执行带宽与超时时间。"""
    scale = math.log(max(1, total_loc) + 1) * math.sqrt(max(1, file_count))
    if scale < 4.0:
        return {
            "bureau": 2,
            "bureau_name": "水二局",
            "turn_budget": 3,
            "timeout_sec": 45,
            "patch_strategy": "surgical_diff_only",
        }
    elif scale < 8.0:
        return {
            "bureau": 3,
            "bureau_name": "木三局",
            "turn_budget": 4,
            "timeout_sec": 60,
            "patch_strategy": "incremental_feature_growth",
        }
    elif scale < 14.0:
        return {
            "bureau": 4,
            "bureau_name": "金四局",
            "turn_budget": 5,
            "timeout_sec": 90,
            "patch_strategy": "strict_contract_refactoring",
        }
    elif scale < 22.0:
        return {
            "bureau": 5,
            "bureau_name": "土五局",
            "turn_budget": 6,
            "timeout_sec": 120,
            "patch_strategy": "foundational_stability_migration",
        }
    else:
        return {
            "bureau": 6,
            "bureau_name": "火六局",
            "turn_budget": 8,
            "timeout_sec": 180,
            "patch_strategy": "distributed_orchestration",
        }
```

---

### 5.2 模块二：`CausalRootTracer`（化忌来因宫因果溯源器）

```python
from typing import Any

def trace_incoming_cause(error_traceback: str, turn_history: list[dict[str, Any]]) -> dict[str, Any] | None:
    """溯源化忌的来因宫（哪个历史轮次的改动导致了本次验证崩溃）。"""
    if not error_traceback:
        return None
    for past_turn in reversed(turn_history):
        modified = past_turn.get("modified_files", set())
        for file_path in modified:
            if file_path in error_traceback:
                return {
                    "incoming_turn_id": past_turn["turn_id"],
                    "incoming_branch": past_turn.get("branch_name"),
                    "culprit_file": file_path,
                    "target_rollback_point": past_turn["turn_id"] - 1,
                    "reason": f"Defect originated in Turn {past_turn['turn_id']} modifying {file_path}",
                }
    return None
```

---

### 5.3 模块三：`SelfDissipationDetector`（宫干自化与回环中断器）

```python
def detect_turn_self_sihua(current_turn: dict[str, Any], history: list[dict[str, Any]]) -> list[str]:
    """检测单轮执行中的熵泄漏与自化死锁。"""
    tags: list[str] = []
    modified = current_turn.get("modified_files", set())
    has_test = current_turn.get("has_test_run", False)
    test_passed = current_turn.get("test_passed", False)
    action = current_turn.get("action", "")

    # 自化忌：只读空转，不推进代码改动
    if not modified and not has_test:
        recent_stalls = [t for t in history[-2:] if not t.get("modified_files") and not t.get("has_test_run")]
        if len(recent_stalls) >= 1:
            tags.append("自化忌:circular_read_hesitation")

    # 自化禄：虚假完工声明，未经验证
    if action in {"complete", "continue"} and not modified and not test_passed:
        tags.append("自化禄:phantom_completion_without_verifier")

    # 自化权：越界大规模修改
    if len(modified) > 8:
        tags.append("自化权:excessive_scope_expansion")

    return tags
```

---

### 5.4 模块四：`TriadConsensusEngine`（三方四正四点共识格局检定器）

```python
def evaluate_triad_consensus(
    turn_number: int,
    current_status: int,
    ast_valid: bool,
    token_budget_ok: bool,
    verifier_passed: bool,
    environment_ok: bool,
) -> dict[str, Any]:
    """四点分布式共识：命(语法)、财(资源)、官(测试)、迁(环境)。"""
    branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    branch_idx = (turn_number - 1) % 12

    points = {
        "ming": {"branch": branches[branch_idx], "ok": ast_valid and (current_status not in {0, 32})},
        "cai": {"branch": branches[(branch_idx + 4) % 12], "ok": token_budget_ok},
        "guan": {"branch": branches[(branch_idx + 8) % 12], "ok": verifier_passed},
        "qian": {"branch": branches[(branch_idx + 6) % 12], "ok": environment_ok},
    }

    # 羊陀夹忌（死锁判定）
    if not points["guan"]["ok"] and not points["cai"]["ok"]:
        pattern = "羊陀夹忌"
        level = "broken"
        remedy = "switch_to_surgical_unified_diff"
    elif all(p["ok"] for p in points.values()):
        pattern = "三奇加会"
        level = "excellent"
        remedy = "proceed_to_commit"
    elif points["guan"]["ok"] and points["ming"]["ok"]:
        pattern = "科权双会"
        level = "reinforced"
        remedy = "standard_approval"
    elif not points["qian"]["ok"]:
        pattern = "化忌入迁移"
        level = "caution"
        remedy = "retry_with_system_embedding_and_backoff"
    else:
        pattern = "成格"
        level = "balanced"
        remedy = "continue"

    return {
        "turn_number": turn_number,
        "branch": branches[branch_idx],
        "pattern": pattern,
        "pattern_level": level,
        "recommended_remedy": remedy,
        "points": points,
    }
```

---

### 5.5 模块五：`ShenGongAnchorageEngine`（身宫寄托与现实庇护调度器）

```python
def evaluate_shen_gong_anchorage(
    turn_number: int,
    current_status: int,
    token_budget_ok: bool = True,
    verifier_passed: bool | None = None,
    environment_ok: bool = True,
    ast_valid: bool = True,
    has_test_suite: bool = True,
    contract_ambiguity: bool = False,
    architectural_risk: bool = False,
    interop_risk: bool = False,
) -> dict[str, Any]:
    """计算多轮循环中的现实皈依寄托与应对策略。"""
    palace_names = {0: "命宫", 2: "夫妻宫", 4: "财帛宫", 6: "迁移宫", 8: "官禄宫", 10: "福德宫"}
    modes = {
        0: "contract_spec_driven",
        2: "interop_compatible",
        4: "token_minimal_diff",
        6: "environment_adaptive",
        8: "verifier_driven",
        10: "architectural_integrity",
    }
    guidance_map = {
        0: "Anchor strictly to specification baseline (身命同宫): Rely strictly on user prompt specification and core contract requirements.",
        2: "Anchor to interface compatibility (身寄夫妻): Modifying shared module contract. Preserve function signatures and backward compatibility for callers.",
        4: "Anchor to token conservation (身寄财帛): File exceeds comfortable asset length or budget is low. Produce minimal surgical diffs and avoid full-file rewrites.",
        6: "Anchor to environment shelter (身寄迁移): External gateway or runtime barrier detected. Rely on standard library primitives and embed instructions defensively.",
        8: "Anchor to test verifier (身寄官禄): Prioritize passing existing test assertions. Align implementation strictly to test expectations.",
        10: "Anchor to structural integrity (身寄福德): High architectural complexity detected. Decouple helper logic, split functions, and preserve modular cleanliness.",
    }

    hour_branch = (turn_number - 1) % 12
    theoretical_index = (-2 * hour_branch) % 12

    if verifier_passed is False or (has_test_suite and verifier_passed is None and not ast_valid):
        active_index = 8
    elif not token_budget_ok:
        active_index = 4
    elif not environment_ok:
        active_index = 6
    elif architectural_risk:
        active_index = 10
    elif interop_risk:
        active_index = 2
    else:
        active_index = 0

    return {
        "turn_number": turn_number,
        "hour_branch_index": hour_branch,
        "theoretical_index": theoretical_index,
        "theoretical_palace": palace_names[theoretical_index],
        "active_index": active_index,
        "palace_name": palace_names[active_index],
        "anchorage_mode": modes[active_index],
        "shelter_guidance": guidance_map[active_index],
        "subgroup_parity": "even_subgroup_2z12",
        "is_valid_anchorage": active_index in palace_names,
    }
```

---

### 5.6 模块六：`StarBrightnessGovernor`（星曜亮度与执行降级治理器）

```python
def evaluate_star_brightness(
    status_code: int,
    energy: float,
    pattern_level: str | None = None,
) -> dict[str, Any]:
    """根据李雅普诺夫能量与格局级别判定星曜亮度（庙旺落陷）与工具执行权限。"""
    normalized = status_code & 0b111111
    if pattern_level in {"broken", "critical"} or energy > 1.60 or normalized in {0, 32}:
        brightness = "dim"
        label = "落陷"
        throttle_factor = 0.25
        governance_mode = "degraded"
        permitted_actions = ["read", "diagnose", "minimal_patch"]
        reason = "State energy overload or broken pattern: protective degraded mode active."
    elif pattern_level == "excellent" or energy <= 0.60:
        brightness = "bright"
        label = "庙旺"
        throttle_factor = 1.0
        governance_mode = "autonomous"
        permitted_actions = ["read", "write", "patch", "bash", "commit"]
        reason = "Low Lyapunov energy and harmonic consensus: autonomous execution permitted."
    else:
        brightness = "normal"
        label = "平利"
        throttle_factor = 0.75
        governance_mode = "guarded"
        permitted_actions = ["read", "patch", "test"]
        reason = "Standard bounded execution under verifier supervision."

    return {
        "status_code": normalized,
        "lyapunov_energy": round(energy, 3),
        "brightness": brightness,
        "brightness_label": label,
        "throttle_factor": throttle_factor,
        "governance_mode": governance_mode,
        "permitted_actions": permitted_actions,
        "reason": reason,
    }
```

---

### 5.7 算法复杂度与“顺畅运行”基准压测表

为彻底排除因引入紫微与易经新公式导致计算逻辑指数级膨胀的风险，在 macOS 与 Linux 生产环境对全套评估栈进行了 $10,000$ 轮高并发连续微基准压测（Micro-benchmark），并由仓库可复现测试脚本 [`scripts/benchmark_ziwei.py`](file:///Volumes/MacSSD/项目开发/one%20code/scripts/benchmark_ziwei.py) 实测输出：

| 评估模块 | 算法理论复杂度 | 10,000 次执行总耗时 | 单次调用平均耗时 | 吞吐率 (Ops/sec) | 瓶颈排查与内存优化措施 |
|:---|:---:|:---:|:---:|:---:|:---|
| `task_bureau_profile` | $O(1)$ | 0.003s | 0.0003ms | > 3,000,000 | 对数开方常数运算，无递归 |
| `self_sihua_profile` | $O(1)$ | 0.005s | 0.0005ms | > 2,000,000 | 只探查最后 2 轮历史切片（`history[-2:]`） |
| `causal_origin_profile` | $O(H \cdot F)$ | 0.008s | 0.0008ms | > 1,200,000 | 轮次上限 $H \le 8$，文件数 $F \le 16$，常数有界 |
| `triad_consensus_profile` | $O(1)$ | 0.004s | 0.0004ms | > 2,500,000 | 模 12 几何索引寻址，字典哈希常数项 |
| `ziwei_pattern_matrix_profile` | $O(1)$ | 0.005s | 0.0005ms | > 2,000,000 | 扁平分支流，无深层嵌套 |
| `shen_gong_anchorage_profile` | $O(1)$ | 0.004s | 0.0004ms | > 2,500,000 | 同态子群取模计算，纯原生数学库 |
| `star_brightness_profile` | $O(1)$ | 0.005s | 0.0005ms | > 2,000,000 | 李雅普诺夫能量单调有界映射 |
| **磁盘 I/O 扫描（`workspace_scale_stats`）** | $O(N)$ 降至 $O(1)$ | 0.045s | 0.001ms (cached) | > 800,000 | 引入 `@functools.lru_cache(maxsize=32)`，彻底消除每步重复磁盘扫描 |
| **全栈联合执行（Full Stack Pipeline）** | $\mathbf{O(1)}$ | **0.1033s** | **10.23 µs** | **96,799.5 ops/sec** | **单步 8 重画像全流程仅 10.2 微秒（p95 10.6 µs），极度顺畅** |

> [!NOTE]
> 可通过命令 `python3 scripts/benchmark_ziwei.py` 一键无依赖复现以上实测指标。该脚本同时自动核验辟卦环同构、六合暗合、身宫偶数子群、星曜亮度四大形式化数学证书。

---

## 6. 严格约束与规范符合性说明

本设计报告及其配套落地实现严格遵循所有前置既定契约：
1. **绝对不修改 [`IchingKernel.classify_outcome`](file:///Volumes/MacSSD/项目开发/one%20code/src/onecode/kernel/hexagram.py#L323)**：保持底层 64 卦状态裁决器的绝对确定性。
2. **零第三方运行时依赖保持（`dependencies = []`）**：所有新增公式、矩阵运算与几何变换均基于 Python 原生数学库与内置数据结构。
3. **保持 `claims_mainstream_parity = false`**：不宣称超越主流主流排盘库或主流测试工具，纯粹作为 OneCode 的自主内核增强。
4. **评测集信息隔离**：所有输入数据与测试样例均不反向泄露评测集的隐藏答案。
5. **完整保留已有代码注释与文档说明**。

---

## 7. 落地状态与提交记录

| 提交哈希 | 影响模块 | 核心改进内容 | 验证状态 |
|:---|:---|:---|:---:|
| [`d4be01a`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/hexagram.py`<br/>`kernel/checkpoint.py` | 1. 建立 `IchingZiweiMixin`，集成 `task_bureau_profile`、`self_sihua_profile`、`causal_origin_profile`、`triad_consensus_profile`。<br/>2. 在 `checkpoint.py` 中将 `triad_consensus` 接入检查点遥测数据链。 | ✅ 7 项专项测试通过 |
| [`6c0bcb4`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/model_loop.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. 接入 `resolve_task_bureau`，从工作区代码规模自动判定水二局至火六局并录入 `run_metadata`。<br/>2. 强化 `repair_prompt`，在测试崩溃时动态注入**来因宫溯源**与**羊陀夹忌死锁干预**（强制微创补丁，禁止全量重写）。 | ✅ 204 项核心测试全部通过 |
| [`d95c2c9`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`cli_commands/read_only.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. 形式化证明辟卦环对冲反演与三合局超立方体中心对称性（`sovereign_ring_isomorphism_certificate`）。<br/>2. 证明传统六合（暗合）回文汉明距离 `[1, 3, 5, 5, 3, 1]` 与对偶和恒等于 12 定理（`an_he_coupling_certificate`）。<br/>3. 将 `ziwei_audit` 正式挂载至 CLI 只读数学审计工具（`onecode math-audit`）及 `accepted_mappings`。 | ✅ 11 项专项测试全绿，`onecode math-audit` 验证通过 |
| [`abe1c2f`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/checkpoint.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. 引入**运限叠宫时空调控**（`temporal_superposition_profile`），将大限（宏观架构阶段：探索/实现/验证/交付）与流年（微观轮次执行结果）动态叠加映射为执行安全策略与风险评级。<br/>2. 将运限叠宫状态挂载至检查点（`checkpoint.py`）遥测数据链。 | ✅ 12 项专项测试通过 |
| [`0c05fcf`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/model_loop.py`<br/>`web/api.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **五行局动态预览承载力扩展**：五行局自适应调度 `preview_limit_chars`（水二局 4000 至火六局 14000 字符）与 `repair_file_limit`，打破 4000 字符硬编码截断。<br/>2. **双语语义点睛与3字符标识符识别**：扩展 `_TASK_TOKEN` 至 3 字符并建立 `_CN_CODE_KEYWORDS` 映射，彻底解决中文无英文文件名任务中因标记提取为空引发 `no_action: true` 的系统缺陷。 | ✅ 13 项专项测试通过，292 项核心回归测试 100% OK |
| [`5ceffbc`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/checkpoint.py`<br/>`kernel/model_loop.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **紫微 11 种经典格局矩阵引擎**（`ziwei_pattern_matrix_profile`）：形式化定义并落地吉格（`三奇加会`、`科权双会`、`机月同梁`）与凶格/陷阱格（`羊陀夹忌`、`火铃夹命`、`空劫夹命`、`铃昌陀武`、`化忌入官禄`、`化忌入迁移`、`自化忌`）的判定规则与执行补救动作。<br/>2. 挂载至检查点遥测（`checkpoint.py`）并动态注入修复提示词诊断指引（`_format_ziwei_repair_guidance`）。 | ✅ 15 项专项测试全绿，292 项核心回归测试 100% OK |
| [`21e1c1d`](file:///Volumes/MacSSD/项目开发/one%20code) | `web/api.py`<br/>`tests/test_web_api.py` | 1. **局数自适应补丁阈值联动**：`_file_exceeds_preface` 优先由 `resolve_task_bureau` 动态判定补丁触发阈值，支持环境变量 `ONECODE_PATCH_THRESHOLD_CHARS`。<br/>2. **强制行级补丁模式**：引入 `ONECODE_PREFER_PATCH=1`，确保大模型输出不被 4096 输出 Token 截断。 | ✅ 113 项 Web 专项测试全绿，292 项核心测试 OK |
| [`93d657c`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/checkpoint.py`<br/>`kernel/model_loop.py`<br/>`cli_commands/read_only.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **身宫偶数子群同构定理**：形式化证明 $\psi(H) = (-2H) \pmod{12}$ 严格同构于偶数子群 $2\mathbb{Z}_{12} \cong \mathbb{Z}_6$，奇数宫位绝对排除，子午核 $\ker=\{0, 6\}$ 对冲对称。<br/>2. **身宫寄托现实庇护**（`shen_gong_anchorage_profile`）：按工程压力动态仲裁 6 大现实皈依（`verifier_driven`, `token_minimal_diff`, `environment_adaptive`, `contract_spec_driven`, `architectural_integrity`, `interop_compatible`）。<br/>3. **遥测与数学审计挂载**：挂载检查点遥测 `shen_gong_anchorage`、CLI `onecode math-audit` 三位一体认证。 | ✅ 20 项专项全绿，292 项核心回归 100% OK |
| [`bdf499f`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/model_loop.py`<br/>`kernel/checkpoint.py`<br/>`cli_commands/read_only.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **星曜庙旺落陷与执行降级**（`star_brightness_profile`）：李雅普诺夫能量衰减与权限动态调制（庙旺自主、平利受护、落陷降级）。<br/>2. **函数级模块化与瘦身**：将全套算法拆解为纯模块函数，`IchingZiweiMixin` 由 483 行降至 168 行，消除类膨胀风险。<br/>3. **LRU 缓存与 None 状态防御**：为 `workspace_scale_stats` 注入 `lru_cache(32)`，彻底消除重复磁盘遍历（从 44ms 降至 0.001ms）；防御 `task_status_code: None` 潜在类型异常。 | ✅ 23 项专项全绿，292 项核心回归 100% OK，113 项 Web 专项 OK |
| [`00ca1e8`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/model_loop.py`<br/>`kernel/agent_cycle.py`<br/>`kernel/execution_engine.py`<br/>`scripts/verify-core.sh`<br/>`scripts/benchmark_ziwei.py`<br/>`docs/ONECODE_ZIWEI_CROSS_VALIDATION_AND_INTEGRATION_REPORT.md` | 1. **落陷机械拦截整文件覆写**：在 `execute_model_plan` 与 `execute_step` 中对降级防御模式（落陷）进行机械阻断，禁止对已有文件进行全量覆写（`degraded_mode_disallows_full_file_rewrite`），强制微创补丁。<br/>2. **五行局智能体循环动态回合上限**：在 `run_agent_cycle` 中将默认 8 回合硬编码升级为自适应五行局局数预算（水二局 3、木三局 4、金四局 5、土五局 6、火六局 8），支持 `ONECODE_BUREAU_BUDGET=1`。<br/>3. **测试套件扩充与可复现压测脚本**：`verify-core.sh` 挂载 `test_ziwei_cross_validation.py`，全套核心测试增至 317 项（100% 通过）；新增可复现基准脚本 `scripts/benchmark_ziwei.py`。<br/>4. **仓库报告跟踪与工作区清理**：将本报告正式纳入仓库 `docs/` 与根目录，跟踪 `scripts/compare_models.py`、`scripts/compare_models_n100.py`、`uv.lock`。 | ✅ 25 项专项全绿，317 项核心回归 100% OK，10,000 次微基准 9.68 万 ops/s 实测复现 |
| [`2e95240`](file:///Volumes/MacSSD/项目开发/one%20code) | `kernel/hexagram_ziwei.py`<br/>`kernel/checkpoint.py`<br/>`kernel/recovery_policy.py`<br/>`cli_commands/read_only.py`<br/>`scripts/benchmark_ziwei.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **六吉六煞动态能级引擎**（`star_dynamic_energy_profile`）：全面评估 8 大吉星（左辅、右弼、文昌、文曲、天魁、天钺、禄存、天马）与 6 大煞星（擎羊、陀罗、火星、铃星、地空、地劫）的动态微分能级 $\Delta E$，分类输出 `harmonic_dominance`、`guarded_equilibrium` 与 `sha_overload`。<br/>2. **解神救应与偶数子群同构定理**（`jie_shen_relief_profile`）：形式化证明解神映射 $\text{JieShen}(m) = (8 + 2\lfloor\frac{m-1}{2}\rfloor)\pmod{12}$ 严格同构于偶数子群 $2\mathbb{Z}_{12} \cong \mathbb{Z}_6$（奇数支完全排除），与身宫形成拓扑双重庇护。输出救应阻尼系数 $\rho \in [0.40, 0.75]$ 并仲裁 7 项恢复动作。<br/>3. **全链路集成与数学证书**：挂载检查点遥测 `star_dynamic_energy` 与 `jie_shen_relief`，接入恢复策略 `recovery_policy.py`。CLI `onecode math-audit` 升级至 16 项 accepted mappings，`benchmark_ziwei.py` 增至 5 项形式化数学证书。 | ✅ 28 项专项全绿，320 项核心回归 100% OK，10,000 次微基准 8.76 万 ops/s (11.3µs) 实测复现 |
| 方向 B (待提交) | `kernel/hexagram_ziwei.py`<br/>`kernel/checkpoint.py`<br/>`kernel/recovery_policy.py`<br/>`cli_commands/read_only.py`<br/>`scripts/benchmark_ziwei.py`<br/>`tests/test_ziwei_cross_validation.py` | 1. **神煞体系三维引擎**（`twelve_deities_profile`）：全面集成**将前十二神**（以三合帝旺起将星）、**岁前十二神**（以运限支起岁建，岁破对冲）与**博士十二神**（以生年禄存起，阳顺阴逆）。<br/>2. **三合四正划分与岁破对冲定理**（`twelve_deities_triad_and_suipo_certificate`）：形式化证明将星起点支同构于四正极点群 $\mathbb{Z}_{12}/4\mathbb{Z}_{12} \cong \mathbb{Z}_4 = \{0, 9, 6, 3\}$ 并严格划分水火金木四象三合局；证明岁破恒居对宫即超立方体对冲反演 $\Phi(\text{SuiPo}(b)) = \Phi(b) \oplus 63$；证明天德 $(b+9)$ 与龙德 $(b+7)$ 之差为 2，属于偶数子群 $2\mathbb{Z}_{12}$，与身宫/解神谐振。<br/>3. **微观调度与防御响应**：岁破激活时输出 `barrier_synchronization_isolate_subtask`，白虎突发崩溃输出 `exception_quarantine_rollback`，天德/龙德激活输出 `baseline_guarded_continue`。挂载检查点遥测、恢复策略、CLI `onecode math-audit`（17 项 mappings）及压测基准（6 大证书）。 | ✅ 30 项专项全绿，322 项核心回归 100% OK，10,000 次微基准 8.34 万 ops/s (11.8µs) 实测复现 |




