import json
import os
import subprocess
import sys
import unittest

from onecode.kernel.hexagram import IchingKernel


class SelfAuditCliTests(unittest.TestCase):
    def test_cli_audit_self_reviews_shell_tui_model_and_kernel_with_iching_status(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
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


if __name__ == "__main__":
    unittest.main()
