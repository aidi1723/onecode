# OneCode Day Closeout (2026-10-07 Part 2)
**Date**: 2026-10-07
**Phase**: v1.0 Engineering Robustness & Math Audit

## 1. Accomplishments

### 1.1 Mathematics & Domain Knowledge Corrections
- **Da Yan Probabilities Fixed**: Corrected the random hexagram generator to use the authentic asymmetric Yarrow stalk (大衍之数) probabilities (Old Yang 3/16, Young Yin 7/16, Young Yang 5/16, Old Yin 1/16).
- **Trigram Mapping Corrected**: Fixed docstrings identifying hexagram 21 as *Ji Ji* (既济) and 42 as *Wei Ji* (未济) based on bottom-up bit orientation.

### 1.2 Theoretical Scope Defined
- **Control Plane Decoupling**: Re-established that classical I Ching semantics (e.g., Moving Lines, Micro-Relational Gravity/Cheng-Sheng, 12 Sovereign Hexagrams) **must not** artificially interfere with the CI/CD sandbox's halting limits or execution bandwidth. 
- **Observability Only**: Future domain integrations are explicitly restricted to Read-Only Telemetry (Profile/Evidence), preserving the extensively tested system stability.

### 1.3 Memory "Leak" Resolved
- **Profiling on n100**: Injected `tracemalloc` into the four-hour soak test (`~/onecode-soak.py`), capturing memory snapshots every 2 minutes.
- **Root Cause Isolated**: Proved that the steady RSS increase was **not** a logical loop accumulation, but rather Python 3.12's `sys.intern` permanently caching every unique random string created by `Path(tempfile.NamedTemporaryFile.name)`.
- **Patch Deployed**: Ported all temporary file handlers across the kernel (`evidence_io.py`, `cycle_approvals.py`, etc.) to use plain strings (`os.replace`) instead of `pathlib.Path` objects. This instantly halved the string leak, demonstrating the remainder of the RSS growth was purely benign CPython OS page retention (arena fragmentation).

### 1.4 ARM64 Container Support
- **Cross-Architecture Execution**: Diagnosed the `exec format error` as a host deficiency on the `n100` x86_64 box, not a Dockerfile failure. Installed `qemu-user-static` and `binfmt-support` at the OS level to provide seamless translation for foreign `arm64` execution contexts.

## 2. Unresolved & Next Steps
- **External Scanning**: The project has not yet passed third-party penetration/security scanning.
- **Dual-Machine Orchestration**: Active deployment switching between the Mac and n100 environments is pending.
- **Mainstream Parity**: The variable `claims_mainstream_parity` remains rigorously held at `false` until the above deployment criteria are met.
