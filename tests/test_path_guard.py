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

    def test_rejects_dotdot_that_resolves_onto_denied_root_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "nested").mkdir()

            with self.assertRaises(PathGuardError):
                PathGuard.write_text(workspace, "nested/../.env", "blocked")

            self.assertFalse((workspace / ".env").exists())

    def test_rejects_case_variants_of_denied_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for path in [".ENV", ".Git/hooks/pre-commit", "Pyproject.toml", ".ONECODE/pending-plans/x.json"]:
                with self.subTest(path=path):
                    with self.assertRaises(PathGuardError):
                        PathGuard.write_text(workspace, path, "blocked")

    def test_rejects_write_through_workspace_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            real = workspace / "real"
            real.mkdir()
            (workspace / "link").symlink_to(real, target_is_directory=True)

            with self.assertRaises(PathGuardError):
                PathGuard.write_text(workspace, "link/out.txt", "blocked")

            self.assertFalse((real / "out.txt").exists())

    def test_write_text_preserves_existing_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "tool.sh"
            target.parent.mkdir()
            target.write_text("echo old\n", encoding="utf-8")
            target.chmod(0o755)

            PathGuard.write_text(workspace, "src/tool.sh", "echo new\n")

            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertEqual(list(target.parent.glob(".tool.sh*")), [])

    def test_resolve_contained_rejects_paths_outside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            outside = Path(tmp) / "secret.txt"
            outside.write_text("nope", encoding="utf-8")

            with self.assertRaises(PathGuardError):
                PathGuard.resolve_contained(root, outside)
            self.assertEqual(PathGuard.resolve_contained(root, "trace.jsonl"), (root / "trace.jsonl").resolve())

    def test_sensitive_read_matches_case_variants(self):
        self.assertTrue(PathGuard.is_sensitive_read_path(Path(".ENV")))
        self.assertTrue(PathGuard.is_sensitive_read_path(Path(".Git") / "config"))
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with self.assertRaises(PathGuardError):
                PathGuard.resolve_read_target(workspace, ".ENV")
            with self.assertRaises(PathGuardError):
                PathGuard.resolve_read_target(workspace, "nested/../.env")


if __name__ == "__main__":
    unittest.main()
