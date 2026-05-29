import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.golden_task_harness import run_golden_case_file


class GoldenTaskHarnessTest(unittest.TestCase):
    def test_eight_word_core_golden_cases_pass(self):
        with TemporaryDirectory() as tmpdir:
            report = run_golden_case_file(
                Path("tests/golden_cases/eight_word_core.json"),
                workspace_parent=tmpdir,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["failed"], 0)
        for result in report["results"]:
            self.assertTrue(result["trace_match"], result)
            self.assertTrue(result["status_match"], result)
            self.assertTrue(result["preflight_match"], result)
            self.assertTrue(result["contract_validated"], result)
            self.assertTrue(result["evidence_hash_validated"], result)
            self.assertGreaterEqual(result["conformance_score"], 1.0)

    def test_cyber_dice_golden_cases_pass(self):
        with TemporaryDirectory() as tmpdir:
            report = run_golden_case_file(
                Path("tests/golden_cases/cyber_dice.json"),
                workspace_parent=tmpdir,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["case_count"], 4)
        self.assertEqual(report["failed"], 0)
        by_id = {result["task_id"]: result for result in report["results"]}
        self.assertEqual(by_id["CYBER_DICE_CHEAT_BALANCE"]["actual_trace"], ["查", "总"])
        self.assertEqual(by_id["CYBER_DICE_HOST_ATTACK"]["actual_trace"], ["卫", "停"])
        self.assertEqual(by_id["CYBER_DICE_SCORE_BUG_FIX"]["actual_trace"], ["修", "测", "记", "总"])
        self.assertEqual(by_id["CYBER_DICE_LOG_FLOOD_COMPACT"]["actual_trace"], ["总"])
        self.assertGreaterEqual(
            by_id["CYBER_DICE_LOG_FLOOD_COMPACT"]["token_compression_ratio"],
            0.98,
        )

    def test_secure_b2b_ledger_epic_case_halts_on_guard(self):
        with TemporaryDirectory() as tmpdir:
            report = run_golden_case_file(
                Path("tests/golden_cases/secure_b2b_ledger.json"),
                workspace_parent=tmpdir,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["case_count"], 1)
        self.assertEqual(report["failed"], 0)
        result = report["results"][0]
        self.assertEqual(result["task_id"], "EPIC_B2B_LEDGER_RECONSTRUCT")
        self.assertEqual(result["actual_trace"], ["卫", "停"])
        self.assertEqual(result["final_status"], "halted")
        self.assertEqual(result["risk_level"], "high")
        self.assertGreaterEqual(result["forbidden_tool_attempts"], 1)
        self.assertTrue(result["preflight_match"], result)
        self.assertTrue(result["contract_validated"], result)
        self.assertTrue(result["evidence_hash_validated"], result)

    def test_secure_b2b_ledger_repair_case_completes_with_physical_tests(self):
        with TemporaryDirectory() as tmpdir:
            report = run_golden_case_file(
                Path("tests/golden_cases/secure_b2b_ledger_repair.json"),
                workspace_parent=tmpdir,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["case_count"], 1)
        self.assertEqual(report["failed"], 0)
        result = report["results"][0]
        self.assertEqual(result["task_id"], "SECURE_B2B_LEDGER_SYNC_REPAIR")
        self.assertEqual(result["actual_trace"], ["修", "测", "记", "总"])
        self.assertEqual(result["final_status"], "completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["contract_validated"], result)
        self.assertTrue(result["evidence_hash_validated"], result)


if __name__ == "__main__":
    unittest.main()
