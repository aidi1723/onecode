import tempfile
import unittest
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
        self.assertIn("--security-opt", command)
        self.assertIn("no-new-privileges", command)
        self.assertIn("--user", command)
        self.assertIn("65534:65534", command)
        self.assertTrue(any(item.startswith("type=bind,src=") and item.endswith(",dst=/workspace") for item in command))
        self.assertNotIn("--volume", command)

    def test_reused_container_commands_share_one_name(self):
        from onecode.kernel.sandbox import SandboxConfig, build_container_create, build_container_exec

        with tempfile.TemporaryDirectory() as tmp:
            config = SandboxConfig(workspace=Path(tmp))
            created = build_container_create(config)
            first = build_container_exec(config, ["python", "-V"])
            second = build_container_exec(config, ["python", "-c", "print(1)"])

        self.assertEqual(created[:3], ["docker", "create", "--name"])
        self.assertEqual(created[-2:], ["sleep", "infinity"])
        self.assertEqual(first[4], second[4])
        self.assertEqual(first[4], created[3])
        self.assertTrue(first[4].startswith("onecode-"))

    def test_reused_sandbox_creates_once_then_execs(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_in_reused_sandbox

        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(list(argv))
            if argv[:2] == ["docker", "inspect"] and len(argv) == 3:
                exists = any(item[:2] == ["docker", "create"] for item in calls)
                return CompletedProcess(argv, 0 if exists else 1, "", "")
            if argv[:3] == ["docker", "inspect", "-f"]:
                return CompletedProcess(argv, 0, "true\n", "")
            return CompletedProcess(argv, 0, "ok\n", "")

        with tempfile.TemporaryDirectory() as tmp, patch("onecode.kernel.sandbox.subprocess.run", side_effect=fake_run):
            config = SandboxConfig(workspace=Path(tmp))
            first = run_in_reused_sandbox(config, ["python", "-V"])
            second = run_in_reused_sandbox(config, ["python", "-V"])

        self.assertEqual(first.stdout, "ok\n")
        self.assertEqual(second.stdout, "ok\n")
        self.assertEqual(sum(item[:2] == ["docker", "create"] for item in calls), 1)
        execs = [item for item in calls if item[:2] == ["docker", "exec"]]
        self.assertEqual(len(execs), 2)
        self.assertEqual(execs[0][4], execs[1][4])

    def test_sandbox_rejects_missing_workspace(self):
        from onecode.kernel.sandbox import SandboxConfig

        with self.assertRaises(ValueError):
            SandboxConfig(workspace=Path("/definitely/missing/onecode/workspace"))

    def test_sandbox_rejects_boolean_numeric_limits(self):
        from onecode.kernel.sandbox import SandboxConfig

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "sandbox timeout_seconds must be positive"):
                SandboxConfig(workspace=Path(tmp), timeout_seconds=True)

            with self.assertRaisesRegex(ValueError, "sandbox pids_limit must be positive"):
                SandboxConfig(workspace=Path(tmp), pids_limit=True)

    def test_sandbox_smoke_returns_blocked_when_docker_missing(self):
        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value=None,
        ):
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_not_found")

    def test_sandbox_smoke_returns_blocked_when_docker_daemon_unavailable(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value="/usr/local/bin/docker",
        ), patch(
            "onecode.kernel.sandbox.run_in_sandbox",
            return_value=CompletedProcess(
                args=["docker", "run"],
                returncode=1,
                stdout="",
                stderr="Cannot connect to the Docker daemon at unix:///tmp/docker.sock. Is the docker daemon running?\n",
            ),
        ):
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_daemon_unavailable")

    def test_sandbox_smoke_returns_blocked_when_docker_socket_permission_denied(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_sandbox_smoke

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value="/usr/local/bin/docker",
        ), patch(
            "onecode.kernel.sandbox.run_in_sandbox",
            return_value=CompletedProcess(
                args=["docker", "run"],
                returncode=1,
                stdout="",
                stderr="permission denied while trying to connect to the docker API at unix:///tmp/docker.sock\n",
            ),
        ):
            result = run_sandbox_smoke(SandboxConfig(workspace=Path(tmp)))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_daemon_unavailable")

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

    def test_cli_sandbox_smoke_creates_missing_workspace(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.shutil.which",
            return_value=None,
        ), patch("builtins.print") as print_mock:
            workspace = Path(tmp) / "missing-smoke-workspace"
            exit_code = main(["sandbox-smoke", "--workspace", str(workspace)])
            result = __import__("json").loads(print_mock.call_args.args[0])
            workspace_exists = workspace.is_dir()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "docker_not_found")
        self.assertTrue(workspace_exists)
