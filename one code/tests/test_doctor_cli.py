import json
import os
import subprocess
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
