"""Held-out split and score summary for the P1 evaluation."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import batch_report  # noqa: E402
import heldout_eval  # noqa: E402
import ledger_stats  # noqa: E402

classify_task = heldout_eval.classify_task
prompt_sha256 = heldout_eval.prompt_sha256
split_tasks = heldout_eval.split_tasks
summarize_rewards = heldout_eval.summarize_rewards


class HeldOutEvalTests(unittest.TestCase):
    def test_hard_verifier_tasks_are_in_sample_and_other_verifier_tasks_are_held_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("data_quality-hard-schema_drift", "product_policy-medium-refund_policy", "notes-easy-readme"):
                task = root / name / "tests"
                task.mkdir(parents=True)
                if "readme" not in name:
                    (task / "verifier.py").write_text("print(1)\n", encoding="utf-8")
            groups = split_tasks(root)
        self.assertEqual(groups["in_sample"], ["data_quality-hard-schema_drift"])
        self.assertEqual(groups["held_out"], ["product_policy-medium-refund_policy"])
        self.assertEqual(groups["excluded"], ["notes-easy-readme"])
        self.assertEqual(classify_task(root / "missing"), "excluded")

    def test_summary_reports_mean_interval_and_delta_and_counts_ungraded_as_zero(self) -> None:
        summary = summarize_rewards(
            [
                {"task_id": "a", "host_reward": 1.0},
                {"task_id": "b", "host_reward": 0.5},
                {"task_id": "c", "host_reward": "ungraded"},
            ],
            reference_mean=0.8474,
        )
        self.assertEqual(summary["task_count"], 3)
        self.assertEqual(summary["ungraded_count"], 1)
        self.assertEqual(summary["mean"], 0.5)
        self.assertEqual(summary["min"], 0.0)
        self.assertEqual(summary["max"], 1.0)
        self.assertEqual(summary["delta_vs_in_sample"], round(0.5 - 0.8474, 4))

    def test_prompt_hash_is_a_stable_sha256(self) -> None:
        digest = prompt_sha256()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, prompt_sha256())

    def test_batch_report_sums_usage_and_leaves_cost_empty_when_the_provider_omits_it(self) -> None:
        report = batch_report.batch_run_report(
            [
                {"duration_s": 1.5, "model_usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14, "call_count": 1}},
                {"duration_s": 2.5, "model_usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4, "call_count": 1, "cost_usd": None}},
            ],
            model="deepseek-v4.1-flash",
            endpoint="https://example.test/v1",
            prompt_sha256="abc",
            git_revision_value="2e3b5e3",
        )
        self.assertEqual(report["git_revision"], "2e3b5e3")
        self.assertEqual(report["prompt_tokens"], 13)
        self.assertEqual(report["completion_tokens"], 5)
        self.assertEqual(report["total_tokens"], 18)
        self.assertEqual(report["duration_s"], 4.0)
        self.assertIsNone(report["cost_usd"])
        self.assertFalse(report["claims_mainstream_parity"])

    def test_ledger_stats_use_the_same_hexagram_codes_for_both_modes(self) -> None:
        summary = ledger_stats.summarize_ledger_rows(
            [
                {"agent_mode": "classic", "iching_status_code": 63, "outcome_status_code": 63, "status": "completed"},
                {"agent_mode": "terminal", "iching_status_code": 63, "outcome_status_code": 63, "status": "completed"},
                {"agent_mode": "terminal", "outcome_status_code": 0, "status": "completed"},
                {"agent_mode": "terminal", "iching_status_code": 40, "outcome_status_code": 40, "status": "halted"},
            ]
        )
        self.assertEqual(summary["by_agent_mode"]["classic"], {"63": 1})
        self.assertEqual(summary["by_agent_mode"]["terminal"], {"63": 2, "40": 1})


if __name__ == "__main__":
    unittest.main()
