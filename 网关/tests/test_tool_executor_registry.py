import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.kernel_policy import KERNEL_POLICIES
from agent_skill_dictionary.tool_executor_registry import execute_registered_tool, registered_tool_names


class ToolExecutorRegistryTest(unittest.TestCase):
    def test_registry_declares_every_kernel_policy_tool(self):
        declared = registered_tool_names()
        missing = {
            code: sorted(set(policy.allowed_tools) - declared)
            for code, policy in KERNEL_POLICIES.items()
            if set(policy.allowed_tools) - declared
        }

        self.assertEqual(missing, {})

    def test_registry_executes_readonly_grep_without_writing_workspace(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "app.py").write_text("VALUE = 42\n", encoding="utf-8")

            result = execute_registered_tool("grep_code", {"pattern": "value"}, workspace)

            self.assertEqual(result["exit_code"], 0)
            self.assertIn("app.py:1:VALUE = 42", result["stdout"])
            self.assertEqual((workspace / "app.py").read_text(encoding="utf-8"), "VALUE = 42\n")

    def test_registry_executes_native_inspect_card_as_compact_readonly_tool(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "sync_node.py").write_text(
                "import httpx\n\nasync def sync_inventory():\n    while True:\n        return None\n",
                encoding="utf-8",
            )

            result = execute_registered_tool(
                "native_inspect_card",
                {"target": "sync_node.py", "max_chars": 500},
                workspace,
            )

            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["tool"], "native_inspect_card")
            self.assertIn("[State]: 101-INSPECT", result["stdout"])
            self.assertIn("sync_inventory", result["stdout"])
            self.assertIn("while True", result["stdout"])
            self.assertLessEqual(len(result["stdout"]), 500)
            self.assertEqual((workspace / "sync_node.py").read_text(encoding="utf-8").splitlines()[0], "import httpx")

    def test_registry_scoped_edit_rejects_path_escape(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = execute_registered_tool(
                "edit_scoped_file",
                {"path": "../escape.py", "content": "print('bad')\n"},
                workspace,
            )

            self.assertNotEqual(result["exit_code"], 0)
            self.assertIn("workspace", result["stderr"])

    def test_registry_run_command_tool_returns_timeout_result(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = execute_registered_tool(
                "run_pytest",
                {
                    "command": [
                        "python3",
                        "-c",
                        "import time; print('started'); time.sleep(5)",
                    ],
                    "timeout_seconds": 1,
                },
                workspace,
            )

            self.assertEqual(result["exit_code"], 124)
            self.assertIn("TIMEOUT", result["stderr"])
            self.assertEqual(result["tool"], "run_pytest")

    def test_registry_run_pytest_timeout_includes_compact_failure_summary(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            result = execute_registered_tool(
                "run_pytest",
                {
                    "command": [
                        "python3",
                        "-c",
                        (
                            "import time\n"
                            "while True:\n"
                            " print('DEBUG LEDGER TRACE: sync_node.py:40 in sync_inventory ConnectError', flush=True)\n"
                            " time.sleep(0.001)\n"
                        ),
                    ],
                    "timeout_seconds": 1,
                },
                workspace,
            )

            self.assertEqual(result["exit_code"], 124)
            self.assertIn("failure_summary", result)
            self.assertIn("sync_node.py:40", result["failure_summary"])
            self.assertLessEqual(len(result["failure_summary"]), 900)


if __name__ == "__main__":
    unittest.main()
