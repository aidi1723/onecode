# YiZiJue-LM 后期维护总览

日期：2026-07-05

## 用途

这份文档给后期本地维护者使用。打开项目目录后，先看根目录 `LOCAL_MAINTENANCE.md`，再按具体任务进入本文件和同目录下的专题文档。

## 维护文档地图

- 本地入口：`LOCAL_MAINTENANCE.md`
- 开发流程：`docs/YIZIJUE_LM_DEVELOPMENT_WORKFLOW_CN.md`
- 发布更新：`docs/YIZIJUE_LM_RELEASE_UPDATE_CHECKLIST_CN.md`
- 数据与训练：`docs/YIZIJUE_LM_DATA_AND_TRAINING_MAINTENANCE_CN.md`
- 故障排查：`docs/YIZIJUE_LM_TROUBLESHOOTING_CN.md`
- 更新记录：`docs/YIZIJUE_LM_MAINTENANCE_CHANGELOG_CN.md`
- 中文收尾：`docs/YIZIJUE_LM_FINAL_CLOSURE_CN_2026-07-05.md`

## 当前维护边界

- `小模型/` 是独立工作区，父级仓库可能还有其他项目和未提交变更。
- OneCode 规则引擎是上游依赖，不应把 OneCode 源码复制到本工作区作为训练资产。
- `release/yizijue-lm-public` 是公开发布包副本，修改 release 相关代码时需要同步更新 release 包。
- `models/`、adapter、checkpoint、基座权重、API key 和本地临时 workspace 不进入源码发布。

## 每次维护前检查

1. 运行 `git status --short -- 小模型`，确认当前工作区是否已有未提交变更。
2. 阅读 `LOCAL_MAINTENANCE.md` 和 `CHANGELOG.md`，确认最近一次收尾状态。
3. 如果要改训练数据，先阅读数据与训练维护文档。
4. 如果要改 release 包，先阅读发布更新清单。
5. 如果要改服务或评估脚本，先运行相关单测或完整 `bash scripts/verify.sh` 建立基线。

## 每次维护后检查

1. 更新相关文档和 `CHANGELOG.md`。
2. 运行 `bash scripts/verify.sh`。
3. 检查不应提交内容：`models/`、缓存、虚拟环境、私密配置。
4. 如果变更 release 包，确认 checksum manifest 已重新生成并校验通过。
5. 提交时只暂存本次任务相关文件。

## 最低验收标准

- README 能指向当前维护入口。
- CHANGELOG 记录本次变化。
- `bash scripts/verify.sh` 通过，或在交接文档中明确记录未运行原因。
- release 包内文件与 `release/checksums.txt` 一致。
- 本地运行边界、模型资产边界和 OneCode 执行边界没有被文档或代码混淆。
