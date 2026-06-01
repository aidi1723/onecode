import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.hexagram import IchingKernel
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
            self.assertIn("duration_ms", result["assets"][0])
            self.assertEqual(result["assets"][0]["duration_ms"], manifest["checkpoints"][0]["duration_ms"])

    def test_run_task_writes_trace_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "trace smoke",
                workspace=Path(tmp),
                run_id="trace-runner-test",
                write_path="src/generated.py",
                write_content="value = 1\n",
            )

            trace_path = Path(result["trace_path"])
            events = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
            ]

            self.assertTrue(trace_path.exists())
            self.assertEqual(result["trace_id"], "trace-runner-test")
            self.assertEqual(events[0]["event_type"], "run_started")
            self.assertIn("tool_call_started", [event["event_type"] for event in events])
            self.assertIn("tool_call_completed", [event["event_type"] for event in events])
            self.assertIn("checkpoint_written", [event["event_type"] for event in events])
            self.assertEqual(events[-1]["event_type"], "run_completed")
            self.assertTrue(all(event["run_id"] == "trace-runner-test" for event in events))

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
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            self.assertGreaterEqual(manifest["checkpoints"][0]["duration_ms"], 10)
            self.assertEqual(result["assets"][0]["duration_ms"], manifest["checkpoints"][0]["duration_ms"])

    def test_run_task_records_action_exception_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("onecode.kernel.runner.PathGuard.write_text", side_effect=OSError("disk write failed")):
                result = run_task(
                    "write fails",
                    workspace=Path(tmp),
                    run_id="action-exception-test",
                    write_path="src/generated.py",
                    write_content="value = 1\n",
                )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "action_exception")
            self.assertEqual(result["payload"]["error_type"], "OSError")
            self.assertEqual(result["payload"]["error_message_tail"], "disk write failed")
            self.assertEqual(result["iching_status_code"], IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KUN))
            self.assertEqual(result["iching_transition_action"], "checkpoint")
            self.assertEqual(result["iching_transition_reason"], "mountain_contains_local_executor_fault")
            self.assertEqual(ledger["reason"], "action_exception")
            self.assertEqual(manifest["checkpoints"][0]["reason"], "action_exception")

    def test_run_task_records_run_exception_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("onecode.kernel.runner.write_checkpoint", side_effect=OSError("manifest write failed")):
                result = run_task(
                    "checkpoint fails",
                    workspace=Path(tmp),
                    run_id="run-exception-test",
                    write_path="src/generated.py",
                    write_content="value = 1\n",
                )

            ledger = json.loads(Path(result["ledger_path"]).read_text(encoding="utf-8"))
            trace_events = [
                json.loads(line)
                for line in Path(result["trace_path"]).read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "run_exception")
            self.assertEqual(result["payload"]["error_type"], "OSError")
            self.assertEqual(result["payload"]["error_message_tail"], "manifest write failed")
            self.assertEqual(result["iching_status_code"], IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KUN))
            self.assertEqual(ledger["reason"], "run_exception")
            self.assertEqual(trace_events[-1]["event_type"], "run_completed")
            self.assertEqual(trace_events[-1]["status"], "halted")
            self.assertEqual(trace_events[-1]["payload"]["reason"], "run_exception")

    def test_run_task_rejects_oversized_write_content_as_resource_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "too large",
                workspace=Path(tmp),
                run_id="resource-budget-test",
                write_path="src/generated.py",
                write_content="x" * 33,
                max_write_bytes=32,
            )

            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            trace_events = [
                json.loads(line)
                for line in Path(result["trace_path"]).read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["payload"]["budget"], "max_write_bytes")
            self.assertEqual(manifest["status"], "halted")
            self.assertEqual(manifest["checkpoints"][0]["reason"], "resource_budget_exceeded")
            self.assertEqual(manifest["checkpoints"][0]["intent_type"], "resource_budget")
            self.assertEqual(trace_events[-1]["event_type"], "run_completed")
            self.assertEqual(trace_events[-1]["status"], "halted")
            self.assertFalse((Path(tmp) / "src" / "generated.py").exists())

    def test_run_task_rejects_non_positive_resource_budget_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "max_actions must be positive"):
                run_task(
                    "invalid budget",
                    workspace=Path(tmp),
                    run_id="invalid-budget-test",
                    max_actions=0,
                )

    def test_run_task_halts_when_trace_budget_is_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "trace budget",
                workspace=Path(tmp),
                run_id="trace-budget-test",
                write_path="src/generated.py",
                write_content="value = 1\n",
                max_trace_bytes=1,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["payload"]["budget"], "max_trace_bytes")
            self.assertTrue(Path(result["ledger_path"]).exists())
            self.assertTrue(Path(result["trace_path"]).exists())

    def test_run_task_halts_when_run_deadline_is_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_task(
                "deadline budget",
                workspace=Path(tmp),
                run_id="deadline-budget-test",
                write_path="src/generated.py",
                write_content="value = 1\n",
                simulated_action_seconds=0.02,
                max_run_seconds=0.001,
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["payload"]["budget"], "max_run_seconds")
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
    def test_cli_shell_schema_prints_projection_contract(self):
        completed = subprocess.run(
            [sys.executable, "-m", "onecode", "shell-schema"],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["name"], "onecode.shell_projection")
        self.assertEqual(payload["version"], 1)
        self.assertIn("rule_state", payload["fields"])
        self.assertEqual(payload["nested_fields"]["rule_state"][0], "status_code")

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
            self.assertEqual(result["evidence_mode"], "wal")
            self.assertIsNone(result["manifest_path"])
            self.assertIsNone(result["ledger_path"])
            self.assertIsNone(result["trace_path"])
            self.assertEqual(result["wal_path"], str((Path(tmp) / ".onecode" / "global-ledger.jsonl").resolve()))
            self.assertTrue(Path(result["wal_path"]).exists())
            self.assertEqual(result["shell_projection"]["run_id"], "cli-test")
            self.assertEqual(result["shell_projection"]["severity"], "ok")
            self.assertEqual(result["shell_projection"]["evidence_ref"]["mode"], "wal")
            self.assertEqual(
                result["shell_projection"]["rule_state"]["status_code"],
                result["iching_status_code"],
            )

    def test_cli_run_can_force_full_strict_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "strict evidence",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-strict",
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

            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "full")
            self.assertTrue(Path(result["manifest_path"]).exists())
            self.assertTrue(Path(result["ledger_path"]).exists())

    def test_cli_run_uses_strict_evidence_profile_from_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            env["ONECODE_EVIDENCE_PROFILE"] = "strict"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "env strict",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-env-strict",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "full")
            self.assertTrue(Path(result["manifest_path"]).exists())
            self.assertTrue(Path(result["ledger_path"]).exists())

    def test_cli_run_rejects_invalid_evidence_profile_without_creating_evidence_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            env["ONECODE_EVIDENCE_PROFILE"] = "heavy"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "bad env profile",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-bad-profile",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("ONECODE_EVIDENCE_PROFILE", completed.stderr)
            self.assertFalse((Path(tmp) / ".onecode").exists())

    def test_cli_run_rejects_invalid_wal_rotate_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            env["ONECODE_WAL_ROTATE_BYTES"] = "bad"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "bad wal rotate",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-bad-wal-rotate",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("ONECODE_WAL_ROTATE_BYTES", completed.stderr)
            self.assertFalse((Path(tmp) / ".onecode" / "global-ledger.jsonl").exists())

    def test_cli_run_accepts_resource_budget_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "too large",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-resource-budget",
                    "--write-path",
                    "src/generated.py",
                    "--write-content",
                    "xxxxxxxxx",
                    "--max-write-bytes",
                    "8",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            result = json.loads(completed.stdout)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["payload"]["budget"], "max_write_bytes")

    def test_cli_run_accepts_wal_relaxed_evidence_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "wal relaxed cli",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-wal-relaxed",
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

            result = json.loads(completed.stdout)
            wal_path = Path(tmp) / ".onecode" / "global-ledger.jsonl"

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["evidence_mode"], "wal")
            self.assertIsNone(result["ledger_path"])
            self.assertIsNone(result["manifest_path"])
            self.assertEqual(result["wal_path"], str(wal_path.resolve()))
            self.assertTrue(wal_path.exists())

    def test_cli_run_rejects_non_positive_resource_budget_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "invalid budget",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-invalid-budget",
                    "--max-actions",
                    "0",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("argument --max-actions: must be a positive integer", completed.stderr)

    def test_cli_run_accepts_run_level_budget_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "trace budget",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "cli-run-level-budget",
                    "--write-path",
                    "src/generated.py",
                    "--write-content",
                    "value = 1\n",
                    "--completed-evidence-mode",
                    "full",
                    "--evidence-durability",
                    "strict",
                    "--max-trace-bytes",
                    "1",
                    "--max-run-seconds",
                    "10",
                ],
                env=env,
                text=True,
                capture_output=True,
            )

            result = json.loads(completed.stdout)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "resource_budget_exceeded")
            self.assertEqual(result["payload"]["budget"], "max_trace_bytes")


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

    def test_run_task_unknown_intent_records_invalid_intent_halt(self):
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
            self.assertEqual(result["iching_transition_action"], "halt")
            self.assertEqual(result["iching_transition_reason"], "sovereignty_fire_boundary_halt")

    def test_run_task_incomplete_write_request_records_invalid_intent_halt(self):
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
            self.assertEqual(result["iching_transition_action"], "halt")
            self.assertEqual(result["iching_transition_reason"], "sovereignty_fire_boundary_halt")
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

    def test_cli_run_exit_code_delegates_to_iching_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
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
                exit_code = main(["run", "delegated", "--workspace", tmp])

        self.assertEqual(exit_code, 0)
        process_exit_code.assert_called_once_with(status="halted", reason="sovereignty_breach")


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

    def test_cli_resume_skips_ready_asset_from_default_wal_only_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            first = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "write wal ready",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "source-wal-run",
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
            second = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "onecode.cli",
                    "run",
                    "resume wal ready",
                    "--workspace",
                    tmp,
                    "--run-id",
                    "retry-wal-run",
                    "--resume-from",
                    "source-wal-run",
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
            self.assertEqual(first_result["evidence_mode"], "wal")
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "resumed_asset_ready")
            self.assertTrue(result["resumed"])
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
            self.assertEqual(result["assets"][0]["balanced_status_code"], 0b011111)
            self.assertEqual(result["assets"][0]["balance_mask"], 0b100000)
            self.assertEqual(result["assets"][0]["balance_action"], "cooldown")
            self.assertEqual(result["assets"][0]["four_symbol_decision"], "overflow")
            self.assertEqual(result["assets"][0]["four_symbol_change_mask"], 0b100000)
            self.assertEqual(result["assets"][1]["balanced_status_code"], 0b011111)
            self.assertEqual(result["global_entropy_decision"], "accept_positive_polarity")
            self.assertIsNone(result["global_entropy_reason"])
            self.assertEqual(result["global_status_code"], IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN))
            self.assertEqual(result["global_transition_action"], "cooldown")
            self.assertIn("global_entropy", result)
            self.assertEqual(result["ledger_path"], str(Path(result["ledger_path"])))
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertEqual(manifest["global_entropy_decision"], result["global_entropy_decision"])
            self.assertEqual(manifest["global_status_code"], result["global_status_code"])
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

    def test_run_task_skips_ready_patch_without_reapplying(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir(parents=True)
            target.write_text("def status():\n    return False\n", encoding="utf-8")

            source = run_task(
                "source patch",
                workspace=workspace,
                run_id="source-patch-run",
                patch_path="src/mesh.py",
                search_block="return False",
                replace_block="return True",
            )

            result = run_task(
                "resume patch",
                workspace=workspace,
                run_id="resume-patch-run",
                resume_from_run_id="source-patch-run",
                patch_path="src/mesh.py",
                search_block="return False",
                replace_block="return True",
            )

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "resumed_asset_ready")
            self.assertEqual(result["intent_type"], "patch_text")
            self.assertEqual(result["sha256"], source["sha256"])
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return True\n")

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
