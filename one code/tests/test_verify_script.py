import os
import subprocess
import sys
import tempfile
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

    def test_release_audit_script_exists_and_is_executable(self):
        script = Path("scripts/release-audit.sh")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_release_audit_runs_readiness_checks_without_publishing(self):
        text = Path("scripts/release-audit.sh").read_text(encoding="utf-8")

        self.assertIn("publish action: not performed", text)
        self.assertIn("git diff --check", text)
        self.assertIn("scripts/check_source_quality.py src", text)
        self.assertIn("scripts/check_wheel_assets.py", text)
        self.assertIn("-m pip wheel", text)
        self.assertIn("mktemp -d", text)
        self.assertIn("BUILD_DIR_EXISTED", text)
        self.assertIn("cleanup_generated_build_dir", text)
        self.assertIn("cleanup_wheel_dir", text)
        self.assertIn("cleanup_generated_artifacts", text)
        self.assertIn("release readiness summary", text)

    def test_release_audit_cleans_generated_artifacts_before_listing_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            scripts_dir = workspace / "scripts"
            scripts_dir.mkdir()
            audit_script = scripts_dir / "release-audit.sh"
            audit_script.write_text(
                Path("scripts/release-audit.sh").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            audit_script.chmod(0o755)

            fake_python = workspace / "fake-python"
            fake_python.write_text(
                """#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-" ]]; then
  rm -rf build
  exit 0
fi

if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "wheel" ]]; then
  mkdir -p build
  wheel_dir=""
  previous=""
  for arg in "$@"; do
    if [[ "$previous" == "-w" ]]; then
      wheel_dir="$arg"
    fi
    previous="$arg"
  done
  if [[ -n "$wheel_dir" ]]; then
    mkdir -p "$wheel_dir"
    touch "$wheel_dir/onecode-0.0.0-py3-none-any.whl"
    printf '%s' "$wheel_dir" > wheel-dir.txt
  fi
  echo "fake wheel built"
  exit 0
fi

echo "fake python check: $*"
""",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            subprocess.run(
                ["git", "init"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=True,
            )

            env = os.environ.copy()
            env["PYTHON"] = str(fake_python)
            completed = subprocess.run(
                ["bash", "scripts/release-audit.sh"],
                cwd=workspace,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("fake wheel built", completed.stdout)
            self.assertIn("untracked release candidates", completed.stdout)
            self.assertNotIn("\nbuild\n", completed.stdout)
            self.assertFalse((workspace / "build").exists())
            wheel_dir = Path((workspace / "wheel-dir.txt").read_text(encoding="utf-8"))
            self.assertFalse(wheel_dir.exists())

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

    def test_ci_verifies_supported_python_version_matrix(self):
        text = Path(".github/workflows/verify.yml").read_text(encoding="utf-8")

        self.assertIn("strategy:", text)
        self.assertIn("matrix:", text)
        for version in ['"3.11"', '"3.12"', '"3.13"']:
            self.assertIn(version, text)
        self.assertIn("python-version: ${{ matrix.python-version }}", text)


if __name__ == "__main__":
    unittest.main()
