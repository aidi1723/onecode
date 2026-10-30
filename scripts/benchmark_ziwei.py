#!/usr/bin/env python3
"""Ziwei Engine Microbenchmark and Verification Reproducibility Harness.

Runs 10,000 iterations of full Ziwei profiling across all 64 hexagram states,
verifies all 4 mathematical certificates, and reports latency, throughput, and percentiles.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from onecode.kernel.hexagram import IchingKernel


def run_microbenchmark(iterations: int = 10_000) -> dict[str, float | int]:
    """Execute full Ziwei profiling loop for N iterations across state space."""
    sample_turn = {"status": "completed", "reason": None}
    sample_history = [{"status": "completed", "reason": None}]
    
    latencies_us: list[float] = []
    
    # Warmup
    for state in range(64):
        _ = IchingKernel.task_bureau_profile(12, 450)
        _ = IchingKernel.self_sihua_profile(sample_turn, sample_history)
        _ = IchingKernel.causal_origin_profile("AssertionError: test failure", sample_history)
        _ = IchingKernel.triad_consensus_profile(1, state)
        _ = IchingKernel.ziwei_pattern_matrix_profile(1, state)
        _ = IchingKernel.shen_gong_anchorage_profile(1, state)
        _ = IchingKernel.star_brightness_profile(state)
        _ = IchingKernel.star_dynamic_energy_profile()
        _ = IchingKernel.jie_shen_relief_profile(1, state)
        _ = IchingKernel.twelve_deities_profile(1, state)
        _ = IchingKernel.flying_sihua_cascade_profile(1, state)
        _ = IchingKernel.triadic_synthesis_profile(state)
        _ = IchingKernel.ming_shen_zhu_profile(1, state)
        _ = IchingKernel.ziwei_tianfu_duality_profile(state)
        _ = IchingKernel.yang_tuo_clamping_profile(1, state)
        _ = IchingKernel.true_solar_time_profile(2026, 6, 15, 12, 0)
        _ = IchingKernel.clock_drift_adaptation_profile(0.0)
        _ = IchingKernel.school_consensus_profile(0)
        _ = IchingKernel.classical_patterns_profile(1, state)
        _ = IchingKernel.auxiliary_stars_polarity_profile(0, state % 12)
        _ = IchingKernel.nested_yunxian_temporal_profile("liunian", 1, status_code=state)
        _ = IchingKernel.noble_horse_stars_profile(0, state % 12, 0)
        _ = IchingKernel.dual_sihua_superposition_profile(0, ["化忌", "化权"])
        _ = IchingKernel.multi_agent_synastry_profile({"stem": 0, "ming_branch": 0}, {"stem": 1, "ming_branch": 4})
        _ = IchingKernel.famous_archetype_profile("ma-yun")
        _ = IchingKernel.full_sihua_graph_profile(0, state)
        _ = IchingKernel.bipartite_synastry_tensor_profile({"stem": 0}, {"stem": 1}, state)
        _ = IchingKernel.full_palace_patterns_profile(1, state)
        _ = IchingKernel.china_dst_profile(1988, 6, 1)
        _ = IchingKernel.aphorism_knowledge_profile("紫微在子")
        _ = IchingKernel.system_pathology_profile(state)
        _ = IchingKernel.partner_star_contract_profile("紫微")
        _ = IchingKernel.sandbox_fengshui_profile()
        _ = IchingKernel.six_channel_healing_profile(state)
        _ = IchingKernel.empty_palace_borrowing_profile(state)
        _ = IchingKernel.four_pillars_nayin_profile(0, 0, 0, 0, 0, 2)
        _ = IchingKernel.doujun_chronology_profile(0, 1, 0, 1, 1, 0)
        _ = IchingKernel.childhood_guard_profile(2, 1, 0)
        _ = IchingKernel.solar_lichun_boundary_profile(2026, 2, 4, 12, 0)
        _ = IchingKernel.auxiliary_stars_pairs_profile(1, 1, 0, 0)
        _ = IchingKernel.city_true_solar_profile("北京", 2026, 6, 15, 12, 0)
        _ = IchingKernel.temporal_superposition_profile("implementation", state)

    start_total = time.perf_counter()
    for i in range(iterations):
        state = i % 64
        turn = (i % 12) + 1
        t0 = time.perf_counter_ns()
        _ = IchingKernel.task_bureau_profile(12, 450)
        _ = IchingKernel.self_sihua_profile(sample_turn, sample_history)
        _ = IchingKernel.causal_origin_profile("AssertionError: test failure", sample_history)
        _ = IchingKernel.triad_consensus_profile(turn, state)
        _ = IchingKernel.ziwei_pattern_matrix_profile(turn, state)
        _ = IchingKernel.shen_gong_anchorage_profile(turn, state)
        _ = IchingKernel.star_brightness_profile(state)
        _ = IchingKernel.star_dynamic_energy_profile()
        _ = IchingKernel.jie_shen_relief_profile(turn, state)
        _ = IchingKernel.twelve_deities_profile(turn, state)
        _ = IchingKernel.flying_sihua_cascade_profile(turn, state)
        _ = IchingKernel.triadic_synthesis_profile(state)
        _ = IchingKernel.ming_shen_zhu_profile(turn, state)
        _ = IchingKernel.ziwei_tianfu_duality_profile(state)
        _ = IchingKernel.yang_tuo_clamping_profile(turn, state)
        _ = IchingKernel.true_solar_time_profile(2026, 6, 15, (turn * 2) % 24, 30)
        _ = IchingKernel.clock_drift_adaptation_profile(5.0)
        _ = IchingKernel.school_consensus_profile(turn - 1)
        _ = IchingKernel.classical_patterns_profile(turn, state)
        _ = IchingKernel.auxiliary_stars_polarity_profile(turn - 1, state % 12)
        _ = IchingKernel.nested_yunxian_temporal_profile("liunian", turn, status_code=state)
        _ = IchingKernel.noble_horse_stars_profile(turn - 1, state % 12, (turn - 1) % 12)
        _ = IchingKernel.dual_sihua_superposition_profile((turn - 1) % 12, ["化忌", "化权"])
        _ = IchingKernel.multi_agent_synastry_profile({"stem": (turn - 1) % 10, "ming_branch": (turn - 1) % 12}, {"stem": turn % 10, "ming_branch": (turn + 4) % 12})
        _ = IchingKernel.famous_archetype_profile("ma-yun")
        _ = IchingKernel.full_sihua_graph_profile(turn - 1, state)
        _ = IchingKernel.bipartite_synastry_tensor_profile({"stem": (turn - 1) % 10}, {"stem": turn % 10}, state)
        _ = IchingKernel.full_palace_patterns_profile(turn, state)
        _ = IchingKernel.china_dst_profile(1988, 6, 1)
        _ = IchingKernel.aphorism_knowledge_profile("紫微在子")
        _ = IchingKernel.system_pathology_profile(state)
        _ = IchingKernel.partner_star_contract_profile("紫微")
        _ = IchingKernel.sandbox_fengshui_profile()
        _ = IchingKernel.six_channel_healing_profile(state)
        _ = IchingKernel.empty_palace_borrowing_profile(state)
        _ = IchingKernel.four_pillars_nayin_profile(0, 0, 0, 0, 0, 2)
        _ = IchingKernel.doujun_chronology_profile(0, 1, 0, 1, 1, 0)
        _ = IchingKernel.childhood_guard_profile(2, 1, 0)
        _ = IchingKernel.solar_lichun_boundary_profile(2026, 2, 4, 12, 0)
        _ = IchingKernel.auxiliary_stars_pairs_profile(1, 1, 0, 0)
        _ = IchingKernel.city_true_solar_profile("北京", 2026, 6, 15, 12, 0)
        _ = IchingKernel.temporal_superposition_profile("implementation", state)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)

    total_time_sec = time.perf_counter() - start_total
    throughput = iterations / total_time_sec if total_time_sec > 0 else 0.0

    latencies_us.sort()
    mean_us = statistics.mean(latencies_us)
    p50_us = latencies_us[int(iterations * 0.50)]
    p95_us = latencies_us[int(iterations * 0.95)]
    p99_us = latencies_us[int(iterations * 0.99)]
    min_us = latencies_us[0]
    max_us = latencies_us[-1]

    return {
        "iterations": iterations,
        "total_time_sec": round(total_time_sec, 4),
        "throughput_ops_sec": round(throughput, 2),
        "mean_latency_us": round(mean_us, 2),
        "p50_latency_us": round(p50_us, 2),
        "p95_latency_us": round(p95_us, 2),
        "p99_latency_us": round(p99_us, 2),
        "min_latency_us": round(min_us, 2),
        "max_latency_us": round(max_us, 2),
    }


def verify_mathematical_certificates() -> dict[str, bool]:
    """Verify all 9 mathematical certificates directly."""
    c_ring = IchingKernel.sovereign_ring_isomorphism_certificate()
    c_anhe = IchingKernel.an_he_coupling_certificate()
    c_shengong = IchingKernel.shen_gong_anchorage_certificate()
    c_bright = IchingKernel.star_brightness_certificate()
    c_jieshen = IchingKernel.jie_shen_even_subgroup_relief_certificate()
    c_twelve = IchingKernel.twelve_deities_triad_and_suipo_certificate()
    c_flying = IchingKernel.flying_sihua_cascade_certificate()
    c_triad = IchingKernel.triadic_synthesis_certificate()
    c_zifu = IchingKernel.ziwei_tianfu_and_yangtuo_certificate()
    c_solar = IchingKernel.solar_equation_and_zishi_certificate()
    c_school = IchingKernel.school_divergence_consensus_certificate()
    c_classical = IchingKernel.classical_patterns_certificate()
    c_aux = IchingKernel.auxiliary_polarity_and_yunxian_certificate()
    c_heming = IchingKernel.heming_synastry_and_noble_stars_certificate()
    c_deep = IchingKernel.deep_computation_and_graph_certificate()
    c_pathology = IchingKernel.pathology_and_environmental_certificate()
    c_sixchan = IchingKernel.six_channel_and_empty_palace_certificate()
    c_doujun = IchingKernel.doujun_and_solar_boundary_certificate()
    c_aux_city = IchingKernel.auxiliary_pairs_and_city_solar_certificate()
    
    return {
        "sovereign_ring": c_ring.get("status") == "verified" and c_ring.get("triad_balance_verified") is True,
        "an_he_coupling": c_anhe.get("status") == "verified" and c_anhe.get("distance_palindrome_verified") is True,
        "shen_gong_anchorage": c_shengong.get("status") == "verified" and c_shengong.get("antipodal_symmetry_verified") is True,
        "star_brightness": c_bright.get("status") == "verified" and c_bright.get("all_states_valid") is True,
        "jie_shen_even_subgroup_relief": c_jieshen.get("status") == "verified" and c_jieshen.get("odd_palace_exclusion_verified") is True,
        "twelve_deities_triad_and_suipo": c_twelve.get("status") == "verified" and c_twelve.get("triad_partition_verified") is True and c_twelve.get("suipo_opposite_involution_verified") is True,
        "flying_sihua_cascade": c_flying.get("status") == "verified" and c_flying.get("sihua_totality_verified") is True and c_flying.get("duigong_involution_verified") is True,
        "triadic_synthesis": c_triad.get("status") == "verified" and c_triad.get("convex_bounds_verified") is True and c_triad.get("two_thirds_domination_verified") is True,
        "ziwei_tianfu_and_yangtuo": c_zifu.get("status") == "verified" and c_zifu.get("ziwei_tianfu_involution_verified") is True and c_zifu.get("tai_pi_fixed_points_verified") is True and c_zifu.get("yang_tuo_clamping_midpoint_verified") is True,
        "solar_equation_and_zishi": c_solar.get("status") == "verified" and c_solar.get("eot_bounded_oscillation_verified") is True and c_solar.get("zishi_measure_partition_verified") is True,
        "school_divergence_consensus": c_school.get("status") == "verified" and c_school.get("seven_stems_unanimous_verified") is True and c_school.get("geng_closure_verified") is True,
        "classical_patterns": c_classical.get("status") == "verified" and c_classical.get("safety_dominance_verified") is True and c_classical.get("supreme_purity_verified") is True,
        "auxiliary_polarity_and_yunxian": c_aux.get("status") == "verified" and c_aux.get("dahao_bijection_verified") is True and c_aux.get("jiekong_stem_duality_verified") is True,
        "heming_synastry_and_noble_stars": c_heming.get("status") == "verified" and c_heming.get("tianluo_diwang_exclusion_verified") is True and c_heming.get("mutual_ji_deadlock_breaker_verified") is True,
        "deep_computation_and_graph": c_deep.get("status") == "verified" and c_deep.get("sihua_48_rays_conservation_verified") is True and c_deep.get("bipartite_96_rays_conservation_verified") is True,
        "pathology_and_environmental": c_pathology.get("status") == "verified" and c_pathology.get("five_element_pathology_totality_verified") is True and c_pathology.get("fourteen_partner_stars_contract_verified") is True,
        "six_channel_and_empty_palace": c_sixchan.get("status") == "verified" and c_sixchan.get("six_channel_transmission_order_verified") is True and c_sixchan.get("nayin_60_jiazi_equipartition_verified") is True,
        "doujun_and_solar_boundary": c_doujun.get("status") == "verified" and c_doujun.get("doujun_surjective_coverage_verified") is True and c_doujun.get("solar_lichun_boundary_switch_verified") is True,
        "auxiliary_pairs_and_city_solar": c_aux_city.get("status") == "verified" and c_aux_city.get("tianxing_tianyao_constant_phase_verified") is True and c_aux_city.get("santai_bazuo_sum_conservation_verified") is True and c_aux_city.get("tianshang_tianshi_migration_sandwiching_verified") is True and c_aux_city.get("major_cities_geodetic_bounds_verified") is True,
    }


def main() -> int:
    print("=" * 68)
    print("OneCode Ziwei Cross-Validation Benchmark & Mathematical Audit")
    print("=" * 68)

    print("\n[1/2] Verifying Mathematical Audit Certificates...")
    cert_results = verify_mathematical_certificates()
    all_certs_ok = all(cert_results.values())
    for cert_name, passed in cert_results.items():
        status_str = "PASS" if passed else "FAIL"
        print(f"  - {cert_name:24s}: [{status_str}]")
    if not all_certs_ok:
        print("ERROR: One or more mathematical certificates failed verification!")
        return 1

    print("\n[2/2] Running 10,000 Profiling Iterations Across 64 Hexagram States...")
    metrics = run_microbenchmark(10_000)

    print("\n" + "-" * 68)
    print("Benchmark Results Summary:")
    print("-" * 68)
    print(f"  Iterations:          {metrics['iterations']:,}")
    print(f"  Total Duration:      {metrics['total_time_sec']} s")
    print(f"  Throughput:          {metrics['throughput_ops_sec']:,} ops/sec")
    print(f"  Mean Latency:        {metrics['mean_latency_us']} µs")
    print(f"  Median (p50):        {metrics['p50_latency_us']} µs")
    print(f"  95th Percentile:     {metrics['p95_latency_us']} µs")
    print(f"  99th Percentile:     {metrics['p99_latency_us']} µs")
    print(f"  Min / Max Latency:   {metrics['min_latency_us']} µs / {metrics['max_latency_us']} µs")
    print("-" * 68)

    report_payload = {
        "certificates": cert_results,
        "benchmark": metrics,
    }
    print(f"\nJSON Output:\n{json.dumps(report_payload, indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
