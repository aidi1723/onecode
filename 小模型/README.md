# YiZiJue-LM 小模型工作区索引

当前蒸馏与清洗数据主目录：

`/Users/aidi/大字典/小模型`

OneCode 项目只作为规则引擎与清洗代码来源，不应继续作为训练资产主目录。

## 后期维护先看

- 本地维护入口：`/Users/aidi/大字典/小模型/LOCAL_MAINTENANCE.md`
- 后期维护总览：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_MAINTENANCE_RUNBOOK_CN.md`
- 中文收尾文档：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_FINAL_CLOSURE_CN_2026-07-05.md`
- 完整验证命令：`bash scripts/verify.sh`

## 关键数据文件

- 总训练集：`/Users/aidi/大字典/小模型/data/train_data_distilled.jsonl`
- Qwen SFT messages 格式：`/Users/aidi/大字典/小模型/data/train_messages_distilled.jsonl`
- Qwen SFT messages 清洗推荐集：`/Users/aidi/大字典/小模型/data/train_messages_distilled_clean.jsonl`
- balanced 主集：`/Users/aidi/大字典/小模型/data/train_data_balanced.jsonl`
- security 高危压力集：`/Users/aidi/大字典/小模型/data/train_data_security.jsonl`

## 蒸馏原始与清洗证据

- 原始 balanced 蒸馏：`/Users/aidi/大字典/小模型/data/training/distillation/raw_deepseek_balanced.jsonl`
- 原始 security 蒸馏：`/Users/aidi/大字典/小模型/data/training/distillation/raw_deepseek_security.jsonl`
- OneCode 接受样本：`/Users/aidi/大字典/小模型/data/training/distillation/accepted_balanced.jsonl`
- OneCode 纠偏样本：`/Users/aidi/大字典/小模型/data/training/distillation/corrected_balanced.jsonl`
- 拒绝样本：`/Users/aidi/大字典/小模型/data/training/distillation/rejected_balanced.jsonl`
- 蒸馏错误日志：`/Users/aidi/大字典/小模型/data/training/distillation/errors_balanced.jsonl`
- messages 标签审计报告：`/Users/aidi/大字典/小模型/data/training/train_messages_distilled_label_audit.json`

## 文档

- 本地维护入口：`/Users/aidi/大字典/小模型/LOCAL_MAINTENANCE.md`
- 后期维护总览：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_MAINTENANCE_RUNBOOK_CN.md`
- 开发流程：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_DEVELOPMENT_WORKFLOW_CN.md`
- 发布更新清单：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_RELEASE_UPDATE_CHECKLIST_CN.md`
- 数据与训练维护：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_DATA_AND_TRAINING_MAINTENANCE_CN.md`
- 故障排查：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_TROUBLESHOOTING_CN.md`
- 维护更新记录：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_MAINTENANCE_CHANGELOG_CN.md`
- 开发手册：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_DEVELOPMENT_MANUAL.md`
- 训练手册：`/Users/aidi/大字典/小模型/docs/YIZIJUE_QWEN15B_TRAINING_RUNBOOK.md`
- 2026-07-05 收尾交接：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_RELEASE_CLOSURE_2026-07-05.md`
- 2026-07-05 中文收尾文档：`/Users/aidi/大字典/小模型/docs/YIZIJUE_LM_FINAL_CLOSURE_CN_2026-07-05.md`
- 更新日志：`/Users/aidi/大字典/小模型/CHANGELOG.md`

## 当前进度

- 合并训练样本：4013 条
- 原始 messages 训练 token 估算：约 1,060,745 tokens
- 清洗推荐 messages：3978 条，约 1,051,555 tokens
- 第一阶段 1,000,000 tokens 目标完成度：已达到；后续训练默认使用 `data/train_messages_distilled_clean.jsonl`
- 标签审计排除 35 条疑似“明确工作区写入但被标为 schema_out_of_contract”的冲突样本，原始数据仍保留用于追溯。

## 一键验证

从本目录运行：

```bash
bash scripts/verify.sh
```

该命令会运行主测试、release 测试、脚本语法检查、评估 gate 正反例和 release checksum。HTTP handler 测试不绑定本地端口，可在普通沙箱权限下运行。

## 继续蒸馏入口

继续蒸馏仍需调用 OneCode 的 Python 规则模块。推荐从 OneCode 目录运行，但输出路径指向小模型目录：

```bash
cd "/Users/aidi/大字典/one code"
PYTHONPATH=src DEEPSEEK_API_KEY="你的key" DEEPSEEK_BASE_URL="http://10.0.0.184:6780" DEEPSEEK_MODEL="deepseek-v4-flash" \
python3 scripts/distill_batches.py \
  --batches 8 \
  --batch-size 120 \
  --profile balanced \
  --raw "/Users/aidi/大字典/小模型/data/training/distillation/raw_deepseek_balanced.jsonl" \
  --accepted "/Users/aidi/大字典/小模型/data/training/distillation/accepted_balanced.jsonl" \
  --corrected "/Users/aidi/大字典/小模型/data/training/distillation/corrected_balanced.jsonl" \
  --rejected "/Users/aidi/大字典/小模型/data/training/distillation/rejected_balanced.jsonl" \
  --train "/Users/aidi/大字典/小模型/data/train_data_balanced.jsonl" \
  --errors "/Users/aidi/大字典/小模型/data/training/distillation/errors_balanced.jsonl" \
  --request-interval-seconds 0.05 \
  --timeout-seconds 60 \
  --max-tokens 1024
```

每次暂停或继续后，重新合并：

```bash
PYTHONPATH="/Users/aidi/大字典/one code/src" \
python3 scripts/build_distilled_training_set.py \
  --balanced "/Users/aidi/大字典/小模型/data/train_data_balanced.jsonl" \
  --security "/Users/aidi/大字典/小模型/data/train_data_security.jsonl" \
  --merged "/Users/aidi/大字典/小模型/data/train_data_distilled.jsonl" \
  --messages "/Users/aidi/大字典/小模型/data/train_messages_distilled.jsonl"
```

重新合并后，先运行标签审计并输出训练推荐集：

```bash
python3 scripts/audit_training_labels.py \
  --input "/Users/aidi/大字典/小模型/data/train_messages_distilled.jsonl" \
  --output "/Users/aidi/大字典/小模型/data/training/train_messages_distilled_label_audit.json" \
  --clean-output "/Users/aidi/大字典/小模型/data/train_messages_distilled_clean.jsonl"
```

`build_distilled_training_set.py` 和 `distill_openai_compatible.py` 依赖 OneCode 的 Python 包。未安装 OneCode 时，`--help` 可正常查看参数；实际运行需要安装 OneCode 或设置 `PYTHONPATH` 指向 OneCode 的 `src`。

## 迁移校验

- 已从 `/Users/aidi/大字典/one code/data` 复制到 `/Users/aidi/大字典/小模型/data`
- 文件数量：3227 对 3227
- `train_data_distilled.jsonl` SHA256 一致
- `train_messages_distilled.jsonl` SHA256 一致
