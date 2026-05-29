import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file
from onecode.kernel.path_guard import PathGuard, PathGuardError


class PathGuardTests(unittest.TestCase):
    def test_write_text_creates_allowed_relative_file_and_returns_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = PathGuard.write_text(workspace, "src/generated.py", "print('ok')\n")
            target = workspace / "src" / "generated.py"

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "print('ok')\n")
            self.assertEqual(result["path"], str(target.resolve()))
            self.assertEqual(result["sha256"], sha256_file(target))

    def test_rejects_path_traversal_without_writing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            outside = Path(tmp) / "outside.txt"

            with self.assertRaises(PathGuardError):
                PathGuard.write_text(workspace, "../outside.txt", "blocked")

            self.assertFalse(outside.exists())

    def test_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            absolute = workspace / "absolute.txt"

            with self.assertRaises(PathGuardError):
                PathGuard.write_text(workspace, str(absolute), "blocked")

            self.assertFalse(absolute.exists())

    def test_rejects_root_config_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for path in [".env", ".env.local", ".gitignore", "pyproject.toml", ".git/config"]:
                with self.subTest(path=path):
                    with self.assertRaises(PathGuardError):
                        PathGuard.write_text(workspace, path, "blocked")
                    self.assertFalse((workspace / path).exists())

    def test_rejects_executable_configuration_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = [
                ".github/workflows/ci.yml",
                "Makefile",
                "setup.py",
                "setup.cfg",
                ".pre-commit-config.yaml",
            ]

            for path in paths:
                with self.subTest(path=path):
                    with self.assertRaises(PathGuardError):
                        PathGuard.write_text(workspace, path, "blocked")
                    self.assertFalse((workspace / path).exists())


if __name__ == "__main__":
    unittest.main()
