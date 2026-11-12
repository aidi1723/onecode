"""Tests for open-ended multi-step terminal loop and anti-tamper governance."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from onecode.kernel.terminal_loop import (
    TerminalAction,
    TerminalObservation,
    TerminalSession,
    TerminalStep,
    _parse_model_action,
    run_terminal_session,
)


class TestTerminalDataClasses(unittest.TestCase):
    def test_terminal_action_dict_roundtrip(self) -> None:
        act = TerminalAction(
            action_type="patch",
            path="src/module.py",
            search_block="foo = 1",
            replace_block="foo = 2",
            start_line=10,
            end_line=20,
            explanation="Fix bug",
        )
        d = act.to_dict()
        self.assertEqual(d["action_type"], "patch")
        self.assertEqual(d["path"], "src/module.py")
        self.assertEqual(d["search_block"], "foo = 1")
        self.assertEqual(d["replace_block"], "foo = 2")
        self.assertEqual(d["start_line"], 10)
        self.assertEqual(d["end_line"], 20)
        self.assertEqual(d["explanation"], "Fix bug")

        restored = TerminalAction.from_dict(d)
        self.assertEqual(restored, act)

    def test_terminal_action_from_dict_aliases(self) -> None:
        raw = {
            "action": "command",
            "cmd": "pytest -v",
            "reason": "Run suite",
        }
        act = TerminalAction.from_dict(raw)
        self.assertEqual(act.action_type, "command")
        self.assertEqual(act.command, ("pytest", "-v"))
        self.assertEqual(act.explanation, "Run suite")

    def test_terminal_observation_and_step_dict(self) -> None:
        obs = TerminalObservation(
            action_type="command",
            status="ok",
            exit_code=0,
            stdout="hello\n" * 1000,
            stderr="warning\n",
            output="done",
        )
        d_obs = obs.to_dict()
        self.assertEqual(d_obs["status"], "ok")
        self.assertLessEqual(len(d_obs["stdout"]), 4000)

        step = TerminalStep(
            turn_index=1,
            action=TerminalAction(action_type="finish"),
            observation=obs,
            hexagram_code=63,
            timestamp_ns=123456789,
        )
        d_step = step.to_dict()
        self.assertEqual(d_step["turn_index"], 1)
        self.assertEqual(d_step["hexagram_code"], 63)
        self.assertEqual(d_step["timestamp_ns"], 123456789)

    def test_parse_model_action_varieties(self) -> None:
        # Markdown wrapped JSON
        text1 = """Here is my plan:
```json
{
  "action_type": "patch",
  "path": "src/core.py",
  "search_block": "a = 1",
  "replace_block": "a = 2"
}
```
"""
        act1 = _parse_model_action(text1)
        self.assertEqual(act1.action_type, "patch")
        self.assertEqual(act1.path, "src/core.py")

        # Plain JSON
        text2 = '{"action_type": "read_file", "path": "src/main.py", "start_line": 5}'
        act2 = _parse_model_action(text2)
        self.assertEqual(act2.action_type, "read_file")
        self.assertEqual(act2.start_line, 5)

        # Invalid JSON fallback
        text3 = "I do not know what to do."
        act3 = _parse_model_action(text3)
        self.assertEqual(act3.action_type, "command")
        self.assertEqual(act3.command, ("git", "status"))


class TestTerminalSessionExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        self.src_file = self.workspace / "src" / "app.py"
        self.src_file.write_text("def solve():\n    return 41\n", encoding="utf-8")

        self.test_file = self.workspace / "tests" / "test_app.py"
        self.test_file.write_text("def test_solve():\n    assert solve() == 42\n", encoding="utf-8")

        self.session = TerminalSession(self.workspace, "Fix solve() to return 42")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_read_file_success_and_line_clamping(self) -> None:
        act = TerminalAction(action_type="read_file", path="src/app.py", start_line=1, end_line=10)
        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "ok")
        self.assertIn("def solve():", obs.output)
        self.assertIn("1 | def solve():", obs.output)

    def test_read_file_errors_and_sensitive_guard(self) -> None:
        # Empty path
        obs1 = self.session.execute_action(TerminalAction(action_type="read_file", path=""))
        self.assertEqual(obs1.status, "error")

        # Nonexistent file
        obs2 = self.session.execute_action(TerminalAction(action_type="read_file", path="src/missing.py"))
        self.assertEqual(obs2.status, "error")
        self.assertEqual(obs2.reason, "file_not_found")

        # Sensitive path
        obs3 = self.session.execute_action(TerminalAction(action_type="read_file", path=".git/config"))
        self.assertEqual(obs3.status, "blocked")
        self.assertEqual(obs3.reason, "sensitive_read_denied")

        # Path traversal
        obs4 = self.session.execute_action(TerminalAction(action_type="read_file", path="../../etc/passwd"))
        self.assertEqual(obs4.status, "blocked")
        self.assertEqual(obs4.reason, "sensitive_read_denied")

    def test_command_workspace_escape_blocked(self) -> None:
        obs = self.session.execute_action(
            TerminalAction(action_type="command", command=("cat", "../secret.txt"))
        )
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(obs.reason, "workspace_escape_denied")
        self.assertEqual(self.session.steps[-1].hexagram_code, 40)

    def test_patch_success(self) -> None:
        act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="    return 41",
            replace_block="    return 42",
        )
        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "ok")
        self.assertEqual(self.src_file.read_text(encoding="utf-8"), "def solve():\n    return 42\n")

    def test_patch_anti_tamper_blocks_test_modifications(self) -> None:
        # Python tests/
        act = TerminalAction(
            action_type="patch",
            path="tests/test_app.py",
            search_block="assert solve() == 42",
            replace_block="assert solve() == 41",
        )
        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "blocked")
        self.assertEqual(obs.reason, "preset_test_immutable")
        self.assertIn("Anti-tamper protection active", obs.stderr)
        self.assertIn("assert solve() == 42", self.test_file.read_text(encoding="utf-8"))

        # Multi-language test paths (Go, TypeScript, Rust, Python test_*.py)
        for lang_test_path in [
            "pkg/service/order_test.go",
            "src/components/button.test.tsx",
            "src/services/api.spec.ts",
            "src/__tests__/utils.js",
            "src/tests.rs",
            "tests/integration_test.rs",
            "app/test_worker.py",
        ]:
            act_lang = TerminalAction(
                action_type="patch",
                path=lang_test_path,
                search_block="assert true",
                replace_block="assert false",
            )
            obs_lang = self.session.execute_action(act_lang)
            self.assertEqual(obs_lang.status, "blocked", f"Should block patch on {lang_test_path}")
            self.assertEqual(obs_lang.reason, "preset_test_immutable")
            self.assertIn("Anti-tamper protection active", obs_lang.stderr)

    def test_command_execution_and_anti_tamper(self) -> None:
        from unittest.mock import patch
        # Safe command
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            act_ok = TerminalAction(action_type="command", command=("python3", "-c", "print('hello_onecode')"))
            obs_ok = self.session.execute_action(act_ok)
            self.assertEqual(obs_ok.status, "ok")
            self.assertIn("hello_onecode", obs_ok.stdout)

        # Anti-tamper command attempting to delete or overwrite tests across languages
        for tamper_cmd in [
            ("rm", "-rf", "tests/test_app.py"),
            ("rm", "-f", "pkg/service/order_test.go"),
            ("unlink", "src/services/api.spec.ts"),
            ("sed", "-i", "s/fail/pass/", "src/components/button.test.tsx"),
            ("tee", "src/tests.rs"),
            ("bash", "-c", "echo ok > tests/test_smoke.py"),
            ("sh", "-c", "echo void > pkg/order_test.go"),
        ]:
            act_tamper = TerminalAction(action_type="command", command=tamper_cmd)
            obs_tamper = self.session.execute_action(act_tamper)
            self.assertEqual(obs_tamper.status, "blocked", f"Should block command {tamper_cmd}")
            self.assertEqual(obs_tamper.reason, "preset_test_immutable")

    def test_read_only_sed_can_print_a_test_file(self) -> None:
        from unittest.mock import patch

        target = self.workspace / "astropy" / "modeling" / "tests" / "test_separable.py"
        target.parent.mkdir(parents=True)
        target.write_text("def test_separable():\n    assert True\n", encoding="utf-8")
        self.session = TerminalSession(self.workspace, "Fix separability")
        printed = TerminalAction(
            action_type="command",
            command=(
                "bash",
                "-lc",
                "nl -ba astropy/modeling/separable.py | sed -n '219,330p'; "
                "echo '--- tests ---'; "
                "sed -n '1,240p' astropy/modeling/tests/test_separable.py",
            ),
        )
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            obs = self.session.execute_action(printed)
        self.assertNotEqual(obs.reason, "preset_test_immutable")
        self.assertEqual(obs.status, "ok")
        self.assertIn("def test_separable():", obs.stdout)
        self.assertEqual(target.read_text(encoding="utf-8"), "def test_separable():\n    assert True\n")

        inplace = TerminalAction(
            action_type="command",
            command=(
                "bash",
                "-lc",
                "sed --in-place 's/assert True/assert False/' astropy/modeling/tests/test_separable.py",
            ),
        )
        blocked = self.session.execute_action(inplace)
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(blocked.reason, "preset_test_immutable")
        self.assertEqual(target.read_text(encoding="utf-8"), "def test_separable():\n    assert True\n")

        inplace_trailing = TerminalAction(
            action_type="command",
            command=(
                "bash",
                "-lc",
                "sed 's/assert True/assert False/' astropy/modeling/tests/test_separable.py -i",
            ),
        )
        blocked_trailing = self.session.execute_action(inplace_trailing)
        self.assertEqual(blocked_trailing.status, "blocked")
        self.assertEqual(blocked_trailing.reason, "preset_test_immutable")

        direct_argv = TerminalAction(
            action_type="command",
            command=("sed", "-i", "s/assert True/assert False/", "astropy/modeling/tests/test_separable.py"),
        )
        blocked_direct = self.session.execute_action(direct_argv)
        self.assertEqual(blocked_direct.status, "blocked")
        self.assertEqual(blocked_direct.reason, "preset_test_immutable")

    def test_stagnation_detection(self) -> None:
        from unittest.mock import patch
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            # Failing command
            failing_cmd = ("python3", "-c", "import sys; sys.exit(1)")
            act = TerminalAction(action_type="command", command=failing_cmd)

            obs1 = self.session.execute_action(act)
            self.assertEqual(obs1.status, "error")

            obs2 = self.session.execute_action(act)
            self.assertEqual(obs2.status, "error")

            # Third identical failing command triggers stagnation halt
            obs3 = self.session.execute_action(act)
            self.assertEqual(obs3.status, "halted")
            self.assertEqual(obs3.reason, "stagnation_loop")

    def test_read_stagnation_detection(self) -> None:
        act = TerminalAction(action_type="read_file", path="src/app.py", start_line=1, end_line=10)
        obs1 = self.session.execute_action(act)
        self.assertEqual(obs1.status, "ok")
        self.assertIn("def solve():", obs1.output)

        obs2 = self.session.execute_action(act)
        self.assertEqual(obs2.status, "error")
        self.assertEqual(obs2.reason, "repeated_read")
        self.assertIn("def solve():", obs2.output)
        self.assertIn("already read this line range (or exceeded consecutive reads) of 'src/app.py'", obs2.stderr)
        self.assertIn("redundant or sliding reads", obs2.stderr)
        self.assertIn("print-only reproduction", obs2.stderr)
        self.assertIn("next redundant read of this file halts", obs2.stderr)
        self.assertEqual(self.session.steps[-1].hexagram_code, 39)
        prompt = self.session.render_turn_prompt()
        self.assertIn("already read this line range (or exceeded consecutive reads) of 'src/app.py'", prompt)
        self.assertIn("def solve():", prompt)

        obs3 = self.session.execute_action(act)
        self.assertEqual(obs3.status, "halted")
        self.assertEqual(obs3.reason, "stagnation_loop")
        self.assertIn("Lyapunov Stagnation Guard", obs3.stderr)
        self.assertEqual(self.session.steps[-1].hexagram_code, 40)

    def test_sliding_read_windows_count_as_the_same_file(self) -> None:
        first = TerminalAction(action_type="read_file", path="src/app.py", start_line=1, end_line=1)
        second = TerminalAction(action_type="read_file", path="src/app.py", start_line=2, end_line=2)
        third = TerminalAction(action_type="read_file", path="src/app.py", start_line=1, end_line=2)
        self.assertEqual(self.session.execute_action(first).status, "ok")
        warned = self.session.execute_action(second)
        self.assertEqual(warned.status, "error")
        self.assertEqual(warned.reason, "repeated_read")
        self.assertIn("return 41", warned.output)
        halted = self.session.execute_action(third)
        self.assertEqual(halted.status, "halted")
        self.assertEqual(halted.reason, "stagnation_loop")

    def test_sequential_large_file_pagination_is_allowed(self) -> None:
        large_file = self.workspace / "src" / "large.py"
        large_file.write_text(
            "\n".join(f"line_{i} = {i}" for i in range(1, 351)) + "\n",
            encoding="utf-8",
        )
        obs1 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=1, end_line=120)
        )
        obs2 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=121, end_line=240)
        )
        obs3 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=241, end_line=350)
        )
        self.assertEqual(obs1.status, "ok")
        self.assertEqual(obs2.status, "ok")
        self.assertEqual(obs3.status, "ok")
        self.assertIn("line_350 = 350", obs3.output)

    def test_redundant_large_sliding_window_read_still_halts(self) -> None:
        large_file = self.workspace / "src" / "large.py"
        large_file.write_text(
            "\n".join(f"line_{i} = {i}" for i in range(1, 351)) + "\n",
            encoding="utf-8",
        )
        obs1 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=1, end_line=200)
        )
        obs2 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=2, end_line=201)
        )
        obs3 = self.session.execute_action(
            TerminalAction(action_type="read_file", path="src/large.py", start_line=3, end_line=202)
        )
        self.assertEqual(obs1.status, "ok")
        self.assertEqual(obs2.status, "error")
        self.assertEqual(obs2.reason, "repeated_read")
        self.assertEqual(obs3.status, "halted")
        self.assertEqual(obs3.reason, "stagnation_loop")

    def test_another_file_or_command_resets_the_read_stall(self) -> None:
        from unittest.mock import patch

        other = self.workspace / "pkg.py"
        other.write_text("value = 1\n", encoding="utf-8")
        app = TerminalAction(action_type="read_file", path="src/app.py", start_line=1, end_line=2)
        other_read = TerminalAction(action_type="read_file", path="pkg.py", start_line=1, end_line=1)
        self.assertEqual(self.session.execute_action(app).status, "ok")
        self.assertEqual(self.session.execute_action(other_read).status, "ok")
        self.assertEqual(self.session.execute_action(app).status, "ok")

        self.assertEqual(self.session.execute_action(app).status, "error")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            command = TerminalAction(action_type="command", command=("python3", "-c", "print('repro')"))
            ran = self.session.execute_action(command)
        self.assertEqual(ran.status, "ok")
        self.assertEqual(self.session.execute_action(app).status, "ok")

    def test_patch_missing_src_prefix_names_the_existing_file(self) -> None:
        target = self.workspace / "astropy" / "modeling" / "separable.py"
        target.parent.mkdir(parents=True)
        target.write_text("cright = 1\n", encoding="utf-8")
        act = TerminalAction(
            action_type="patch",
            path="src/astropy/modeling/separable.py",
            search_block="cright = 1",
            replace_block="cright = right",
        )
        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "error")
        self.assertEqual(obs.reason, "patch_target_not_found")
        self.assertEqual(
            obs.stderr,
            "File 'src/astropy/modeling/separable.py' does not exist, but "
            "'astropy/modeling/separable.py' exists in the workspace. "
            "Did you mean 'astropy/modeling/separable.py'? Do not add a 'src/' prefix.",
        )
        self.assertEqual(target.read_text(encoding="utf-8"), "cright = 1\n")
        self.assertIn("Did you mean 'astropy/modeling/separable.py'", self.session.render_turn_prompt())

        dotted = TerminalAction(
            action_type="patch",
            path="./src/astropy/modeling/separable.py",
            search_block="cright = 1",
            replace_block="cright = right",
        )
        dotted_obs = self.session.execute_action(dotted)
        self.assertIn("Did you mean 'astropy/modeling/separable.py'", dotted_obs.stderr)

        absent = TerminalAction(
            action_type="patch",
            path="src/missing.py",
            search_block="x = 1",
            replace_block="x = 2",
        )
        absent_obs = self.session.execute_action(absent)
        self.assertEqual(absent_obs.stderr, "patch_target_not_found")
        self.assertNotIn("Did you mean", absent_obs.stderr)

    def test_collection_return_patch_asks_for_membership_checks(self) -> None:
        target = self.workspace / "src" / "opt.py"
        target.write_text(
            "def inherited_members_option(arg):\n"
            "    if arg is None:\n"
            "        return 'object'\n"
            "    return arg\n"
            "def consume(name, option):\n"
            "    return name == option\n",
            encoding="utf-8",
        )
        widened = TerminalAction(
            action_type="patch",
            path="src/opt.py",
            search_block="        return 'object'",
            replace_block="        return {'object'}",
        )
        self.assertEqual(self.session.execute_action(widened).status, "ok")
        prompt = self.session.render_turn_prompt()
        self.assertIn("membership checks ('in')", prompt)
        self.assertNotIn("Proceed to run verification tests with 'command'", prompt)

        narrowed = TerminalAction(
            action_type="patch",
            path="src/opt.py",
            search_block="    return name == option",
            replace_block="    return name in option",
        )
        self.assertEqual(self.session.execute_action(narrowed).status, "ok")
        later = self.session.render_turn_prompt()
        self.assertIn("Proceed to run verification tests with 'command'", later)
        self.assertNotIn("membership checks ('in')", later)

    def test_missing_test_command_tells_the_model_not_to_retry(self) -> None:
        from unittest.mock import patch

        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            missing = TerminalAction(
                action_type="command",
                command=("python3", "-c", "import sys; print('no tests ran'); sys.exit(4)"),
            )
            observed = self.session.execute_action(missing)
        self.assertEqual(observed.exit_code, 4)
        prompt = self.session.render_turn_prompt()
        self.assertIn("Do not retry it", prompt)
        self.assertIn("exit code 4", prompt)

    def test_finish_action(self) -> None:
        act = TerminalAction(action_type="finish", explanation="All tests pass successfully.")
        obs_blocked = self.session.execute_action(act)
        self.assertEqual(obs_blocked.status, "error")
        self.assertEqual(obs_blocked.reason, "unmodified_workspace")
        self.assertFalse(self.session.is_finished)

        patch_act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="return 41",
            replace_block="return 42",
        )
        self.session.execute_action(patch_act)

        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "ok")
        self.assertTrue(self.session.is_finished)
        self.assertEqual(self.session.finish_explanation, "All tests pass successfully.")

    def test_post_patch_successful_command_guides_autonomous_finish(self) -> None:
        from unittest.mock import patch

        patch_act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="return 41",
            replace_block="return 42",
        )
        self.assertEqual(self.session.execute_action(patch_act).status, "ok")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            verify_cmd = TerminalAction(
                action_type="command",
                command=("python3", "-c", "print('all good'); exit(0)"),
            )
            self.assertEqual(self.session.execute_action(verify_cmd).status, "ok")
        prompt = self.session.render_turn_prompt()
        self.assertIn("Verification succeeded (exit code 0)", prompt)
        self.assertIn("Submit 'finish' now", prompt)

    def test_post_patch_inspection_command_does_not_trigger_premature_finish(self) -> None:
        from unittest.mock import patch

        patch_act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="return 41",
            replace_block="return 42",
        )
        self.assertEqual(self.session.execute_action(patch_act).status, "ok")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            inspect_cmd = TerminalAction(
                action_type="command",
                command=("bash", "-lc", "sed -n '1,10p' src/app.py"),
            )
            self.assertEqual(self.session.execute_action(inspect_cmd).status, "ok")
        prompt = self.session.render_turn_prompt()
        self.assertIn("Inspection command completed (exit code 0)", prompt)
        self.assertIn("apply them with 'patch'", prompt)
        self.assertNotIn("Submit 'finish' now", prompt)

    def test_post_patch_failing_command_instructs_adjustment(self) -> None:
        from unittest.mock import patch

        patch_act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="return 41",
            replace_block="return 42",
        )
        self.assertEqual(self.session.execute_action(patch_act).status, "ok")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            failing_cmd = TerminalAction(
                action_type="command",
                command=("python3", "-c", "print('assertion error'); exit(1)"),
            )
            self.assertEqual(self.session.execute_action(failing_cmd).status, "error")
        prompt = self.session.render_turn_prompt()
        self.assertIn("exited with code 1", prompt)
        self.assertIn("adjust the implementation with 'patch'", prompt)
        self.assertNotIn("Submit 'finish' now", prompt)

    def test_post_patch_critical_final_turn_directive(self) -> None:
        patch_act = TerminalAction(
            action_type="patch",
            path="src/app.py",
            search_block="return 41",
            replace_block="return 42",
        )
        self.assertEqual(self.session.execute_action(patch_act).status, "ok")
        self.session.max_turns = 2
        prompt = self.session.render_turn_prompt()
        self.assertIn("CRITICAL FINAL TURN", prompt)
        self.assertIn("Submit 'finish' NOW", prompt)

    def test_finish_action_accepts_command_modified_workspace(self) -> None:
        import subprocess

        # Initialize git repo in self.workspace
        subprocess.run(["git", "init"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.org"], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=self.workspace, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.workspace, capture_output=True, check=True)

        finish_act = TerminalAction(action_type="finish", explanation="Done via script.")
        # Modify file directly (simulating script write)
        (self.workspace / "src" / "app.py").write_text("def solve():\n    return 999\n", encoding="utf-8")

        obs = self.session.execute_action(finish_act)
        self.assertEqual(obs.status, "ok")
        self.assertTrue(self.session.is_finished)


class TestTerminalPromptAndFaultCoupling(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "tests").mkdir(parents=True, exist_ok=True)

        self.src_file = self.workspace / "src" / "calc.py"
        self.src_file.write_text(
            "class Calculator:\n"
            "    def compute(self, x: int) -> int:\n"
            "        return x + 1\n",
            encoding="utf-8",
        )

        self.session = TerminalSession(self.workspace, "Repair compute method")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_prompt_rendering_with_symbol_hints(self) -> None:
        # Simulate a previous command failure with a stack trace pointing to Calculator.compute
        fake_err = (
            'Traceback (most recent call last):\n'
            '  File "src/calc.py", line 3, in compute\n'
            '    return x + 1\n'
            'TypeError: unsupported operand type(s)\n'
        )
        fake_obs = TerminalObservation(
            action_type="command",
            status="error",
            exit_code=1,
            stderr=fake_err,
        )
        self.session._record_step(
            TerminalAction(action_type="command", command=("pytest",)),
            fake_obs,
            hexagram_code=39,
        )

        prompt = self.session.render_turn_prompt(include_fault_hints=True)
        self.assertIn("Fault Localization Hints", prompt)
        self.assertIn("src/calc.py", prompt)
        self.assertIn("compute", prompt)
        self.assertIn("Execution History", prompt)
        self.assertIn("Turn 1:", prompt)


class TestRunTerminalSessionLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        self.file = self.workspace / "src" / "target.py"
        self.file.write_text("x = 10\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_run_terminal_session_successful_flow(self) -> None:
        responses = [
            json.dumps({"action_type": "read_file", "path": "src/target.py"}),
            json.dumps({"action_type": "patch", "path": "src/target.py", "search_block": "x = 10", "replace_block": "x = 20"}),
            json.dumps({"action_type": "finish", "explanation": "Target updated to 20"}),
        ]

        class MockProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        provider = MockProvider(responses)
        recorded_steps: list[TerminalStep] = []

        res = run_terminal_session(
            "Update x to 20",
            self.workspace,
            provider,
            max_turns=5,
            approval_mode="scoped_auto",
            on_step=lambda step: recorded_steps.append(step),
        )

        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["reason"], "agent_finished")
        self.assertEqual(res["turns_completed"], 3)
        self.assertEqual(len(recorded_steps), 3)
        self.assertEqual(self.file.read_text(encoding="utf-8"), "x = 20\n")

    def test_run_terminal_session_provider_error(self) -> None:
        class FailingProvider:
            def complete(self, prompt: str) -> str:
                raise ConnectionError("Gateway 524 timeout")

        res = run_terminal_session("Failing task", self.workspace, FailingProvider(), max_turns=5)
        self.assertEqual(res["status"], "halted")
        self.assertEqual(res["reason"], "provider_error")
        self.assertIn("Gateway 524 timeout", res["error"])

    def test_run_terminal_session_turn_exhaustion(self) -> None:
        class EndlessProvider:
            def complete(self, prompt: str) -> str:
                return json.dumps({"action_type": "read_file", "path": "src/target.py"})

        res = run_terminal_session("Endless task", self.workspace, EndlessProvider(), max_turns=2)
        self.assertEqual(res["status"], "halted")
        self.assertEqual(res["reason"], "turn_limit_exhausted")
        self.assertEqual(res["turns_completed"], 2)


class TestTerminalModelLoopIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        self.target = self.workspace / "src" / "target.py"
        self.target.write_text("x = 10\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_run_model_task_terminal_mode_success(self) -> None:
        from onecode.kernel.model_loop import run_model_task

        responses = [
            json.dumps({"action_type": "read_file", "path": "src/target.py"}),
            json.dumps({
                "action_type": "patch",
                "path": "src/target.py",
                "search_block": "x = 10",
                "replace_block": "x = 20",
            }),
            json.dumps({"action_type": "finish", "explanation": "Target updated to 20"}),
        ]

        class SequenceProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str, **kwargs: object) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        turn_events: list[dict[str, object]] = []
        result = run_model_task(
            "Fix target value to 20",
            workspace=self.workspace,
            run_id="test-term-run",
            api_key="mock-key",
            agent_mode="terminal",
            approval_mode="scoped_auto",
            provider=SequenceProvider(responses),
            on_turn=lambda t: turn_events.append(t),
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["agent_mode"], "terminal")
        self.assertEqual(result["outcome_status_code"], 63)
        self.assertEqual(result["global_status_code"], 63)
        self.assertEqual(result["iching_status_code"], 63)
        self.assertIn("iching_transition_action", result)
        self.assertIn("dispatch_decision", result)
        self.assertEqual(result["repair_attempt_count"], 1)
        self.assertEqual(result["modified_files"], ["src/target.py"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "x = 20\n")
        self.assertEqual(len(turn_events), 3)

        trace_file = Path(result["trace_path"])
        self.assertTrue(trace_file.is_file())
        trace_lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(trace_lines), 3)
        self.assertEqual(trace_lines[0]["action"]["action_type"], "read_file")
        self.assertEqual(trace_lines[1]["action"]["action_type"], "patch")
        self.assertEqual(trace_lines[2]["action"]["action_type"], "finish")

    def test_command_modified_files_tracked_in_session_and_model_terminal(self) -> None:
        from unittest.mock import patch
        from onecode.kernel.model_loop import run_model_task

        responses = [
            json.dumps({
                "action_type": "command",
                "command": [
                    "python3",
                    "-c",
                    "p='src/target.py'; open(p,'w').write('x = 42\\n')",
                ],
            }),
            json.dumps({"action_type": "finish", "explanation": "Target updated via command"}),
        ]

        class SequenceProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str, **kwargs: object) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            result = run_model_task(
                "Update src/target.py to 42 using python3",
                workspace=self.workspace,
                run_id="test-cmd-write-audit",
                api_key="mock-key",
                agent_mode="terminal",
                approval_mode="scoped_auto",
                provider=SequenceProvider(responses),
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "x = 42\n")
        self.assertIn("src/target.py", result["modified_files"])
        self.assertIn("src/target.py", result["written"])
        self.assertIn("src/target.py", result["command_modified_files"])

    def test_run_model_task_terminal_mode_via_env(self) -> None:
        import os
        from onecode.kernel.model_loop import run_model_task

        responses = [
            json.dumps({"action_type": "patch", "path": "src/target.py", "search_block": "x = 10", "replace_block": "x = 30"}),
            json.dumps({"action_type": "finish", "explanation": "Target updated to 30"}),
        ]

        class SequenceProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str, **kwargs: object) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        old_env = os.environ.get("ONECODE_AGENT_MODE")
        try:
            os.environ["ONECODE_AGENT_MODE"] = "terminal"
            result = run_model_task(
                "Check task",
                workspace=self.workspace,
                run_id="test-term-env",
                api_key="mock-key",
                agent_mode="classic",
                approval_mode="scoped_auto",
                provider=SequenceProvider(responses),
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["agent_mode"], "terminal")
        finally:
            if old_env is None:
                os.environ.pop("ONECODE_AGENT_MODE", None)
            else:
                os.environ["ONECODE_AGENT_MODE"] = old_env


    def test_run_model_task_terminal_mode_approval_gates(self) -> None:
        """Tests P0-2: approval_mode=strict blocks write actions without callback, and respects approval callback."""
        from onecode.kernel.model_loop import run_model_task

        responses_patch = [
            json.dumps({"action_type": "patch", "path": "src/target.py", "search_block": "x = 10", "replace_block": "x = 50"}),
            json.dumps({"action_type": "finish"}),
        ]

        class SequenceProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str, **kwargs: object) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        # 1. Strict mode without callback -> write action blocked with approval_required
        res_no_callback = run_model_task(
            "Fix target",
            workspace=self.workspace,
            run_id="test-term-strict-no-cb",
            api_key="mock-key",
            agent_mode="terminal",
            approval_mode="strict",
            require_explicit_approval=True,
            execution_approval=None,
            provider=SequenceProvider(list(responses_patch)),
        )
        self.assertEqual(res_no_callback["status"], "halted")
        self.assertEqual(res_no_callback["approval_mode"], "strict")
        self.assertFalse(res_no_callback["auto_approved_for_eval"])
        self.assertGreaterEqual(res_no_callback["blocked_approvals_count"], 1)

        # 2. Strict mode with callback that rejects -> blocked with approval_denied
        res_rejected = run_model_task(
            "Fix target",
            workspace=self.workspace,
            run_id="test-term-strict-rejected",
            api_key="mock-key",
            agent_mode="terminal",
            approval_mode="strict",
            execution_approval=lambda action: False,
            provider=SequenceProvider(list(responses_patch)),
        )
        self.assertEqual(res_rejected["status"], "halted")
        self.assertGreaterEqual(res_rejected["blocked_approvals_count"], 1)

        # 3. Strict mode with callback that approves -> completes and records approval evidence
        res_approved = run_model_task(
            "Fix target",
            workspace=self.workspace,
            run_id="test-term-strict-approved",
            api_key="mock-key",
            agent_mode="terminal",
            approval_mode="strict",
            execution_approval=lambda action: True,
            provider=SequenceProvider(list(responses_patch)),
        )
        self.assertEqual(res_approved["status"], "completed")
        self.assertGreaterEqual(res_approved["approved_actions_count"], 1)
        self.assertEqual(res_approved["approval_mode"], "strict")

    def test_run_model_task_wal_write_failure_visibility(self) -> None:
        """Tests P0-5: WAL write failure is recorded in warnings and wal_write_error_count."""
        from unittest.mock import patch
        from onecode.kernel.model_loop import run_model_task

        responses = [
            json.dumps({"action_type": "patch", "path": "src/target.py", "search_block": "x = 10", "replace_block": "x = 99"}),
            json.dumps({"action_type": "finish", "explanation": "Target updated to 99"}),
        ]

        class SequenceProvider:
            def __init__(self, resps: list[str]) -> None:
                self.resps = resps
                self.idx = 0

            def complete(self, prompt: str, **kwargs: object) -> str:
                res = self.resps[self.idx]
                self.idx += 1
                return res

        def _exploding_wal(*args: object, **kwargs: object) -> None:
            raise IOError("Simulated disk I/O failure during WAL fsync")

        with patch("onecode.kernel.checkpoint.write_global_wal", side_effect=_exploding_wal):
            res = run_model_task(
                "Update x",
                workspace=self.workspace,
                run_id="test-wal-fail",
                api_key="mock-key",
                agent_mode="terminal",
                approval_mode="scoped_auto",
                provider=SequenceProvider(responses),
            )

        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["wal_write_status"], "failed")
        self.assertEqual(res["wal_write_error_count"], 1)
        self.assertTrue(any("wal_write_failed" in w for w in res.get("warnings", [])))

    def test_kernel_faults_are_attached_to_the_task_result(self) -> None:
        from unittest.mock import patch
        from onecode.kernel.model_loop import _record_kernel_fault, run_model_task

        def _probe(*_args: object, **_kwargs: object) -> dict[str, str]:
            _record_kernel_fault("probe", RuntimeError("probe-fault"))
            return {"status": "halted", "reason": "probe"}

        with patch("onecode.kernel.model_loop._execute_model_task", side_effect=_probe):
            result = run_model_task("probe", workspace=self.workspace, api_key="mock-key", provider=object())
        self.assertTrue(any("probe-fault" in item for item in result.get("warnings", [])))

    def test_anti_tamper_hash_baseline_catches_python_c_and_ruby_tests(self) -> None:
        """Tests P0-3: Multi-language hash baseline detects test modifications via python -c and covers _test.rb."""
        from unittest.mock import patch

        go_test = self.workspace / "pkg" / "order_test.go"
        go_test.parent.mkdir(parents=True, exist_ok=True)
        go_test.write_text("package order\n// Original test\n", encoding="utf-8")

        rb_test = self.workspace / "spec" / "user_test.rb"
        rb_test.parent.mkdir(parents=True, exist_ok=True)
        rb_test.write_text("# Original ruby minitest\n", encoding="utf-8")

        session = TerminalSession(self.workspace, "Audit test", approval_mode="scoped_auto")
        self.assertIn("pkg/order_test.go", session.initial_test_hashes)
        self.assertIn("spec/user_test.rb", session.initial_test_hashes)

        # Modify pkg/order_test.go via python -c (bypassing simple command regex)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            tamper_action = TerminalAction(
                action_type="command",
                command=("python3", "-c", "open('pkg/order_test.go', 'w').write('package order\\n// HACKED\\n')"),
            )
            obs = session.execute_action(tamper_action)
            self.assertEqual(obs.status, "blocked")
            self.assertEqual(obs.reason, "preset_test_immutable")
            self.assertIn("Anti-tamper protection active", obs.stderr)
            self.assertIn("pkg/order_test.go", obs.stderr)
            self.assertEqual(go_test.read_text(encoding="utf-8"), "package order\n// Original test\n")
            # Step hexagram code should be 40 (火地晋)
            self.assertEqual(session.steps[-1].hexagram_code, 40)

            created = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "open('spec/extra_test.rb','w').write('x')"),
            ))
            self.assertEqual(created.reason, "preset_test_immutable")
            self.assertFalse((self.workspace / "spec" / "extra_test.rb").exists())

            # Attempting finish after tampering must also be blocked with 40
            finish_obs = session.execute_action(TerminalAction(action_type="finish"))
            self.assertEqual(finish_obs.status, "blocked")
            self.assertEqual(finish_obs.reason, "preset_test_immutable")
            self.assertEqual(session.steps[-1].hexagram_code, 40)

    def test_interpreter_oneliners_are_blocked_before_they_touch_test_files(self) -> None:
        from unittest.mock import patch

        go_test = self.workspace / "pkg" / "order_test.go"
        go_test.parent.mkdir(parents=True, exist_ok=True)
        go_test.write_text("package order\n// Original test\n", encoding="utf-8")
        session = TerminalSession(self.workspace, "Block before execution", approval_mode="scoped_auto")
        sentinel = self.workspace / "sentinel.txt"
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            observed = session.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "open('sentinel.txt','w').write('ran'); open('pkg/order_test.go','w').write('hacked')",
                ),
            ))
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertFalse(sentinel.exists())
            self.assertEqual(go_test.read_text(encoding="utf-8"), "package order\n// Original test\n")

            perl = session.execute_action(TerminalAction(
                action_type="command",
                command=("perl", "-pi", "-e", "s/Original/Hacked/", "pkg/order_test.go"),
            ))
            node = session.execute_action(TerminalAction(
                action_type="command",
                command=("node", "-e", "require('fs').writeFileSync('pkg/order_test.go','hacked')"),
            ))
            self.assertEqual(perl.reason, "preset_test_immutable")
            self.assertEqual(node.reason, "preset_test_immutable")
        clean = TerminalSession(self.workspace, "Allowed one-liner", approval_mode="scoped_auto")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            allowed = clean.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "print(1)"),
            ))
        self.assertNotEqual(allowed.reason, "preset_test_immutable")
        self.assertEqual(allowed.exit_code, 0)

    def test_spliced_test_paths_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        session = TerminalSession(self.workspace, "Spliced test path", approval_mode="scoped_auto")
        hidden = self.workspace / "tests" / "hidden_case.py"
        spec_file = self.workspace / "spec" / "extra.rb"
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            literal = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "open('tests/' + 'hidden_case.py', 'w').write('x')"),
            ))
            variable = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "name='hidden_case.py'; open('tests/' + name, 'w').write('x')"),
            ))
            pathlib_write = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "from pathlib import Path; Path('spec').joinpath('extra.rb').write_text('x')"),
            ))
            encoded = session.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "open('sentinel.txt','w').write('ran'); open(chr(116)+'ests/hidden.py','w').write('x')",
                ),
            ))
        self.assertEqual(literal.reason, "preset_test_immutable")
        self.assertEqual(variable.reason, "preset_test_immutable")
        self.assertEqual(pathlib_write.reason, "preset_test_immutable")
        self.assertEqual(encoded.reason, "preset_test_immutable")
        self.assertFalse(hidden.exists())
        self.assertFalse(spec_file.exists())
        self.assertFalse((self.workspace / "sentinel.txt").exists())
        self.assertEqual(session.steps[-1].hexagram_code, 40)

        readable = self.workspace / "tests" / "test_keep.py"
        readable.parent.mkdir(parents=True, exist_ok=True)
        readable.write_text("KEEP\n", encoding="utf-8")
        (self.workspace / "src").mkdir(exist_ok=True)
        implementation = TerminalSession(self.workspace, "Write implementation", approval_mode="scoped_auto")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            wrote = implementation.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "open('src/app.py','w').write('tests passed')"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "tests passed")
        self.assertEqual(readable.read_text(encoding="utf-8"), "KEEP\n")

    def test_environment_test_paths_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        session = TerminalSession(self.workspace, "Environment path", approval_mode="scoped_auto")
        hidden = self.workspace / "tests" / "from_env.py"
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host", "ONECODE_TARGET": "tests/from_env.py"}):
            observed = session.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import os; open('sentinel.txt','w').write('ran'); open(os.environ['ONECODE_TARGET'],'w').write('x')",
                ),
            ))
        self.assertEqual(observed.reason, "preset_test_immutable")
        self.assertFalse((self.workspace / "sentinel.txt").exists())
        self.assertFalse(hidden.exists())
        self.assertEqual(session.steps[-1].hexagram_code, 40)

        writer = TerminalSession(self.workspace, "Environment content", approval_mode="scoped_auto")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host", "ONECODE_NOTE": "from-env"}):
            wrote = writer.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import os; open('src/app.py','w').write(os.environ.get('ONECODE_NOTE', 'from-env'))",
                ),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "from-env")

    def test_computed_test_paths_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        session = TerminalSession(self.workspace, "Computed path", approval_mode="scoped_auto")
        hidden = self.workspace / "tests" / "hidden.py"
        script = (
            "def target():\n"
            "    folder = 't' + 'ests'\n"
            "    return folder + '/' + 'hidden.py'\n"
            "open('sentinel.txt','w').write('ran')\n"
            "open(target(),'w').write('x')\n"
        )
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            observed = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", script),
            ))
        self.assertEqual(observed.reason, "preset_test_immutable")
        self.assertFalse((self.workspace / "sentinel.txt").exists())
        self.assertFalse(hidden.exists())
        self.assertEqual(session.steps[-1].hexagram_code, 40)

        writer = TerminalSession(self.workspace, "Literal pathlib write", approval_mode="scoped_auto")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            wrote = writer.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "from pathlib import Path; Path('src/app.py').write_text('ok')"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")

    def test_static_literal_var_python_write_allowed_while_dynamic_target_blocked(self) -> None:
        from unittest.mock import patch

        session = TerminalSession(self.workspace, "Literal var write check", approval_mode="scoped_auto")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            allowed = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "p='src/app.py'; open(p,'w').write('ok')"),
            ))
            blocked_var = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "p='tests/hidden_var.py'; open(p,'w').write('x')"),
            ))
            blocked_dyn = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "def t():\n    return 'src/app.py'\nopen(t(),'w').write('bad')"),
            ))
        self.assertEqual(allowed.exit_code, 0)
        self.assertNotEqual(allowed.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(blocked_var.reason, "preset_test_immutable")
        self.assertFalse((self.workspace / "tests" / "hidden_var.py").exists())
        self.assertEqual(blocked_dyn.reason, "preset_test_immutable")

    def test_imported_module_writes_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        inner = self.workspace / "inner.py"
        inner.write_text("open('tests/inner_hidden.py','w').write('x')\n", encoding="utf-8")
        outer = self.workspace / "outer.py"
        outer.write_text("import inner\nopen('outer_sentinel.txt','w').write('ran')\n", encoding="utf-8")
        safe = self.workspace / "safe_writer.py"
        safe.write_text("def dump():\n    open('src/app.py','w').write('ok')\n", encoding="utf-8")
        hidden = self.workspace / "tests" / "hidden.py"
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            imported = TerminalSession(self.workspace, "Import write", approval_mode="scoped_auto")
            observed = imported.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import helper"),
            ))
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse(hidden.exists())
            self.assertEqual(imported.steps[-1].hexagram_code, 40)

            chained = TerminalSession(self.workspace, "Chained import", approval_mode="scoped_auto")
            chain = chained.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import outer"),
            ))
            self.assertEqual(chain.reason, "preset_test_immutable")
            self.assertFalse((self.workspace / "outer_sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "inner_hidden.py").exists())

            script = TerminalSession(self.workspace, "Run module", approval_mode="scoped_auto")
            ran = script.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "helper.py"),
            ))
            self.assertEqual(ran.reason, "preset_test_immutable")
            self.assertFalse((self.workspace / "sentinel.txt").exists())

            allowed = TerminalSession(self.workspace, "Safe import", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import safe_writer; safe_writer.dump()"),
            ))
            printed = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import json; print(json.dumps({'a': 1}))"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(printed.exit_code, 0)
        self.assertIn("a", printed.stdout)

    def test_module_flag_and_variable_import_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        writer = self.workspace / "mod_writer.py"
        writer.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_mod.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        hidden = self.workspace / "tests" / "hidden.py"
        hidden.parent.mkdir(parents=True, exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_flag = TerminalSession(self.workspace, "Dash m", approval_mode="scoped_auto")
            flagged = by_flag.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-m", "mod_writer"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse(hidden.exists())
            self.assertEqual(flagged.reason, "preset_test_immutable")
            self.assertEqual(by_flag.steps[-1].hexagram_code, 40)

            by_name = TerminalSession(self.workspace, "Variable import", approval_mode="scoped_auto")
            variable = by_name.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "name='mod_writer'; __import__(name)"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(variable.reason, "preset_test_immutable")

            by_importlib = TerminalSession(self.workspace, "Importlib variable", approval_mode="scoped_auto")
            loaded = by_importlib.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import importlib; name='mod_writer'; importlib.import_module(name)"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(loaded.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe module flag", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-m", "safe_mod"),
            ))
            printed = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "__import__('json'); print(1)"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(printed.exit_code, 0)
        self.assertIn("1", printed.stdout)

    def test_exec_and_loader_writes_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        module = self.workspace / "mod_writer.py"
        module.write_text(
            "open('module_sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_exec.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_exec = TerminalSession(self.workspace, "Exec file", approval_mode="scoped_auto")
            executed = by_exec.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "exec(open('helper.py').read())"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(executed.reason, "preset_test_immutable")
            self.assertEqual(by_exec.steps[-1].hexagram_code, 40)

            by_path = TerminalSession(self.workspace, "Run path", approval_mode="scoped_auto")
            ran_path = by_path.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import runpy; runpy.run_path('helper.py')"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(ran_path.reason, "preset_test_immutable")

            by_module = TerminalSession(self.workspace, "Run module", approval_mode="scoped_auto")
            ran_module = by_module.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import runpy; name='mod_writer'; runpy.run_module(name)"),
            ))
            self.assertFalse((self.workspace / "module_sentinel.txt").exists())
            self.assertEqual(ran_module.reason, "preset_test_immutable")

            by_loader = TerminalSession(self.workspace, "File loader", approval_mode="scoped_auto")
            loaded = by_loader.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import importlib.util\n"
                    "spec = importlib.util.spec_from_file_location('m', 'helper.py')\n"
                    "mod = importlib.util.module_from_spec(spec)\n"
                    "spec.loader.exec_module(mod)\n",
                ),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(loaded.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe exec", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "exec(open('safe_exec.py').read())"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")

    def test_getattr_and_source_loader_writes_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_exec.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_loader = TerminalSession(self.workspace, "Source loader", approval_mode="scoped_auto")
            loaded = by_loader.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import importlib.machinery\n"
                    "importlib.machinery.SourceFileLoader('m', 'helper.py').load_module()\n",
                ),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(loaded.reason, "preset_test_immutable")
            self.assertEqual(by_loader.steps[-1].hexagram_code, 40)

            by_getattr = TerminalSession(self.workspace, "Getattr run path", approval_mode="scoped_auto")
            fetched = by_getattr.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import runpy; getattr(runpy, 'run_' + 'path')('helper.py')"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(fetched.reason, "preset_test_immutable")

            by_split_loader = TerminalSession(self.workspace, "Getattr loader", approval_mode="scoped_auto")
            split = by_split_loader.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import importlib.machinery\n"
                    "getattr(importlib.machinery, 'Source' + 'FileLoader')('m', 'helper.py').load_module()\n",
                ),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(split.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe loader", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import importlib.machinery\n"
                    "importlib.machinery.SourceFileLoader('m', 'safe_exec.py').load_module()\n",
                ),
            ))
            printed = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import json; print(getattr(json, 'dumps')({'a': 1}))"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(printed.exit_code, 0)
        self.assertIn("a", printed.stdout)

    def test_loader_hidden_in_an_imported_module_is_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        facade = self.workspace / "facade.py"
        facade.write_text(
            "import runpy\n"
            "def go():\n"
            "    getattr(runpy, 'run_' + 'path')('helper.py')\n",
            encoding="utf-8",
        )
        loader = self.workspace / "loader_facade.py"
        loader.write_text(
            "import importlib.machinery\n"
            "def go():\n"
            "    importlib.machinery.SourceFileLoader('m', 'helper.py').load_module()\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_facade.py"
        safe.write_text(
            "def go():\n"
            "    open('src/app.py','w').write('ok')\n",
            encoding="utf-8",
        )
        (self.workspace / "tests").mkdir(exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_import = TerminalSession(self.workspace, "Facade getattr", approval_mode="scoped_auto")
            observed = by_import.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import facade; facade.go()"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertEqual(by_import.steps[-1].hexagram_code, 40)

            by_loader = TerminalSession(self.workspace, "Facade loader", approval_mode="scoped_auto")
            loaded = by_loader.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import loader_facade; loader_facade.go()"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(loaded.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe facade", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import safe_facade; safe_facade.go()"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")

    def test_imported_framework_module_with_dynamic_import_is_not_blocked(self) -> None:
        from unittest.mock import patch

        pkg = self.workspace / "framework"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("import importlib\ndef load(x):\n    return importlib.import_module(x)\n", encoding="utf-8")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            session = TerminalSession(self.workspace, "Framework import", approval_mode="scoped_auto")
            obs = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import framework; print('loaded')"),
            ))
        self.assertEqual(obs.exit_code, 0)
        self.assertNotEqual(obs.reason, "preset_test_immutable")

    def test_framework_module_flag_with_dynamic_getattr_is_not_blocked(self) -> None:
        from unittest.mock import patch

        pkg = self.workspace / "dyn_framework"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "__main__.py").write_text(
            "class Runner:\n"
            "    def run(self, fn):\n"
            "        return getattr(self, fn)()\n"
            "    def ping(self):\n"
            "        return 'pong'\n"
            "print(Runner().run('ping'))\n",
            encoding="utf-8",
        )
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            session = TerminalSession(self.workspace, "Framework module flag", approval_mode="scoped_auto")
            obs = session.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-m", "dyn_framework"),
            ))
        self.assertEqual(obs.exit_code, 0)
        self.assertNotEqual(obs.reason, "preset_test_immutable")

    def test_subprocess_interpreter_writes_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        facade = self.workspace / "spawn_facade.py"
        facade.write_text(
            "import subprocess\n"
            "def go():\n"
            "    subprocess.run(['python3', 'helper.py'])\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_spawn.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(exist_ok=True)
        inline = (
            "import subprocess; subprocess.run(['python3', '-c', "
            "\"open('c_sentinel.txt','w').write('ran'); open('tests/hidden.py','w').write('x')\"])"
        )
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_module = TerminalSession(self.workspace, "Subprocess module", approval_mode="scoped_auto")
            observed = by_module.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import spawn_facade; spawn_facade.go()"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertEqual(by_module.steps[-1].hexagram_code, 40)

            by_inline = TerminalSession(self.workspace, "Subprocess inline", approval_mode="scoped_auto")
            inline_obs = by_inline.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", inline),
            ))
            self.assertFalse((self.workspace / "c_sentinel.txt").exists())
            self.assertEqual(inline_obs.reason, "preset_test_immutable")

            by_system = TerminalSession(self.workspace, "Os system", approval_mode="scoped_auto")
            system_obs = by_system.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import os; os.system('python3 helper.py')"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(system_obs.reason, "preset_test_immutable")

            by_variable = TerminalSession(self.workspace, "Variable argv", approval_mode="scoped_auto")
            variable_obs = by_variable.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import subprocess; cmd=['python3', 'helper.py']; subprocess.run(cmd)"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(variable_obs.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe subprocess", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import subprocess; subprocess.run(['python3', 'safe_spawn.py'])"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")

    def test_shell_wrapped_interpreter_writes_are_blocked_before_execution(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        safe = self.workspace / "safe_shell.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_shell = TerminalSession(self.workspace, "Bash wrapper", approval_mode="scoped_auto")
            observed = by_shell.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "-c", "python3 helper.py"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertEqual(by_shell.steps[-1].hexagram_code, 40)

            by_subprocess = TerminalSession(self.workspace, "Subprocess bash", approval_mode="scoped_auto")
            launched = by_subprocess.execute_action(TerminalAction(
                action_type="command",
                command=(
                    "python3", "-c",
                    "import subprocess; subprocess.run(['bash', '-c', 'python3 helper.py'])",
                ),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(launched.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe bash", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "-c", "python3 safe_shell.py"),
            ))
            echoed = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "-c", "echo ok"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(echoed.exit_code, 0)
        self.assertIn("ok", echoed.stdout)

    def test_shell_script_files_are_blocked_before_they_touch_tests(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text(
            "open('sentinel.txt','w').write('ran')\nopen('tests/hidden.py','w').write('x')\n",
            encoding="utf-8",
        )
        script = self.workspace / "helper.sh"
        script.write_text("python3 helper.py\n", encoding="utf-8")
        destructive = self.workspace / "tamper.sh"
        destructive.write_text("echo ran > sentinel.txt\nrm -f tests/test_keep.py\n", encoding="utf-8")
        safe = self.workspace / "safe_shell.py"
        safe.write_text("open('src/app.py','w').write('ok')\n", encoding="utf-8")
        safe_script = self.workspace / "safe.sh"
        safe_script.write_text("python3 safe_shell.py\n", encoding="utf-8")
        kept = self.workspace / "tests" / "test_keep.py"
        kept.parent.mkdir(parents=True, exist_ok=True)
        kept.write_text("KEEP\n", encoding="utf-8")
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            by_file = TerminalSession(self.workspace, "Bash script", approval_mode="scoped_auto")
            observed = by_file.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "helper.sh"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
            self.assertEqual(observed.reason, "preset_test_immutable")
            self.assertEqual(by_file.steps[-1].hexagram_code, 40)

            by_rm = TerminalSession(self.workspace, "Shell rm", approval_mode="scoped_auto")
            removed = by_rm.execute_action(TerminalAction(
                action_type="command",
                command=("sh", "./tamper.sh"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(kept.read_text(encoding="utf-8"), "KEEP\n")
            self.assertEqual(removed.reason, "preset_test_immutable")

            by_subprocess = TerminalSession(self.workspace, "Subprocess script", approval_mode="scoped_auto")
            launched = by_subprocess.execute_action(TerminalAction(
                action_type="command",
                command=("python3", "-c", "import subprocess; subprocess.run(['bash', 'helper.sh'])"),
            ))
            self.assertFalse((self.workspace / "sentinel.txt").exists())
            self.assertEqual(launched.reason, "preset_test_immutable")

            allowed = TerminalSession(self.workspace, "Safe shell file", approval_mode="scoped_auto")
            wrote = allowed.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "safe.sh"),
            ))
        self.assertEqual(wrote.exit_code, 0)
        self.assertNotEqual(wrote.reason, "preset_test_immutable")
        self.assertEqual((self.workspace / "src" / "app.py").read_text(encoding="utf-8"), "ok")
        self.assertEqual(kept.read_text(encoding="utf-8"), "KEEP\n")

    def test_eval_inside_a_shell_script_is_blocked_before_it_runs(self) -> None:
        from unittest.mock import patch

        helper = self.workspace / "helper.py"
        helper.write_text("open('tests/hidden.py','w').write('x')\n", encoding="utf-8")
        script = self.workspace / "helper.sh"
        script.write_text("eval python3 helper.py\n", encoding="utf-8")
        (self.workspace / "tests").mkdir()
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            session = TerminalSession(self.workspace, "Eval script", approval_mode="scoped_auto")
            observed = session.execute_action(TerminalAction(
                action_type="command",
                command=("bash", "helper.sh"),
            ))
        self.assertFalse((self.workspace / "tests" / "hidden.py").exists())
        self.assertEqual(observed.reason, "preset_test_immutable")
        self.assertEqual(session.steps[-1].hexagram_code, 40)

    def test_pycache_pyc_files_do_not_trigger_test_tamper(self) -> None:
        from unittest.mock import patch

        framework_test = self.workspace / "django" / "test"
        framework_test.mkdir(parents=True, exist_ok=True)
        pycache = framework_test / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            session = TerminalSession(self.workspace, "Pycache check", approval_mode="scoped_auto")
            # Simulate a bytecode file generated during import
            (pycache / "html.cpython-312.pyc").write_bytes(b"\x00\x01\x02")
            intact, reason = session.verify_test_files_integrity()
        self.assertTrue(intact)
        self.assertEqual(reason, "")


    def test_find_exec_escaped_semicolon_not_blocked_as_tamper(self) -> None:
        from onecode.kernel.terminal_loop import _command_tamper_target

        script = r"find kvstore -maxdepth 2 -type f -print -exec sed -n '1,320p' {} \; && sed -n '1,320p' tests/test_kvstore.py"
        target = _command_tamper_target(self.workspace, ("bash", "-lc", script))
        self.assertEqual(target, "")


if __name__ == "__main__":
    unittest.main()
