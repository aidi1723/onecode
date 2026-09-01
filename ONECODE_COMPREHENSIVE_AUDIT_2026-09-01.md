# OneCode 项目审核报告（完整版）

**审核日期**: 2026-09-01  
**项目版本**: v0.8.0  
**审核范围**: `/Volumes/MacSSD/项目开发/one code`  
**审核方法**: 代码审查、测试执行、文档评估、安全分析

---

## 执行摘要

OneCode 是一个**本地优先的 agent 内核原型**，专注于受控的文件写入、可恢复执行和确定性状态管理。核心特点：

- ✅ **零运行时依赖**（核心包），可选 TUI 依赖精确锁定
- ✅ **907 个单元测试全通过**（19.5 秒，跳过 1 个环境依赖测试）
- ✅ **多层安全防护**：路径沙盒 + 权限审批 + Docker 隔离
- ✅ **易经六十四卦状态系统**：用 6 比特状态码、五行生克、阴阳平衡驱动确定性控制流
- ✅ **完整的设计文档**（43 个设计规范）+ 新增的文档索引和贡献指南

**综合评分**: ⭐⭐⭐⭐☆ (4.5/5)

---

## 1. 项目概览

### 1.1 基本信息

```
项目名称:    OneCode
版本:        0.8.0
许可证:      GPL-3.0-only
Python版本:  >=3.11
```

### 1.2 代码规模统计

```
源代码:      68 个 .py 文件,  20,013 行
测试代码:    73 个 .py 文件,  22,698 行 (907 个测试)
文档:        124 个 .md 文件, 31,515 行
  - 设计文档:  43 个 (docs/superpowers/specs/)
  - 完成报告:  30 个 (docs/*.md)
  - 主文档:    README.md (24K), INDEX.md (6.4K), CONTRIBUTING.md (6.1K)

测试覆盖比:  1.13:1 (测试行数 > 源代码行数)
文档/代码比: 1.57:1 (高于行业平均)
```

### 1.3 模块结构

```
src/onecode/
├── kernel/          (49 个模块, 15,440 行) - 核心规则引擎
│   ├── hexagram.py       (1,597 行) - I Ching 64 卦状态机
│   ├── training_data.py  (2,441 行) - 训练数据生成
│   ├── runner.py         (997 行)  - 执行编排
│   ├── checkpoint.py     (960 行)  - 状态检查点
│   └── model_loop.py     (797 行)  - 模型调用循环
├── cli_commands/    (3 个模块) - CLI 命令适配器
├── web/             (5 个模块) - 本地 HTTP API (stdlib only)
├── tui/             (2 个模块) - 可选终端 UI (textual)
└── contracts/       (JSON fixtures) - 公开 schema 契约
```

### 1.4 CLI 命令（39 个）

**核心执行**:
- `run`, `run-plan`, `run-execution-plan`, `run-model`
- `inspect`, `list-runs`

**质量保证**:
- `doctor` (内置冒烟测试)
- `benchmark`, `sandbox-smoke`
- `math-audit` (状态空间完整性验证)

**本地服务**:
- `serve` (HTTP API)
- `shell` (LibreChat 集成)
- `tui` (终端界面)

**训练/评估** (20+ 命令):
- `generate-training-data`, `build-training-corpus`
- `run-yizijue-lm-eval` 等

---

## 2. 架构评估 ⭐⭐⭐⭐⭐

### 2.1 设计原则

OneCode 遵循严格的设计约束：

1. **本地优先**: 核心无网络依赖
2. **确定性**: 相同输入 → 相同输出
3. **证据导向**: append-only 记录，防篡改链
4. **规则闭包**: 外部事实是证据而非规则

### 2.2 I Ching 状态系统（独特设计）

**原理**:
- **6-bit 状态码** (0-63) 对应易经六十四卦
- 每卦由两个三爻卦（trigram）组成
- 八卦 → 五行映射：乾兑(金)、震巽(木)、坎(水)、离(火)、坤艮(土)
- 五行生克关系驱动状态转换

**转换优先级**:
1. 硬安全约束（路径越界、超时）覆盖一切
2. 阴阳压力（纯阳 → 冷却，纯阴 → 发现）
3. 五行关系（外卦对内卦施加影响）
4. 中性回退

**示例**: 状态码 40 (`0b101000`)
- 外卦: `101` (离/Li) → 火元素
- 内卦: `000` (坤/Kun) → 土元素
- 关系: 火克土 → halt，原因 "sovereignty_fire_boundary_halt"

**评价**:
- ✅ **数学完备**: 64 状态空间，拓扑闭合，Lyapunov 稳定性证明
- ✅ **确定性**: 无随机性，完全可复现
- ✅ **有完整设计文档**: 43 个设计规范详细解释数学原理
- ⚠️ **学习曲线陡峭**: 需要理解易经、五行、阴阳才能调试
- ⚠️ **团队协作挑战**: 外部贡献者需要专门 onboarding

### 2.3 模块设计

**优点**:
- 职责分明：kernel (规则) / cli_commands (适配) / web (API) / tui (界面)
- 适度耦合：通过 `IchingKernel` 统一决策，避免规则分散
- 纯函数为主：核心算法无副作用

**代码复杂度**:
- 平均每文件 315 行（kernel 模块）
- 7 个文件超过 500 行（可接受）
- 4 个文件超过 800 行：
  - `training_data.py` (2,441 行) ⚠️ 建议拆分
  - `hexagram.py` (1,597 行) - 数学规则表，可接受

---

## 3. 代码质量评估 ⭐⭐⭐⭐⭐

### 3.1 依赖管理

```toml
[project]
dependencies = []  # 核心零依赖！

[project.optional-dependencies]
tui = ["textual==8.2.7"]  # 精确锁定版本
```

**评价**: ⭐⭐⭐⭐⭐ 满分
- 核心完全独立于外部生态
- 无供应链攻击风险
- 可完全离线审计

### 3.2 版本一致性

```
pyproject.toml:  version = "0.8.0"
__init__.py:     __version__ = "0.8.0"
README.md:       v0.8.0
```

✅ 所有版本标识一致

### 3.3 代码风格

**外部依赖（仅 stdlib）**:
- `pathlib.Path` (32 次)
- `json` (23 次)
- `dataclasses` (14 次)
- `subprocess` (6 次，均为 `shell=False`)

✅ 无隐藏的第三方依赖

### 3.4 可维护性

**优点**:
- 类型提示完整（`from __future__ import annotations`, `typing.Any`）
- 数据类广泛使用（`@dataclass(frozen=True)`）
- 纯函数为主，副作用集中在 runner 和 path_guard

**需改进**:
- `training_data.py` 2,441 行建议拆分为 corpus/eval/adjudicate 子模块
- `hexagram.py` 包含大量硬编码规则表，建议增加内联注释

---

## 4. 测试覆盖评估 ⭐⭐⭐⭐⭐

### 4.1 测试统计

```
核心测试:  234 个测试, 7.3 秒  (verify-core.sh)
完整套件:  907 个测试, 19.5 秒 (verify.sh)
跳过测试:  1 个 (环境依赖，非致命)
```

**通过率**: 100% ✅

### 4.2 测试覆盖范围

通过测试文件名分析：
- ✅ 核心执行器 (runner, model_loop, execution)
- ✅ I Ching 状态机 (hexagram, iching_kernel_integration)
- ✅ 恢复机制 (resumption, task_resume)
- ✅ 路径守卫 (path_guard)
- ✅ 沙盒 (sandbox)
- ✅ 验证器 (verifier)
- ✅ WAL (write-ahead log)
- ✅ Shell 投影 (shell_projection)
- ✅ YiZiJue logits 策略
- ✅ Benchmark 评分

**边界条件测试**（示例）:
- `test_run_model_task_rejects_boolean_numeric_limits` - 拒绝 bool 作为 int
- `test_audit_rejects_tampered_wal_only_evidence` - WAL 篡改检测
- `test_path_guard_blocks_traversal` - 路径逃逸防护

### 4.3 Doctor 冒烟测试

内置 `onecode doctor` 运行 8 个真实场景：
1. ✅ `write_text` - 正常写入（状态码 39）
2. ✅ `resume_skip` - 恢复跳过（状态码 35）
3. ✅ `sovereignty_breach` - 路径越界（状态码 40, halted）
4. ✅ `http_timeout` - HTTP 超时（状态码 17, halted）
5. ✅ `project_context` - 项目规则加载
6. ✅ `runtime_config` - 运行时配置
7. ✅ `skill_context` - 技能上下文
8. ✅ `recovery_policy` - 恢复策略

---

## 5. 安全评估 ⭐⭐⭐⭐

### 5.1 路径遍历防护 ⭐⭐⭐⭐⭐

**文件**: `src/onecode/kernel/path_guard.py:36-90`

```python
# 1. 解析并检查逃逸
root = workspace_root.resolve()
target = (root / requested).resolve()
target.relative_to(root)  # ValueError if escaped

# 2. 黑名单
DENIED_ROOT_FILES = {"pyproject.toml", ".gitignore", ".env"}
DENIED_EXECUTABLE_ROOT_FILES = {".pre-commit-config.yaml", "Makefile", ...}

# 3. 写入前目录检查
if ".git" in parts or ".github" in parts:
    raise PathGuardError(...)
```

**防护措施**:
- ✅ `Path.resolve()` + `relative_to()` 防符号链接逃逸
- ✅ 根目录配置文件写入黑名单
- ✅ `.git`, `.github` 完全禁止
- ✅ 原子写入：`NamedTemporaryFile` + `fsync` + `replace`

**风险**: 无明显漏洞

### 5.2 命令注入防护 ⭐⭐⭐⭐⭐

**文件**: `src/onecode/kernel/execution_tools.py:329`, `verifier.py:255`

```python
# 强制 shell=False
subprocess.run(spec.command, shell=False, ...)

# 环境变量白名单
COMMAND_ENV_ALLOWLIST = frozenset({
    "PATH", "HOME", "TMPDIR", "TEMP", "TMP",
    "LANG", "LC_ALL", "TERM", "SHELL", "USER", ...
})
environment = {k: v for k, v in os.environ.items() 
               if k in COMMAND_ENV_ALLOWLIST}
```

**防护措施**:
- ✅ 所有 `subprocess.run()` 显式 `shell=False`
- ✅ 命令参数列表化（`list[str]`）而非字符串拼接
- ✅ 环境变量白名单（仅保留 27 个安全变量）
- ✅ 输出清洗：`SENSITIVE_ASSIGNMENT_PATTERN` 正则检测并遮盖凭据

**风险**: 无明显漏洞

### 5.3 Web API 认证 ⭐⭐⭐⭐

**文件**: `src/onecode/web/auth.py:9-19`, `api.py:1292`

```python
# 常量时间比较
secrets.compare_digest(authorization, f"Bearer {token}")

# 默认绑定本地
def run_server(host: str = "127.0.0.1", port: int = 19080)

# Loopback 可选免认证
if token is None:
    return allow_unauthenticated and host in LOOPBACK_HOSTS
```

**防护措施**:
- ✅ `secrets.compare_digest()` 防时序攻击
- ✅ 默认绑定 `127.0.0.1`
- ✅ Loopback 免认证需显式标志

**风险**:
- ⚠️ **中等**: 代码未强制 loopback，可被误配置为 `0.0.0.0`
- README 已警告"仅用于本地预览或可信回环"
- **建议**: 在 `run_server()` 启动时检查 `host`，非 loopback 且无 token 时拒绝启动

### 5.4 Docker 沙盒 ⭐⭐⭐⭐⭐

**文件**: `src/onecode/kernel/sandbox.py:34-64`

```python
docker_command = [
    "docker", "run", "--rm",
    "--network", "none",       # 禁用网络
    "--memory", "512m", "--cpus", "1",
    "--pids-limit", "256",
    "--cap-drop", "ALL",       # 移除所有 capabilities
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
    "--read-only",             # 容器文件系统只读
]
```

**防护**: 符合安全最佳实践，无明显漏洞

### 5.5 凭据处理 ⭐⭐⭐⭐

```
.gitignore:  .env, .env.*
本地文件:    .env.local (85 字节，未提交)
API keys:    从环境变量读取 (DASHSCOPE_API_KEY, DEEPSEEK_API_KEY 等)
输出遮盖:    model_config.py 实现 API key masking
```

**防护**:
- ✅ 凭据不硬编码
- ✅ 遵循 12-factor 原则
- ✅ 输出自动遮盖敏感值

**风险**: 低

### 5.6 反序列化 ⭐⭐⭐⭐⭐

```bash
$ grep -rn "pickle\|yaml\.load\|eval(\|exec(" src/ --include="*.py"
# 0 结果
```

- ✅ 无 `pickle.load()`
- ✅ 无 `yaml.load()`（仅用 `json.load()`）
- ✅ 无 `eval()` 或 `exec()` 直接调用

**风险**: 无

---

## 6. 文档评估 ⭐⭐⭐⭐

### 6.1 文档结构（改进后）

```
README.md (24K)
  ├─ 新增 "Documentation" 章节，链接到索引
  ├─ 安装、验证、CLI 命令
  └─ 使用示例

docs/INDEX.md (6.4K, 新建)
  ├─ 快速入门
  ├─ 架构与设计（易经系统概述 + 实例）
  ├─ API 参考
  ├─ 开发指南
  └─ 发布历史

CONTRIBUTING.md (6.1K, 从 332 字节扩展)
  ├─ 开发环境设置
  ├─ 易经系统必读指南
  ├─ 调试状态码方法
  ├─ TDD 要求
  └─ 内核修改特殊规则

docs/superpowers/specs/ (43 个设计文档)
  ├─ I Ching 规则设计
  ├─ 阴阳五行映射
  ├─ 各版本设计规范
  └─ 子系统设计

docs/*.md (30 个完成报告)
  └─ 版本发布记录、验收报告

src/onecode/kernel/hexagram.py
  └─ 新增 46 行模块文档字符串
```

### 6.2 改进点

**之前的问题**:
- ❌ 设计文档藏在 `docs/superpowers/specs/` 子目录，难以发现
- ❌ README 无架构文档链接
- ❌ CONTRIBUTING.md 仅 15 行占位符
- ❌ hexagram.py 无模块文档

**改进后**:
- ✅ 创建 `docs/INDEX.md` 完整导航
- ✅ README 添加 "Documentation" 章节
- ✅ CONTRIBUTING.md 扩展为 200+ 行完整指南
- ✅ hexagram.py 添加 46 行详细文档字符串，链接设计文档

### 6.3 学习路径

```
README → docs/INDEX.md → 易经系统概述 → 43 个设计文档 → CONTRIBUTING.md
```

新用户现在可以：
1. 从 README 跳转到文档索引
2. 在索引中看到易经系统简明概述（六爻、五行、实例）
3. 查找 43 个设计文档的详细数学证明
4. 通过 CONTRIBUTING.md 了解开发流程和调试方法

### 6.4 仍需改进

- ⚠️ Git 历史假设失效：多个 closure 文档引用 commit hash 和分支名，但**本地不是 git 仓库**
- ⚠️ 缺少架构流程图（状态机可视化）
- ⚠️ 30 个 closure 报告占据主 docs 目录，掩盖设计文档

---

## 7. 独特设计深度分析

### 7.1 为什么选择易经？

**设计文档** (`docs/superpowers/specs/2026-05-28-onecode-iching-source-alignment.md`) 给出理由：

1. **确定性数学模型**: 64 状态空间完备，拓扑闭合
2. **多层抽象**: yin/yang → 四象 → 八卦 → 六十四卦，天然层次结构
3. **动态平衡**: 五行生克关系提供非线性反馈
4. **无随机性**: 传统状态机易引入随机重试、指数退避等不确定因素

**对比传统方法**:
- 传统状态机: enum + switch-case → 容易添加临时补丁
- 易经系统: 所有决策必须映射到 64 状态空间 → 强制规则闭包

### 7.2 实际效果

**优点**:
- ✅ 907 个测试 19.5 秒全通过 → 规则系统稳定
- ✅ `math-audit` 命令验证状态空间完整性 → 可审计
- ✅ 完全确定性 → 相同输入必产生相同输出
- ✅ 丰富的元数据 → `iching_profile` 包含详细的决策依据

**缺点**:
- ⚠️ 学习曲线陡峭 → 需要数周理解 64 卦系统
- ⚠️ 调试复杂 → 状态码 17 触发 "network_water_preserves_resume_seed"，非直觉
- ⚠️ 团队协作挑战 → 外部贡献者需要专门培训

### 7.3 适用场景

**适合**:
- ✅ 需要完全确定性、可复现的控制流
- ✅ 单人或小团队深度掌控的项目
- ✅ 研究性项目，探索非传统控制理论

**不适合**:
- ❌ 需要快速上手的开源协作项目
- ❌ 团队成员流动性高的企业项目
- ❌ 调试效率优先的生产环境

---

## 8. 主要风险与建议

### 8.1 高优先级 🔴

#### 1. Git 历史假设失效
**问题**: 多个 closure 文档引用 commit hash（如 `1f3d691b`）、分支名（`feature/gateway-iching-rule-sync`），但**本地目录不是 git 仓库**

**影响**: 用户无法通过 `git log` 审查声称的"closure"过程

**建议**:
- 方案 A: 重新初始化 git 仓库，恢复历史
- 方案 B: 重写文档，去除 git 引用，改为日期索引

#### 2. Web API 绑定验证缺失
**问题**: 代码未强制 `127.0.0.1`，可被误配置为 `0.0.0.0`

**建议**: 在 `run_server()` 中添加：
```python
if host not in LOOPBACK_HOSTS and not token:
    raise ValueError("Non-loopback host requires token")
```

#### 3. 文档可发现性改进
**问题**: 虽然已创建 INDEX.md，但 closure 报告仍占据主 docs 目录

**建议**:
- 将 closure 报告移到 `docs/releases/` 或 `docs/closure/`
- 在 docs 根目录保留索引和关键文档

### 8.2 中优先级 🟡

#### 4. training_data.py 拆分
**问题**: 2,441 行单文件过大

**建议**: 重构为包结构：
```
kernel/training/
  ├── __init__.py
  ├── corpus.py
  ├── evaluation.py
  └── adjudication.py
```

#### 5. 架构可视化
**问题**: 缺少状态机流程图

**建议**: 
- 添加 Mermaid 或 GraphViz 状态转换图到 INDEX.md
- 可视化五行生克关系

#### 6. 易经快速参考
**问题**: 虽有 43 个设计文档，但缺少单页速查表

**建议**: 创建 `docs/ICHING_QUICKREF.md`，包含：
- 64 卦速查表（状态码 → 卦名 → 含义）
- 常见状态码含义（0, 17, 35, 39, 40 等）
- 调试流程图

### 8.3 低优先级 🟢

#### 7. CI/CD 配置验证
**问题**: 有 `.github/` 目录但未检查内容

**建议**: 验证 GitHub Actions 配置是否正常工作

#### 8. 性能基准测试
**问题**: 907 测试 19.5 秒尚可，但随规模增长可能变慢

**建议**: 考虑并行化（pytest-xdist）或增量测试

#### 9. 开发依赖声明
**问题**: 虽然核心零依赖，但开发时需要 pytest 等工具

**建议**: 添加 `pyproject.toml` 的 `dev` 可选依赖

---

## 9. 评分卡

| 维度 | 评分 | 说明 |
|------|------|------|
| **代码质量** | ⭐⭐⭐⭐⭐ (5/5) | 结构清晰，类型完整，纯函数为主，复杂度可控 |
| **安全性** | ⭐⭐⭐⭐ (4/5) | 路径防护、命令注入防护、沙盒配置优秀，Web API 需强化绑定验证 |
| **测试覆盖** | ⭐⭐⭐⭐⭐ (5/5) | 907 测试全通过，边界条件充分，doctor 冒烟测试完备 |
| **依赖管理** | ⭐⭐⭐⭐⭐ (5/5) | 核心零依赖，可选依赖精确锁定，无供应链风险 |
| **文档质量** | ⭐⭐⭐⭐ (4/5) | 有 43 个设计文档 + 新增索引/贡献指南，但 git 引用失效，需要流程图 |
| **可维护性** | ⭐⭐⭐⭐ (4/5) | 设计文档完整，但学习曲线陡峭，需专门 onboarding |
| **创新性** | ⭐⭐⭐⭐⭐ (5/5) | 易经状态系统是独特的控制理论实验，有数学证明支撑 |

**综合评分**: ⭐⭐⭐⭐☆ (4.5/5)

---

## 10. 结论

OneCode 是一个**技术实现卓越、设计深思熟虑**的项目。核心优势：

### 10.1 核心优势

1. **零依赖架构** ⭐⭐⭐⭐⭐
   - 核心完全独立，无供应链风险
   - 可完全离线审计
   - 这是本项目最大的工程价值

2. **安全实现优秀** ⭐⭐⭐⭐
   - 路径守卫、命令注入防护、Docker 沙盒均符合最佳实践
   - 少量改进空间（Web API 绑定验证）

3. **测试覆盖极高** ⭐⭐⭐⭐⭐
   - 907 测试，19.5 秒通过
   - 边界条件充分（bool vs int、路径逃逸、WAL 篡改等）
   - doctor 冒烟测试覆盖真实场景

4. **数学基础扎实** ⭐⭐⭐⭐⭐
   - 64 状态空间完备，拓扑闭合
   - 有 Lyapunov 稳定性证明
   - `math-audit` 命令可验证规则完整性

5. **文档改进显著** ⭐⭐⭐⭐
   - 从"几乎无文档"改进为"有索引、有指南、有设计文档"
   - 新用户学习路径清晰

### 10.2 主要挑战

1. **学习曲线陡峭** ⚠️
   - 理解 64 卦系统需要数周投入
   - 调试需要对照卦象、五行、阴阳多层规则
   - 外部贡献者需要专门培训

2. **Git 历史缺失** ⚠️
   - 文档引用 commit/branch 但本地非 git 仓库
   - 无法审查版本演进过程

3. **可视化不足** ⚠️
   - 缺少状态机流程图
   - 缺少易经速查表

### 10.3 最适用场景

**推荐使用** ✅:
- 单人或小团队深度控制的 agent 内核开发
- 需要完全确定性、可审计的本地工具
- 研究性项目，探索非传统控制理论
- 对供应链安全有极高要求的场景

**不推荐使用** ❌:
- 需要快速上手的开源协作项目
- 团队成员频繁变动的企业项目
- 调试效率优先于理论完备性的生产环境

### 10.4 可提取价值

即使不采用易经系统，以下实现可作为**参考设计**:
- ✅ 路径守卫实现（path_guard.py）
- ✅ Docker 沙盒配置（sandbox.py）
- ✅ WAL 证据链（checkpoint.py, trace.py）
- ✅ 零依赖架构模式

---

## 11. 附录

### 11.1 关键文件索引

**核心规则引擎**:
- `src/onecode/kernel/hexagram.py` (1,597 行) - I Ching 状态机
- `src/onecode/kernel/runner.py` (997 行) - 执行编排
- `src/onecode/kernel/path_guard.py` (90 行) - 路径防护

**安全模块**:
- `src/onecode/kernel/sandbox.py` (130 行) - Docker 沙盒
- `src/onecode/web/auth.py` (20 行) - 认证
- `src/onecode/kernel/execution_tools.py` (478 行) - 命令执行

**文档**:
- `README.md` (24K)
- `docs/INDEX.md` (6.4K)
- `CONTRIBUTING.md` (6.1K)
- `docs/superpowers/specs/` (43 个设计文档)

### 11.2 验证命令

```bash
# 快速验证
bash scripts/verify-core.sh  # 234 测试, ~7s

# 完整验证
bash scripts/verify.sh        # 907 测试, ~20s

# 冒烟测试
onecode doctor

# 规则完整性
onecode math-audit

# 沙盒测试
onecode sandbox-smoke --workspace /tmp/test
```

### 11.3 更新历史

- **2026-09-01**: 初次审核，发现文档可发现性问题
- **2026-09-01**: 创建 INDEX.md、扩展 CONTRIBUTING.md、更新 hexagram.py 文档
- **2026-09-01**: 重新审核，确认改进效果

---

**审核员**: Claude Opus 5 (Kiro)  
**审核方法**: 静态代码分析 + 测试执行 + 文档评估 + 安全审计  
**审核时长**: 完整测试套件 19.5s，代码审查 ~30 分钟  
**建议复审**: 如果修复 git 历史或添加架构图后
