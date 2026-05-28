import json
import os
import subprocess
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main


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
            self.assertEqual(result["plan_path"], str(plan_path.resolve()))
            self.assertEqual(result["plan_sha256"], hashlib.sha256(plan_path.read_bytes()).hexdigest())
            self.assertEqual(result["plan_asset_count"], 2)
            self.assertEqual(summary["plan_path"], str(plan_path.resolve()))
            self.assertEqual(summary["plan_sha256"], result["plan_sha256"])
            self.assertEqual(summary["plan_asset_count"], 2)
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

    def test_cli_run_plan_exit_code_delegates_to_iching_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "delegated plan",
                        "assets": [{"path": "../outside.py", "content": "blocked\n"}],
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch(
                    "onecode.cli.run_task",
                    return_value={
                        "status": "halted",
                        "reason": "sovereignty_breach",
                    },
                ),
                patch("onecode.cli.IchingKernel.process_exit_code", return_value=0) as process_exit_code,
                patch("builtins.print"),
            ):
                exit_code = main(["run-plan", "--workspace", tmp, "--plan", str(plan_path)])

        self.assertEqual(exit_code, 0)
        process_exit_code.assert_called_once_with(status="halted", reason="sovereignty_breach")

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

    def test_cli_run_plan_rejects_duplicate_paths_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "duplicate-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "duplicate",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n"},
                            {"path": "src/a.py", "content": "A = 2\n"},
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
                    "duplicate-plan",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid plan asset 2: duplicate path src/a.py", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "src" / "a.py").exists())

    def test_cli_run_plan_rejects_unknown_asset_fields_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "unknown-field-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "unknown field",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n", "command": "echo no"},
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
                    "unknown-field-plan",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid plan asset 1: unknown fields command", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((workspace / "src" / "a.py").exists())

    def test_cli_run_plan_rejects_invalid_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "invalid-json-plan.json"
            plan_path.write_text("{not json", encoding="utf-8")
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
                    "invalid-json-plan",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid plan: invalid_json", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
