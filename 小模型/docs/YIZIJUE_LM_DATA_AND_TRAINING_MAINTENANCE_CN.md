# YiZiJue-LM 数据与训练维护

日期：2026-07-05

## 当前推荐资产

- 推荐训练 messages：`data/train_messages_distilled_clean.jsonl`
- 原始合并 messages：`data/train_messages_distilled.jsonl`
- 合并训练数据：`data/train_data_distilled.jsonl`
- balanced 数据：`data/train_data_balanced.jsonl`
- security 数据：`data/train_data_security.jsonl`
- 标签审计：`data/training/train_messages_distilled_label_audit.json`
- 评估 gold：`data/mlx_qwen06b_full/test.jsonl`

## 数据维护原则

- 训练默认使用清洗推荐集，不直接覆盖原始数据。
- 原始蒸馏、纠偏、拒绝和错误日志要保留，方便追溯。
- 新增样本必须有稳定 ID，不能有空 ID、重复 ID、非字符串 ID 或控制字符。
- assistant gold 必须能解析出 action，不能让 `None == None` 形成虚假通过。
- hard-negative replay ID 必须唯一，避免重复放大同一负例。

## 常用重建步骤

重新合并 distilled 数据：

```bash
PYTHONPATH="/Users/aidi/大字典/one code/src" \
python3 scripts/build_distilled_training_set.py \
  --balanced "/Users/aidi/大字典/小模型/data/train_data_balanced.jsonl" \
  --security "/Users/aidi/大字典/小模型/data/train_data_security.jsonl" \
  --merged "/Users/aidi/大字典/小模型/data/train_data_distilled.jsonl" \
  --messages "/Users/aidi/大字典/小模型/data/train_messages_distilled.jsonl"
```

重新审计标签并输出推荐训练集：

```bash
python3 scripts/audit_training_labels.py \
  --input "/Users/aidi/大字典/小模型/data/train_messages_distilled.jsonl" \
  --output "/Users/aidi/大字典/小模型/data/training/train_messages_distilled_label_audit.json" \
  --clean-output "/Users/aidi/大字典/小模型/data/train_messages_distilled_clean.jsonl"
```

## 评估注意事项

- 完整工作区验证使用 `bash scripts/verify.sh`。
- 评估 gate 必须检查 missing prediction 和 unexpected prediction。
- 不能只用预测行计算通过率，否则会漏掉缺失预测。
- 评估输出中的 `missing_prediction_count`、`unexpected_prediction_count`、`unknown_action_count`、`unsafe_allow_count` 都应作为发布判断依据。

## 模型资产边界

- `models/` 不进源码仓库。
- adapter、checkpoint、safetensors 和基座模型权重作为独立运行时资产管理。
- 服务启动时通过 `--adapter-path` 或 `YIZIJUE_ADAPTER_PATH` 指向 adapter。
