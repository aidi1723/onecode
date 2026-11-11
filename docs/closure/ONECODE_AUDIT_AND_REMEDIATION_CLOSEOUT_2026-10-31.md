# Comprehensive Audit & Remediation Closeout, 2026-10-31

Version stays 1.0.0. Tag `v1.0.0` stays at `dd51424`. Tag `v0.8.0` stays at `e1adb3c`. No new hexagram was added ($Q_6 = \{0..63\}$). `IchingKernel.classify_outcome` was not edited (0 diff). `claims_mainstream_parity` stays false. The model channel User-Agent stays `onecode/0.8`. Core runtime dependencies strictly stay `dependencies = []`.

This note formalizes the closeout of the comprehensive project audit conducted on 2026-10-31, remediating all 8 audit findings across Phase 1 (P0), Phase 2 (P1), and Phase 3 (P2), and verifying the complete 1,467-test suite, source quality gates, 26 mathematical audit certificates, and microsecond-level benchmarking.

---

## 1. Remediation Summary Across All Audit Findings

### Phase 1 (P0: System-Breaking & Static Analysis Blockers)
- **P0-1: Checkpoint Telemetry Compaction in Manifest** ([`checkpoint.py`](../../src/onecode/kernel/checkpoint.py))
  - Implemented `compact_checkpoint_telemetry(telemetry)` retaining the 8 essential cycle keys (`moving_lines`, `cycle_phase`, `micro_relations`, `sihua`, `changed_bands`, `foundation_broken`, `pattern_state`, `pattern_name`).
  - Historical checkpoints in `manifest["checkpoints"]` now record compact telemetry, while full 31-profile telemetry is preserved in standalone checkpoints (`checkpoints/{turn:04d}.json`) and top-level manifest telemetry.
  - Eliminates the ~21 KB per-checkpoint inflation in `manifest.json`, preventing `manifest_metrics_section_bytes_exceeded:checkpoints` after 12 turns.
  - Verified: [`tests/test_rule_parallel_tasks.py`](../../tests/test_rule_parallel_tasks.py) all 64 hexagrams pass in 0.467s.

- **P0-2: Static Analysis Full Pass (Ruff & Mypy 100% Clean)** ([`hexagram_ziwei.py`](../../src/onecode/kernel/hexagram_ziwei.py), [`web/api.py`](../../src/onecode/web/api.py), [`cli.py`](../../src/onecode/cli.py))
  - In `hexagram_ziwei.py`: wired `water_triad`, `fire_triad`, `metal_triad`, `wood_triad` into `_evaluate_twelve_deities_certificate` to mathematically assert `b in triads[b % 4]`; typed `stages: dict[str, dict[str, Any]]` and cast `tolerance = float(...)`; typed `test_breaking_kwargs: list[dict[str, Any]]`; typed `five_axes` and extracted pair values cleanly; wired `t_native` and `pressure` into Sihua cascade and organ pathology.
  - In `web/api.py`: typed `raw_metadata` and narrowed `metadata: dict[str, Any]`.
  - In `cli.py`: annotated `precision_targets: list[str] = []`.
  - Verified: `ruff check src tests` (0 warnings, 0 errors), `mypy src/` (107 files checked, 0 errors).

### Phase 2 (P1: Architectural Alignment & Defense-in-Depth)
- **P1-3: Web API & Kernel Verifier Parity** ([`verifier.py`](../../src/onecode/kernel/verifier.py), [`web/api.py`](../../src/onecode/web/api.py))
  - Both `verify_shell_write` and `run_two_stage_verifier` now uniformly detect `ONECODE_HOST_VERIFIER_CMD` and `verifier.py` fallback when `tests/` directory is absent.
  - Ensures repositories with external or host test harnesses receive full automated verification without false "no tests" skips.

- **P1-4: Repair Prompt Context & Anti-Tampering Guard** ([`web/api.py`](../../src/onecode/web/api.py), [`model_loop.py`](../../src/onecode/kernel/model_loop.py))
  - In `api.py:handle_onecode_plan_approval` and `model_loop.py:_run_model_task_repair_loop`, passed `workspace=workspace` to `repair_prompt` to enable `find_closest_patch_context` excerpt extraction.
  - Added strict check in `_run_model_task_repair_loop`: any patch attempting to modify `tests/` is rejected immediately with `repair_plan_cannot_modify_tests`, preventing models from gaming verifiers by weakening assertions.
  - Verified: new unit test `test_model_repair_rejects_patches_modifying_tests`.

- **P1-5: Flying Sihua Cascade & System Pathology Variable Integration** ([`hexagram_ziwei.py`](../../src/onecode/kernel/hexagram_ziwei.py))
  - Connected `t_native` to compute natal Hua Ji star and branch (`native_ji_branch`), detecting natal collision (`native_clash`).
  - Connected `pressure` dictionary to Five Elements pathology detection (`lock_contention`, `memory`, `cpu`, `cache`).

### Phase 3 (P2: Boundary Resilience & Tool Hygiene)
- **P2-6: UTF-8 Multibyte Truncation Resilience & Tool Parameter Parity** ([`execution_tools.py`](../../src/onecode/kernel/execution_tools.py))
  - `ReadTextTool.execute` uses `errors="replace"` on raw byte slices to prevent `UnicodeDecodeError` when multibyte UTF-8 characters are sliced on byte boundaries.
  - Added `status_code` support to `GlobFilesTool`, `OutlineTool`, `SearchTextTool`, and `GitCommitTool`.
  - Verified: new unit tests `test_read_text_tool_multibyte_truncation_does_not_crash` and `test_observation_tools_accept_status_code_in_plan_action`.

- **P2-7: PathGuard Canonicalization in Rewrite Detection & Scale Cache Invalidation** ([`model_loop.py`](../../src/onecode/kernel/model_loop.py), [`execution_engine.py`](../../src/onecode/kernel/execution_engine.py))
  - Replaced raw string concatenation `workspace / path` with `PathGuard.resolve_target(workspace, path)` in `_plan_has_existing_file_rewrite` and `execute_step`, preventing path traversal (`..`) bypass.
  - Augmented `_cached_workspace_scale_stats` and `workspace_scale_stats` with directory `mtime_ns` key, automatically invalidating cached file count and LOC when directory contents change.

- **P2-8: Execution Engine Line Limit Compliance & Degraded Mode Safety** ([`execution_engine.py`](../../src/onecode/kernel/execution_engine.py))
  - `execute_plan` maintained at 136 lines, strictly below the 160-line ceiling.
  - Reinforced safety break mechanics for degraded execution posture.

---

## 2. Verification Gates & Benchmarks

1. **Source Quality Gate (`scripts/check_source_quality.py src`)**:
   - `source quality ok`: all functions $\le 160$ lines, all classes $\le 500$ lines.

2. **Static Analysis & Type Inference**:
   - `ruff check src tests`: `All checks passed!` (0 warnings).
   - `mypy src/`: `Success: no issues found in 107 source files` (0 errors).

3. **Core Fast Gate (`scripts/verify-core.sh`)**:
   - Ran 400 tests in 12.545s, `OK`.
   - Doctor: all 9 system checks passed (`passed: true`, status `ok`).

4. **Full Production Gate (`scripts/verify.sh`)**:
   - Ran 1,467 unit tests in 51.782s, `OK`.
   - Coverage: **87%** (18,209 statements, 2,407 missed), exceeding the 80% threshold.
   - Doctor: status `ok`.

5. **26 Ziwei Mathematical Audit Certificates & Benchmarking (`scripts/benchmark_ziwei.py`)**:
   - All 26 certificates verified `[PASS]`:
     `sovereign_ring`, `an_he_coupling`, `shen_gong_anchorage`, `star_brightness`, `jie_shen_even_subgroup_relief`, `twelve_deities_triad_and_suipo`, `flying_sihua_cascade`, `triadic_synthesis`, `ziwei_tianfu_and_yangtuo`, `solar_equation_and_zishi`, `school_divergence_consensus`, `classical_patterns`, `auxiliary_polarity_and_yunxian`, `heming_synastry_and_noble_stars`, `deep_computation_and_graph`, `pathology_and_environmental`, `six_channel_and_empty_palace`, `doujun_and_solar_boundary`, `auxiliary_pairs_and_city_solar`, `changsheng_and_expanded_patterns`, `ziwu_liuzhu_and_shengke`, `dipper_axes_and_sha_po_lang`, `ming_zhu_shen_zhu_and_void_stars`, `pattern_breaking_and_resonance`, `systemic_parameter_coupling`, `iching_classical_correspondence`.
   - 10,000 profiling iterations across 64 hexagram states:
     - Total duration: 1.8851 s
     - Throughput: **5,304.66 ops/sec**
     - Mean latency: **188.26 µs**
     - Median (p50): 185.04 µs
     - 95th Percentile: 211.08 µs
     - 99th Percentile: 291.38 µs
     - Min / Max: 168.54 µs / 743.62 µs

---

## 3. Invariants & Commit Record

- `IchingKernel.classify_outcome`: completely untouched (0 diff).
- `dependencies = []`: zero external runtime dependencies strictly preserved in [`pyproject.toml`](../../pyproject.toml).
- Commit history on `main`:
  - `dcb5298`: `fix(kernel): resolve full-project audit findings across checkpoint telemetry, static analysis, verifier parity, and tool resilience`
  - `1862db7`: `feat(benchmark): wire host verifier precedence, adaptive bureau turn budgets, and n100 repair loop telemetry`
  - `163128b`: `feat(kernel): elevate 7 ziwei certificates to non-tautological axiomatic and engine-invoked invariant verification`
  - `bc0c4e8`: `feat(kernel): link dynamic status code to recovery policy and apply jie shen damping to repair cooldowns`
  - `8fe7a52`: `feat(kernel): enforce physical cooldown, path hazard partitioning, host verifier fallback, and precision assertion targets`
