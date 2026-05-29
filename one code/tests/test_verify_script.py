import os
import subprocess
import sys
import unittest
from pathlib import Path


class VerifyScriptTests(unittest.TestCase):
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
        self.assertNotIn("export PYTHONPATH", text)

    def test_verify_script_runs_non_recursive_smoke_check(self):
        env = os.environ.copy()
        env.pop("PYTHON", None)
        env.pop("VIRTUAL_ENV", None)
        completed = subprocess.run(
            ["bash", "scripts/verify.sh", "--skip-tests"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("compileall", completed.stdout)
        self.assertIn("doctor", completed.stdout)

    def test_verify_script_accepts_current_interpreter_override(self):
        env = os.environ.copy()
        env["PYTHON"] = sys.executable

        completed = subprocess.run(
            ["bash", "scripts/verify.sh", "--skip-tests"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("doctor", completed.stdout)


if __name__ == "__main__":
    unittest.main()
