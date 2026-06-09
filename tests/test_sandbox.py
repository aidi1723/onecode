import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch


class SandboxTests(unittest.TestCase):
    def test_build_docker_command_mounts_workspace_at_fixed_path(self):
        from onecode.kernel.sandbox import SandboxConfig, build_docker_command

        with tempfile.TemporaryDirectory() as tmp:
            command = build_docker_command(
                SandboxConfig(workspace=Path(tmp), image="python:3.12-slim"),
                ["python", "-c", "print('ok')"],
            )

        self.assertEqual(command[:3], ["docker", "run", "--rm"])
        self.assertIn("--workdir", command)
        self.assertIn("/workspace", command)
        self.assertIn("python:3.12-slim", command)
        self.assertIn("python", command)

    def test_build_docker_command_can_disable_network(self):
        from onecode.kernel.sandbox import SandboxConfig, build_docker_command

        with tempfile.TemporaryDirectory() as tmp:
            command = build_docker_command(
                SandboxConfig(workspace=Path(tmp), image="python:3.12-slim", network="none"),
                ["python", "-V"],
            )

        self.assertIn("--network", command)
        self.assertIn("none", command)

    def test_build_docker_command_uses_stronger_default_isolation_flags(self):
        from onecode.kernel.sandbox import SandboxConfig, build_docker_command

        with tempfile.TemporaryDirectory() as tmp:
            command = build_docker_command(
                SandboxConfig(workspace=Path(tmp), image="python:3.12-slim"),
                ["python", "-V"],
            )

        self.assertIn("--cap-drop", command)
        self.assertIn("ALL", command)
        self.assertIn("--pids-limit", command)
        self.assertIn("256", command)
        self.assertIn("--read-only", command)
        self.assertIn("--tmpfs", command)
        self.assertIn("/tmp:rw,noexec,nosuid,size=64m", command)

    @unittest.skipUnless(hasattr(os, "getuid"), "requires Unix user ids")
    def test_build_docker_command_runs_as_host_user_for_bind_mount_writes(self):
        from onecode.kernel.sandbox import SandboxConfig, build_docker_command

        with tempfile.TemporaryDirectory() as tmp:
            command = build_docker_command(
                SandboxConfig(workspace=Path(tmp), image="python:3.12-slim"),
                ["python", "-V"],
            )

        self.assertIn("--user", command)
        user_index = command.index("--user")
        self.assertEqual(command[user_index + 1], f"{os.getuid()}:{os.getgid()}")

    def test_sandbox_rejects_missing_workspace(self):
        from onecode.kernel.sandbox import SandboxConfig

        with self.assertRaises(ValueError):
            SandboxConfig(workspace=Path("/definitely/missing/onecode/workspace"))

    def test_sandbox_smoke_returns_blocked_when_docker_missing(self):
        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value=None,
        ):
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_not_found")

    def test_sandbox_smoke_writes_report(self):
        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value=None,
        ):
            report_path = Path(tmp) / "sandbox-smoke.json"
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)), report_path=report_path)
            report_exists = report_path.exists()

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(report_exists)

    def test_sandbox_smoke_reports_mount_propagation_failure(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value="/usr/local/bin/docker",
        ), patch(
            "onecode.kernel.sandbox.run_in_sandbox",
            return_value=CompletedProcess(
                args=["docker", "run"],
                returncode=0,
                stdout="True\n",
                stderr="",
            ),
        ):
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)))

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "sandbox_mount_not_propagated")

    def test_cli_sandbox_smoke_reports_blocked_without_docker(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value=None,
        ), patch("builtins.print") as print_mock:
            exit_code = main(["sandbox-smoke", "--workspace", tmp])
            result = __import__("json").loads(print_mock.call_args.args[0])

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_not_found")
