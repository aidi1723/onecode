import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.sandbox_test_harness import force_docker_run_timeout, install_sandbox_docker_stub


class SandboxTestHarnessTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        install_sandbox_docker_stub(self)

    def _sandbox_run(self, command: list[str], **kwargs):
        from onecode.kernel import sandbox

        return sandbox.subprocess.run(command, **kwargs)

    def test_docker_lifecycle_commands_return_success(self):
        for command in (
            ["docker", "version"],
            ["docker", "info"],
            ["docker", "inspect", "onecode-container"],
            ["docker", "create", "--name", "onecode-container"],
            ["docker", "start", "onecode-container"],
            ["docker", "kill", "onecode-container"],
        ):
            with self.subTest(command=command):
                completed = self._sandbox_run(command, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0)
                self.assertIsInstance(completed, subprocess.CompletedProcess)

    def test_docker_run_unittest_returns_real_failure_from_workspace_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_generated.py").write_text(
                "import unittest\n\n"
                "class GeneratedTests(unittest.TestCase):\n"
                "    def test_generated(self):\n"
                "        self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            command = [
                "docker",
                "run",
                "--rm",
                "--mount",
                f"type=bind,src={workspace.as_posix()},dst=/workspace",
                "python:3.12-slim",
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
            ]

            completed = self._sandbox_run(command, capture_output=True, text=True)

            self.assertNotEqual(completed.returncode, 0)
            combined = f"{completed.stdout}\n{completed.stderr}"
            self.assertIn("FAIL", combined)

    def test_docker_run_python_c_executes_script_without_source_sniffing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            script = (
                "from pathlib import Path\n"
                "Path('marker.txt').write_text('AssertionError\\n')\n"
            )
            command = [
                "docker",
                "run",
                "--rm",
                "--mount",
                f"type=bind,src={workspace.as_posix()},dst=/workspace",
                "python:3.12-slim",
                "python",
                "-c",
                script,
            ]

            completed = self._sandbox_run(command, capture_output=True, text=True)

            self.assertEqual(completed.returncode, 0)
            self.assertEqual((workspace / "marker.txt").read_text(encoding="utf-8"), "AssertionError\n")

    def test_non_docker_commands_use_original_subprocess_run(self):
        completed = self._sandbox_run(
            [sys.executable, "-c", "print('host-ok')"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("host-ok", completed.stdout)

    def test_force_docker_run_timeout_raises_and_keeps_shared_stub(self):
        force_docker_run_timeout(self)

        with self.assertRaises(subprocess.TimeoutExpired):
            self._sandbox_run(["docker", "run", "--rm", "python:3.12-slim", "python", "-V"])

        killed = self._sandbox_run(["docker", "kill", "onecode_ephemeral_test"], capture_output=True, text=True)
        self.assertEqual(killed.returncode, 0)

        host = self._sandbox_run(
            [sys.executable, "-c", "print('still-host')"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(host.returncode, 0)
        self.assertIn("still-host", host.stdout)

    def test_harness_source_does_not_sniff_script_or_test_text(self):
        source = Path(__file__).with_name("sandbox_test_harness.py").read_text(encoding="utf-8")

        self.assertNotIn('"AssertionError" in script_content', source)
        self.assertNotIn('"time.sleep" in script_content', source)
        self.assertNotIn('".fail(" in file_content', source)


if __name__ == "__main__":
    unittest.main()
