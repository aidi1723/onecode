import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from agent_skill_dictionary.executor import execute_command


class ExecutorTest(unittest.TestCase):
    def test_execute_command_captures_real_exit_code_and_writes_audit_log(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            audit_log = workspace / "audit.log.jsonl"

            result = execute_command(
                ["python3", "-c", "print('executor-ok')"],
                cwd=workspace,
                audit_log_path=audit_log,
            )

            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["stdout"], "executor-ok\n")
            self.assertEqual(result["stderr"], "")
            self.assertEqual(len(result["evidence"]["sha256"]), 64)
            self.assertTrue(audit_log.exists())

    def test_execute_command_rejects_cwd_outside_workspace_root(self):
        with TemporaryDirectory() as workspace_dir, TemporaryDirectory() as outside_dir:
            with self.assertRaises(ValueError):
                execute_command(
                    ["python3", "-c", "print('nope')"],
                    cwd=outside_dir,
                    workspace_root=workspace_dir,
                )

    def test_execute_command_records_nonzero_exit_code_and_stderr(self):
        with TemporaryDirectory() as tmpdir:
            result = execute_command(
                [
                    "python3",
                    "-c",
                    "import sys; print('bad', file=sys.stderr); raise SystemExit(7)",
                ],
                cwd=tmpdir,
            )

            self.assertEqual(result["exit_code"], 7)
            self.assertIn("bad", result["stderr"])
            self.assertEqual(result["evidence"]["exit_code"], 7)

    def test_execute_command_returns_structured_failure_when_binary_is_missing(self):
        with TemporaryDirectory() as tmpdir:
            with patch("agent_skill_dictionary.executor.subprocess.run", side_effect=FileNotFoundError("pytest")):
                result = execute_command(["pytest", "-q"], cwd=tmpdir)

        self.assertEqual(result["exit_code"], 127)
        self.assertIn("Command not found", result["stderr"])
        self.assertIn("pytest", result["stderr"])
        self.assertEqual(result["evidence"]["exit_code"], 127)

    def test_execute_command_can_run_inside_docker_sandbox_when_available(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            completed = SimpleNamespace(returncode=0, stdout="docker-ok\n", stderr="")

            with patch("agent_skill_dictionary.executor.shutil.which", return_value="/usr/bin/docker"), patch(
                "agent_skill_dictionary.executor.subprocess.run",
                return_value=completed,
            ) as run_mock:
                result = execute_command(
                    ["pytest", "--cov"],
                    cwd=workspace,
                    workspace_root=workspace,
                    use_docker=True,
                    docker_image="python:3.11-slim",
                )

            self.assertEqual(result["sandbox"], "docker")
            self.assertEqual(result["exit_code"], 0)
            docker_command = run_mock.call_args.args[0]
            self.assertEqual(docker_command[:3], ["docker", "run", "--rm"])
            self.assertIn("--network", docker_command)
            self.assertIn("none", docker_command)
            self.assertIn("--memory", docker_command)
            self.assertIn("1g", docker_command)
            self.assertIn("--cpus", docker_command)
            self.assertIn("2", docker_command)
            self.assertIn("--read-only", docker_command)
            self.assertIn("--tmpfs", docker_command)
            self.assertIn("/tmp:rw,noexec,nosuid,size=256m", docker_command)
            self.assertIn("--user", docker_command)
            self.assertIn("65534:65534", docker_command)
            self.assertIn(f"{workspace.resolve()}:/workspace:ro", docker_command)
            self.assertNotIn(f"{workspace.resolve()}:/workspace", docker_command)
            self.assertIn("python:3.11-slim", docker_command)
            self.assertEqual(docker_command[-2:], ["pytest", "--cov"])

    def test_execute_command_falls_back_to_local_when_docker_is_unavailable(self):
        with TemporaryDirectory() as tmpdir:
            with patch("agent_skill_dictionary.executor.shutil.which", return_value=None):
                result = execute_command(
                    ["python3", "-c", "print('local-ok')"],
                    cwd=tmpdir,
                    use_docker=True,
                )

            self.assertEqual(result["sandbox"], "local")
            self.assertEqual(result["sandbox_fallback"], "docker_unavailable")
            self.assertEqual(result["stdout"], "local-ok\n")

    def test_execute_command_can_require_docker_sandbox(self):
        with TemporaryDirectory() as tmpdir:
            with patch("agent_skill_dictionary.executor.shutil.which", return_value=None):
                result = execute_command(
                    ["python3", "-c", "print('must-not-run')"],
                    cwd=tmpdir,
                    use_docker=True,
                    require_docker=True,
                )

        self.assertEqual(result["sandbox"], "docker")
        self.assertEqual(result["sandbox_fallback"], "docker_unavailable")
        self.assertEqual(result["exit_code"], 126)
        self.assertIn("Docker sandbox is required", result["stderr"])


if __name__ == "__main__":
    unittest.main()
