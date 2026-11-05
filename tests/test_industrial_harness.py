"""Tests for the Industrial Agent Reliability & Governance Benchmark Harness."""
from __future__ import annotations

import unittest

from scripts.bench_industrial import (
    compute_pass_k_metrics,
    generate_industrial_audit_markdown,
    run_failsafe_rollback_harness,
    run_negative_control_harness,
)


class IndustrialHarnessTests(unittest.TestCase):
    def test_compute_pass_k_empty_records(self) -> None:
        metrics = compute_pass_k_metrics([])
        self.assertIn("error", metrics)

    def test_compute_pass_k_deterministic_and_drift_categorization(self) -> None:
        r1 = {
            "task-det": {"task_id": "task-det", "host_reward": 1.0},
            "task-drift": {"task_id": "task-drift", "host_reward": 0.5},
            "task-fail": {"task_id": "task-fail", "host_reward": 0.0},
        }
        r2 = {
            "task-det": {"task_id": "task-det", "host_reward": 1.0},
            "task-drift": {"task_id": "task-drift", "host_reward": 1.0},
            "task-fail": {"task_id": "task-fail", "host_reward": 0.0},
        }
        r3 = {
            "task-det": {"task_id": "task-det", "host_reward": 1.0},
            "task-drift": {"task_id": "task-drift", "host_reward": 0.2},
            "task-fail": {"task_id": "task-fail", "host_reward": 0.0},
        }
        metrics = compute_pass_k_metrics([r1, r2, r3], k_values=[1, 2, 3])
        self.assertEqual(metrics["total_tasks"], 3)
        self.assertEqual(metrics["total_rounds"], 3)

        # pass@1 for round 3: only task-det is 1.0 -> 1/3 = 0.3333
        self.assertAlmostEqual(metrics["latest_pass_at_1"], 0.3333, places=3)

        # pass^2 (r2 and r3): task-det is 1.0 in both, task-drift is 1.0 in r2 but 0.2 in r3 -> 1/3
        pass_2 = metrics["pass_pow_k"]["pass^2"]
        self.assertTrue(pass_2["available"])
        self.assertEqual(pass_2["passed_count"], 1)

        # pass^3 (r1, r2, r3): task-det is 1.0 in all three -> 1/3
        pass_3 = metrics["pass_pow_k"]["pass^3"]
        self.assertTrue(pass_3["available"])
        self.assertEqual(pass_3["passed_count"], 1)

        self.assertIn("task-det", metrics["deterministic_assets"])
        self.assertIn("task-drift", metrics["stochastic_drift_assets"])
        self.assertIn("task-fail", metrics["blocked_assets"])

    def test_negative_control_harness_catches_all_traps(self) -> None:
        report = run_negative_control_harness()
        self.assertTrue(report["all_passed"], f"Negative control traps failed: {report}")
        self.assertEqual(report["total_traps"], 5)
        self.assertEqual(report["passed_traps"], 5)
        self.assertAlmostEqual(report["compliance_rate"], 1.0)

    def test_failsafe_rollback_harness_preserves_invariants(self) -> None:
        report = run_failsafe_rollback_harness()
        self.assertTrue(report["all_passed"], f"Fail-safe invariants failed: {report}")
        self.assertEqual(report["total_invariants"], 2)
        self.assertEqual(report["passed_invariants"], 2)

    def test_generate_industrial_audit_markdown_includes_all_sections(self) -> None:
        redline = run_negative_control_harness()
        failsafe = run_failsafe_rollback_harness()
        md = generate_industrial_audit_markdown(None, redline, failsafe)
        self.assertIn("OneCode 工业级智能体可靠性与合规安全审查报告", md)
        self.assertIn("负向控制与 SOP 红线诱捕测试", md)
        self.assertIn("状态准入与故障回滚验真", md)
        self.assertIn("NC-01", md)
        self.assertIn("FS-01", md)


if __name__ == "__main__":
    unittest.main()
