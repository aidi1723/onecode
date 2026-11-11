import tempfile
import unittest
from pathlib import Path

from onecode.kernel.execution_scope import (
    ExecutionScope,
    ToolCapabilityPolicy,
    is_destructive_command,
)
from onecode.kernel.model_loop import run_model_task
from onecode.kernel.phased_terminal import run_phased_terminal_session
from onecode.kernel.terminal_loop import (
    TerminalAction,
    TerminalSession,
)


class ExecutionScopeTests(unittest.TestCase):
    def test_destructive_command_detection(self) -> None:
        self.assertTrue(is_destructive_command(["rm", "-rf", "/tmp/test"]))
        self.assertTrue(is_destructive_command(["bash", "-c", "rm -f file.txt"]))
        self.assertTrue(is_destructive_command(["git", "reset", "--hard", "HEAD~1"]))
        self.assertTrue(is_destructive_command(["git", "clean", "-fdx"]))
        self.assertTrue(is_destructive_command(["kill", "-9", "1234"]))
        self.assertFalse(is_destructive_command(["ls", "-la"]))
        self.assertFalse(is_destructive_command(["git", "status"]))
        self.assertFalse(is_destructive_command(["pytest", "testing/test_something.py"]))

    def test_read_only_scope_allows_safe_actions(self) -> None:
        dec_read = ToolCapabilityPolicy.evaluate(ExecutionScope.READ_ONLY, "read_file")
        self.assertTrue(dec_read.allowed)
        self.assertEqual(dec_read.hexagram_code, 63)

        dec_finish = ToolCapabilityPolicy.evaluate(ExecutionScope.READ_ONLY, "finish")
        self.assertTrue(dec_finish.allowed)

        dec_cmd = ToolCapabilityPolicy.evaluate(
            ExecutionScope.READ_ONLY,
            "command",
            ["git", "status"],
            is_inspection=True,
        )
        self.assertTrue(dec_cmd.allowed)

    def test_read_only_scope_blocks_modifications(self) -> None:
        dec_patch = ToolCapabilityPolicy.evaluate(ExecutionScope.READ_ONLY, "patch")
        self.assertFalse(dec_patch.allowed)
        self.assertEqual(dec_patch.reason, "scope_violation")
        self.assertEqual(dec_patch.hexagram_code, 39)
        self.assertIn("forbidden in READ_ONLY execution scope", dec_patch.stderr)

        dec_mut_cmd = ToolCapabilityPolicy.evaluate(
            ExecutionScope.READ_ONLY,
            "command",
            ["pytest", "-q"],
            is_inspection=False,
        )
        self.assertFalse(dec_mut_cmd.allowed)
        self.assertEqual(dec_mut_cmd.reason, "scope_violation")
        self.assertEqual(dec_mut_cmd.hexagram_code, 39)

    def test_patch_guarded_scope_allows_patches_and_blocks_destructive(self) -> None:
        dec_patch = ToolCapabilityPolicy.evaluate(ExecutionScope.PATCH_GUARDED, "patch")
        self.assertTrue(dec_patch.allowed)

        dec_safe_cmd = ToolCapabilityPolicy.evaluate(
            ExecutionScope.PATCH_GUARDED,
            "command",
            ["pytest", "-q"],
        )
        self.assertTrue(dec_safe_cmd.allowed)

        dec_dest_cmd = ToolCapabilityPolicy.evaluate(
            ExecutionScope.PATCH_GUARDED,
            "command",
            ["rm", "-rf", "src/legacy"],
        )
        self.assertFalse(dec_dest_cmd.allowed)
        self.assertEqual(dec_dest_cmd.reason, "destructive_command_denied")
        self.assertEqual(dec_dest_cmd.hexagram_code, 39)

    def test_terminal_session_read_only_enforcement(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            src_file = workspace / "module.py"
            src_file.write_text("def hello(): pass\n", encoding="utf-8")

            session = TerminalSession(
                workspace,
                task="Inspect code in read only mode",
                execution_scope=ExecutionScope.READ_ONLY,
                require_modification=False,
            )

            # 1. Attempt patch -> blocked by scope
            patch_act = TerminalAction(
                action_type="patch",
                path="module.py",
                search_block="def hello(): pass\n",
                replace_block="def hello(): return 42\n",
            )
            obs_patch = session.execute_action(patch_act)
            self.assertEqual(obs_patch.status, "blocked")
            self.assertEqual(obs_patch.reason, "scope_violation")
            self.assertEqual(session.steps[-1].hexagram_code, 39)

            # 2. Attempt non-inspection command -> blocked by scope
            cmd_act = TerminalAction(
                action_type="command",
                command=("pytest", "-q"),
            )
            obs_cmd = session.execute_action(cmd_act)
            self.assertEqual(obs_cmd.status, "blocked")
            self.assertEqual(obs_cmd.reason, "scope_violation")
            self.assertEqual(session.steps[-1].hexagram_code, 39)

            # 3. Read file -> allowed
            read_act = TerminalAction(
                action_type="read_file",
                path="module.py",
                start_line=1,
                end_line=5,
            )
            obs_read = session.execute_action(read_act)
            self.assertEqual(obs_read.status, "ok")
            self.assertIn("def hello(): pass", obs_read.output)

    def test_run_phased_session_bounds_phase1_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "src").mkdir()
            target_file = workspace / "src" / "calc.py"
            target_file.write_text("def add(a, b): return 0\n", encoding="utf-8")

            call_count = 0

            def mock_provider(prompt: str) -> str:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Phase 1: Try patch -> will be blocked by read_only scope!
                    return '{"action_type": "patch", "path": "src/calc.py", "search_block": "def add(a, b): return 0\\n", "replace_block": "def add(a, b): return a + b\\n"}'
                if call_count == 2:
                    # Phase 1: Read file -> allowed
                    return '{"action_type": "read_file", "path": "src/calc.py", "start_line": 1, "end_line": 5}'
                if call_count == 3:
                    # Phase 1: Finish with distilled plan
                    return '{"action_type": "finish", "explanation": "Diagnosed: replace return 0 with return a + b in src/calc.py"}'
                if call_count == 4:
                    # Phase 2: Patch allowed under full_terminal
                    return '{"action_type": "patch", "path": "src/calc.py", "search_block": "def add(a, b): return 0\\n", "replace_block": "def add(a, b): return a + b\\n"}'
                return '{"action_type": "finish", "explanation": "Verification complete."}'

            result = run_phased_terminal_session(
                task="Fix addition calculation",
                workspace=workspace,
                provider=mock_provider,
                max_turns=10,
                plan_turns=3,
                auto_approved_for_eval=True,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(target_file.read_text(encoding="utf-8"), "def add(a, b): return a + b\n")

    def test_run_model_task_with_scoped_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "hello.py").write_text("msg = 'hi'\n", encoding="utf-8")

            def mock_provider(prompt: str) -> str:
                return '{"action_type": "read_file", "path": "hello.py", "start_line": 1, "end_line": 2}'

            res = run_model_task(
                task="Inspect hello.py in read-only mode",
                workspace=workspace,
                provider=mock_provider,
                agent_mode="terminal",
                max_turns=1,
                execution_scope="read_only",
                api_key="mock-key",
            )
            self.assertEqual(res.get("status"), "halted")
            self.assertEqual(res.get("reason"), "turn_limit_exhausted")
            steps = res.get("terminal_steps", [])
            self.assertTrue(len(steps) >= 1)
            self.assertEqual(steps[0]["action"]["action_type"], "read_file")
            self.assertEqual(steps[0]["observation"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
