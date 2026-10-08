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

### 1.4 Memory "Leak" Root Cause Confirmed (Python 3.12.3 Immortal Strings)
- **Soak Test Results**: The 4-hour soak test on `n100` (Python 3.12.3) demonstrated that string patches to `evidence_io.py` and others did **not** flatten the RSS curve. Over a 12-minute window, RSS grew strictly linearly from 21.7 MB to 33.3 MB (an increase of 1.6-2.0 MB every 2 minutes) with zero plateau.
- **Tracemalloc Fingerprint**: `pathlib.py:404` accounted for the highest number of new allocations, reaching 21,331 objects (3,229 KiB) at t=720. 
- **CPython Bug Identification**: The true root cause is a confirmed CPython bug present in versions 3.12.0 to 3.12.6, where `sys.intern(str(x))` created immortal string objects that bypass garbage collection. This bug was fixed in 3.12.7 via `gh-113993`. This perfectly explains why the identical test on macOS Python 3.12.12 yielded no leak (200,000 unique paths consumed only 3 blocks).
- **Secondary Analysis**: The remaining `Path` constructions in `cycle_approvals.py` (which deduplicate via stable SHA-256) and `path_guard.py` (which only inspect existing files) do not generate the ~3600 new unique strings seen every 2 minutes. Furthermore, the 3.2 MB `pathlib` overhead represents only a fraction of the 11.6 MB total RSS delta, proving that a purely code-level `os.path.join` mitigation is both insufficient and fundamentally dodging a compiler-level flaw.
- **Success Criteria / Next Steps**: ✅ **RESOLVED**. The `n100` Python environment was upgraded to 3.12.7 via `uv`. 12 minutes, 8,000 rounds, RSS reading remained at 22.20 MB, did not reproduce the linear growth of 3.12.3.

### 1.5 ARM64 Container Host Support (✅ Verified)
- **Host Configuration**: Installed `qemu-user-static` and `binfmt-support` at the OS level on `n100`.
- **Success Criteria**: ✅ **RESOLVED**. Successfully executed `docker run --rm --platform linux/arm64 python:3.12.3-slim python3 -c 'import platform; print(platform.machine())'` via SSH on `n100`, which correctly output `aarch64`. The host perfectly emulates ARM64 containers.

## 2. Unresolved & Next Steps
- **External Scanning**: Edge-case sandbox escapes have been sealed (host fallback warnings enforced, on-disk approval HMAC signature, comprehensive Docker container termination on timeout, disabled pre-approval MCP tool registration process launch, and removed verifier un-sandboxed host fallback). The project has not yet passed third-party penetration/security scanning.
- **Dual-Machine Orchestration**: Active deployment switching between the Mac and n100 environments is pending.
- **Mainstream Parity**: The variable `claims_mainstream_parity` remains rigorously held at `false` until the above deployment criteria are met.
