import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.runner import run_task


class RunnerTests(unittest.TestCase):
    def test_run_task_writes_manifest_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task("smoke", workspace=Path(tmp), run_id="runner-test")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["state"], "000000")
            self.assertFalse(result["partial"])
            manifest_path = Path(result["manifest_path"])
            ledger_path = Path(result["ledger_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(ledger_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["checkpoints"][0]["status"], "completed")

    def test_run_task_can_force_timeout_for_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "timeout",
                workspace=Path(tmp),
                http_timeout_seconds=0.01,
                run_id="timeout-test",
                simulated_action_seconds=0.05,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["state"], "000000")
            self.assertTrue(result["partial"])
            self.assertEqual(result["reason"], "http_timeout")
            self.assertTrue(Path(result["manifest_path"]).exists())
            self.assertTrue(Path(result["ledger_path"]).exists())

    def test_run_task_persists_run_metadata_in_single_ledger_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "metadata",
                workspace=Path(tmp),
                run_id="metadata-test",
                run_metadata={"plan_sha256": "abc123", "plan_asset_count": 2},
            )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["plan_sha256"], "abc123")
            self.assertEqual(result["plan_asset_count"], 2)
            self.assertEqual(ledger["plan_sha256"], "abc123")
            self.assertEqual(ledger["plan_asset_count"], 2)

    def test_run_task_metadata_cannot_override_rule_driven_result_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "metadata guarded",
                workspace=Path(tmp),
                run_id="metadata-guarded-test",
                run_metadata={
                    "status": "halted",
                    "reason": "external_override",
                    "iching_status_code": 0,
                    "plan_sha256": "abc123",
                },
            )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "completed")
            self.assertIsNone(result["reason"])
            self.assertNotEqual(result["iching_status_code"], 0)
            self.assertEqual(result["plan_sha256"], "abc123")
            self.assertEqual(ledger["status"], "completed")
            self.assertIsNone(ledger["reason"])
            self.assertNotEqual(ledger["iching_status_code"], 0)


class CliTests(unittest.TestCase):
    def test_cli_run_prints_json_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "smoke",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-test",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["run_id"], "cli-test")
            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["partial"])
            self.assertTrue(Path(result["manifest_path"]).exists())


class RunnerSovereigntyTests(unittest.TestCase):
    def test_run_task_write_text_creates_file_and_records_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = os.getcwd()
            os.chdir(tmp)
            self.addCleanup(os.chdir, original_cwd)
            workspace = Path("relative-workspace")
            result = run_task(
                "write",
                workspace=workspace,
                run_id="write-test",
                write_path="src/generated.py",
                write_content="print('ok')\n",
            )

            target = (workspace / "src" / "generated.py").resolve()
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["decision"], "allowed")
            self.assertTrue(target.exists())
            self.assertEqual(result["sha256"], result["payload"]["sha256"])
            self.assertEqual(result["payload"]["path"], str(target))

    def test_run_task_halts_illegal_write_without_creating_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp).parent / "outside.txt"
            if outside.exists():
                outside.unlink()

            result = run_task(
                "bad write",
                workspace=Path(tmp),
                run_id="bad-write-test",
                write_path="../outside.txt",
                write_content="blocked",
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["decision"], "halted")
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertFalse(outside.exists())

    def test_run_task_denies_bash_execution_without_running_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "deny bash",
                workspace=Path(tmp),
                run_id="deny-bash-test",
                intent_type="bash_execution",
                command="echo no",
            )

            self.assertEqual(result["status"], "denied")
            self.assertEqual(result["decision"], "denied")
            self.assertEqual(result["reason"], "permission_denied")

    def test_run_task_unknown_intent_records_discovery_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "unknown intent",
                workspace=Path(tmp),
                run_id="unknown-intent-test",
                intent_type="teleport_asset",
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["decision"], "halted")
            self.assertEqual(result["reason"], "invalid_intent")
            self.assertEqual(result["iching_transition_action"], "discover")
            self.assertEqual(result["iching_transition_reason"], "rule_gap_requires_mapping")

    def test_run_task_incomplete_write_request_records_discovery_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "incomplete write",
                workspace=Path(tmp),
                run_id="incomplete-write-test",
                write_path="src/missing_content.py",
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["decision"], "halted")
            self.assertEqual(result["reason"], "invalid_intent")
            self.assertEqual(result["iching_transition_action"], "discover")
            self.assertEqual(result["iching_transition_reason"], "rule_gap_requires_mapping")
            self.assertFalse((Path(tmp) / "src" / "missing_content.py").exists())


class CliSovereigntyTests(unittest.TestCase):
    def test_cli_write_text_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "write",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-write",
                    "--write-path",
                    "src/cli_asset.py",
                    "--write-content",
                    "x = 1\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["decision"], "allowed")
            self.assertTrue((Path(tmp) / "src" / "cli_asset.py").exists())

    def test_cli_illegal_write_halts(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "bad write",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-bad-write",
                    "--write-path",
                    "../outside.txt",
                    "--write-content",
                    "blocked",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertNotEqual(completed.returncode, 0)


class CliResumeFlagTests(unittest.TestCase):
    def test_cli_accepts_repeated_write_text_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "multi write",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-multi",
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

            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 2)
            self.assertEqual(result["completed_count"], 2)
            self.assertEqual(len(result["assets"]), 2)
            self.assertEqual((Path(tmp) / "src" / "a.py").read_text(encoding="utf-8"), "a = 1\n")
            self.assertEqual(
                (Path(tmp) / "tests" / "test_a.py").read_text(encoding="utf-8"),
                "def test_a():\n    assert True\n",
            )

    def test_cli_rejects_mixed_write_interfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "bad args",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-conflict",
                    "--write-path",
                    "src/a.py",
                    "--write-content",
                    "a = 1\n",
                    "--write-text",
                    "src/b.py=b = 1\n",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("cannot combine --write-text with --write-path or --write-content", completed.stderr)

    def test_cli_rejects_invalid_write_text_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "bad write text",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-bad-write-text",
                    "--write-text",
                    "missing-equals",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--write-text must use PATH=CONTENT with a non-empty path", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_cli_accepts_resume_from_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "resume smoke",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "resume-cli",
                    "--resume-from",
                    "previous-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["run_id"], "resume-cli")
            self.assertEqual(result["resumed_from"], "previous-run")

    def test_cli_resume_skips_ready_asset_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            first = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "write ready",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "source-run",
                    "--write-path",
                    "src/mesh.py",
                    "--write-content",
                    "mesh = 'ready'\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            first_result = json.loads(first.stdout)
            first_sha = first_result["sha256"]

            second = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "resume ready",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "retry-run",
                    "--resume-from",
                    "source-run",
                    "--write-path",
                    "src/mesh.py",
                    "--write-content",
                    "mesh = 'rewritten'\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(second.stdout)
            target = Path(tmp) / "src" / "mesh.py"
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "resumed_asset_ready")
            self.assertTrue(result["resumed"])
            self.assertEqual(result["sha256"], first_sha)
            self.assertEqual(target.read_text(encoding="utf-8"), "mesh = 'ready'\n")

    def test_cli_resume_writes_missing_asset_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "write ready",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "source-run",
                    "--write-path",
                    "src/mesh.py",
                    "--write-content",
                    "mesh = 'ready'\n",
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
                    "run",
                    "resume missing",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "retry-run",
                    "--resume-from",
                    "source-run",
                    "--write-path",
                    "tests/test_mesh.py",
                    "--write-content",
                    "def test_mesh():\n    assert True\n",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            target = Path(tmp) / "tests" / "test_mesh.py"
            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["resumed"])
            self.assertEqual(result["resumed_from"], "source-run")
            self.assertEqual(target.read_text(encoding="utf-8"), "def test_mesh():\n    assert True\n")


class RunnerMultiAssetTests(unittest.TestCase):
    def test_run_task_rejects_invalid_write_text_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "--write-text must use PATH=CONTENT"):
                run_task(
                    "invalid write text",
                    workspace=Path(tmp),
                    run_id="invalid-write-text",
                    write_texts=["missing-equals"],
                )

    def test_run_task_writes_multiple_assets_and_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "multi write",
                workspace=workspace,
                run_id="multi-write",
                write_texts=[
                    "src/a.py=a = 1\n",
                    "tests/test_a.py=def test_a():\n    assert True\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 2)
            self.assertEqual(result["completed_count"], 2)
            self.assertEqual(result["skipped_count"], 0)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(len(result["assets"]), 2)
            self.assertEqual([asset["index"] for asset in result["assets"]], [1, 2])
            self.assertEqual(result["assets"][0]["payload"]["path"], "src/a.py")
            self.assertEqual(result["assets"][1]["payload"]["path"], "tests/test_a.py")
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertEqual((workspace / "src" / "a.py").read_text(encoding="utf-8"), "a = 1\n")
            self.assertEqual(
                (workspace / "tests" / "test_a.py").read_text(encoding="utf-8"),
                "def test_a():\n    assert True\n",
            )

    def test_run_task_reports_completed_when_multi_asset_run_ends_with_skipped_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "write ready",
                workspace=workspace,
                run_id="source-run",
                write_path="src/ready.py",
                write_content="ready = True\n",
            )

            result = run_task(
                "resume mixed",
                workspace=workspace,
                run_id="mixed-run",
                resume_from_run_id="source-run",
                write_texts=[
                    "src/new.py=new = True\n",
                    "src/ready.py=should_not_overwrite\n",
                ],
            )

            self.assertEqual(result["status"], "completed")
            self.assertIsNone(result["reason"])
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["skipped_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(result["assets"][0]["status"], "completed")
            self.assertEqual(result["assets"][1]["status"], "skipped")
            self.assertEqual(result["assets"][1]["reason"], "resumed_asset_ready")
            self.assertEqual((workspace / "src" / "ready.py").read_text(encoding="utf-8"), "ready = True\n")
            self.assertEqual((workspace / "src" / "new.py").read_text(encoding="utf-8"), "new = True\n")

    def test_run_task_skips_ready_asset_and_writes_missing_asset_in_one_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first = run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/mesh.py",
                write_content="mesh = 'ready'\n",
            )

            result = run_task(
                "resume multi",
                workspace=workspace,
                run_id="retry-run",
                resume_from_run_id="source-run",
                write_texts=[
                    "src/mesh.py=mesh = 'rewritten'\n",
                    "tests/test_mesh.py=def test_mesh():\n    assert True\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["requested_count"], 2)
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["skipped_count"], 1)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(result["assets"][0]["status"], "skipped")
            self.assertEqual(result["assets"][0]["sha256"], first["sha256"])
            self.assertEqual(result["assets"][1]["status"], "completed")
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "mesh = 'ready'\n")
            self.assertEqual(
                (workspace / "tests" / "test_mesh.py").read_text(encoding="utf-8"),
                "def test_mesh():\n    assert True\n",
            )

    def test_run_task_uses_iching_kernel_for_resume_skip_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/mesh.py",
                write_content="mesh = 'ready'\n",
            )

            with patch("onecode.kernel.runner.IchingKernel.should_skip", return_value=False):
                result = run_task(
                    "resume through iching",
                    workspace=workspace,
                    run_id="retry-run",
                    resume_from_run_id="source-run",
                    write_path="src/mesh.py",
                    write_content="mesh = 'rewritten'\n",
                )

            self.assertEqual(result["status"], "completed")
            self.assertFalse(result["resumed"])
            self.assertEqual((workspace / "src" / "mesh.py").read_text(encoding="utf-8"), "mesh = 'rewritten'\n")

    def test_run_task_halts_on_middle_asset_and_does_not_write_later_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "fail fast",
                workspace=workspace,
                run_id="fail-fast",
                write_texts=[
                    "src/ok.py=ok = True\n",
                    "../outside.py=blocked\n",
                    "src/after.py=after = True\n",
                ],
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "halted")
            self.assertTrue(result["partial"])
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertEqual(result["requested_count"], 3)
            self.assertEqual(result["completed_count"], 1)
            self.assertEqual(result["skipped_count"], 0)
            self.assertEqual(result["failed_count"], 1)
            self.assertEqual(len(result["assets"]), 2)
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertTrue((workspace / "src" / "ok.py").exists())
            self.assertFalse((workspace / "src" / "after.py").exists())
            self.assertFalse((workspace.parent / "outside.py").exists())

    def test_run_task_uses_iching_dispatch_decision_for_multi_asset_loop_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            def dispatch_decision(transition):
                if transition.action == "halt":
                    return "continue"
                return "continue"

            with patch("onecode.kernel.runner.IchingKernel.dispatch_decision", side_effect=dispatch_decision):
                result = run_task(
                    "kernel dispatch",
                    workspace=workspace,
                    run_id="kernel-dispatch",
                    write_texts=[
                        "src/ok.py=ok = True\n",
                        "../outside.py=blocked\n",
                        "src/after.py=after = True\n",
                    ],
                )

            self.assertEqual(result["requested_count"], 3)
            self.assertEqual(len(result["assets"]), 3)
            self.assertTrue((workspace / "src" / "ok.py").exists())
            self.assertTrue((workspace / "src" / "after.py").exists())
            self.assertFalse((workspace.parent / "outside.py").exists())


if __name__ == "__main__":
    unittest.main()
