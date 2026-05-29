import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


class PathSentinelTest(unittest.TestCase):
    def run_sentinel(self, kind: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "bin" / kind),
                *args,
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "ONEWORD_ACTIVE_CODE": "查"},
            check=False,
        )

    def run_build_mode_sentinel(
        self,
        kind: str,
        *args: str,
        workspace: Path,
        request_text: str = "实现 cluster-state-sync",
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            "ONEWORD_ACTIVE_CODE": "造",
            "ONEWORD_BUILD_MODE": "1",
            "ONEWORD_BUILD_MODE_WORKSPACE": str(workspace),
            "ONEWORD_BUILD_MODE_REQUEST_TEXT": request_text,
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "bin" / kind),
                *args,
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_bash_sentinel_blocks_dangerous_command_in_inspect_state(self):
        with TemporaryDirectory() as tmpdir:
            sentinel = Path(tmpdir) / "DANGER_SENTINEL_DO_NOT_DELETE.txt"
            sentinel.write_text("keep\n", encoding="utf-8")

            result = self.run_sentinel("bash", "-lc", f"rm -f {sentinel}")

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(sentinel.exists())
            self.assertIn("oneword local preflight denied", result.stderr)

    def test_rm_sentinel_blocks_delete_in_inspect_state(self):
        with TemporaryDirectory() as tmpdir:
            sentinel = Path(tmpdir) / "DANGER_SENTINEL_DO_NOT_DELETE.txt"
            sentinel.write_text("keep\n", encoding="utf-8")

            result = self.run_sentinel("rm", "-f", str(sentinel))

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(sentinel.exists())
            self.assertIn("oneword local preflight denied", result.stderr)

    def test_shell_alias_sentinels_block_execution_in_inspect_state(self):
        for kind in ("sh", "zsh"):
            with self.subTest(kind=kind), TemporaryDirectory() as tmpdir:
                sentinel = Path(tmpdir) / f"{kind}_probe.txt"

                result = self.run_sentinel(kind, "-lc", f"touch {sentinel}")

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(sentinel.exists())
                self.assertIn("oneword local preflight denied", result.stderr)

    def test_file_mutation_sentinels_block_common_write_tools_in_inspect_state(self):
        cases = {
            "tee": lambda target: ("-a", str(target)),
            "mv": lambda target: (str(target.with_suffix(".src")), str(target)),
            "cp": lambda target: (str(target.with_suffix(".src")), str(target)),
            "chmod": lambda target: ("777", str(target)),
        }
        for kind, build_args in cases.items():
            with self.subTest(kind=kind), TemporaryDirectory() as tmpdir:
                target = Path(tmpdir) / f"{kind}_probe.txt"
                src = target.with_suffix(".src")
                src.write_text("source\n", encoding="utf-8")
                if kind == "chmod":
                    target.write_text("keep\n", encoding="utf-8")

                result = self.run_sentinel(kind, *build_args(target))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("oneword local preflight denied", result.stderr)
                if kind in {"tee", "mv", "cp"}:
                    self.assertFalse(target.exists())

    def test_interpreter_sentinels_block_inline_execution_in_inspect_state(self):
        commands = {
            "python": ("-c", "print('blocked')"),
            "node": ("-e", "console.log('blocked')"),
        }
        for kind, args in commands.items():
            with self.subTest(kind=kind):
                result = self.run_sentinel(kind, *args)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("oneword local preflight denied", result.stderr)

    def test_build_mode_sentinel_blocks_workspace_with_unplanned_dependency_shim(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "fastapi").mkdir()
            (workspace / "fastapi" / "__init__.py").write_text("fake\n", encoding="utf-8")

            result = self.run_build_mode_sentinel(
                "python",
                "-c",
                "print('must-not-run')",
                workspace=workspace,
            )

            self.assertEqual(result.returncode, 126)
            self.assertIn("oneword build mode sovereignty denied", result.stderr)
            self.assertIn("sovereignty_workspace_gate", result.stderr)
            self.assertIn("fastapi/__init__.py", result.stderr)
            self.assertNotIn("must-not-run", result.stdout)

    def test_build_mode_sentinel_blocks_missing_required_environment(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = self.run_build_mode_sentinel(
                "python",
                "-c",
                "print('must-not-run')",
                workspace=workspace,
                extra_env={
                    "ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS": "1",
                    "ONEWORD_BUILD_MODE_PYTHON": str(workspace / "missing-python"),
                },
            )

            self.assertEqual(result.returncode, 126)
            self.assertIn("oneword build mode sovereignty denied", result.stderr)
            self.assertIn("sovereignty_environment_gate", result.stderr)
            self.assertIn("sqlmodel", result.stderr)
            self.assertNotIn("must-not-run", result.stdout)

    def test_build_mode_sentinel_allows_clean_workspace_to_reach_normal_preflight(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = self.run_build_mode_sentinel(
                "python",
                "-c",
                "print('normal-preflight')",
                workspace=workspace,
            )

            self.assertNotIn("oneword build mode sovereignty denied", result.stderr)
            self.assertIn("oneword local preflight denied", result.stderr)


if __name__ == "__main__":
    unittest.main()
