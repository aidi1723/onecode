# OneCode Symbolic Audit Extension (`onecode-symbolic-audit`)

Optional companion package providing cultural/symbolic correspondence tables (King Wen hexagram pairs, Jing Fang eight-palace tables, and Ziwei Doushu cross-validation certificates) for [`onecode-kernel`](../../README.md).

## Why This Is Separate / 为何物理拆分为独立扩展包

Core `onecode-kernel` enforces filesystem safety guards, SHA-256 evidence chains, deterministic verifier gates, and `shell_projection` context compression using pure standard-library engineering code with zero dependency on symbolic/divination correspondence tables. Installing this package is **strictly optional** and only needed when running extended symbolic audit certificates or opt-in `ONECODE_SYMBOLIC_TELEMETRY=1` skin telemetry.

## Installation & Verification / 安装与独立验证

```bash
# Install core runtime first, then optional symbolic extension
pip install -e .
pip install -e ./packages/onecode-symbolic-audit

# Or run the extension test suite and microbenchmark directly from the monorepo:
bash scripts/verify-symbolic.sh
```
