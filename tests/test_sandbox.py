import os
import sys
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
        self.assertIn(f"{os.getuid()}:{os.getgid()}", command)
        self.assertTrue(any(item.startswith("type=bind,src=") and item.endswith(",dst=/workspace") for item in command))
        self.assertNotIn("--volume", command)

    def test_sensitive_directories_are_mounted_readonly(self):
        from onecode.kernel.sandbox import SandboxConfig, build_docker_command

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / "tests").mkdir()
            command = build_docker_command(SandboxConfig(workspace=workspace, image="python:3.12-slim"), ["python3", "-V"])
        joined = " ".join(command)
        self.assertIn("dst=/workspace/.git,readonly", joined)
        self.assertIn("dst=/workspace/tests,readonly", joined)

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

    def test_container_argv_uses_the_image_python(self):
        from onecode.kernel.sandbox import container_argv

        rewritten = container_argv([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        self.assertEqual(rewritten, ["python3", "-m", "unittest", "discover", "-s", "tests"])
        self.assertEqual(container_argv(["python", "-c", "print(1)"]), ["python3", "-c", "print(1)"])
        self.assertEqual(container_argv(["git", "status"]), ["git", "status"])

    def test_sandbox_image_can_be_selected_for_the_host(self):
        from onecode.kernel.sandbox import SandboxConfig, default_sandbox_image

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ONECODE_SANDBOX_IMAGE": "python:3.12-slim-amd64"}):
            self.assertEqual(default_sandbox_image(), "python:3.12-slim-amd64")
            self.assertEqual(SandboxConfig(workspace=Path(tmp)).image, "python:3.12-slim-amd64")

    def test_image_architecture_must_match_the_host(self):
        from onecode.kernel.sandbox import architectures_match

        self.assertTrue(architectures_match("amd64", "x86_64"))
        self.assertTrue(architectures_match("arm64", "aarch64"))
        self.assertFalse(architectures_match("arm64", "x86_64"))
        self.assertFalse(architectures_match("amd64", "aarch64"))

    def test_foreign_image_uses_a_local_native_sibling(self):
        from onecode.kernel.sandbox import runnable_sandbox_image

        def arch(image: str) -> str | None:
            if image == "python:3.12-slim":
                return "arm64"
            if image == "python:3.12-slim-amd64":
                return "amd64"
            return None

        with patch("onecode.kernel.sandbox._image_architecture", side_effect=arch), patch(
            "onecode.kernel.sandbox.platform.machine", return_value="x86_64"
        ):
            self.assertEqual(runnable_sandbox_image("python:3.12-slim"), "python:3.12-slim-amd64")

        def missing_sibling(image: str) -> str | None:
            return "arm64" if image == "python:3.12-slim" else None

        with patch("onecode.kernel.sandbox._image_architecture", side_effect=missing_sibling), patch(
            "onecode.kernel.sandbox.platform.machine", return_value="x86_64"
        ):
            self.assertEqual(runnable_sandbox_image("python:3.12-slim"), "python:3.12-slim")

    def test_ephemeral_sandbox_uses_a_local_native_sibling(self):
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_in_sandbox, _IMAGE_ARCH

        calls: list[list[str]] = []

        def fake_run(argv, **kwargs):
            calls.append(list(argv))
            if argv[:3] == ["docker", "image", "inspect"]:
                image = argv[-1]
                arch = "arm64" if image == "python:3.12-slim" else "amd64" if image == "python:3.12-slim-amd64" else ""
                return CompletedProcess(argv, 0 if arch else 1, f"{arch}\n", "")
            return CompletedProcess(argv, 0, "ok\n", "")

        _IMAGE_ARCH.clear()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "onecode.kernel.sandbox.subprocess.run", side_effect=fake_run
        ), patch("onecode.kernel.sandbox.shutil.which", return_value="/usr/bin/docker"), patch(
            "onecode.kernel.sandbox.platform.machine", return_value="x86_64"
        ):
            run_in_sandbox(SandboxConfig(workspace=Path(tmp), image="python:3.12-slim"), ["python3", "-c", "print(1)"])
        _IMAGE_ARCH.clear()
        docker_runs = [argv for argv in calls if argv[:2] == ["docker", "run"]]
        self.assertEqual(len(docker_runs), 1)
        self.assertIn("python:3.12-slim-amd64", docker_runs[0])

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

    def test_parallel_reused_sandbox_creates_the_container_once(self):
        import threading
        import time
        from subprocess import CompletedProcess

        from onecode.kernel.sandbox import SandboxConfig, run_in_reused_sandbox

        calls: list[list[str]] = []
        gate = threading.Lock()
        overlap = 0
        max_overlap = 0

        def fake_run(argv, **kwargs):
            nonlocal overlap, max_overlap
            if argv[:2] == ["docker", "inspect"] and len(argv) == 3:
                with gate:
                    overlap += 1
                    max_overlap = max(max_overlap, overlap)
                    exists = any(item[:2] == ["docker", "create"] for item in calls)
                time.sleep(0.05)
                with gate:
                    overlap -= 1
                    exists = any(item[:2] == ["docker", "create"] for item in calls)
                return CompletedProcess(argv, 0 if exists else 1, "", "")
            with gate:
                calls.append(list(argv))
            if argv[:3] == ["docker", "inspect", "-f"]:
                return CompletedProcess(argv, 0, "true\n", "")
            return CompletedProcess(argv, 0, "ok\n", "")

        with tempfile.TemporaryDirectory() as tmp, patch("onecode.kernel.sandbox.subprocess.run", side_effect=fake_run):
            config = SandboxConfig(workspace=Path(tmp))
            results: list[CompletedProcess] = []

            def run() -> None:
                results.append(run_in_reused_sandbox(config, ["python3", "-c", "print(1)"]))

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(max_overlap, 1)
        self.assertEqual([item.stdout for item in results], ["ok\n", "ok\n"])
        self.assertEqual(sum(item[:2] == ["docker", "create"] for item in calls), 1)

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
