# OneCode Milestone Pause Note (v0.8.0)

**Date**: 2026-10-08
**Status**: Milestone Paused / Boundary Sealed

This document serves as a milestone pause record for the current iteration. The codebase is paused at its currently established boundaries.

## 1. Established Boundaries (Implemented & Enforced)

### 1.1 Process & Execution Safety
* **MCP Pre-Approval Execution Sealed**: `register_mcp_tools` now explicitly requires the caller to provide `remote_names` and no longer spawns the `McpStdioClient` process during registration. Process launching (`subprocess.Popen`) is strictly deferred until after the tool execution is explicitly approved.
* **Verifier Host Fallback Sealed**: The verifier (`run_verifier`) now strictly mandates a `sandbox_config`. If omitted, the verifier halts execution immediately, returning `sandbox_required`, and will absolutely not fall back to executing on the host via `subprocess.run`.
* **Host Secret Access**: Unapproved processes are strictly prohibited from execution. Approved, host-bound commands (e.g., `run_command`) retain legitimate read access to `~/.onecode/approval-secret.key` per system design.

### 1.2 易经观测的架构红线 (The I-Ching Architectural Red Line)
* 动爻、十二消息卦、承乘比应、大衍比例（3/16、7/16、5/16、1/16 以及 25% 基线）、互卦和交卦的返回值**只能**进入 Evidence 或 Trace 日志。
* `sandbox.py`、`verifier.py`、`execution_engine.py` 和 `runner.py` 内部的分支**绝对不可**读取它们，绝不能因为偏离大衍基线而去改写解码、模型计划或触发停机。

### 1.3 System Stability
* **Memory Baseline Observation**: Upgraded the `n100` environment to Python 3.12.7. Soaking for 12 minutes (8,000 rounds of `execute_plan`) showed RSS stabilizing at 22.20 MB without the linear `pathlib` growth seen in 3.12.3.
* **ARM64 Emulation**: Validated `qemu-user-static` and `binfmt-support` on the `n100` host, natively supporting ARM64 container emulation without architectural mismatches.

## 2. Unresolved & Pending Items (Next Phase)

The following items are intentionally left unaddressed in this iteration and are carried forward as pending tasks:

1. **Third-Party Security Scanning**: The codebase has fortified edge-cases but has not yet undergone or passed external/third-party penetration and security scanning. No pre-emptive code changes are being made for this at this time.
2. **API Key Revocation**: The leaked API key in `.env.local` remains suspended. Permanent revocation from the OpenAI console remains a pending manual action for the user. (Note: `~/.onecode/approval-secret.key` is the local approval signing file and is in active use).
3. **Dual-Machine Sync & Orchestration**: The `scripts/sync_deployment.sh` script is functional but currently inactive. Active deployment toggling between the Mac and `n100` is paused. The cross-signed `echo test` command on `n100` remains permanently suspended as `PENDING_APPROVAL`.
4. **Mainstream Parity**: The variable `claims_mainstream_parity` remains rigorously held at `false` until the above deployment criteria are fully satisfied.
