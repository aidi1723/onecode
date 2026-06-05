import unittest

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


if __name__ == "__main__":
    unittest.main()
