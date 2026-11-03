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
        # Test file must remain unchanged
        self.assertIn("assert solve() == 42", self.test_file.read_text(encoding="utf-8"))

    def test_command_execution_and_anti_tamper(self) -> None:
        from unittest.mock import patch
        # Safe command
        with patch.dict("os.environ", {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
            act_ok = TerminalAction(action_type="command", command=("python3", "-c", "print('hello_onecode')"))
            obs_ok = self.session.execute_action(act_ok)
            self.assertEqual(obs_ok.status, "ok")
            self.assertIn("hello_onecode", obs_ok.stdout)

        # Anti-tamper command attempting to delete test
        act_tamper = TerminalAction(action_type="command", command=("rm", "-rf", "tests/test_app.py"))
        obs_tamper = self.session.execute_action(act_tamper)
        self.assertEqual(obs_tamper.status, "blocked")
        self.assertEqual(obs_tamper.reason, "preset_test_immutable")

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

    def test_finish_action(self) -> None:
        act = TerminalAction(action_type="finish", explanation="All tests pass successfully.")
        obs = self.session.execute_action(act)
        self.assertEqual(obs.status, "ok")
        self.assertTrue(self.session.is_finished)
        self.assertEqual(self.session.finish_explanation, "All tests pass successfully.")


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
            provider=SequenceProvider(responses),
            on_turn=lambda t: turn_events.append(t),
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["agent_mode"], "terminal")
        self.assertEqual(result["outcome_status_code"], 0)
        self.assertEqual(result["iching_status_code"], 63)
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

    def test_run_model_task_terminal_mode_via_env(self) -> None:
        import os
        from onecode.kernel.model_loop import run_model_task

        responses = [
            json.dumps({"action_type": "finish", "explanation": "No change needed"}),
        ]

        class SimpleProvider:
            def complete(self, prompt: str, **kwargs: object) -> str:
                return responses[0]

        old_env = os.environ.get("ONECODE_AGENT_MODE")
        try:
            os.environ["ONECODE_AGENT_MODE"] = "terminal"
            result = run_model_task(
                "Check task",
                workspace=self.workspace,
                run_id="test-term-env",
                api_key="mock-key",
                agent_mode="classic",
                provider=SimpleProvider(),
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["agent_mode"], "terminal")
        finally:
            if old_env is None:
                os.environ.pop("ONECODE_AGENT_MODE", None)
            else:
                os.environ["ONECODE_AGENT_MODE"] = old_env


if __name__ == "__main__":
    unittest.main()
