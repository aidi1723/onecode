import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.cycle_approvals import load_pending_approvals, persist_pending_approval
from onecode.kernel.path_guard import PathGuard, PathGuardError


class HostInputFuzzTests(unittest.TestCase):
    def test_null_and_oversized_paths_raise_path_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for relative in ("a\x00b", "a/" + ("b" * 20_000), "\x00"):
                with self.subTest(relative=relative[:8]):
                    with self.assertRaises(PathGuardError):
                        PathGuard.resolve_target(workspace, relative)
                    with self.assertRaises(PathGuardError):
                        PathGuard.resolve_read_target(workspace, relative)

    def test_malformed_cli_env_and_config_raise_clean_errors(self):
        from onecode.cli import main
        from onecode.kernel.model_config import read_model_config, write_model_config

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "work"
            workspace.mkdir()
            argv_cases = [
                ["run", "task", "--max-task-chars", "0"],
                ["run", "hello\x00", "--workspace", str(workspace)],
                ["missing-command"],
            ]
            from contextlib import redirect_stderr, redirect_stdout
            from io import StringIO

            for argv in argv_cases:
                with self.subTest(argv=argv[0] if argv[0] != "run" else argv[1][:12]):
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
                        main(argv)
                    self.assertIsInstance(caught.exception.code, int)
            with redirect_stdout(StringIO()):
                oversized = main(["run", "x" * 200_000, "--workspace", str(workspace), "--max-task-chars", "10"])
            self.assertIsInstance(oversized, int)
            self.assertNotEqual(oversized, 0)

            home = Path(tmp) / "home"
            home.mkdir()
            (home / "config.json").write_text("{", encoding="utf-8")
            with patch.dict(os.environ, {"ONECODE_HOME": str(home)}):
                with self.assertRaises(ValueError):
                    read_model_config()
                with self.assertRaises(ValueError):
                    write_model_config(endpoint="\x00", api_key="secret")
                with self.assertRaises(ValueError):
                    write_model_config(endpoint="https://example.test/" + ("a" * 20_000), api_key="secret")


class ReleaseRollbackTests(unittest.TestCase):
    def test_rollback_restores_the_previous_release_and_old_task(self):
        from onecode.kernel.release_rollback import rollback_release, snapshot_release, stage_release

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "VERSION").write_text("0.8.0\n", encoding="utf-8")
            (root / "config.json").write_text('{"model":"old"}\n', encoding="utf-8")
            saved = persist_pending_approval(root, "run_command", {"argv": ["rm", "-rf", "./temp_test_dir"]})
            snapshot_release(root, "0.8.0")
            stage_release(
                root,
                "1.0.0",
                {
                    "VERSION": "1.0.0\n",
                    "config.json": "not-json\n",
                    ".onecode/pending-cycle/broken.json": "{",
                },
            )

            started = time.perf_counter()
            restored = rollback_release(root)
            elapsed = time.perf_counter() - started

            self.assertLess(elapsed, 60)
            self.assertEqual(restored["version"], "0.8.0")
            self.assertEqual((root / "VERSION").read_text(encoding="utf-8"), "0.8.0\n")
            self.assertEqual((root / "config.json").read_text(encoding="utf-8"), '{"model":"old"}\n')
            pending = load_pending_approvals(root)
            self.assertEqual([item["id"] for item in pending], [saved["id"]])
            self.assertEqual(pending[0]["params"]["argv"], ["rm", "-rf", "./temp_test_dir"])

    def test_release_command_rolls_back_from_the_cli(self):
        from contextlib import redirect_stdout
        from io import StringIO

        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "VERSION").write_text("0.8.0\n", encoding="utf-8")
            (root / "config.json").write_text('{"model":"old"}\n', encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["release", "snapshot", "--root", str(root), "--version", "0.8.0"]), 0)
                self.assertEqual(main(["release", "stage", "--root", str(root), "--version", "1.0.0"]), 0)
                self.assertEqual(main(["release", "rollback", "--root", str(root)]), 0)
            self.assertEqual((root / "VERSION").read_text(encoding="utf-8"), "0.8.0\n")
            self.assertEqual((root / "config.json").read_text(encoding="utf-8"), '{"model":"old"}\n')


if __name__ == "__main__":
    unittest.main()
