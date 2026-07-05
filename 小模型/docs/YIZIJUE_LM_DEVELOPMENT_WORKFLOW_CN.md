# YiZiJue-LM 后期开发流程

日期：2026-07-05

## 适用范围

用于后续修改脚本、测试、服务、评估 gate、数据构建流程和文档时保持一致流程。

## 推荐流程

1. 明确修改范围：脚本、测试、数据、release 包、文档分别处理。
2. 先看相关测试：`tests/` 和 `release/yizijue-lm-public/tests/`。
3. 小步修改，避免同时重构无关模块。
4. 修改共享脚本时，同步检查 release 包内是否有对应副本。
5. 修改用户可见说明时，同步更新 README、CHANGELOG 和维护文档。
6. 结束前运行 `bash scripts/verify.sh`。

## 常用验证命令

完整验证：

```bash
bash scripts/verify.sh
```

只跑主工作区测试：

```bash
python3 -m unittest discover -s tests
```

只跑 release 包测试：

```bash
cd release/yizijue-lm-public
python3 -m unittest discover -s tests
```

只跑 release 自检：

```bash
cd release/yizijue-lm-public
bash scripts/verify_release.sh
```

## 修改脚本时

- 保持 CLI 错误可读，不把 Python traceback 暴露给普通用户。
- 输入 JSONL 必须先做结构校验，再进入模型推理或数据处理。
- 不要默默 `str()` 转换 ID、预测值或 action 字段。
- 新增异常分支时补测试，优先覆盖失败输入。

## 修改服务时

- 保持 `/predict` 只接受 JSON object。
- 继续校验 `Content-Length`、请求体大小和 `max_tokens`。
- 不要在 HTTP 响应里泄露原始生成异常。
- 不要写死本机 adapter 路径，继续使用 `--adapter-path` 或 `YIZIJUE_ADAPTER_PATH`。

## 修改文档时

- 根目录入口优先更新 `LOCAL_MAINTENANCE.md`。
- 面向本地维护的内容写中文，面向公开发布包的内容保持 release 包现有英文风格。
- 如果文档提到验证范围，要与 `scripts/verify.sh` 的实际行为一致。
- 不使用平台特定 checksum 工具说明；统一指向 Python 校验脚本。
