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
    def write_plan(self, workspace: Path, path: str = "task-plan.json") -> Path:
        plan_path = workspace / path
        plan_path.write_text(
            json.dumps(
                {
                    "task": "verified plan",
                    "assets": [
                        {"path": "src/generated.py", "content": "VALUE = 1\n"},
                        {
                            "path": "tests/test_generated.py",
                            "content": "import unittest\n\nclass GeneratedTests(unittest.TestCase):\n    def test_generated(self):\n        self.assertEqual(1, 1)\n",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return plan_path

    def write_policy(
        self,
        workspace: Path,
        command: list[str],
        timeout_ms: int = 5000,
        cwd: str = ".",
        verifier_id: str = "python-unittest",
    ) -> Path:
        policy_path = workspace / "verifiers.json"
        policy_path.write_text(
            json.dumps(
                {
                    "verifiers": [
                        {
                            "id": verifier_id,
                            "command": command,
                            "cwd": cwd,
                            "timeout_ms": timeout_ms,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return policy_path

    def test_cli_run_plan_runs_passing_verifier_and_records_task_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(
                workspace,
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "verified",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])

            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["delivery_status"], "deliverable")
            self.assertEqual(result["verifier_results"][0]["status"], "passed")
            self.assertIsNone(result["verifier_results"][0]["reason"])
            self.assertTrue(result["task_completion_evidence"]["verifiers_passed"])
            self.assertTrue(result["task_completion_evidence"]["assets_complete"])
            self.assertIn("task_status_code", result)

    def test_cli_run_plan_resume_records_ready_asset_and_verifier_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(
                workspace,
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            )
            with patch("builtins.print"):
                main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "source-verified",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "resume-verified",
                        "--resume-from",
                        "source-verified",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])
            decisions = {(decision["target_type"], decision["target_id"]): decision for decision in result["task_resume_decisions"]}

            self.assertEqual(exit_code, 0)
            self.assertEqual(decisions[("asset", "src/generated.py")]["kind"], "ready")
            self.assertEqual(decisions[("asset", "tests/test_generated.py")]["kind"], "ready")
            self.assertEqual(decisions[("verifier", "python-unittest")]["kind"], "ready")
            self.assertIn("task_resume_status_code", result)

    def test_cli_run_plan_resume_records_verify_when_verifier_evidence_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            with patch("builtins.print"):
                main(["run-plan", "--workspace", tmp, "--plan", str(plan_path), "--run-id", "source-assets"])

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "resume-needs-verify",
                        "--resume-from",
                        "source-assets",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])
            decisions = {(decision["target_type"], decision["target_id"]): decision for decision in result["task_resume_decisions"]}

            self.assertEqual(exit_code, 0)
            self.assertEqual(decisions[("asset", "src/generated.py")]["kind"], "verify")
            self.assertEqual(decisions[("asset", "tests/test_generated.py")]["kind"], "verify")
            self.assertEqual(decisions[("verifier", "python-unittest")]["kind"], "apply")

    def test_cli_run_plan_resume_halts_on_asset_hash_conflict_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            source_plan = self.write_plan(workspace, "source-plan.json")
            recovery_plan = workspace / "recovery-plan.json"
            recovery_plan.write_text(
                json.dumps(
                    {
                        "task": "recovery",
                        "assets": [
                            {"path": "src/generated.py", "content": "VALUE = 2\n"},
                            {"path": "src/later.py", "content": "LATER = True\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch("builtins.print"):
                main(["run-plan", "--workspace", tmp, "--plan", str(source_plan), "--run-id", "source-assets"])
            (workspace / "src" / "generated.py").write_text("VALUE = 99\n", encoding="utf-8")

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(recovery_plan),
                        "--run-id",
                        "resume-conflict",
                        "--resume-from",
                        "source-assets",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "asset_hash_conflict")
            self.assertFalse((workspace / "src" / "later.py").exists())

    def test_cli_run_plan_blocks_delivery_when_verifier_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(
                workspace,
                [sys.executable, "-c", "import sys; print('bad verifier'); sys.exit(5)"],
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "verifier-failed",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "verifier_failed")
            self.assertEqual(result["delivery_status"], "blocked")
            self.assertEqual(result["verifier_results"][0]["exit_code"], 5)
            self.assertIn("bad verifier", result["verifier_results"][0]["stdout_tail"])

    def test_cli_run_plan_blocks_delivery_when_verifier_times_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(
                workspace,
                [sys.executable, "-c", "import time; time.sleep(1)"],
                timeout_ms=10,
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "verifier-timeout",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "verifier_timeout")
            self.assertEqual(result["verifier_results"][0]["reason"], "verifier_timeout")

    def test_cli_run_plan_rejects_unknown_verifier_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-V"])

            with self.assertRaises(SystemExit):
                main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "unknown-verifier",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "missing",
                    ]
                )

            self.assertFalse((workspace / "src" / "generated.py").exists())

    def test_cli_run_plan_rejects_verifier_cwd_outside_workspace_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-V"], cwd="..")

            with self.assertRaises(SystemExit):
                main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "outside-cwd",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )

            self.assertFalse((workspace / "src" / "generated.py").exists())

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
