import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch

from onecode.cli import delivery_summary, inspect_run, main
from onecode.kernel.model_provider import ModelPlan, ModelPlanPatch
from onecode.kernel.runner import run_task
from tests.test_run_plan_cli import FakeRepairProvider


class InspectCliTests(unittest.TestCase):
    def test_cli_inspect_reports_verifier_task_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "verified inspect",
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
            policy_path = workspace / "verifiers.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                                "cwd": ".",
                                "timeout_ms": 5000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
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
                        "verified",
                        "--verifier-policy",
                        str(policy_path),
                        "--verifier",
                        "python-unittest",
                    ]
                )

            exit_code, summary = inspect_run(workspace, "verified")

            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["delivery_status"], "deliverable")
            self.assertIn("task_status_code", summary)
            self.assertIn("task_transition_action", summary)
            self.assertTrue(summary["task_completion_evidence"]["verifiers_passed"])
            self.assertEqual(summary["verifier_results"][0]["status"], "passed")

    def test_cli_inspect_reports_task_resume_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "resume inspect",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n"},
                            {"path": "src/b.py", "content": "B = 1\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print"):
                main(
                    [
                        "run",
                        "source",
                        "--workspace",
                        tmp,
                        "--run-id",
                        "source",
                        "--write-path",
                        "src/a.py",
                        "--write-content",
                        "A = 1\n",
                        "--completed-evidence-mode",
                        "full",
                        "--evidence-durability",
                        "strict",
                    ]
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
                        "resumed",
                        "--resume-from",
                        "source",
                    ]
                )

            exit_code, summary = inspect_run(workspace, "resumed")

            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["task_resume_decisions"][0]["kind"], "ready")
            self.assertIn("task_resume_status_code", summary)
            self.assertIn("task_resume_transition_action", summary)

    def test_cli_inspect_reports_repair_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan_path = workspace / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "repair inspect",
                        "assets": [
                            {"path": "src/calc.py", "content": "def value():\n    return 1\n"},
                            {
                                "path": "tests/test_calc.py",
                                "content": "import unittest\nfrom src.calc import value\n\nclass CalcTests(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(value(), 20)\n",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            policy_path = workspace / "verifiers.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                                "cwd": ".",
                                "timeout_ms": 5000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
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
                with patch("builtins.print"):
                    main(
                        [
                            "run-plan",
                            "--workspace",
                            tmp,
                            "--plan",
                            str(plan_path),
                            "--run-id",
                            "repaired",
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

            exit_code, summary = inspect_run(workspace, "repaired")

            self.assertEqual(exit_code, 0)
            self.assertTrue(summary["repaired"])
            self.assertEqual(summary["repair_attempt_count"], 1)
            self.assertEqual(summary["initial_verifier_results"][0]["status"], "failed")
            self.assertEqual(summary["repair_verifier_results"][-1][0]["status"], "passed")

    def test_cli_inspect_prints_existing_run_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "inspect source",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-run",
                    "--write-text",
                    "src/a.py=a = 1\n",
                    "--write-text",
                    "tests/test_a.py=def test_a():\n    assert True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            summary = json.loads(completed.stdout)

            self.assertEqual(summary["run_id"], "inspect-run")
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["requested_count"], 2)
            self.assertEqual(summary["completed_count"], 2)
            self.assertEqual(summary["checkpoint_count"], 2)
            self.assertTrue(Path(summary["manifest_path"]).exists())
            self.assertTrue(Path(summary["ledger_path"]).exists())
            self.assertIn("iching_status_code", summary)
            self.assertEqual(summary["shell_projection"]["run_id"], "inspect-run")
            self.assertEqual(summary["shell_projection"]["severity"], "ok")
            self.assertEqual(summary["shell_projection"]["evidence_ref"]["mode"], "full")

    def test_cli_inspect_prints_wal_only_run_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "inspect wal",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-wal",
                    "--completed-evidence-mode",
                    "wal",
                    "--evidence-durability",
                    "relaxed",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-wal",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            summary = json.loads(completed.stdout)

            self.assertEqual(summary["run_id"], "inspect-wal")
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["evidence_mode"], "wal")
            self.assertEqual(summary["requested_count"], 1)
            self.assertEqual(summary["completed_count"], 1)
            self.assertEqual(summary["failed_count"], 0)
            self.assertIsNone(summary["manifest_path"])
            self.assertIsNone(summary["ledger_path"])
            self.assertTrue(Path(summary["wal_path"]).exists())
            self.assertIn("profile_sha256", summary)
            self.assertEqual(summary["shell_projection"]["run_id"], "inspect-wal")
            self.assertEqual(summary["shell_projection"]["severity"], "ok")
            self.assertEqual(summary["shell_projection"]["evidence_ref"]["mode"], "wal")

    def test_cli_list_runs_includes_wal_only_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "list wal",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "list-wal",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            wal_run_root = Path(tmp) / ".onecode" / "runs" / "list-wal"
            if wal_run_root.exists():
                shutil.rmtree(wal_run_root)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "list full",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "list-full",
                    "--completed-evidence-mode",
                    "full",
                    "--evidence-durability",
                    "strict",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "list-runs",
                    "--workspace",
                    tmp,
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            runs = {entry["run_id"]: entry for entry in result["runs"]}

            self.assertEqual(runs["list-wal"]["evidence_mode"], "wal")
            self.assertEqual(runs["list-wal"]["shell_projection"]["evidence_ref"]["mode"], "wal")
            self.assertIsNone(runs["list-wal"]["ledger_path"])
            self.assertEqual(runs["list-full"]["status"], "completed")
            self.assertEqual(runs["list-full"]["shell_projection"]["evidence_ref"]["mode"], "full")
            self.assertNotEqual(runs["list-full"].get("evidence_mode"), "wal")
            self.assertEqual(sorted(runs), ["list-full", "list-wal"])

    def test_cli_inspect_reports_corrupt_global_wal(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            wal_path = Path(tmp) / ".onecode" / "global-ledger.jsonl"
            wal_path.parent.mkdir(parents=True)
            wal_path.write_text("{not json\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "inspect-wal",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            summary = json.loads(completed.stdout)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(summary["status"], "corrupt")
            self.assertEqual(summary["corrupt_reason"], "invalid_global_wal_json")
            self.assertEqual(summary["wal_path"], str(wal_path.resolve()))

    def test_cli_inspect_reports_tampered_global_wal_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "wal tamper",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "wal-tamper",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            wal_path = Path(tmp) / ".onecode" / "global-ledger.jsonl"
            entry = json.loads(wal_path.read_text(encoding="utf-8").splitlines()[0])
            entry["st"] = "halted"
            wal_path.write_text(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "wal-tamper",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            summary = json.loads(completed.stdout)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(summary["status"], "corrupt")
            self.assertEqual(summary["corrupt_reason"], "global_wal_chain_hash_mismatch")
            self.assertEqual(summary["wal_path"], str(wal_path.resolve()))

    def test_cli_inspect_and_list_runs_read_rotated_global_wal_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            env["ONECODE_WAL_ROTATE_BYTES"] = "1"
            for run_id in ("wal-old", "wal-new"):
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "onecode.cli",
                        "run",
                        f"rotate {run_id}",
                        "--workspace",
                        tmp,
                        "--run-id",
                        run_id,
                    ],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=True,
                )

            archive_path = Path(tmp) / ".onecode" / "global-ledger.1.jsonl"
            active_path = Path(tmp) / ".onecode" / "global-ledger.jsonl"
            inspect_old = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "wal-old",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            listed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "list-runs",
                    "--workspace",
                    tmp,
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            old_summary = json.loads(inspect_old.stdout)
            runs = {entry["run_id"]: entry for entry in json.loads(listed.stdout)["runs"]}

            self.assertTrue(archive_path.exists())
            self.assertTrue(active_path.exists())
            self.assertEqual(old_summary["status"], "completed")
            self.assertEqual(old_summary["wal_path"], str(archive_path.resolve()))
            self.assertEqual(runs["wal-old"]["evidence_mode"], "wal")
            self.assertEqual(runs["wal-old"]["wal_path"], str(archive_path.resolve()))
            self.assertEqual(runs["wal-new"]["evidence_mode"], "wal")
            self.assertEqual(runs["wal-new"]["wal_path"], str(active_path.resolve()))

    def test_cli_inspect_reports_resumed_project_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "source project",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "project-source",
                    "--write-text",
                    "src/mesh.py=READY = True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            resumed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "resume project",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "project-resume",
                    "--resume-from",
                    "project-source",
                    "--write-text",
                    "src/mesh.py=READY = False\n",
                    "--write-text",
                    "tests/test_mesh.py=def test_mesh():\n    assert True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            run_result = json.loads(resumed.stdout)

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "project-resume",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            summary = json.loads(inspected.stdout)
            self.assertEqual(run_result["status"], "completed")
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["resumed_from"], "project-source")
            self.assertEqual(summary["requested_count"], 2)
            self.assertEqual(summary["completed_count"], 1)
            self.assertEqual(summary["skipped_count"], 1)
            self.assertEqual(summary["failed_count"], 0)
            self.assertEqual(summary["checkpoint_count"], 2)
            self.assertEqual((Path(tmp) / "src" / "mesh.py").read_text(encoding="utf-8"), "READY = True\n")
            self.assertEqual(
                (Path(tmp) / "tests" / "test_mesh.py").read_text(encoding="utf-8"),
                "def test_mesh():\n    assert True\n",
            )

    def test_cli_inspect_reports_complex_task_completion_state_after_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            failed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "complex fail",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "complex-failed",
                    "--write-text",
                    "src/a.py=A = 1\n",
                    "--write-text",
                    "src/b.py=B = 1\n",
                    "--write-text",
                    "../outside.py=blocked\n",
                    "--write-text",
                    "src/c.py=C = 1\n",
                    "--write-text",
                    "tests/test_c.py=def test_c():\n    assert True\n",
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
                    "run",
                    "complex resume",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "complex-resumed",
                    "--resume-from",
                    "complex-failed",
                    "--write-text",
                    "src/a.py=A = 2\n",
                    "--write-text",
                    "src/b.py=B = 2\n",
                    "--write-text",
                    "src/c.py=C = 1\n",
                    "--write-text",
                    "tests/test_c.py=def test_c():\n    assert True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            run_result = json.loads(resumed.stdout)

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "complex-resumed",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            summary = json.loads(inspected.stdout)

            self.assertEqual(run_result["status"], "completed")
            self.assertEqual(summary["delivery_status"], "deliverable")
            self.assertEqual(summary["next_action"], "idle")
            self.assertEqual(summary["resumed_from"], "complex-failed")
            self.assertEqual(summary["requested_count"], 4)
            self.assertEqual(summary["completed_count"], 2)
            self.assertEqual(summary["skipped_count"], 2)
            self.assertEqual(summary["failed_count"], 0)
            self.assertEqual(summary["resolved_count"], 4)
            self.assertEqual(summary["remaining_count"], 0)
            self.assertEqual(summary["checkpoint_count"], 4)
            self.assertEqual(
                [(asset["status"], asset["path"]) for asset in summary["assets"]],
                [
                    ("skipped", "src/a.py"),
                    ("skipped", "src/b.py"),
                    ("completed", "src/c.py"),
                    ("completed", "tests/test_c.py"),
                ],
            )
            self.assertEqual((Path(tmp) / "src" / "a.py").read_text(encoding="utf-8"), "A = 1\n")
            self.assertEqual((Path(tmp) / "src" / "b.py").read_text(encoding="utf-8"), "B = 1\n")
            self.assertEqual((Path(tmp) / "src" / "c.py").read_text(encoding="utf-8"), "C = 1\n")
            self.assertEqual(
                (Path(tmp) / "tests" / "test_c.py").read_text(encoding="utf-8"),
                "def test_c():\n    assert True\n",
            )

    def test_cli_inspect_reports_blocked_complex_task_can_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            failed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "complex blocked",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "complex-blocked",
                    "--write-text",
                    "src/a.py=A = 1\n",
                    "--write-text",
                    "../outside.py=blocked\n",
                    "--write-text",
                    "src/b.py=B = 1\n",
                ],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(failed.returncode, 0)

            inspected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "complex-blocked",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            summary = json.loads(inspected.stdout)

            self.assertEqual(summary["status"], "halted")
            self.assertEqual(summary["reason"], "sovereignty_breach")
            self.assertEqual(summary["delivery_status"], "blocked")
            self.assertEqual(summary["next_action"], "resume")
            self.assertEqual(summary["requested_count"], 3)
            self.assertEqual(summary["completed_count"], 1)
            self.assertEqual(summary["skipped_count"], 0)
            self.assertEqual(summary["failed_count"], 1)
            self.assertEqual(summary["resolved_count"], 2)
            self.assertEqual(summary["remaining_count"], 1)
            self.assertEqual(summary["checkpoint_count"], 2)
            self.assertEqual(
                [(asset["status"], asset["reason"], asset["path"]) for asset in summary["assets"]],
                [
                    ("completed", None, "src/a.py"),
                    ("halted", "sovereignty_breach", None),
                ],
            )

    def test_delivery_summary_delegates_next_action_to_iching_kernel(self):
        ledger = {
            "status": "halted",
            "requested_count": 3,
            "completed_count": 1,
            "skipped_count": 0,
            "failed_count": 1,
        }
        expected = {
            "delivery_status": "blocked",
            "next_action": "resume",
            "resolved_count": 2,
            "remaining_count": 1,
        }

        with patch("onecode.cli.IchingKernel.delivery_decision", return_value=expected) as delivery_decision:
            summary = delivery_summary(ledger)

        self.assertEqual(summary, expected)
        delivery_decision.assert_called_once_with(
            status="halted",
            requested_count=3,
            completed_count=1,
            skipped_count=0,
            failed_count=1,
        )

    def test_cli_inspect_missing_run_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "missing")
            self.assertEqual(error["run_id"], "missing-run")

    def test_cli_inspect_corrupt_run_returns_nonzero_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "corrupt-run"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text("{not json", encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "corrupt-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "corrupt-run")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_non_object_json_returns_corrupt_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "list-run"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text("[]", encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "list-run",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "list-run")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "non_object_json")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_non_list_checkpoints_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "bad-checkpoints"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": {"not": "a list"}}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "bad-checkpoints",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "bad-checkpoints")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoints")

    def test_cli_inspect_missing_checkpoints_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-checkpoints"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text('{"status": "completed"}', encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-checkpoints",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-checkpoints")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_checkpoints")

    def test_cli_inspect_missing_manifest_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-manifest-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text('{"checkpoints": []}', encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-manifest-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-manifest-status")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_missing_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-ledger-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"completed_count": 0}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-ledger-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-ledger-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_blank_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "blank-ledger-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": ""}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "blank-ledger-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "blank-ledger-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_unknown_manifest_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "unknown-manifest-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "teleported", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "unknown-manifest-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "unknown-manifest-status")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_status")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_mismatched_manifest_and_ledger_status_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "mismatched-status"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "halted"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "mismatched-status",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "mismatched-status")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "status_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_negative_ledger_count_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "negative-count"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                '{"status": "completed", "completed_count": -1}',
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "negative-count",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "negative-count")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_count")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_halted_run_requires_completed_trace_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            result = run_task(
                "too large",
                workspace=Path(tmp),
                run_id="missing-trace-completion",
                write_path="src/generated.py",
                write_content="x" * 33,
                max_write_bytes=32,
            )
            trace_path = Path(result["trace_path"])
            events = [
                line
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if '"event_type": "run_completed"' not in line
            ]
            trace_path.write_text("\n".join(events) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-trace-completion",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["corrupt_reason"], "missing_trace_run_completed")
            self.assertIn("trace.jsonl", error["corrupt_path"])

    def test_cli_inspect_rejects_tampered_evidence_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_task(
                "chain inspect",
                workspace=Path(tmp),
                run_id="tampered-chain",
                write_path="src/generated.py",
                write_content="value = 1\n",
            )
            chain_path = Path(tmp) / ".onecode" / "runs" / "tampered-chain" / "evidence-chain.jsonl"
            records = [
                json.loads(line)
                for line in chain_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            records[-1]["artifact_sha256"] = "0" * 64
            chain_path.write_text(
                "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "tampered-chain",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["corrupt_reason"], "evidence_chain_hash_mismatch")
            self.assertIn("evidence-chain.jsonl", error["corrupt_path"])

    def test_cli_inspect_impossible_ledger_count_total_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "impossible-count"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": []}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 1, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "impossible-count",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "impossible-count")
            self.assertIn("ledger.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "count_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_ledger_counts_must_match_checkpoint_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-count-mismatch"
            run_root.mkdir(parents=True)
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir()
            checkpoint_path.write_text('{"status": "completed"}', encoding="utf-8")
            checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "'
                    + str(checkpoint_path)
                    + '", "sha256": "'
                    + checkpoint_sha
                    + '"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 2, '
                    '"completed_count": 2, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "checkpoint-count-mismatch",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-count-mismatch")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "checkpoint_count_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_checkpoint_missing_evidence_fields_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-missing-evidence"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": [{"status": "completed"}]}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "checkpoint-missing-evidence",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-missing-evidence")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_evidence")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_malformed_checkpoint_sha256_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "malformed-checkpoint-sha"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "checkpoints/0001.json", "sha256": "abc"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "malformed-checkpoint-sha",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "malformed-checkpoint-sha")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_evidence")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_missing_checkpoint_file_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "missing-checkpoint-file"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "'
                    + str(run_root / "checkpoints" / "0001.json")
                    + '", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "missing-checkpoint-file",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "missing-checkpoint-file")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "missing_checkpoint_file")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_checkpoint_sha_mismatch_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-sha-mismatch"
            run_root.mkdir(parents=True)
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir()
            checkpoint_path.write_text('{"status": "completed"}', encoding="utf-8")
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "'
                    + str(checkpoint_path)
                    + '", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "checkpoint-sha-mismatch",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-sha-mismatch")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "checkpoint_sha_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_invalid_checkpoint_json_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "invalid-checkpoint-json"
            run_root.mkdir(parents=True)
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir()
            checkpoint_path.write_text("{not json", encoding="utf-8")
            checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "'
                    + str(checkpoint_path)
                    + '", "sha256": "'
                    + checkpoint_sha
                    + '"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "invalid-checkpoint-json",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "invalid-checkpoint-json")
            self.assertIn("0001.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_json")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_checkpoint_status_mismatch_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "checkpoint-status-mismatch"
            run_root.mkdir(parents=True)
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir()
            checkpoint_path.write_text('{"status": "halted"}', encoding="utf-8")
            checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
            (run_root / "manifest.json").write_text(
                (
                    '{"status": "completed", "checkpoints": ['
                    '{"status": "completed", "path": "'
                    + str(checkpoint_path)
                    + '", "sha256": "'
                    + checkpoint_sha
                    + '"}'
                    "]}"
                ),
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text(
                (
                    '{"status": "completed", "requested_count": 1, '
                    '"completed_count": 1, "skipped_count": 0, "failed_count": 0}'
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "checkpoint-status-mismatch",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "checkpoint-status-mismatch")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "checkpoint_record_mismatch")
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_inspect_non_object_checkpoint_entry_returns_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "bad-checkpoint-entry"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text(
                '{"status": "completed", "checkpoints": ["bad"]}',
                encoding="utf-8",
            )
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "inspect",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "bad-checkpoint-entry",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            error = json.loads(completed.stdout)
            self.assertEqual(error["status"], "corrupt")
            self.assertEqual(error["run_id"], "bad-checkpoint-entry")
            self.assertIn("manifest.json", error["corrupt_path"])
            self.assertEqual(error["corrupt_reason"], "invalid_checkpoint_entry")


if __name__ == "__main__":
    unittest.main()
