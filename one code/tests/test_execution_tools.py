import tempfile
import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
import io
from unittest.mock import patch

from onecode.kernel.path_guard import PathGuardError


class ExecutionToolsTests(unittest.TestCase):
    def test_read_text_preserves_complete_utf8_characters_at_byte_limit(self):
        from onecode.kernel.execution_tools import ReadTextTool

        cases = [("中文", 4, "中", True), ("a\U0001f680z", 4, "a", True),
                 ("中文", 6, "中文", False), ("", 1, "", False), ("ab", 1, "a", True)]
        for content, limit, expected, truncated in cases:
            with self.subTest(content=content, limit=limit), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                (workspace / "text.txt").write_text(content, encoding="utf-8")
                result = ReadTextTool().execute({"path": "text.txt", "max_bytes": limit}, workspace)
                self.assertEqual(result["content"], expected)
                self.assertEqual(result["byte_count"], len(expected.encode("utf-8")))
                self.assertEqual(result["truncated"], truncated)

    def test_read_text_bounds_io_not_just_returned_content(self):
        from onecode.kernel.execution_tools import ReadTextTool

        class BoundedStream(io.BytesIO):
            def read(self, size=-1):
                if not 0 <= size <= 2:
                    raise AssertionError(f"unbounded read: {size}")
                return super().read(size)

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "large.txt").touch()
            stream = BoundedStream(b"x" * (8 * 1024 * 1024))
            with patch.object(Path, "open", return_value=stream):
                result = ReadTextTool().execute({"path": "large.txt", "max_bytes": 1}, workspace)
            self.assertEqual(result["content"], "x")
            self.assertTrue(result["truncated"])

    def test_read_text_still_rejects_invalid_utf8(self):
        from onecode.kernel.execution_tools import ReadTextTool

        for raw, limit in ((b"a\xffz", 2), (b"a\xe4", 2), (b"\xff", 4)):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                (workspace / "text.txt").write_bytes(raw)
                with self.assertRaises(UnicodeDecodeError):
                    ReadTextTool().execute({"path": "text.txt", "max_bytes": limit}, workspace)

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
            (workspace / "environment-link").symlink_to(".env.local")

            searched = SearchTextTool().execute({"query": "needle", "path": "."}, workspace)

            with self.assertRaises(PathGuardError):
                ReadTextTool().execute({"path": ".env.local"}, workspace)
            with self.assertRaises(PathGuardError):
                ReadTextTool().execute({"path": "environment-link"}, workspace)

        self.assertEqual([match["path"] for match in searched["matches"]], ["README.md"])

    def test_search_text_enforces_literal_file_byte_and_depth_limits(self):
        from onecode.kernel.execution_tools import SearchTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "top").mkdir()
            (workspace / "top" / "small.txt").write_text("visible needle\n", encoding="utf-8")
            (workspace / "top" / "large.txt").write_text("x" * 200 + " needle\n", encoding="utf-8")
            (workspace / "deep" / "child").mkdir(parents=True)
            (workspace / "deep" / "child" / "hidden.txt").write_text("needle\n", encoding="utf-8")

            result = SearchTextTool().execute(
                {
                    "query": "needle",
                    "path": ".",
                    "max_depth": 2,
                    "max_files": 10,
                    "max_file_bytes": 50,
                    "max_total_bytes": 100,
                },
                workspace,
            )

            with self.assertRaisesRegex(ValueError, "literal"):
                SearchTextTool().execute({"query": "(a+)+$", "regex": True}, workspace)

        self.assertEqual([match["path"] for match in result["matches"]], ["top/small.txt"])
        self.assertLessEqual(result["scanned_file_count"], 10)
        self.assertLessEqual(result["scanned_bytes"], 100)
        self.assertTrue(result["truncated"])

    def test_search_text_processes_collected_files_before_reporting_file_limit(self):
        from onecode.kernel.execution_tools import SearchTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for name in ("a.txt", "b.txt", "c.txt"):
                (workspace / name).write_text("needle\n", encoding="utf-8")

            result = SearchTextTool().execute(
                {"query": "needle", "path": ".", "max_depth": 1, "max_files": 2},
                workspace,
            )

        self.assertEqual([match["path"] for match in result["matches"]], ["a.txt", "b.txt"])
        self.assertEqual(result["scanned_file_count"], 2)
        self.assertTrue(result["truncated"])

    def test_git_status_disables_repository_fsmonitor_hook(self):
        from onecode.kernel.execution_tools import GitStatusTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            marker = workspace / "fsmonitor-ran"
            hook = workspace / "fsmonitor.sh"
            hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nprintf '\\n'\n", encoding="utf-8")
            hook.chmod(0o755)
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
            subprocess.run(
                ["git", "config", "core.fsmonitor", str(hook)],
                cwd=workspace,
                capture_output=True,
                check=True,
            )

            result = GitStatusTool().execute({}, workspace)
            hook_ran = marker.exists()

        self.assertFalse(hook_ran)
        self.assertTrue(any("fsmonitor.sh" in entry for entry in result["entries"]))

    def test_run_command_requires_argv(self):
        from onecode.kernel.execution_tools import RunCommandTool

        with self.assertRaisesRegex(ValueError, "argv"):
            RunCommandTool().plan_action({"command": "pwd && rm file"})

    def test_run_command_scrubs_service_secrets_from_environment_and_evidence(self):
        from onecode.kernel.execution_tools import RunCommandTool

        secret = "service-secret-must-not-persist"
        script = f"import os; print(os.getenv('OPENAI_API_KEY', 'missing')); print('{secret}')"
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PATH": os.environ.get("PATH", ""), "OPENAI_API_KEY": secret},
            clear=True,
        ):
            result = RunCommandTool().execute({"argv": [sys.executable, "-c", script]}, Path(tmp))

        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertIn("missing", result["stdout"])
        self.assertIn("[REDACTED]", serialized)


if __name__ == "__main__":
    unittest.main()
