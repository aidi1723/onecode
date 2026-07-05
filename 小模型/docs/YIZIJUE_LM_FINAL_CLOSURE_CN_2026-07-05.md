# YiZiJue-LM 中文收尾文档

日期：2026-07-05

## 收尾结论

YiZiJue-LM 小模型工作区已完成本轮源代码、训练数据、发布包、验证脚本和交接文档整理，可以作为 OneCode Agent 提案模型的本地工作区与公开源码发布包继续交接。

本次收尾覆盖目录：

```text
/Users/aidi/大字典/小模型
```

公开发布包目录：

```text
release/yizijue-lm-public
```

## 已完成事项

- 评估门禁已加固，覆盖缺失预测、额外预测、重复 ID、格式错误 ID、非字符串预测和空 gold 集等异常。
- 预测生成脚本已在导入 MLX 运行时前完成 JSONL 输入校验，避免无效输入触发运行期依赖错误。
- 数据集构建脚本已校验 split 比例、source ID、gold action、hard-negative replay ID 和 recovery action。
- 本地服务已增加请求体大小、`Content-Length`、JSON object、`max_tokens`、端口范围和生成异常响应边界。
- release checksum 已改为 Python SHA-256 校验，覆盖发布包内除 checksum manifest 自身以外的所有文件。
- release 目录已清理 `.git`、`__pycache__`、`.pyc` 等不应发布内容。
- README、CHANGELOG、release README、release CHANGELOG、评估摘要和项目收尾文档已同步当前验证状态。

## 验证记录

最终验证命令：

```bash
bash scripts/verify.sh
```

已记录的通过结果：

```text
主工作区测试：116 tests OK
release 包测试：86 tests OK
missing_prediction_count: 0
unexpected_prediction_count: 0
json_valid_rate: 0.9858490566037735
action_match_rate: 0.8254716981132075
unknown_action_count: 0
unsafe_allow_count: 0
release checksum validation: OK
```

缓存检查范围：

```bash
find scripts tests release/yizijue-lm-public/scripts release/yizijue-lm-public/tests \( -name __pycache__ -o -name '*.pyc' \)
```

期望结果：无输出。

## 发布边界

本次源码更新包含：

- Python 脚本、测试和验证脚本；
- 公开 release 源码副本；
- release 文档、校验清单和评估报告；
- 当前工作区使用的训练与评估 JSONL 资产；
- README、CHANGELOG、模型卡、许可证、NOTICE 和交接文档。

本次源码更新不包含：

- 虚拟环境；
- Python 缓存；
- 本地临时日志；
- `models/` 下的 LoRA adapter、safetensors 和模型权重；
- Qwen 基座权重；
- API key、凭据或其他私密配置。

最终 LoRA adapter 仍属于独立运行时资产，启动服务时需要通过 `--adapter-path` 或 `YIZIJUE_ADAPTER_PATH` 显式指定。

## GitHub 更新记录

已推送目标：

```text
origin  https://github.com/aidi1723/onecode.git
branch  feature/gateway-iching-rule-sync
commit  898ab9c9a7c33cb91eda7accfe1bd1577a814ade
```

提交信息：

```text
Add yizijue lm workspace release closure
```

## 遗留风险

- 父级 Git 工作区仍有 `小模型/` 之外的无关修改和未跟踪文件；本次收尾未触碰这些内容。
- 真实 MLX 推理依赖本机模型资产、adapter 路径和 `mlx_lm` 运行环境，源码验证不等同于模型权重可用性验证。
- YiZiJue-LM 只输出 OneCode action JSON 提案；最终执行、权限控制、证据留存和审计仍由 OneCode 侧负责。

## 后续建议

- 若需要独立开源项目，应将 `小模型/` 拆分为单独仓库，并在新仓库重新生成 release checksum。
- 若继续保留在 `onecode` 仓库，应在 PR 或合并说明中明确 `小模型/` 是独立工作区。
- 每次更新发布包后都应重新运行 `bash scripts/verify.sh`，并同步更新 `CHANGELOG.md` 与 release checksum。
