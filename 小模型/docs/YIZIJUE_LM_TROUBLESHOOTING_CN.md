# YiZiJue-LM 故障排查

日期：2026-07-05

## `bash scripts/verify.sh` 失败

先看失败发生在哪一段：

- 主工作区测试：检查 `tests/` 对应失败用例。
- release 测试：进入 `release/yizijue-lm-public` 复现。
- 脚本语法检查：检查最近改动的 `scripts/*.py`。
- 评估 gate：检查 gold、predictions、ID 覆盖和 action 解析。
- release checksum：检查 release 文件是否新增、删除、修改但没有更新 manifest。

## release checksum 失败

常见原因：

- release 包新增文件但 `release/checksums.txt` 未更新；
- checksum manifest 列出了自身；
- manifest 中路径不是规范 POSIX 相对路径；
- release 包出现 symlink；
- 文件内容变了但 digest 没更新。

处理顺序：

1. 确认 release 包内没有不应发布文件。
2. 重新生成 `release/yizijue-lm-public/release/checksums.txt`。
3. 运行 `python3 scripts/check_release_checksums.py`。
4. 再运行 `bash scripts/verify.sh`。

## 评估 gate 失败

重点检查：

- prediction ID 是否完整覆盖 gold ID；
- 是否存在 gold 之外的 prediction ID；
- JSONL 行是否为 object；
- `prediction` 字段是否存在且为字符串；
- assistant gold 是否能解析出 action；
- threshold 是否在 `0..1` 范围内。

如果是全量 gold 对测试集 predictions 运行，预期会失败，并应在错误中看到 `missing_prediction_count`。

## 预测生成失败

先确认输入 JSONL：

- 每行是 JSON object；
- ID 非空、唯一、字符串；
- `messages` 字段存在且格式正确；
- 至少有一条 user message；
- 文件不是空文件。

输入校验通过后，再检查 MLX 环境和 adapter 路径。

## 本地服务失败

检查顺序：

1. adapter 是否通过 `--adapter-path` 或 `YIZIJUE_ADAPTER_PATH` 指定。
2. 端口是否在 `0..65535`。
3. 请求体是否是 JSON object。
4. `Content-Length` 是否规范。
5. `max_tokens` 是否在 `1..512`，且不是布尔值。

服务不应返回原始生成异常。如果需要定位底层 MLX 问题，在本地日志或调试环境里查，不把原始异常暴露给 HTTP 调用方。
