"""Tests for two-phase terminal session orchestration."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.phased_terminal import (
    _extract_plan_summary,
    _format_phase1_task,
    _format_phase2_task,
    run_phased_terminal_session,
)
from onecode.kernel.terminal_loop import TerminalAction, TerminalObservation, TerminalStep


class TestPhasedTerminalFormatting(unittest.TestCase):
    def test_format_phase1_and_phase2_tasks(self) -> None:
        p1 = _format_phase1_task("Fix bug in calculation", plan_turns=5)
        self.assertIn("PHASE 1: INVESTIGATION", p1)
        self.assertIn("Fix bug in calculation", p1)
        self.assertIn("BUDGET: 5 TURNS", p1)

        p2 = _format_phase2_task("Fix bug in calculation", "Root cause is off-by-one in calc.py")
        self.assertIn("PHASE 2: IMPLEMENTATION", p2)
        self.assertIn("Root cause is off-by-one in calc.py", p2)

    def test_extract_plan_summary_from_steps(self) -> None:
        steps = [
            TerminalStep(
                turn_index=1,
                action=TerminalAction("read_file", path="src/math.py", explanation="Investigating logic"),
                observation=TerminalObservation("read_file", "ok", output="def add(a, b): return a - b"),
            ),
            TerminalStep(
                turn_index=2,
                action=TerminalAction("command", command=("pytest",), explanation="Running tests"),
                observation=TerminalObservation("command", "ok", exit_code=1, stderr="AssertionError: 2 != 4"),
            ),
        ]
        summary = _extract_plan_summary({"steps": [s.to_dict() for s in steps]})
        self.assertIn("src/math.py", summary)
        self.assertIn("pytest", summary)
        self.assertIn("AssertionError", summary)


class TestPhasedTerminalExecution(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        (self.workspace / "src").mkdir(parents=True)
        (self.workspace / "src" / "calc.py").write_text("def solve():\n    return 10\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(parents=True)
        (self.workspace / "tests" / "test_calc.py").write_text("def test_solve(): pass\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_phased_session_successful_flow(self) -> None:
        # Phase 1: turn 1 read_file, turn 2 finish with plan
        # Phase 2: turn 1 patch, turn 2 command, turn 3 finish
        responses = [
            # Phase 1 turn 1
            json.dumps({
                "action_type": "read_file",
                "path": "src/calc.py",
                "start_line": 1,
                "end_line": 5,
                "explanation": "Checking implementation",
            }),
            # Phase 1 turn 2: finish with plan
            json.dumps({
                "action_type": "finish",
                "explanation": "Root cause: return 10 should be return 42 in src/calc.py.",
            }),
            # Phase 2 turn 1: patch
            json.dumps({
                "action_type": "patch",
                "path": "src/calc.py",
                "search_block": "return 10",
                "replace_block": "return 42",
                "explanation": "Applying planned fix",
            }),
            # Phase 2 turn 2: command
            json.dumps({
                "action_type": "command",
                "command": ["python3", "-c", "import sys; sys.exit(0)"],
                "explanation": "Verifying fix",
            }),
            # Phase 2 turn 3: finish
            json.dumps({
                "action_type": "finish",
                "explanation": "Fix verified successfully.",
            }),
        ]
        resp_iter = iter(responses)
        provider = lambda _prompt: next(resp_iter)

        steps_emitted: list[TerminalStep] = []
        result = run_phased_terminal_session(
            "Change return 10 to return 42 in src/calc.py",
            self.workspace,
            provider,
            max_turns=10,
            plan_turns=4,
            approval_mode="strict",
            execution_approval=lambda _act: True,
            on_step=lambda s: steps_emitted.append(s),
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["reason"], "agent_finished")
        self.assertEqual(result["phase1_turns"], 2)
        self.assertEqual(result["phase2_turns"], 3)
        self.assertEqual(result["turns_completed"], 5)
        self.assertEqual(len(result["steps"]), 5)
        # Check turn indices are continuous: 1, 2, 3, 4, 5
        self.assertEqual([s["turn_index"] for s in result["steps"]], [1, 2, 3, 4, 5])
        self.assertEqual([s.turn_index for s in steps_emitted], [1, 2, 3, 4, 5])
        self.assertIn("return 10 should be return 42", result["phase1_summary"])
        self.assertIn("return 42", (self.workspace / "src" / "calc.py").read_text(encoding="utf-8"))

    def test_phased_session_plan_exhaustion_transitions_to_phase2(self) -> None:
        # Phase 1: 2 turns of read_file without calling finish (reaching plan_turns=2)
        # Phase 2: turn 1 patch, turn 2 finish
        responses = [
            # Phase 1 turn 1
            json.dumps({
                "action_type": "read_file",
                "path": "src/calc.py",
                "explanation": "Exploring calc.py",
            }),
            # Phase 1 turn 2
            json.dumps({
                "action_type": "command",
                "command": ["echo", "still investigating"],
                "explanation": "Still reading",
            }),
            # Phase 2 turn 1: patch
            json.dumps({
                "action_type": "patch",
                "path": "src/calc.py",
                "search_block": "return 10",
                "replace_block": "return 99",
                "explanation": "Patching in phase 2",
            }),
            # Phase 2 turn 2: finish
            json.dumps({
                "action_type": "finish",
                "explanation": "Finished patch in phase 2.",
            }),
        ]
        resp_iter = iter(responses)
        provider = lambda _prompt: next(resp_iter)

        result = run_phased_terminal_session(
            "Change calc return",
            self.workspace,
            provider,
            max_turns=6,
            plan_turns=2,
            approval_mode="strict",
            execution_approval=lambda _act: True,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["phase1_turns"], 2)
        self.assertEqual(result["phase2_turns"], 2)
        self.assertEqual(result["turns_completed"], 4)
        self.assertIn("src/calc.py", result["phase1_summary"])

    def test_phased_session_phase1_anti_tamper_halts(self) -> None:
        # Phase 1: model tries to modify test file via patch
        responses = [
            json.dumps({
                "action_type": "patch",
                "path": "tests/test_calc.py",
                "search_block": "pass",
                "replace_block": "assert True",
                "explanation": "Tampering with test",
            }),
        ]
        resp_iter = iter(responses)
        provider = lambda _prompt: next(resp_iter)

        result = run_phased_terminal_session(
            "Tamper task",
            self.workspace,
            provider,
            max_turns=6,
            plan_turns=2,
            approval_mode="strict",
            execution_approval=lambda _act: True,
        )

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "preset_test_immutable")

    def test_phased_session_fallback_on_low_turns(self) -> None:
        responses = [
            json.dumps({
                "action_type": "finish",
                "explanation": "Finished immediately",
            }),
        ]
        resp_iter = iter(responses)
        provider = lambda _prompt: next(resp_iter)

        result = run_phased_terminal_session(
            "Quick task",
            self.workspace,
            provider,
            max_turns=2,
            require_modification=False,
            approval_mode="strict",
            auto_approved_for_eval=True,
        )
        self.assertEqual(result["status"], "completed")


class TestPhasedModelLoopIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        (self.workspace / "src").mkdir(parents=True)
        (self.workspace / "src" / "app.py").write_text("def run():\n    return False\n", encoding="utf-8")
        (self.workspace / "tests").mkdir(parents=True)
        (self.workspace / "tests" / "test_app.py").write_text("def test_run(): pass\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_model_task_phased_terminal_success(self) -> None:
        from onecode.kernel.model_loop import run_model_task

        responses = [
            # Phase 1: finish plan
            json.dumps({
                "action_type": "finish",
                "explanation": "Plan: change return False to return True in src/app.py",
            }),
            # Phase 2: patch
            json.dumps({
                "action_type": "patch",
                "path": "src/app.py",
                "search_block": "return False",
                "replace_block": "return True",
                "explanation": "Execute plan",
            }),
            # Phase 2: finish
            json.dumps({
                "action_type": "finish",
                "explanation": "Fix verified.",
            }),
        ]
        resp_iter = iter(responses)
        mock_provider = lambda _prompt: next(resp_iter)

        result = run_model_task(
            "Fix app return",
            workspace=self.workspace,
            provider=mock_provider,
            api_key="mock-key",
            agent_mode="phased_terminal",
            max_turns=6,
            require_explicit_approval=True,
            execution_approval=lambda _act: True,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["agent_mode"], "phased_terminal")
        self.assertEqual(result["iching_status_code"], 63)
        self.assertEqual(result["phase1_turns"], 1)
        self.assertEqual(result["phase2_turns"], 2)
        self.assertEqual(result["turns_completed"], 3)
        self.assertIn("return True", (self.workspace / "src" / "app.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
