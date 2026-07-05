# YiZiJue-LM 发布更新清单

日期：2026-07-05

## 什么时候使用

只要修改 `release/yizijue-lm-public` 下的脚本、测试、文档、日志或发布说明，都要使用这份清单。

## 发布包边界

release 包应包含：

- 可公开的脚本和测试；
- README、CHANGELOG、MODEL_CARD、LICENSE、NOTICE；
- release notes、评估摘要、项目收尾说明；
- checksum manifest 覆盖的发布文件。

release 包不应包含：

- `.git`；
- `__pycache__`、`.pyc`；
- 本地虚拟环境；
- 模型权重、adapter checkpoint；
- 私密 API key、服务地址、个人凭据。

## 更新步骤

1. 修改主工作区脚本或文档。
2. 如果 release 包有对应副本，同步修改 `release/yizijue-lm-public`。
3. 更新 release 包内 `CHANGELOG.md` 和相关 docs。
4. 重新生成 `release/yizijue-lm-public/release/checksums.txt`。
5. 运行 `cd release/yizijue-lm-public && bash scripts/verify_release.sh`。
6. 回到工作区根目录运行 `bash scripts/verify.sh`。

## checksum 生成方式

使用 Python 生成，排除 checksum manifest 自身：

```bash
python3 - <<'PY'
from hashlib import sha256
from pathlib import Path

root = Path("release/yizijue-lm-public")
manifest = root / "release/checksums.txt"
paths = sorted(
    path for path in root.rglob("*")
    if path.is_file() and path != manifest
)
manifest.write_text(
    "".join(
        f"{sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in paths
    ),
    encoding="utf-8",
)
PY
```

随后校验：

```bash
python3 scripts/check_release_checksums.py
```

## 发布前确认

- `release/checksums.txt` 没有列出自身。
- release 包内没有 symlink。
- 所有 release 文件都在 checksum manifest 中。
- README 中的 release self-check 说明与 `scripts/verify_release.sh` 一致。
- 根目录 `CHANGELOG.md` 记录了 release 相关变化。
