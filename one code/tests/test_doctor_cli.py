import json
import os
import subprocess
import sys
import unittest

from onecode.kernel.hexagram import IchingKernel


class DoctorCliTests(unittest.TestCase):
    def test_cli_math_audit_reports_control_theory_mapping_summary(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        completed = subprocess.run(
            [sys.executable, "-m", "onecode.cli", "math-audit"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        result = json.loads(completed.stdout)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["state_count"], 64)
        self.assertGreaterEqual(result["attractor_count"], 1)
        self.assertEqual(result["unclassified_state_count"], 0)
        self.assertEqual(result["reference_only"], ["probabilistic_sampling", "runtime_gain_learning", "multi_agent_tensor_product"])
        self.assertIn("lyapunov_min", result)
        self.assertIn("lyapunov_max", result)
        self.assertLessEqual(result["lyapunov_min"], result["lyapunov_max"])
        self.assertEqual(result["accepted_mappings"][0], "transition_graph")
        self.assertIn("stability", result)
        self.assertEqual(result["stability"]["state_count"], 64)
        self.assertEqual(result["stability"]["unclassified_state_count"], 0)
        self.assertLessEqual(result["stability"]["max_steps_to_attractor"], 64)
        self.assertEqual(
            result["stability"]["energy_increase_transition_count"]
            + result["stability"]["energy_decrease_transition_count"]
            + result["stability"]["energy_flat_transition_count"],
            64,
        )
        self.assertIn("topology", result)
        self.assertEqual(result["topology"]["state_space"], "Q6")
        self.assertEqual(result["topology"]["unclosed_transition_count"], 0)
        self.assertIn("lyapunov", result)
        self.assertTrue(result["lyapunov"]["nonincreasing"])
        self.assertEqual(result["lyapunov"]["energy_increase_transition_count"], 0)
        self.assertIn("entropy_gate", result)
        self.assertEqual(result["entropy_gate"]["low_entropy_halt_probe"]["decision"], "sovereignty_halt")
        self.assertEqual(result["entropy_gate"]["exploration_probe"]["decision"], "observe")
        self.assertIn("totality", result)
        self.assertTrue(result["totality"]["total_over_known_inputs"])
        self.assertEqual(result["totality"]["unmapped_count"], 0)
        self.assertIn("safety_dominance", result)
        self.assertTrue(result["safety_dominance"]["safe"])
        self.assertEqual(result["safety_dominance"]["unsafe_pass_through_count"], 0)
        self.assertIn("collision_risk", result)
        self.assertTrue(result["collision_risk"]["safe"])
        self.assertEqual(result["collision_risk"]["unsafe_collision_count"], 0)

    def test_cli_doctor_runs_core_smoke_checks(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        completed = subprocess.run(
            [sys.executable, "-m", "onecode.cli", "doctor"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        result = json.loads(completed.stdout)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            [check["name"] for check in result["checks"]],
            ["write_text", "resume_skip", "sovereignty_breach", "http_timeout"],
        )
        self.assertTrue(all(check["passed"] for check in result["checks"]))
        self.assertEqual(result["checks"][0]["detail"]["run_id"], "doctor-write")
        self.assertEqual(result["checks"][1]["detail"]["run_id"], "doctor-resume")
        self.assertEqual(result["checks"][2]["detail"]["run_id"], "doctor-breach")
        self.assertEqual(result["checks"][3]["detail"]["run_id"], "doctor-timeout")

        expected = {
            "write_text": (IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN), "cooldown", "continue"),
            "resume_skip": (IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.DUI), "cooldown", "continue"),
            "sovereignty_breach": (IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN), "halt", "stop"),
            "http_timeout": (IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN), "checkpoint", "stop"),
        }
        for check in result["checks"]:
            expected_status_code, expected_transition_action, expected_dispatch_decision = expected[check["name"]]
            detail = check["detail"]
            self.assertEqual(detail["iching_status_code"], expected_status_code)
            self.assertEqual(detail["iching_transition_action"], expected_transition_action)
            self.assertEqual(detail["dispatch_decision"], expected_dispatch_decision)
            self.assertIn("iching_transition_reason", detail)


if __name__ == "__main__":
    unittest.main()
