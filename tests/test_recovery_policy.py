import os
import unittest
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.recovery_policy import RecoveryContext, recovery_status


class RecoveryPolicyTests(unittest.TestCase):
    def test_each_initial_scenario_maps_to_bounded_action_and_iching_status(self):
        expected_actions = {
            "trace_flush_failure": "repair",
            "verifier_failure": "repair",
            "resume_conflict": "inspect",
            "sandbox_failure": "reconfigure",
            "provider_failure": "retry_once",
            "config_partial_invalid": "inspect",
            "project_context_invalid": "inspect",
        }
        for scenario, action in expected_actions.items():
            with self.subTest(scenario=scenario):
                status = recovery_status(scenario)
                self.assertEqual(status["recommended_action"], action)
                self.assertEqual(status["attempted"], False)
                self.assertEqual(status["element"], "fire")
                self.assertIn("iching_status_code", status)
                self.assertIn("dispatch_decision", status)

    def test_attempts_are_limited_and_exhaustion_halts(self):
        context = RecoveryContext()
        first = context.record_attempt("provider_failure", success=False)
        second = context.record_attempt("provider_failure", success=False)

        self.assertEqual(first["attempt_count"], 1)
        self.assertEqual(first["attempts_remaining"], 1)
        self.assertEqual(second["state"], "exhausted")
        self.assertEqual(second["recommended_action"], "halt")
        self.assertEqual(
            second["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )

    def test_successful_attempt_records_recovered_state(self):
        context = RecoveryContext()
        result = context.record_attempt("verifier_failure", success=True)

        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["recommended_action"], "inspect")
        self.assertEqual(result["attempt_count"], 1)

    def test_recovery_status_with_explicit_status_code(self):
        # Default clean engineering mode: bounded damping without symbolic skin
        status_40 = recovery_status("verifier_failure", status_code=40, attempt_count=1)
        self.assertEqual(status_40["iching_status_code"], 40)
        self.assertNotIn("jie_shen_relief", status_40)
        self.assertNotIn("twelve_deities", status_40)
        self.assertTrue(status_40["relief_effective"])
        self.assertEqual(status_40["lyapunov_damping_factor"], 0.75)

        status_47 = recovery_status("verifier_failure", status_code=47, attempt_count=2)
        self.assertEqual(status_47["iching_status_code"], 47)
        self.assertEqual(status_47["lyapunov_damping_factor"], 0.60)

        # Opt-in symbolic telemetry preserves jie_shen_relief / twelve_deities payload
        with patch.dict(os.environ, {"ONECODE_SYMBOLIC_TELEMETRY": "1"}):
            sym_40 = recovery_status("verifier_failure", status_code=40, attempt_count=1)
            self.assertIn("jie_shen_relief", sym_40)
            self.assertTrue(sym_40["jie_shen_relief"]["relief_effective"])
            self.assertEqual(sym_40["jie_shen_relief"]["damping_factor"], 0.75)
            sym_47 = recovery_status("verifier_failure", status_code=47, attempt_count=2)
            self.assertEqual(sym_47["jie_shen_relief"]["damping_factor"], 0.60)

    def test_record_attempt_preserves_explicit_status_code(self):
        context = RecoveryContext()
        result = context.record_attempt("verifier_failure", success=False, status_code=47)
        self.assertEqual(result["iching_status_code"], 47)
        self.assertEqual(result["attempt_count"], 1)


if __name__ == "__main__":
    unittest.main()
