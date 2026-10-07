# OneCode Day Closeout (2026-10-07 Part 2)
**Date**: 2026-10-07
**Phase**: v1.0 Engineering Robustness & Math Audit

## 1. Accomplishments

### 1.1 Mathematics & Domain Knowledge Corrections
- **Da Yan Probabilities Fixed**: Corrected the domain modeling to use the authentic asymmetric Yarrow stalk (大衍之数) probabilities (Old Yang 3/16, Young Yin 7/16, Young Yang 5/16, Old Yin 1/16).
- **Trigram Mapping Corrected**: Fixed docstrings identifying hexagram 21 as *Ji Ji* (既济) and 42 as *Wei Ji* (未济) based on bottom-up bit orientation.

### 1.2 Theoretical Scope Defined
- **Control Plane Decoupling**: Re-established that classical I Ching semantics (e.g., Moving Lines, Micro-Relational Gravity/Cheng-Sheng, 12 Sovereign Hexagrams) **must not** artificially interfere with the CI/CD sandbox's halting limits or execution bandwidth. 
- **Observability Only**: Future domain integrations are explicitly restricted to Read-Only Telemetry (Profile/Evidence), preserving the extensively tested system stability.

### 1.3 Memory "Leak" Mitigated (Full Verification Pending)
- **Profiling on n100**: Injected `tracemalloc` into the four-hour soak test (`~/onecode-soak.py`), capturing memory snapshots every 2 minutes.
- **Root Cause Isolated**: Found that the steady RSS increase correlated heavily with Python 3.12's `sys.intern` permanently caching every unique random string created by `Path(tempfile.NamedTemporaryFile.name)`.
- **Patch Deployed**: Ported all temporary file handlers across the kernel (`evidence_io.py`, `cycle_approvals.py`, `path_guard.py`, `model_config.py`) to use plain strings (`os.replace`) instead of `pathlib.Path` objects. Corrected an `AttributeError` exception in failure cleanups to correctly use `os.unlink(temp_path)`.
- **Success Criteria Pending**: While the `tracemalloc` short-term slice shows string retention stopped, the true success metric requires running a complete 4-hour soak test to conclusively prove the resident memory (RSS) curve flattens completely.

### 1.4 ARM64 Container Host Support (Container Verification Pending)
- **Host Configuration**: Installed `qemu-user-static` and `binfmt-support` at the OS level on `n100` to provide translation for foreign `arm64` execution contexts.
- **Success Criteria Pending**: We must explicitly run a `linux/arm64` container on the `n100` host and verify its successful launch before declaring cross-architecture execution fully resolved.

## 2. Unresolved & Next Steps
- **External Scanning**: The project has not yet passed third-party penetration/security scanning.
- **Dual-Machine Orchestration**: Active deployment switching between the Mac and n100 environments is pending.
- **Mainstream Parity**: The variable `claims_mainstream_parity` remains rigorously held at `false` until the above deployment criteria are met.
