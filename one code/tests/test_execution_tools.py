import tempfile
import unittest
from pathlib import Path

from onecode.kernel.path_guard import PathGuardError


class ExecutionToolsTests(unittest.TestCase):
    def test_default_registry_exposes_read_and_guarded_tools(self):
        from onecode.kernel.execution_tools import default_tool_registry

        registry = default_tool_registry()

        self.assertEqual(
            registry.names(),
            ["git_status", "list_files", "patch_text", "read_text", "run_command", "search_text", "write_text"],
        )
        self.assertFalse(registry.get("read_text").requires_approval)
        self.assertTrue(registry.get("run_command").requires_approval)

    def test_read_text_returns_bounded_workspace_content(self):
        from onecode.kernel.execution_tools import ReadTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("one\ntwo\nthree\n", encoding="utf-8")

            result = ReadTextTool().execute({"path": "README.md", "max_lines": 2}, workspace)

        self.assertEqual(result["content"], "one\ntwo\n")
        self.assertTrue(result["truncated"])

    def test_read_text_rejects_workspace_escape(self):
        from onecode.kernel.execution_tools import ReadTextTool

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PathGuardError):
                ReadTextTool().execute({"path": "../secret"}, Path(tmp))

    def test_list_and_search_are_bounded(self):
        from onecode.kernel.execution_tools import ListFilesTool, SearchTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "a.py").write_text("needle\n", encoding="utf-8")
            (workspace / "src" / "b.py").write_text("needle\nneedle\n", encoding="utf-8")

            listed = ListFilesTool().execute({"path": "src", "max_entries": 1}, workspace)
            searched = SearchTextTool().execute({"query": "needle", "path": "src", "max_matches": 2}, workspace)

        self.assertEqual(len(listed["files"]), 1)
        self.assertTrue(listed["truncated"])
        self.assertEqual(len(searched["matches"]), 2)
        self.assertTrue(searched["truncated"])

    def test_list_files_accepts_workspace_root(self):
        from onecode.kernel.execution_tools import ListFilesTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("project\n", encoding="utf-8")

            listed = ListFilesTool().execute({"path": ".", "max_entries": 10}, workspace)

        self.assertEqual(listed["path"], ".")
        self.assertEqual(listed["files"], ["README.md"])

    def test_list_files_skips_symlinks_outside_workspace(self):
        from onecode.kernel.execution_tools import ListFilesTool, ReadTextTool

        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            workspace = Path(tmp)
            outside = Path(outside_tmp) / "secret.txt"
            outside.write_text("secret\n", encoding="utf-8")
            (workspace / "README.md").write_text("project\n", encoding="utf-8")
            (workspace / "external.txt").symlink_to(outside)

            listed = ListFilesTool().execute({"path": ".", "max_entries": 10}, workspace)

            with self.assertRaises(PathGuardError):
                ReadTextTool().execute({"path": "external.txt"}, workspace)

        self.assertEqual(listed["files"], ["README.md"])

    def test_root_search_skips_environment_secrets(self):
        from onecode.kernel.execution_tools import ReadTextTool, SearchTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("visible-needle\n", encoding="utf-8")
            (workspace / ".env.local").write_text("TOKEN=secret-needle\n", encoding="utf-8")

            searched = SearchTextTool().execute({"query": "needle", "path": "."}, workspace)

            with self.assertRaises(PathGuardError):
                ReadTextTool().execute({"path": ".env.local"}, workspace)

        self.assertEqual([match["path"] for match in searched["matches"]], ["README.md"])

    def test_run_command_requires_argv(self):
        from onecode.kernel.execution_tools import RunCommandTool

        with self.assertRaisesRegex(ValueError, "argv"):
            RunCommandTool().plan_action({"command": "pwd && rm file"})


if __name__ == "__main__":
    unittest.main()
