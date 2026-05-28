import json
import os
import subprocess
import sys
import unittest

from onecode.kernel.hexagram import IchingKernel


class DoctorCliTests(unittest.TestCase):
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
