# YiZiJue-LM 后期维护更新记录

## 2026-07-05

### 新增

- 新增根目录 `LOCAL_MAINTENANCE.md`，作为本地后期维护第一入口。
- 新增中文收尾文档 `docs/YIZIJUE_LM_FINAL_CLOSURE_CN_2026-07-05.md`。
- 新增后期维护总览、开发流程、发布更新清单、数据训练维护、故障排查和维护更新记录。

### 当前验证基线

- 完整验证命令：`bash scripts/verify.sh`
- 主工作区测试：116 tests OK
- release 包测试：86 tests OK
- release checksum validation：OK

### 维护提醒

- 每次阶段性更新后同步维护 `LOCAL_MAINTENANCE.md`、`CHANGELOG.md` 和本文件。
- 修改 release 包后必须重新生成并验证 `release/yizijue-lm-public/release/checksums.txt`。
- 不把 `models/`、adapter、checkpoint、基座权重、虚拟环境或凭据提交进源码仓库。
