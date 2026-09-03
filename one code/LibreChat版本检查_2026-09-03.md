# LibreChat 壳系统版本检查报告

**检查日期**: 2026-09-03  
**检查对象**: `/Users/aidi/大字典/onecode-librecat`

---

## 📊 当前状态

### 本地版本
- **当前版本**: v0.8.7
- **当前分支**: `feature/onecode-shell-v087-hardening`
- **最新提交**: `224e73e8e` (2026-07-16)
- **提交信息**: "docs: record OneCode v0.8.7 verification"

### 上游最新版本
- **官方最新版**: v0.8.8-rc2
- **发布日期**: 2025-09-03 (今天)
- **状态**: Release Candidate (候选版本)

---

## ⚠️ 版本差距分析

### 当前状况
```
本地: v0.8.7 (稳定版)
上游: v0.8.8-rc2 (候选版本)
差距: 1 个小版本 + 2 个 RC 迭代
```

### 版本性质判断

**v0.8.8-rc2 = Release Candidate 2**
- ✅ 表示 v0.8.8 正在测试阶段
- ⚠️ 尚未发布正式稳定版
- 📅 通常 RC2 之后还会有正式版

---

## 🔍 当前集成状态

### OneCode 与 LibreChat 集成记录

根据 `ONECODE_LIBRECHAT_V087_HARDENING_CLOSURE_2026-07-15.md`：

#### 集成规范
- **社区基线**: LibreChat v0.8.7 (提交 `9e74cc0e5`)
- **OneCode 端口**: 完整验证并通过
- **集成分支**: `feature/onecode-shell-v087-hardening`
- **回滚检查点**: `checkpoint/onecode-shell-pre-v087-20260715`

#### 可靠性改进
✅ 提供商超时标准化为 `ModelProviderTimeout`  
✅ 失败规划返回稳定 HTTP 504/502 + 证据引用  
✅ 强制 `maxRetries: 0`（零外层重试）  
✅ 运行时超时边界 `(0, 600]` 秒  
✅ 认证秘钥使用原子私有 `0700/0600` 状态  
✅ Mongo 持久化 `dbPath`，重启时 `doCleanup: false`  

#### 验证证据
| 测试项 | 结果 |
|--------|------|
| OneCode 聚焦套件 | 163 通过 |
| OneCode 完整验证 | 903 通过，1 环境跳过 |
| LibreChat 端点测试 | 35 通过 |
| LibreChat 服务器测试 | 27 通过 |
| LibreChat 客户端测试 | 28 通过 |
| 生产构建 | 9,315 模块转换成功 |
| 浏览器控制台 | 0 错误，0 警告 |

#### 实时验收
✅ 桌面 `1440x900` 和移动 `390x844` 视图正常  
✅ 登录、项目状态、Console 六个标签页正常  
✅ 读任务完成并显示账本引用  
✅ 写任务返回 `approval_required` 带预览  
✅ 重启保持认证状态和 Mongo 数据（278 文件不变）  
✅ 模型超时产生 HTTP 504，证据链完整  

---

## 💡 升级建议

### 🟢 推荐：暂不升级

**理由**:

1. **当前版本稳定**
   - v0.8.7 是经过完整验证的稳定版
   - 所有 OneCode 集成测试通过
   - 生产环境运行良好

2. **上游版本未稳定**
   - v0.8.8-rc2 是测试候选版
   - 可能存在未发现的问题
   - 正式版 v0.8.8 尚未发布

3. **集成成本高**
   - 需要重新端口所有 OneCode 修改
   - 需要完整的验证流程（163+903+90 测试）
   - 需要桌面/移动端验收测试
   - 需要更新所有闭包文档

### 📅 建议升级时机

**等待以下条件之一**:

1. **LibreChat v0.8.8 正式版发布**
   - 不是 RC，而是稳定的 v0.8.8
   - 通常在 RC2 之后 1-4 周

2. **v0.8.9 或更大版本**
   - 如果 v0.8.8 改动较小，可跳过
   - 等待功能更丰富的版本

3. **发现关键安全漏洞**
   - 如果 v0.8.7 存在严重安全问题
   - 立即升级到最新稳定版

---

## 🔄 如果决定升级到 v0.8.8-rc2

### 升级流程（高风险）

```bash
cd /Users/aidi/大字典/onecode-librechat

# 1. 创建当前状态检查点
git branch checkpoint/onecode-shell-pre-v088rc2-$(date +%Y%m%d)
git tag onecode-shell-v087-final

# 2. 获取上游最新代码
git fetch origin --tags
git checkout -b feature/onecode-shell-v088rc2-migration

# 3. 合并或变基到 v0.8.8-rc2
git merge v0.8.8-rc2
# 或
git rebase v0.8.8-rc2

# 4. 端口所有 OneCode 修改
# - 检查冲突
# - 重新应用 OneCode 端点
# - 重新配置零重试策略
# - 更新超时配置
# - 验证认证流程

# 5. 运行完整测试套件
npm test
cd /Users/aidi/大字典/one\ code
PYTHONPATH=src python3 -m unittest discover -s tests -v

# 6. 实时验收测试
PYTHONPATH=src python3 -m onecode shell --show-credentials
# 测试桌面/移动视图
# 测试读/写/批准流程
# 测试重启持久化

# 7. 记录闭包文档
# - ONECODE_LIBRECHAT_V088RC2_MIGRATION_CLOSURE_$(date +%Y-%m-%d).md
```

### 预估工作量
- **代码迁移**: 4-8 小时
- **测试验证**: 2-4 小时
- **文档记录**: 1-2 小时
- **总计**: 7-14 小时

### 风险评估
- 🔴 **高风险**: RC 版本可能有未知 bug
- 🟡 **中风险**: OneCode 端口可能与新代码冲突
- 🟢 **低风险**: 有完整的回滚检查点

---

## 📋 检查清单

如果你仍想升级，请确认：

- [ ] 阅读 LibreChat v0.8.8-rc2 的 Release Notes
- [ ] 评估新功能是否对 OneCode 有价值
- [ ] 确认有足够时间进行完整测试
- [ ] 创建当前状态的完整备份
- [ ] 记录回滚计划
- [ ] 准备闭包文档模板

---

## 🎯 结论

**推荐行动**: **保持当前 v0.8.7 版本**

**原因**:
1. v0.8.7 已完整验证，稳定可靠
2. v0.8.8-rc2 是测试版，风险高
3. 无紧急升级需求
4. 集成成本大于收益

**下一步监控**:
- 关注 LibreChat GitHub releases 页面
- 等待 v0.8.8 正式版发布
- 评估 v0.8.8 的 changelog 和新功能
- 在正式版发布后 2-4 周再考虑升级

---

**检查人**: Claude (Opus 5)  
**建议优先级**: 低  
**下次检查建议**: v0.8.8 正式版发布后
