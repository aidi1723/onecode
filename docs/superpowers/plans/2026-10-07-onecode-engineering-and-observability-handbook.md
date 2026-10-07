# OneCode Engineering & Observability Handbook
**Date**: 2026-10-07
**Target Version**: v0.8.0 Release Candidate

## 1. Executive Summary

The OneCode kernel possesses a verified mathematical topology for its $Q_6$ state space and I Ching transformations. `classify_outcome` maps to 6 out of 64 states, and the majority of hexagram calculations serve purely as observable evidence rather than control logic. 

This handbook establishes the development roadmap required to lift the project toward readiness. It explicitly rejects "forced metaphors" (e.g., using I Ching semantics to arbitrarily override CI/CD rules) and pivots the focus entirely to **hard engineering robustness** and **pure observability**.

---

## 2. Phase 1: Engineering Gaps & Production Blockers (生产环境硬卡点)

The system cannot pass production sign-off until the following infrastructure defects are resolved. Note that resolving these does **not** instantly qualify the project for v1.0. `claims_mainstream_parity` remains `false` until external penetration scanning and dual-machine release orchestration are also completed.

### 2.1 Memory Profiling in Soak Tests (浸泡测试内存验证)
**The State**:
The Python 3.12 `pathlib` `sys.intern` correlation was observed on `n100` (Python 3.12.3) but absent on macOS (Python 3.12.12). This represents a correlated observation, not a universally proven root cause.
**Action Items**:
- Run the full 4-hour soak test and permanently record the RSS plateau curve as hard evidence.
- Verify that GC assertions hold steadily at a baseline without monotonic growth over long durations.
- **Success Criteria**: A complete 4-hour log proving the memory curve goes flat, committed to the repository.

### 2.2 ARM64 Container Host Compatibility (宿主机跨架构支持)
**The State**:
`qemu-user-static` and `binfmt_misc` have been installed directly on the `n100` host.
**Action Items**:
- Boot the `python:3.12-slim` ARM64 image using the configured emulator.
- **Success Criteria**: Commit the execution output confirming the host successfully runs and returns `aarch64` from within the foreign architecture container.

---

## 3. Phase 2: I Ching Deepening as Pure Observability (易经规则的只读观测层)

While the fundamental control plane (Dispatch, Transition, Bandwidth, Sovereignty Fire) is mathematically closed and must remain untouched, deeper I Ching concepts will be integrated strictly as **Read-Only Evidence Profiles (观测证据层)**. 

**Acceptance Criteria (验收条件)**:
No field may be added without an explicit test proving its isolation. For each read-only field (Moving Lines, Micro-Structural Vectors, Sequential Telemetry), there must be a test asserting that adding or removing the field leaves the output of `transition`, `dispatch`, `sovereignty_fire`, and `execution_bandwidth` **byte-for-byte identical**, and that the `agent_cycle` halt reason remains completely unchanged.

**Implementation Landing Zones (待建项落点)**:
The fields `moving_lines`, `micro_relations` (承乘比应), and `cycle_phase` currently do not exist in the source code. Because `agent_cycle.py` does not directly reference `wal.py`, these multi-turn cycle telemetry items must be injected into the evidence payload generated in `runner.py` and `execution_engine.py` before being committed to the WAL.

### 3.1 Base Hexagram & Moving Lines Tracking (本卦定义与动爻追踪)
- **Input Definition (输入定义)**: The "Base Hexagram" (本卦) for any turn is derived exactly from the `status_code` of the PREVIOUS evidence record. The first round's base hexagram is explicitly defined as empty/none.
- **Implementation**: Extend the profile to identify the specific bits that flipped between the Base Hexagram and the Resulting Hexagram. Output this as a telemetry array. 

### 3.2 Micro-Structural Vectors (承、乘、比、应)
- **Implementation**: Calculate the physical layout forces: Cheng (承), Sheng (乘), Bi (比), Ying (应).
- **Usage**: Add these exact counts to the JSON evidence payload. They must **not** be wired into `lyapunov_energy` or `sovereignty_fire`.

### 3.3 Temporal & Sequential Telemetry (宏观时序与周期标注)
- **Hardcoded Sequences (卦序定死)**: 
  - The 12 Sovereign Hexagrams (十二消息卦) must be hardcoded strictly as: **复、临、泰、大壮、夬、乾、姤、遁、否、观、剥、坤**.
  - The King Wen Sequence (文王序卦) must use a fixed 1 to 64 lookup table embedded within the tests, without runtime dynamic interpretation.
- **Usage**: Map `cycle_count % 12` to the Sovereign Hexagrams and output the chronological stamp (`cycle_phase`) in the telemetry. Do not use sequence distance to adjust execution tolerance.

---

## 4. Conclusion

By strictly separating Deterministic Control Logic from Philosophical Telemetry, OneCode preserves its tested stability. Resolving the memory and cross-arch blockers will finalize its v0.8.0 deployment viability.
