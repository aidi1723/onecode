import json
import os
import subprocess
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from onecode.cli import build_run_plan_repair_prompt, is_patch_only_repair_plan, main
from onecode.kernel.model_provider import ModelPlan, ModelPlanAsset, ModelPlanPatch


class FakeRepairProvider:
    def __init__(self, plans: list[ModelPlan]):
        self.plans = list(plans)
        self.prompts: list[str] = []

    def create_plan(self, task: str, model: str, http_timeout_seconds: float) -> ModelPlan:
        self.prompts.append(task)
        return self.plans.pop(0)


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

    def write_repair_plan(self, workspace: Path) -> Path:
        plan_path = workspace / "repair-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "task": "repairable plan",
                    "assets": [
                        {
                            "path": "src/calc.py",
                            "content": "def value():\n    return 1\n",
                        },
                        {
                            "path": "tests/test_calc.py",
                            "content": "import unittest\nfrom src.calc import value\n\nclass CalcTests(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(value(), 20)\n",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return plan_path

    def test_cli_run_plan_repair_requires_selected_verifiers_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_plan(workspace)

            with self.assertRaises(SystemExit):
                main(
                    [
                        "run-plan",
                        "--workspace",
                        tmp,
                        "--plan",
                        str(plan_path),
                        "--run-id",
                        "repair-no-verifier",
                        "--max-repair-attempts",
                        "1",
                    ]
                )

            self.assertFalse((workspace / "src" / "generated.py").exists())

    def test_run_plan_repair_prompt_includes_verifier_evidence(self):
        prompt = build_run_plan_repair_prompt(
            task="repair task",
            result={
                "run_id": "run-1",
                "task_status_code": 48,
                "task_transition_action": "halt",
                "task_resume_decisions": [{"kind": "ready", "target_id": "src/a.py"}],
            },
            verifier_results=[
                {
                    "id": "unit",
                    "status": "failed",
                    "reason": "verifier_failed",
                    "exit_code": 1,
                    "stdout_tail": "stdout evidence",
                    "stderr_tail": "stderr evidence",
                }
            ],
            planned_asset_paths=["src/a.py", "tests/test_a.py"],
        )

        self.assertIn("unit", prompt)
        self.assertIn("verifier_failed", prompt)
        self.assertIn("stdout evidence", prompt)
        self.assertIn("stderr evidence", prompt)
        self.assertIn("src/a.py", prompt)
        self.assertIn("patches only", prompt)

    def test_run_plan_repair_accepts_only_patch_plans(self):
        patch_plan = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="src/a.py", search_block="bad", replace_block="good")],
        )
        asset_plan = ModelPlan(
            task="bad repair",
            assets=[ModelPlanAsset(path="src/a.py", content="value = 1\n")],
        )

        self.assertTrue(is_patch_only_repair_plan(patch_plan))
        self.assertFalse(is_patch_only_repair_plan(asset_plan))

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

    def test_cli_run_plan_repairs_failed_verifier_with_patch_only_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_repair_plan(workspace)
            policy_path = self.write_policy(
                workspace,
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            )
            provider = FakeRepairProvider(
                [
                    ModelPlan(
                        task="repair",
                        patches=[
                            ModelPlanPatch(
                                path="src/calc.py",
                                search_block="def value():\n    return 1\n",
                                replace_block="def value():\n    return 20\n",
                            )
                        ],
                    )
                ]
            )

            with patch("onecode.cli.build_provider", return_value=provider):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repair-success",
                            "--verifier-policy",
                            str(policy_path),
                            "--verifier",
                            "python-unittest",
                            "--repair-api-key",
                            "test-key",
                            "--max-repair-attempts",
                            "1",
                        ]
                    )
            result = json.loads(print_mock.call_args.args[0])

            self.assertEqual(exit_code, 0)
            self.assertTrue(result["repaired"])
            self.assertEqual(result["repair_attempt_count"], 1)
            self.assertEqual(result["repair_verifier_results"][-1][0]["status"], "passed")
            self.assertIn("return 20", (workspace / "src" / "calc.py").read_text(encoding="utf-8"))
            self.assertIn("verifier_failed", provider.prompts[0])

    def test_cli_run_plan_rejects_non_patch_repair_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_repair_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            provider = FakeRepairProvider(
                [ModelPlan(task="bad repair", assets=[ModelPlanAsset(path="src/calc.py", content="bad\n")])]
            )

            with patch("onecode.cli.build_provider", return_value=provider):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repair-rejected",
                            "--verifier-policy",
                            str(policy_path),
                            "--verifier",
                            "python-unittest",
                            "--repair-api-key",
                            "test-key",
                            "--max-repair-attempts",
                            "1",
                        ]
                    )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertFalse(result["repaired"])
            self.assertEqual(result["repair_rejected_reason"], "repair_plan_must_use_patches_only")

    def test_cli_run_plan_exhausted_repair_attempt_remains_halted(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_repair_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            provider = FakeRepairProvider(
                [
                    ModelPlan(
                        task="repair",
                        patches=[
                            ModelPlanPatch(
                                path="src/calc.py",
                                search_block="def value():\n    return 1\n",
                                replace_block="def value():\n    return 3\n",
                            )
                        ],
                    )
                ]
            )

            with patch("onecode.cli.build_provider", return_value=provider):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repair-exhausted",
                            "--verifier-policy",
                            str(policy_path),
                            "--verifier",
                            "python-unittest",
                            "--repair-api-key",
                            "test-key",
                            "--max-repair-attempts",
                            "1",
                        ]
                    )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertFalse(result["repaired"])
            self.assertEqual(result["repair_attempt_count"], 1)
            self.assertEqual(result["repair_verifier_results"][-1][0]["status"], "failed")

    def test_cli_run_plan_second_repair_prompt_uses_latest_verifier_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_repair_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            provider = FakeRepairProvider(
                [
                    ModelPlan(
                        task="repair",
                        patches=[
                            ModelPlanPatch(
                                path="src/calc.py",
                                search_block="def value():\n    return 1\n",
                                replace_block="def value():\n    return 300\n",
                            )
                        ],
                    ),
                    ModelPlan(
                        task="repair",
                        patches=[
                            ModelPlanPatch(
                                path="src/calc.py",
                                search_block="def value():\n    return 300\n",
                                replace_block="def value():\n    return 20\n",
                            )
                        ],
                    ),
                ]
            )

            with patch("onecode.cli.build_provider", return_value=provider):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repair-second-prompt",
                            "--verifier-policy",
                            str(policy_path),
                            "--verifier",
                            "python-unittest",
                            "--repair-api-key",
                            "test-key",
                            "--max-repair-attempts",
                            "2",
                        ]
                    )
            result = json.loads(print_mock.call_args.args[0])

            self.assertEqual(exit_code, 0)
            self.assertTrue(result["repaired"])
            self.assertEqual(len(provider.prompts), 2)
            self.assertIn("300 != 20", provider.prompts[1])

    def test_cli_run_plan_does_not_repair_when_attempts_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = self.write_repair_plan(workspace)
            policy_path = self.write_policy(workspace, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            provider = FakeRepairProvider([])

            with patch("onecode.cli.build_provider", return_value=provider):
                with patch("builtins.print") as print_mock:
                    exit_code = main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repair-disabled",
                            "--verifier-policy",
                            str(policy_path),
                            "--verifier",
                            "python-unittest",
                        ]
                    )
            result = json.loads(print_mock.call_args.args[0])

            self.assertNotEqual(exit_code, 0)
            self.assertNotIn("repair_attempt_count", result)
            self.assertEqual(provider.prompts, [])

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
