import tempfile
import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from onecode.kernel.path_guard import PathGuardError


class ExecutionToolsTests(unittest.TestCase):
    def test_default_registry_exposes_read_and_guarded_tools(self):
        from onecode.kernel.execution_tools import default_tool_registry

        registry = default_tool_registry()

        self.assertEqual(
            registry.names(),
            ["git_commit", "git_diff", "git_status", "glob_files", "list_files", "outline", "patch_text", "read_text", "run_command", "search_text", "write_text"],
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

            with self.assertRaisesRegex(ValueError, "expensive"):
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

    def test_search_text_regex_matches_literal_default_stays_exact(self):
        from onecode.kernel.execution_tools import SearchTextTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "app.py").write_text("needle = 1\n", encoding="utf-8")

            regex_result = SearchTextTool().execute({"query": r"n..dle", "regex": True, "path": "."}, workspace)
            literal_result = SearchTextTool().execute({"query": r"n..dle", "path": "."}, workspace)

        self.assertEqual(regex_result["matches"][0]["path"], "src/app.py")
        self.assertEqual(literal_result["matches"], [])
        self.assertEqual(literal_result["reason"], "search_miss")

    def test_glob_and_outline_report_search_miss(self):
        from onecode.kernel.execution_tools import GlobFilesTool, OutlineTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "app.py").write_text("class Mesh:\n    def run(self):\n        return 1\n", encoding="utf-8")

            found = GlobFilesTool().execute({"pattern": "src/*.py"}, workspace)
            missing = GlobFilesTool().execute({"pattern": "tests/*.py"}, workspace)
            outline = OutlineTool().execute({"path": "src/app.py"}, workspace)
            empty = OutlineTool().execute({"path": "missing.py"}, workspace)

        self.assertEqual(found["paths"], ["src/app.py"])
        self.assertEqual(missing["reason"], "search_miss")
        self.assertEqual([(item["kind"], item["name"]) for item in outline["symbols"]], [("class", "Mesh"), ("function", "run")])
        self.assertEqual(empty["reason"], "search_miss")

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

    def test_unknown_patch_parameters_name_the_accepted_fields(self):
        from onecode.kernel.execution_tools import PatchTextTool

        with self.assertRaises(ValueError) as caught:
            PatchTextTool().plan_action({"path": "stats.py", "rewrite_blocks": "[]"})

        message = str(caught.exception)
        self.assertIn("rewrite_blocks", message)
        self.assertIn("search_block", message)
        self.assertIn("replace_block", message)

    def test_list_files_skips_onecode_metadata(self):
        from onecode.kernel.execution_tools import ListFilesTool

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "src").mkdir()
            (workspace / "src" / "app.py").write_text("x\n", encoding="utf-8")
            pending = workspace / ".onecode" / "pending-cycle"
            pending.mkdir(parents=True)
            (pending / "secret.json").write_text("{}\n", encoding="utf-8")

            listed = ListFilesTool().execute({"path": "."}, workspace)

        self.assertIn("src/app.py", listed["files"])
        self.assertFalse(any(".onecode" in path for path in listed["files"]))

    def test_run_command_scrubs_service_secrets_from_environment_and_evidence(self):
        from onecode.kernel.execution_tools import RunCommandTool

        secret = "service-secret-must-not-persist"
        script = f"import os; print(os.getenv('OPENAI_API_KEY', 'missing')); print('{secret}')"
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"PATH": os.environ.get("PATH", ""), "OPENAI_API_KEY": secret, "ONECODE_RUN_COMMAND_SANDBOX": "host"},
            clear=True,
        ):
            result = RunCommandTool().execute({"argv": [sys.executable, "-c", script]}, Path(tmp))

        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        self.assertIn("missing", result["stdout"])
        self.assertIn("[REDACTED]", serialized)

    def test_run_command_uses_docker_sandbox_when_requested(self):
        from subprocess import CompletedProcess

        from onecode.kernel import execution_tools
        from onecode.kernel.execution_tools import RunCommandTool

        execution_tools._DOCKER_READY = None
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "docker"}
        ), patch(
            "onecode.kernel.sandbox.run_in_reused_sandbox",
            return_value=CompletedProcess(args=[], returncode=0, stdout="ok\n", stderr=""),
        ) as sandbox:
            result = RunCommandTool().execute({"argv": ["python", "-c", "print('ok')"]}, Path(tmp))

        self.assertEqual(result["returncode"], 0)
        self.assertIn("ok", result["stdout"])
        sandbox.assert_called_once()

    def test_run_command_streams_output_and_timeout_reports_http_timeout(self):
        from onecode.kernel.execution_tools import RunCommandTool

        chunks = []
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            streamed = RunCommandTool().execute(
                {"argv": [sys.executable, "-c", "print('one'); print('two')"], "timeout_seconds": 5},
                Path(tmp),
                on_output=chunks.append,
            )
            timed_out = RunCommandTool().execute(
                {"argv": [sys.executable, "-c", "import time; time.sleep(30)"], "timeout_seconds": 1},
                Path(tmp),
            )

        self.assertEqual(streamed["returncode"], 0)
        self.assertEqual("".join(chunks), "one\ntwo\n")
        self.assertEqual(timed_out["status"], "halted")
        self.assertEqual(timed_out["reason"], "http_timeout")

    def test_git_diff_is_read_only_and_commit_records_selected_paths(self):
        from onecode.kernel.execution_tools import GitCommitTool, GitDiffTool

        self.assertFalse(GitDiffTool().requires_approval)
        self.assertTrue(GitCommitTool().requires_approval)
        from onecode.kernel.approval_plans import model_plan_requires_approval
        from onecode.kernel.execution_contracts import GuardrailConfig
        from onecode.kernel.model_provider import ModelExecutionStep, ModelPlan, ModelToolCall

        commit_plan = ModelPlan(
            task="record a",
            execution_steps=[
                ModelExecutionStep(
                    id="commit",
                    description="commit a",
                    tool_calls=[ModelToolCall(tool_name="git_commit", params={"message": "add a", "paths": ["a.txt"]})],
                )
            ],
        )
        self.assertTrue(model_plan_requires_approval(commit_plan))
        self.assertIn("git_commit", GuardrailConfig().require_approval_for)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "onecode@local.test"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.name", "OneCode"], cwd=workspace, check=True)
            (workspace / "a.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "a.txt"], cwd=workspace, check=True)

            diff = GitDiffTool().execute({}, workspace)
            with self.assertRaises(ValueError):
                GitCommitTool().execute({}, workspace)
            committed = GitCommitTool().execute({"message": "add a", "paths": ["a.txt"]}, workspace)
            status = subprocess.run(["git", "status", "--short"], cwd=workspace, capture_output=True, text=True, check=True)

        self.assertIn("a.txt", diff["diff"])
        self.assertEqual(committed["status"], "completed")
        self.assertEqual(status.stdout, "")


if __name__ == "__main__":
    unittest.main()
