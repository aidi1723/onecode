import os
import socket
import subprocess
import sys
import unittest
from pathlib import Path


class VerifyScriptTests(unittest.TestCase):
    def test_bootstrap_local_script_exists_and_supports_dry_run(self):
        script = Path("scripts/bootstrap-local.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

        completed = subprocess.run(
            ["bash", str(script), "--dry-run"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("install-local.sh", completed.stdout)
        self.assertIn("start-local.sh", completed.stdout)
        self.assertIn("http://127.0.0.1:14080/c/new", completed.stdout)

    def test_makefile_documents_customer_shortcuts(self):
        makefile = Path("Makefile")

        self.assertTrue(makefile.exists())
        text = makefile.read_text(encoding="utf-8")

        for snippet in [
            "bootstrap:",
            "doctor:",
            "install:",
            "start:",
            "verify:",
            "scripts/bootstrap-local.sh",
            "scripts/doctor-local.sh",
            "scripts/install-local.sh",
            "scripts/start-local.sh",
        ]:
            self.assertIn(snippet, text)

    def test_doctor_local_script_exists_and_supports_skip_flags(self):
        script = Path("scripts/doctor-local.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

        completed = subprocess.run(
            [
                "bash",
                str(script),
                "--skip-ports",
                "--skip-shell",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("OneCode local deployment doctor", completed.stdout)
        self.assertIn("status: ok", completed.stdout)

    def test_install_local_script_exists_and_supports_dry_run(self):
        script = Path("scripts/install-local.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

        completed = subprocess.run(
            ["bash", str(script), "--dry-run"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("pip install -e .", completed.stdout)
        self.assertIn("doctor-local.sh --skip-ports", completed.stdout)
        self.assertIn("npm install", completed.stdout)
        self.assertIn("shell/onecode-librechat", completed.stdout)

    def test_start_local_script_exists_and_supports_dry_run(self):
        script = Path("scripts/start-local.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

        completed = subprocess.run(
            ["bash", str(script), "--dry-run"],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("onecode shell", completed.stdout)
        self.assertIn("--show-credentials", completed.stdout)
        self.assertIn("http://127.0.0.1:14080/c/new", completed.stdout)
        self.assertIn("doctor-local.sh", completed.stdout)

    def test_start_local_dry_run_uses_custom_landing_port(self):
        completed = subprocess.run(
            [
                "bash",
                "scripts/start-local.sh",
                "--librechat-port",
                "14180",
                "--dry-run",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("http://127.0.0.1:14180/c/new", completed.stdout)
        self.assertIn("--librechat-port 14180", completed.stdout)

    def test_doctor_local_reports_busy_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            busy_port = str(sock.getsockname()[1])

            completed = subprocess.run(
                [
                    "bash",
                    "scripts/doctor-local.sh",
                    "--skip-shell",
                    "--librechat-port",
                    busy_port,
                    "--onecode-port",
                    "1",
                    "--mongo-port",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(f"busy: LibreChat shell port {busy_port}", completed.stderr)

    def test_demo_v07_script_exists_and_is_executable(self):
        script = Path("scripts/demo_v07.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_demo_v07_script_documents_v07_commands(self):
        text = Path("scripts/demo_v07.sh").read_text(encoding="utf-8")

        for snippet in [
            "list-verifier-presets",
            "init-verifier-policy",
            "run-plan",
            "inspect",
            "list-runs",
        ]:
            self.assertIn(snippet, text)

    def test_demo_v07_script_runs_with_current_interpreter(self):
        env = os.environ.copy()
        env["PYTHON"] = sys.executable

        completed = subprocess.run(
            ["bash", "scripts/demo_v07.sh"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("demo workspace", completed.stdout)
        self.assertIn("demo-plan-verified", completed.stdout)
        self.assertIn("presets: python-compileall, python-unittest", completed.stdout)
        self.assertIn("policy: completed", completed.stdout)
        self.assertIn("run-plan: completed / deliverable", completed.stdout)
        self.assertIn("verifier: python-unittest passed", completed.stdout)
        self.assertIn("inspect: completed / deliverable", completed.stdout)
        self.assertNotIn("iching_profile", completed.stdout)
        self.assertNotIn("element_matrix", completed.stdout)

    def test_verify_script_exists_and_is_executable(self):
        script = Path("scripts/verify.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_verify_script_uses_short_module_entrypoint(self):
        script = Path("scripts/verify.sh")
        text = script.read_text(encoding="utf-8")

        self.assertIn('"$PYTHON_BIN" -m onecode doctor', text)
        self.assertNotIn("-m onecode.cli doctor", text)

    def test_verify_script_uses_overridable_python_interpreter(self):
        text = Path("scripts/verify.sh").read_text(encoding="utf-8")

        self.assertIn('PYTHON_BIN="${PYTHON:-}"', text)
        self.assertIn('elif [[ -z "$PYTHON_BIN" && -x ".venv/bin/python" ]]; then', text)
        self.assertIn('"$PYTHON_BIN" -m pip install -e .[tui]', text)
        self.assertIn('"$PYTHON_BIN" -m unittest discover -s tests -v', text)
        self.assertIn("--skip-install", text)

    def test_verify_script_runs_non_recursive_smoke_check(self):
        env = os.environ.copy()
        env.pop("PYTHON", None)
        env.pop("VIRTUAL_ENV", None)
        completed = subprocess.run(
            ["bash", "scripts/verify.sh", "--skip-install", "--skip-tests"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("install skipped", completed.stdout)
        self.assertIn("compileall", completed.stdout)
        self.assertIn("doctor", completed.stdout)

    def test_verify_script_accepts_current_interpreter_override(self):
        env = os.environ.copy()
        env["PYTHON"] = sys.executable

        completed = subprocess.run(
            ["bash", "scripts/verify.sh", "--skip-install", "--skip-tests"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("doctor", completed.stdout)


if __name__ == "__main__":
    unittest.main()
