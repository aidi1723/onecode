import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file
from onecode.kernel.path_guard import PathGuard, PathGuardError


class PathGuardTests(unittest.TestCase):
    def test_protected_paths_cannot_be_reached_through_parent_segments(self):
        for target in (".env", ".env.local", "pyproject.toml", ".gitignore", "setup.py", "setup.cfg",
                       "Makefile", ".pre-commit-config.yaml", ".git/config", ".github/workflows/ci.yml"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                (workspace / "nested").mkdir()
                with self.assertRaises(PathGuardError):
                    PathGuard.write_text(workspace, f"nested/../{target}", "forbidden")
                self.assertFalse((workspace / target).exists())

    def test_protected_paths_cannot_be_reached_through_symlinks(self):
        for target in (".env", ".env.local", "pyproject.toml", "Makefile", ".git/config", ".github/workflows/ci.yml"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                protected = workspace / target
                protected.parent.mkdir(parents=True, exist_ok=True)
                protected.write_text("original", encoding="utf-8")
                (workspace / "alias").symlink_to(target)
                with self.assertRaises(PathGuardError):
                    PathGuard.write_text(workspace, "alias", "forbidden")
                self.assertEqual(protected.read_text(encoding="utf-8"), "original")

    def test_directory_symlink_obeys_write_policy_and_workspace_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            for name in (".git", ".github", "src"):
                (workspace / name).mkdir()
                (workspace / f"alias-{name}").symlink_to(name, target_is_directory=True)
            (workspace / "outside").symlink_to(Path(tmp), target_is_directory=True)
            for target in ("alias-.git/config", "alias-.github/workflows/ci.yml", "outside/out.txt"):
                with self.subTest(target=target), self.assertRaises(PathGuardError):
                    PathGuard.write_text(workspace, target, "forbidden")
            PathGuard.write_text(workspace, "alias-src/allowed.txt", "allowed")
            self.assertEqual((workspace / "src/allowed.txt").read_text(), "allowed")
            self.assertFalse((Path(tmp) / "out.txt").exists())

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

    def test_rejects_nested_git_and_github_control_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = [
                "nested/.github/workflows/ci.yml",
                "subproject/.git/hooks/pre-commit",
                "a/b/.git/config",
            ]

            for path in paths:
                with self.subTest(path=path):
                    with self.assertRaises(PathGuardError):
                        PathGuard.write_text(workspace, path, "blocked")
                    self.assertFalse((workspace / path).exists())


if __name__ == "__main__":
    unittest.main()
