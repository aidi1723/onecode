# OneCode Day Closeout (2026-10-07 Part 2)
**Date**: 2026-10-07
**Phase**: v0.8.0 收尾，v1.0 未签发

## 1. Accomplishments

### 1.1 Architectural Security & Audit Fixes
- **run-model Bypass Closed**: Fixed a critical vulnerability where `run-model` bypassed approvals and silently fell back to the host environment when Docker was unavailable. It now strictly enforces approval gates.
- **Workspace Fingerprint Optimized**: Replaced `rglob("*")` with `os.walk` in `_workspace_fingerprint` to explicitly ignore `.venv` and `.git`, preventing the 2000-file cap from blinding the system to actual `src/` changes.
- **Redirect Token Leakage Blocked**: Created `StripAuthRedirectHandler` to ensure `Authorization` tokens are not transparently leaked when HTTP requests are redirected to foreign hosts.

### 1.2 Testing & Static Analysis
- **0 Mypy Errors**: Fully typed `src/` (resolving 300+ errors across 33 files) by adding `Protocol` and `ClassVar` definitions to `IchingProfileMixin` and other components.
- **Test Coverage Elevated**: 1062 tests ran (1 failure on the flaky GC assertion which passed upon isolation). Statement coverage reached 84% (up from failures in `deployment_boundary`, `diagnostics`, and `web/api` which were pushed to >85%).

### 1.3 Theoretical Scope Defined
- **Control Plane Decoupling**: Re-established that classical I Ching semantics (e.g., Moving Lines, Micro-Relational Gravity/Cheng-Sheng, 12 Sovereign Hexagrams) **must not** artificially interfere with the CI/CD sandbox's halting limits or execution bandwidth. 
- **Observability Only**: Future domain integrations are explicitly restricted to Read-Only Telemetry (Profile/Evidence), preserving the extensively tested system stability.

### 1.4 Memory "Leak" Mitigated (已缓解，待验证)
- **Root Cause Correlated**: Tracemalloc on the n100 host (Python 3.12.3) correlated the steady RSS increase with `sys.intern` caching every unique string created by `Path()`. Note: This was NOT reproduced on macOS Python 3.12.12 (where 200k unique paths only consumed 3 memory blocks), indicating a specific correlation with Python 3.12.3 rather than a universal leak.
- **Patch Deployed**: Ported multiple temporary file handlers (`evidence_io.py`, `model_config.py`, `approval_plans.py`) to use `os.replace`. However, `cycle_approvals.py:82` and `path_guard.py:62` still construct unique names using `Path()`. The problem is mitigated but not structurally eliminated.
- **Success Criteria Pending**: We must complete a 4-hour soak test demonstrating an RSS plateau.

### 1.5 ARM64 Container Host Support (已缓解，待验证)
- **Host Configuration**: Installed `qemu-user-static` and `binfmt-support` at the OS level on `n100`.
- **Success Criteria Pending**: We must explicitly run a `linux/arm64` container on the `n100` host and record its successful launch.

## 2. Unresolved & Next Steps
- **External Scanning**: The project has not yet passed third-party penetration/security scanning.
- **Dual-Machine Orchestration**: Active deployment switching between the Mac and n100 environments is pending.
- **Mainstream Parity**: The variable `claims_mainstream_parity` remains rigorously held at `false` until the above deployment criteria are met.
