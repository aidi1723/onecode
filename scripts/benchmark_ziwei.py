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
    """Verify all 6 mathematical certificates directly."""
    c_ring = IchingKernel.sovereign_ring_isomorphism_certificate()
    c_anhe = IchingKernel.an_he_coupling_certificate()
    c_shengong = IchingKernel.shen_gong_anchorage_certificate()
    c_bright = IchingKernel.star_brightness_certificate()
    c_jieshen = IchingKernel.jie_shen_even_subgroup_relief_certificate()
    c_twelve = IchingKernel.twelve_deities_triad_and_suipo_certificate()
    
    return {
        "sovereign_ring": c_ring.get("status") == "verified" and c_ring.get("triad_balance_verified") is True,
        "an_he_coupling": c_anhe.get("status") == "verified" and c_anhe.get("distance_palindrome_verified") is True,
        "shen_gong_anchorage": c_shengong.get("status") == "verified" and c_shengong.get("antipodal_symmetry_verified") is True,
        "star_brightness": c_bright.get("status") == "verified" and c_bright.get("all_states_valid") is True,
        "jie_shen_even_subgroup_relief": c_jieshen.get("status") == "verified" and c_jieshen.get("odd_palace_exclusion_verified") is True,
        "twelve_deities_triad_and_suipo": c_twelve.get("status") == "verified" and c_twelve.get("triad_partition_verified") is True and c_twelve.get("suipo_opposite_involution_verified") is True,
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
