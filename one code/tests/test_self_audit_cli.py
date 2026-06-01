import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from onecode.kernel.self_audit import audit_check, audit_self
from onecode.kernel.hexagram import IchingKernel


class SelfAuditCliTests(unittest.TestCase):
    def test_cli_audit_self_reviews_shell_tui_model_and_kernel_with_iching_status(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        env["ONECODE_AUDIT_SELF_DEPTH"] = "1"
        completed = subprocess.run(
            [sys.executable, "-m", "onecode.cli", "audit-self"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        result = json.loads(completed.stdout)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["iching_status_code"], IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN))
        self.assertEqual(result["iching_transition_action"], "cooldown")
        self.assertEqual(result["dispatch_decision"], "continue")
        self.assertEqual(
            [check["name"] for check in result["checks"]],
            [
                "cli_entrypoint",
                "tui_bootstrap",
                "model_provider_matrix",
                "compileall",
                "unittest",
                "doctor",
            ],
        )
        self.assertTrue(all(check["passed"] for check in result["checks"]))
        self.assertEqual(result["checks"][1]["detail"]["shell"], "tui")
        self.assertEqual(result["checks"][2]["detail"]["providers"], ["qwen", "deepseek", "kimi", "zhipu"])

    def test_audit_self_failed_check_stops_dispatch(self):
        def failed_doctor():
            return {"status": "failed", "checks": [audit_check("doctor-smoke", False)]}

        result = audit_self(
            project_root=Path.cwd(),
            doctor_runner=failed_doctor,
            run_unittest=False,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["iching_status_code"], IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(result["iching_transition_action"], "halt")
        self.assertEqual(result["dispatch_decision"], "stop")


if __name__ == "__main__":
    unittest.main()
