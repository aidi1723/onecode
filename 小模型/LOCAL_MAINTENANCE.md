# YiZiJue-LM Local Maintenance Notes

日期：2026-07-05

这份文件放在项目根目录，供后期本地维护、继续开发、交接排查时第一时间查看。

## 先看哪里

- 本地维护入口：`LOCAL_MAINTENANCE.md`
- 中文收尾文档：`docs/YIZIJUE_LM_FINAL_CLOSURE_CN_2026-07-05.md`
- 英文发布交接：`docs/YIZIJUE_LM_RELEASE_CLOSURE_2026-07-05.md`
- 开发手册：`docs/YIZIJUE_LM_DEVELOPMENT_MANUAL.md`
- 训练手册：`docs/YIZIJUE_QWEN15B_TRAINING_RUNBOOK.md`
- 更新日志：`CHANGELOG.md`
- 公开发布包：`release/yizijue-lm-public`

## 当前维护状态

- 主工作区验证命令：`bash scripts/verify.sh`
- 最近验证结果：主测试 116 项 OK，release 测试 86 项 OK。
- release checksum：已通过 Python SHA-256 校验。
- 推荐训练集：`data/train_messages_distilled_clean.jsonl`
- 标签审计报告：`data/training/train_messages_distilled_label_audit.json`
- release 自检命令：`cd release/yizijue-lm-public && bash scripts/verify_release.sh`

## 日常开发顺序

1. 修改代码、数据或文档前，先看 `CHANGELOG.md` 和本文件确认当前边界。
2. 涉及训练数据时，优先使用 `data/train_messages_distilled_clean.jsonl`。
3. 涉及发布包时，同时更新 `release/yizijue-lm-public` 内的脚本、文档和 checksum。
4. 提交前运行 `bash scripts/verify.sh`。
5. 若更新 release 文件，重新生成并验证 `release/yizijue-lm-public/release/checksums.txt`。

## 不要提交的内容

- `models/` 下的 adapter、safetensors、checkpoint 或基座模型权重；
- 虚拟环境和本地缓存；
- `__pycache__`、`.pyc`、`.DS_Store`；
- API key、凭据、私有服务地址；
- 本地实验产生的临时 workspace 和大体积日志。

## 运行边界

YiZiJue-LM 只负责输出 OneCode action JSON 提案，不直接承担最终执行权限。最终执行、权限控制、审计和证据留存仍由 OneCode 侧负责。

本地 MLX 推理依赖外部运行时和模型资产。服务启动时必须显式提供 adapter：

```bash
python3 scripts/serve_yizijue_mlx.py --adapter-path /path/to/adapter
```

或设置：

```bash
export YIZIJUE_ADAPTER_PATH=/path/to/adapter
```

## GitHub 记录

当前已推送分支：

```text
origin  https://github.com/aidi1723/onecode.git
branch  feature/gateway-iching-rule-sync
```

已有收尾提交：

```text
898ab9c9a7c33cb91eda7accfe1bd1577a814ade  Add yizijue lm workspace release closure
6d851420327df3f767ddb713b507d6b9bb1a8528  Add Chinese yizijue lm closure document
```

## 后续维护建议

- 如果继续放在 `onecode` 仓库，保持 `小模型/` 作为独立工作区维护。
- 如果拆成独立仓库，先复制本文件、README、CHANGELOG、`docs/`、`release/yizijue-lm-public`，再重新生成 checksum。
- 每次阶段性收尾后，更新本文件的验证结果和最新提交记录。
