import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RunPlanCliTests(unittest.TestCase):
    def test_cli_run_plan_writes_assets_and_inspects_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "plan smoke",
                        "assets": [
                            {"path": "src/mesh.py", "content": "READY = True\n"},
                            {"path": "tests/test_mesh.py", "content": "def test_mesh():\n    assert True\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run-plan",
                    "--workspace",
                    tmp,
                    "--plan",
                    str(plan_path),
                    "--run-id",
                    "plan-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(completed.stdout)

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "plan-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            summary = json.loads(inspected.stdout)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 2)
            self.assertEqual(summary["delivery_status"], "deliverable")
            self.assertEqual(summary["next_action"], "idle")
            self.assertEqual(summary["completed_count"], 2)
            self.assertEqual(summary["remaining_count"], 0)
            self.assertEqual(
                [(asset["status"], asset["path"]) for asset in summary["assets"]],
                [("completed", "src/mesh.py"), ("completed", "tests/test_mesh.py")],
            )
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "READY = True\n")
            self.assertEqual(
                (workspace / "tests" / "test_mesh.py").read_text(encoding="utf-8"),
                "def test_mesh():\n    assert True\n",
            )

    def test_cli_run_plan_halts_then_resumes_with_recovery_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            failing_plan = workspace / "failing-plan.json"
            failing_plan.write_text(
                json.dumps(
                    {
                        "task": "plan fail",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n"},
                            {"path": "../outside.py", "content": "blocked\n"},
                            {"path": "src/b.py", "content": "B = 1\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            recovery_plan = workspace / "recovery-plan.json"
            recovery_plan.write_text(
                json.dumps(
                    {
                        "task": "plan recover",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 2\n"},
                            {"path": "src/b.py", "content": "B = 1\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            failed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run-plan",
                    "--workspace",
                    tmp,
                    "--plan",
                    str(failing_plan),
                    "--run-id",
                    "plan-failed",
                ],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(failed.returncode, 0)

            resumed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run-plan",
                    "--workspace",
                    tmp,
                    "--plan",
                    str(recovery_plan),
                    "--run-id",
                    "plan-resumed",
                    "--resume-from",
                    "plan-failed",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(resumed.stdout)

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "plan-resumed",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            summary = json.loads(inspected.stdout)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["skipped_count"], 1)
            self.assertEqual(summary["delivery_status"], "deliverable")
            self.assertEqual(summary["resumed_from"], "plan-failed")
            self.assertEqual(
                [(asset["status"], asset["path"]) for asset in summary["assets"]],
                [("skipped", "src/a.py"), ("completed", "src/b.py")],
            )
            self.assertEqual((workspace / "src" / "a.py").read_text(encoding="utf-8"), "A = 1\n")
            self.assertEqual((workspace / "src" / "b.py").read_text(encoding="utf-8"), "B = 1\n")
            self.assertFalse((workspace.parent / "outside.py").exists())

    def test_cli_run_plan_rejects_invalid_plan_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "bad-plan.json"
            plan_path.write_text(json.dumps({"task": "bad", "assets": [{"path": "src/a.py"}]}), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run-plan",
                    "--workspace",
                    tmp,
                    "--plan",
                    str(plan_path),
                    "--run-id",
                    "bad-plan",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid plan asset 1: content must be a string", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "src" / "a.py").exists())


if __name__ == "__main__":
    unittest.main()
