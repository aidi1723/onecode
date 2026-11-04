import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.verifier import (
    VERIFIER_POLICY_PRESETS,
    VerifierSpec,
    VerifierResult,
    load_verifier_policy,
    run_verifier,
    task_status_from_results,
)


class VerifierPolicyTests(unittest.TestCase):
    def test_guarded_unittest_undoes_an_import_time_assert_patch(self):
        from onecode.kernel.verifier import guarded_unittest_command

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "fee.py").write_text(
                "import unittest\nunittest.TestCase.assertEqual = lambda self, a, b, msg=None: None\n"
                "def fee(value):\n    return 0\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_fee.py").write_text(
                "import unittest\nfrom src.fee import fee\n"
                "class T(unittest.TestCase):\n"
                "    def test_fee(self):\n"
                "        self.assertEqual(fee(1), 1)\n",
                encoding="utf-8",
            )
            command = guarded_unittest_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("FAILED", completed.stdout + completed.stderr)
    def test_load_verifier_policy_accepts_allowlisted_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": ["python3", "-m", "unittest", "discover", "-s", "tests"],
                                "cwd": ".",
                                "timeout_ms": 1000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            policy = load_verifier_policy(path)

            spec = policy.require("python-unittest")
            self.assertEqual(spec.id, "python-unittest")
            self.assertEqual(spec.command, ["python3", "-m", "unittest", "discover", "-s", "tests"])
            self.assertEqual(spec.cwd, ".")
            self.assertEqual(spec.timeout_ms, 1000)

    def test_load_verifier_policy_rejects_non_preset_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "custom-shell",
                                "command": ["python3", "-c", "print('arbitrary')"],
                                "cwd": ".",
                                "timeout_ms": 1000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "verifier command is not allowed"):
                load_verifier_policy(path)

    def test_load_verifier_policy_rejects_python_path_impersonation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": ["tools/python", "-m", "unittest", "discover", "-s", "tests"],
                                "cwd": ".",
                                "timeout_ms": 1000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "verifier command is not allowed"):
                load_verifier_policy(path)

    def test_load_verifier_policy_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {"id": "unit", "command": VERIFIER_POLICY_PRESETS["python-unittest"]["command"], "cwd": ".", "timeout_ms": 1000},
                            {"id": "unit", "command": VERIFIER_POLICY_PRESETS["python-unittest"]["command"], "cwd": ".", "timeout_ms": 1000},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate verifier id"):
                load_verifier_policy(path)

    def test_load_verifier_policy_rejects_boolean_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": VERIFIER_POLICY_PRESETS["python-unittest"]["command"],
                                "cwd": ".",
                                "timeout_ms": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "verifier timeout_ms must be positive"):
                load_verifier_policy(path)

    def test_policy_require_rejects_unknown_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {"id": "unit", "command": VERIFIER_POLICY_PRESETS["python-unittest"]["command"], "cwd": ".", "timeout_ms": 1000}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            policy = load_verifier_policy(path)

            with self.assertRaisesRegex(ValueError, "unknown verifier id"):
                policy.require("missing")


class VerifierExecutionTests(unittest.TestCase):
    def test_task_status_ignores_boolean_asset_status_codes(self):
        without_status = task_status_from_results({"assets": []}, [])
        with_boolean_status = task_status_from_results({"assets": [{"raw_status_code": True}]}, [])

        self.assertEqual(with_boolean_status["task_status_code"], without_status["task_status_code"])
        self.assertEqual(with_boolean_status["task_transition_action"], without_status["task_transition_action"])

    def test_run_verifier_without_sandbox_halts_and_does_not_call_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="ok",
                command=["python3", "-c", "print('ok')"],
                cwd=".",
                timeout_ms=5000,
            )

            with patch("onecode.kernel.verifier.subprocess.run") as mock_run:
                result = run_verifier(workspace, spec)
                
            self.assertEqual(mock_run.call_count, 0)
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "sandbox_required")
            self.assertEqual(result.failure_kind, "exception")
            self.assertIn("Sandbox configuration is required", result.stderr_tail)

    def test_host_python_is_rewritten_and_a_missing_image_python_checkpoints(self):
        from subprocess import CompletedProcess

        from onecode.kernel.hexagram import IchingKernel
        from onecode.kernel.sandbox import SandboxConfig

        seen: list[list[str]] = []

        def fake_run(config, command):
            seen.append(list(command))
            return CompletedProcess(
                args=command,
                returncode=127,
                stdout="",
                stderr='exec: "python3": executable file not found in $PATH',
            )

        with tempfile.TemporaryDirectory() as tmp:
            spec = VerifierSpec(
                id="python-unittest",
                command=[sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=".",
                timeout_ms=5000,
            )
            with patch("onecode.kernel.verifier.image_platform_mismatch", return_value=False), patch(
                "onecode.kernel.verifier.run_in_sandbox", side_effect=fake_run
            ):
                result = run_verifier(
                    Path(tmp),
                    spec,
                    sandbox_config=SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
                )

        self.assertEqual(seen[0][0], "python3")
        self.assertEqual(result.reason, "interpreter_not_found")
        transition = IchingKernel.transition(IchingKernel.classify_outcome("halted", result.reason))
        self.assertEqual(transition.action, "checkpoint")
        self.assertEqual(transition.status_code, IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KUN))

    def test_verifier_fails_when_unittest_exits_zero_without_running_tests_or_aborted(self):
        from subprocess import CompletedProcess
        from onecode.kernel.sandbox import SandboxConfig

        with tempfile.TemporaryDirectory() as tmp:
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "unittest", "discover", "-s", "tests"],
                cwd=".",
                timeout_ms=5000,
            )
            fake_aborted = CompletedProcess(args=spec.command, returncode=0, stdout="", stderr="")
            with patch("onecode.kernel.verifier.image_platform_mismatch", return_value=False), patch(
                "onecode.kernel.verifier.run_in_sandbox", return_value=fake_aborted
            ):
                result = run_verifier(
                    Path(tmp),
                    spec,
                    sandbox_config=SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
                )
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "verifier_empty_or_aborted")

            fake_empty = CompletedProcess(
                args=spec.command,
                returncode=0,
                stdout="Ran 0 tests in 0.000s\n\nNO TESTS RAN\n",
                stderr="",
            )
            with patch("onecode.kernel.verifier.image_platform_mismatch", return_value=False), patch(
                "onecode.kernel.verifier.run_in_sandbox", return_value=fake_empty
            ):
                empty = run_verifier(
                    Path(tmp),
                    spec,
                    sandbox_config=SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
                )
            self.assertEqual(empty.status, "skipped")
            self.assertEqual(empty.reason, "no_unittest_collected")

    def test_foreign_image_checkpoints_before_the_container_starts(self):
        from onecode.kernel.hexagram import IchingKernel
        from onecode.kernel.sandbox import SandboxConfig

        with tempfile.TemporaryDirectory() as tmp:
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "unittest", "discover", "-s", "tests"],
                cwd=".",
                timeout_ms=5000,
            )
            with patch("onecode.kernel.verifier.image_platform_mismatch", return_value=True), patch(
                "onecode.kernel.verifier.run_in_sandbox"
            ) as sandbox:
                result = run_verifier(
                    Path(tmp),
                    spec,
                    sandbox_config=SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
                )

        sandbox.assert_not_called()
        self.assertEqual(result.reason, "image_platform_mismatch")
        transition = IchingKernel.transition(IchingKernel.classify_outcome("halted", result.reason))
        self.assertEqual(transition.action, "checkpoint")
        self.assertEqual(transition.status_code, IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))

    def test_verifier_uses_a_local_native_image_when_the_tag_cannot_run(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig

        seen: list[str] = []

        def arch(image: str) -> str | None:
            if image == "python:3.12-slim":
                return "arm64"
            if image == "python:3.12-slim-amd64":
                return "amd64"
            return None

        def fake_run(config, command):
            seen.append(config.image)
            return CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox._image_architecture", side_effect=arch
        ), patch("onecode.kernel.sandbox.platform.machine", return_value="x86_64"), patch(
            "onecode.kernel.verifier.run_in_sandbox", side_effect=fake_run
        ):
            result = run_verifier(
                Path(tmp),
                VerifierSpec(id="python-unittest", command=["python3", "-c", "print(1)"], cwd=".", timeout_ms=5000),
                sandbox_config=SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
            )

        self.assertEqual(result.status, "passed")
        self.assertEqual(seen, ["python:3.12-slim-amd64"])

    def test_colima_socket_miss_is_a_local_executor_checkpoint(self):
        from onecode.kernel.hexagram import IchingKernel
        from onecode.kernel.run_inspection import apply_verifier_evidence
        from onecode.kernel.sandbox import SandboxConfig

        message = (
            "failed to connect to the docker API at unix:///Users/aidi/.colima/default/docker.sock; "
            "check if the path is correct and if the daemon is running: "
            "dial unix /Users/aidi/.colima/default/docker.sock: connect: no such file or directory"
        )

        def docker_down(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0] if args else kwargs.get("args", []),
                returncode=1,
                stdout="",
                stderr=message,
            )

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "unittest", "discover", "-s", "tests"],
                cwd=".",
                timeout_ms=5000,
            )
            with patch("onecode.kernel.sandbox.subprocess.run", side_effect=docker_down):
                verifier = run_verifier(
                    workspace,
                    spec,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim", network="none"),
                )
            enhanced = apply_verifier_evidence(
                {
                    "run_id": "colima-miss",
                    "status": "completed",
                    "reason": None,
                    "partial": False,
                    "requested_count": 1,
                    "completed_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "assets": [],
                    "iching_status_code": 39,
                    "iching_transition_action": "cooldown",
                },
                workspace,
                [verifier],
            )

        transition = IchingKernel.transition(IchingKernel.classify_outcome("halted", "sandbox_required"))
        self.assertEqual(verifier.reason, "sandbox_required")
        self.assertEqual(enhanced["status"], "halted")
        self.assertEqual(enhanced["iching_status_code"], transition.status_code)
        self.assertEqual(enhanced["iching_transition_action"], "checkpoint")
        self.assertEqual(enhanced["task_dispatch_decision"], "stop")

    def test_run_verifier_does_not_inherit_secret_environment(self):
        from onecode.kernel.sandbox import SandboxConfig
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-secret-value"},
            clear=False,
        ):
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="env",
                command=["python3", "-c", "import os; print(os.environ.get('OPENAI_API_KEY', ''))"],
                cwd=".",
                timeout_ms=5000,
            )

            with patch("onecode.kernel.sandbox.subprocess.run") as run_mock:
                run_mock.return_value.stdout = b""
                run_mock.return_value.stderr = b""
                run_mock.return_value.returncode = 0
                result = run_verifier(workspace, spec, sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim"))

        self.assertEqual(result.status, "passed")
        self.assertNotIn("sk-secret-value", result.stdout_tail)

    def test_run_verifier_records_failure_evidence(self):
        from onecode.kernel.sandbox import SandboxConfig
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="fail",
                command=["python3", "-c", "import sys; print('bad'); sys.exit(7)"],
                cwd=".",
                timeout_ms=5000,
            )

            with patch("onecode.kernel.sandbox.subprocess.run") as run_mock:
                run_mock.return_value.stdout = b"bad\n"
                run_mock.return_value.stderr = b""
                run_mock.return_value.returncode = 7
                result = run_verifier(workspace, spec, sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim"))

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "verifier_failed")
            self.assertEqual(result.exit_code, 7)
            self.assertIn("bad", result.stdout_tail)

    def test_run_verifier_records_timeout(self):
        from onecode.kernel.sandbox import SandboxConfig
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="slow",
                command=["python3", "-c", "import time; time.sleep(1)"],
                cwd=".",
                timeout_ms=10,
            )

            with patch("onecode.kernel.sandbox.subprocess.run") as run_mock:
                run_mock.side_effect = subprocess.TimeoutExpired(cmd=["docker"], timeout=10)
                result = run_verifier(workspace, spec, sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim"))

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "verifier_timeout")
            self.assertEqual(result.failure_kind, "timeout")
            self.assertIsNone(result.exit_code)

    def test_run_verifier_rejects_cwd_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            spec = VerifierSpec(id="outside", command=["python3", "-V"], cwd="..", timeout_ms=1000)

            with self.assertRaisesRegex(ValueError, "verifier cwd outside workspace"):
                run_verifier(workspace, spec)

    def test_run_verifier_writes_trace_events(self):
        from onecode.kernel.sandbox import SandboxConfig
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            trace_path = workspace / ".onecode" / "runs" / "verifier-run" / "trace.jsonl"
            spec = VerifierSpec(
                id="ok",
                command=["python3", "-c", "print('ok')"],
                cwd=".",
                timeout_ms=5000,
            )

            with patch("onecode.kernel.sandbox.subprocess.run") as run_mock:
                run_mock.return_value.stdout = b"ok\n"
                run_mock.return_value.stderr = b""
                run_mock.return_value.returncode = 0
                result = run_verifier(
                    workspace,
                    spec,
                    trace_path=trace_path,
                    trace_id="verifier-run",
                    run_id="verifier-run",
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim")
                )
            events = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(result.status, "passed")
            self.assertEqual(
                [event["event_type"] for event in events],
                ["verifier_started", "verifier_completed"],
            )
            self.assertEqual(events[0]["payload"]["verifier_id"], "ok")
            self.assertEqual(events[1]["status"], "passed")
            self.assertIsNone(events[1]["payload"]["failure_kind"])

    def test_run_verifier_can_use_sandbox_config(self):
        from onecode.kernel.sandbox import SandboxConfig

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="ok",
                command=["python3", "-V"],
                cwd=".",
                timeout_ms=5000,
            )

            with patch("onecode.kernel.sandbox.subprocess.run") as run_mock:
                run_mock.return_value.stdout = "Python 3\n"
                run_mock.return_value.stderr = ""
                run_mock.return_value.returncode = 0
                result = run_verifier(
                    workspace,
                    spec,
                    sandbox_config=SandboxConfig(workspace=workspace, image="python:3.12-slim"),
                )

            called_command = run_mock.call_args.args[0]
            self.assertEqual(result.status, "passed")
            self.assertIn("docker", called_command)
            self.assertIn("/workspace", called_command)

    def test_verifier_command_allowed_supports_targeted_unittest(self):
        from onecode.kernel.verifier import verifier_command_allowed

        self.assertTrue(verifier_command_allowed(["python3", "-m", "unittest", "tests.test_pay"]))
        self.assertTrue(verifier_command_allowed(["python3", "-m", "unittest", "tests/test_pay.py"]))
        self.assertTrue(verifier_command_allowed(["python3", "-m", "unittest", "-v", "tests/test_pay.py"]))
        self.assertTrue(verifier_command_allowed(["python3", "-m", "unittest", "-q", "tests.test_pay"]))
        self.assertFalse(verifier_command_allowed(["python3", "-m", "unittest", "../outside.py"]))
        self.assertFalse(verifier_command_allowed(["python3", "-m", "unittest", "src/pay.py"]))
        self.assertFalse(verifier_command_allowed(["python3", "-m", "unittest", "tests/../evil.py"]))
        self.assertFalse(verifier_command_allowed(["python3", "-m", "pytest", "tests/test_pay.py"]))

    def test_targeted_test_for_path_resolves_corresponding_test(self):
        from onecode.kernel.verifier import targeted_test_for_path

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "tests").mkdir()
            (workspace / "src" / "pay.py").write_text("RATE = 10\n", encoding="utf-8")
            (workspace / "tests" / "test_pay.py").write_text("import unittest\n", encoding="utf-8")

            self.assertEqual(targeted_test_for_path(workspace, "src/pay.py"), "tests/test_pay.py")
            self.assertIsNone(targeted_test_for_path(workspace, "src/missing_test.py"))
            self.assertIsNone(targeted_test_for_path(workspace, "../escape.py"))

    def test_run_two_stage_verifier_short_circuits_on_stage1_failure(self):
        from onecode.kernel.verifier import VerifierResult, run_two_stage_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_pay.py").write_text("import unittest\n", encoding="utf-8")

            failed_stage1 = VerifierResult(
                id="python-unittest-targeted",
                status="failed",
                reason="verifier_failed",
                failure_kind="command_failed",
                exit_code=1,
                duration_ms=50,
                stdout_tail="",
                stderr_tail="AssertionError in test_pay\n",
                stdout_sha256="",
                stderr_sha256="",
                cwd=".",
                command=["python3", "-m", "unittest", "tests/test_pay.py"],
            )

            with patch("onecode.kernel.verifier.run_verifier", return_value=failed_stage1) as mock_run:
                final, all_results = run_two_stage_verifier(
                    workspace,
                    targeted_test="tests/test_pay.py",
                    sandbox_config=None,
                )

            self.assertEqual(final.status, "failed")
            self.assertEqual(len(all_results), 1)
            self.assertEqual(all_results[0].id, "python-unittest-targeted")
            mock_run.assert_called_once()

    def test_run_two_stage_verifier_proceeds_to_stage2_on_stage1_pass(self):
        from onecode.kernel.verifier import VerifierResult, run_two_stage_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_pay.py").write_text("import unittest\n", encoding="utf-8")

            passed_stage1 = VerifierResult(
                id="python-unittest-targeted",
                status="passed",
                reason=None,
                failure_kind=None,
                exit_code=0,
                duration_ms=40,
                stdout_tail="Ran 1 test in 0.01s\nOK\n",
                stderr_tail="",
                stdout_sha256="",
                stderr_sha256="",
                cwd=".",
                command=["python3", "-m", "unittest", "tests/test_pay.py"],
            )
            passed_stage2 = VerifierResult(
                id="python-unittest",
                status="passed",
                reason=None,
                failure_kind=None,
                exit_code=0,
                duration_ms=120,
                stdout_tail="Ran 5 tests in 0.05s\nOK\n",
                stderr_tail="",
                stdout_sha256="",
                stderr_sha256="",
                cwd=".",
                command=["python3", "-m", "unittest", "discover", "-s", "tests"],
            )

            with patch("onecode.kernel.verifier.run_verifier", side_effect=[passed_stage1, passed_stage2]) as mock_run:
                final, all_results = run_two_stage_verifier(
                    workspace,
                    targeted_test="tests/test_pay.py",
                    sandbox_config=None,
                )

            self.assertEqual(final.status, "passed")
            self.assertEqual(len(all_results), 2)
            self.assertEqual(all_results[0].id, "python-unittest-targeted")
            self.assertEqual(all_results[1].id, "python-unittest")
            self.assertEqual(mock_run.call_count, 2)

    def test_verifier_result_backward_compatibility_defaults(self):
        from onecode.kernel.verifier import VerifierResult

        # When caller does not provide stdout_sha256, stderr_sha256, cwd, or command
        res = VerifierResult(
            id="legacy-verifier",
            status="passed",
            reason=None,
            failure_kind=None,
            exit_code=0,
            duration_ms=25,
            stdout_tail="legacy output",
            stderr_tail="",
        )
        self.assertEqual(res.id, "legacy-verifier")
        self.assertEqual(res.cwd, ".")
        self.assertEqual(res.command, [])
        self.assertTrue(len(res.stdout_sha256) == 64)
        self.assertTrue(len(res.stderr_sha256) == 64)

    def test_run_host_verifier_passes_when_exit_zero_and_reward_one(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            verifier = tmp_path / "verifier.py"
            verifier.write_text(
                "import os\n"
                "from pathlib import Path\n"
                "log_dir = Path(os.environ['LOG_DIR'])\n"
                "(log_dir / 'reward.txt').write_text('1.0')\n"
                "(log_dir / 'reward.json').write_text('{\"passed\": 10, \"total\": 10}')\n",
                encoding="utf-8",
            )
            checked, reward = run_host_verifier(workspace, verifier)
            self.assertEqual(checked.status, "passed")
            self.assertIsNone(checked.reason)
            self.assertEqual(checked.exit_code, 0)
            self.assertEqual(reward, 1.0)
            self.assertEqual(checked.id, "host-verifier")

    def test_run_host_verifier_rejects_full_score_without_assertion_counts(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            verifier = tmp_path / "verifier.py"
            verifier.write_text(
                "import os\n"
                "from pathlib import Path\n"
                "log_dir = Path(os.environ['LOG_DIR'])\n"
                "(log_dir / 'reward.txt').write_text('1.0')\n",
                encoding="utf-8",
            )
            checked, reward = run_host_verifier(workspace, verifier)
            self.assertEqual(checked.status, "failed")
            self.assertEqual(checked.reason, "reward_forgery_detected")
            self.assertEqual(reward, 0.0)

    def test_run_host_verifier_rejects_stdlib_shadow_before_execution(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            (workspace / "json.py").write_text("def dumps(*args, **kwargs):\n    return '{}'\n", encoding="utf-8")
            verifier = tmp_path / "verifier.py"
            verifier.write_text("raise SystemExit(0)\n", encoding="utf-8")
            checked, reward = run_host_verifier(workspace, verifier)
            self.assertEqual(checked.status, "failed")
            self.assertEqual(checked.reason, "sys_path_hijack_detected")
            self.assertEqual(reward, 0.0)

    def test_run_host_verifier_rejects_nested_stdlib_shadow(self):
        from onecode.kernel.verifier import audit_workspace_for_sys_path_hijacking

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            nested = workspace / "src" / "pkg"
            nested.mkdir(parents=True)
            (nested / "json.py").write_text("def dumps(*args, **kwargs):\n    return '{}'\n", encoding="utf-8")
            violations = audit_workspace_for_sys_path_hijacking(workspace)
            self.assertTrue(any("json.py" in item for item in violations))

    def test_run_host_verifier_fails_when_reward_less_than_one(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            verifier = tmp_path / "verifier.py"
            verifier.write_text(
                "import os\n"
                "from pathlib import Path\n"
                "log_dir = Path(os.environ['LOG_DIR'])\n"
                "(log_dir / 'reward.txt').write_text('0.857')\n",
                encoding="utf-8",
            )
            checked, reward = run_host_verifier(workspace, verifier)
            self.assertEqual(checked.status, "failed")
            self.assertEqual(checked.reason, "verifier_failed")
            self.assertEqual(checked.exit_code, 0)
            self.assertEqual(reward, 0.857)

    def test_run_host_verifier_fails_when_exit_code_nonzero(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            verifier = tmp_path / "verifier.py"
            verifier.write_text(
                "import sys\n"
                "sys.exit(2)\n",
                encoding="utf-8",
            )
            checked, reward = run_host_verifier(workspace, verifier)
            self.assertEqual(checked.status, "failed")
            self.assertEqual(checked.reason, "verifier_failed")
            self.assertEqual(checked.exit_code, 2)
            self.assertEqual(reward, "ungraded")

    def test_run_host_verifier_handles_missing_script(self):
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            checked, reward = run_host_verifier(workspace, Path(tmp) / "nonexistent.py")
            self.assertEqual(checked.status, "failed")
            self.assertEqual(checked.reason, "host_verifier_not_found")
            self.assertEqual(reward, "ungraded")

    def test_verifier_result_container_fields(self):
        r1 = VerifierResult(
            id="test",
            status="passed",
            reason=None,
            failure_kind=None,
            exit_code=0,
            duration_ms=10,
            stdout_tail="",
            stderr_tail="",
            cwd=".",
        )
        d1 = r1.to_dict()
        self.assertNotIn("container_id", d1)
        self.assertNotIn("container_image", d1)
        self.assertNotIn("container_arch", d1)

        r2 = VerifierResult(
            id="test",
            status="passed",
            reason=None,
            failure_kind=None,
            exit_code=0,
            duration_ms=10,
            stdout_tail="",
            stderr_tail="",
            cwd=".",
            container_id="abc12345",
            container_image="python:3.12-slim-amd64",
            container_arch="amd64",
        )
        d2 = r2.to_dict()
        self.assertEqual(d2["container_id"], "abc12345")
        self.assertEqual(d2["container_image"], "python:3.12-slim-amd64")
        self.assertEqual(d2["container_arch"], "amd64")

    def test_run_host_verifier_dispatches_to_container_verifier(self):
        from unittest.mock import patch
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import run_host_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            verifier = Path(tmp) / "verifier.py"
            verifier.write_text("print('hello')", encoding="utf-8")
            cfg = SandboxConfig(workspace=workspace, image="test-image")

            expected_res = VerifierResult(
                id="host-verifier",
                status="passed",
                reason=None,
                failure_kind=None,
                exit_code=0,
                duration_ms=10,
                stdout_tail="",
                stderr_tail="",
                cwd=str(workspace),
                container_id="cid123",
            )
            with patch("onecode.kernel.verifier._run_container_verifier", return_value=(expected_res, 1.0)) as mock_run:
                checked, reward = run_host_verifier(workspace, verifier, sandbox_config=cfg)
                mock_run.assert_called_once_with(
                    workspace=workspace,
                    verifier=verifier.resolve(),
                    sandbox_config=cfg,
                    timeout_seconds=180.0,
                )
                self.assertEqual(checked.container_id, "cid123")
                self.assertEqual(reward, 1.0)

    def test_run_container_verifier_cidfile_requires_64_hex_chars(self):
        from unittest.mock import patch
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import _run_container_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            verifier = Path(tmp) / "verifier.py"
            verifier.write_text("print('hello')", encoding="utf-8")
            cfg = SandboxConfig(workspace=workspace, image="test-image")

            fake_proc = type("CompletedProc", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            with patch("shutil.which", return_value="/usr/bin/docker"), \
                 patch("onecode.kernel.verifier.image_platform_mismatch", return_value=False), \
                 patch("onecode.kernel.sandbox._image_architecture", return_value="amd64"):

                def write_valid_cid(*args, **kwargs):
                    cidfile = args[0][4]
                    Path(cidfile).write_text("a" * 64, encoding="utf-8")
                    reward_file = Path(cidfile).parent / "reward.txt"
                    reward_file.write_text("1.0", encoding="utf-8")
                    return fake_proc

                with patch("subprocess.run", side_effect=write_valid_cid):
                    res, rew = _run_container_verifier(workspace, verifier, cfg)
                    self.assertEqual(res.container_id, "a" * 64)
                    self.assertEqual(res.container_arch, "amd64")

                def write_invalid_cid(*args, **kwargs):
                    cidfile = args[0][4]
                    Path(cidfile).write_text("not-a-valid-container-id", encoding="utf-8")
                    reward_file = Path(cidfile).parent / "reward.txt"
                    reward_file.write_text("1.0", encoding="utf-8")
                    return fake_proc

                with patch("subprocess.run", side_effect=write_invalid_cid):
                    res, rew = _run_container_verifier(workspace, verifier, cfg)
                    self.assertIsNone(res.container_id)
                    self.assertIsNone(res.container_arch)

    def test_container_log_mount_does_not_contain_the_cidfile(self):
        from unittest.mock import patch
        from onecode.kernel.sandbox import SandboxConfig
        from onecode.kernel.verifier import _run_container_verifier

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            verifier = Path(tmp) / "verifier.py"
            verifier.write_text("print('hello')", encoding="utf-8")
            cfg = SandboxConfig(workspace=workspace, image="test-image")
            captured: list[list[str]] = []

            def record(argv, **kwargs):
                captured.append(list(argv))
                cidfile = Path(argv[4])
                cidfile.write_text("b" * 64, encoding="utf-8")
                return type("CompletedProc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with patch("shutil.which", return_value="/usr/bin/docker"), \
                 patch("onecode.kernel.verifier.image_platform_mismatch", return_value=False), \
                 patch("onecode.kernel.sandbox._image_architecture", return_value="amd64"), \
                 patch("subprocess.run", side_effect=record):
                _run_container_verifier(workspace, verifier, cfg)
            command = captured[0]
            cidfile = Path(command[command.index("--cidfile") + 1])
            mount = next(item for item in command if "dst=/log_dir" in item and "type=bind" in item)
            staging = Path(next(part.removeprefix("src=") for part in mount.split(",") if part.startswith("src=")))
            resolved_cid = cidfile.resolve()
            resolved_staging = staging.resolve()
            self.assertFalse(resolved_cid.is_relative_to(resolved_staging))
            self.assertNotEqual(resolved_cid.parent, resolved_staging)

    def test_skipped_verifier_does_not_halt_completed_run(self):
        from onecode.kernel.run_inspection import apply_verifier_evidence

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            verifier = VerifierResult(
                id="python-unittest",
                status="skipped",
                reason="no_unittest_collected",
                failure_kind=None,
                exit_code=0,
                duration_ms=5,
                stdout_tail="",
                stderr_tail="Ran 0 tests in 0.000s\nOK",
            )
            result = {
                "run_id": "test-skipped-verifier",
                "status": "completed",
                "reason": None,
                "partial": False,
                "requested_count": 1,
                "completed_count": 1,
                "skipped_count": 0,
                "failed_count": 0,
                "assets": [],
                "iching_status_code": 63,
            }
            enhanced = apply_verifier_evidence(result, workspace, [verifier])
            self.assertEqual(enhanced["status"], "completed")
            self.assertIsNone(enhanced["reason"])
            self.assertEqual(enhanced["delivery_status"], "deliverable")

    def test_unittest_guard_executes_function_test_cases(self):
        from onecode.kernel.verifier import guarded_unittest_command

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_smoke.py").write_text(
                "import pathlib\n\ndef test_entry_present():\n    assert pathlib.Path('tests/test_smoke.py').exists()\n",
                encoding="utf-8",
            )
            cmd = guarded_unittest_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
            proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("Ran 1 test", proc.stderr + proc.stdout)
            self.assertIn("OK", proc.stderr + proc.stdout)



