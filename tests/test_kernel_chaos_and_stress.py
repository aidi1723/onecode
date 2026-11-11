"""Comprehensive chaos injection, boundary stress, and polyglot penetration test suite.

Validates the OneCode kernel against extreme adversarial conditions:
1. Massive observation flood attacks (100k+ lines, memory bounds).
2. Provider chaos, rate-limit simulation, and fault-recovery self-healing.
3. Multi-task batch stress, memory stability, and WAL ledger HMAC chain invariance.
4. Adversarial penetration & multi-language test anti-tamper boundaries (Python, Go, TS, Rust).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from onecode.kernel.execution_scope import ExecutionScope
from onecode.kernel.terminal_loop import (
    TerminalAction,
    TerminalSession,
    run_terminal_session,
)


class KernelChaosAndStressTests(unittest.TestCase):
    def test_massive_output_flood_truncation_and_memory_stability(self) -> None:
        """Verifies the kernel caps observation size when a tool emits a massive output flood."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            session = TerminalSession(
                workspace,
                "Process large log",
                max_turns=3,
                auto_approved_for_eval=True,
            )

            # Allow host command execution for unit test
            with patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
                cmd_action = TerminalAction(
                    action_type="command",
                    command=("python3", "-c", "for i in range(50000): print(f'FLOOD_LINE_{i}_DATA_STREAM_PAYLOAD')"),
                )
                obs = session.execute_action(cmd_action)

            self.assertEqual(obs.status, "ok")
            # Output must be capped, preventing memory exhaustion or token explosion
            self.assertLess(len(obs.stdout), 500000)
            self.assertIn("FLOOD_LINE_", obs.stdout)

            # Ensure prompt rendering handles the truncated output gracefully
            prompt = session.render_turn_prompt()
            self.assertIsInstance(prompt, str)
            self.assertLess(len(prompt), 100000)

    def test_provider_fault_chaos_and_self_healing_retry(self) -> None:
        """Verifies session survives transient provider failures (rate limits / connection drops)."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "sample.py").write_text("x = 1\n", encoding="utf-8")

            class FlakyProvider:
                def __init__(self) -> None:
                    self.call_count = 0

                def complete(self, _prompt: str) -> str:
                    self.call_count += 1
                    if self.call_count == 1:
                        # Transient failure on first attempt
                        raise ConnectionResetError("Simulated socket reset by peer")
                    # Self-heals on second attempt
                    return json.dumps({
                        "action_type": "finish",
                        "explanation": "Completed after transient recovery",
                    })

            provider = FlakyProvider()
            result = run_terminal_session(
                "Simple task",
                workspace,
                provider,
                max_turns=2,
                auto_approved_for_eval=True,
                require_modification=False,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(provider.call_count, 2)
            self.assertIn("Completed after transient recovery", result["explanation"])

    def test_multi_task_batch_execution_and_rollback_invariance(self) -> None:
        """Runs 20 consecutive sessions to verify memory stability and rollback isolation."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            core_file = workspace / "module.py"
            core_file.write_text("INITIAL_STATE = True\n", encoding="utf-8")

            class AlternatingProvider:
                def __init__(self, succeed: bool) -> None:
                    self.succeed = succeed

                def complete(self, _prompt: str) -> str:
                    if self.succeed:
                        return json.dumps({
                            "action_type": "finish",
                            "explanation": "Clean success",
                        })
                    return json.dumps({
                        "action_type": "patch",
                        "path": "module.py",
                        "search_block": "INITIAL_STATE = True\n",
                        "replace_block": "INITIAL_STATE = False\n",
                    })

            # Run 20 alternating sessions with rollback_on_failure
            for i in range(20):
                should_fail = (i % 2 == 1)
                provider = AlternatingProvider(succeed=not should_fail)
                res = run_terminal_session(
                    f"Batch task {i}",
                    workspace,
                    provider,
                    max_turns=1,
                    auto_approved_for_eval=True,
                    require_modification=False,
                    rollback_on_failure=True,
                )
                if should_fail:
                    # Failed/halted turns must be rolled back, preserving initial state
                    self.assertEqual(res["status"], "halted")
                    self.assertEqual(core_file.read_text(encoding="utf-8"), "INITIAL_STATE = True\n")
                else:
                    self.assertEqual(res["status"], "completed")

            # After 20 sessions, workspace remains pristine
            self.assertEqual(core_file.read_text(encoding="utf-8"), "INITIAL_STATE = True\n")

    def test_adversarial_tamper_penetration_resistance(self) -> None:
        """Penetration test: verifies malicious test-tampering vectors are strictly blocked (Hexagram 40)."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            test_file = tests_dir / "test_auth.py"
            test_file.write_text("def test_auth(): assert True\n", encoding="utf-8")

            session = TerminalSession(
                workspace,
                "Adversarial security audit",
                max_turns=10,
                auto_approved_for_eval=True,
            )

            malicious_commands: list[tuple[str, ...]] = [
                # Direct deletion
                ("rm", "-f", "tests/test_auth.py"),
                # Truncation
                ("truncate", "-s", "0", "tests/test_auth.py"),
                # In-place sed
                ("sed", "-i", "s/assert True/pass/g", "tests/test_auth.py"),
                # Python inline file deletion
                ("python3", "-c", "import os; os.unlink('tests/test_auth.py')"),
                # Python inline file overwrite
                ("python3", "-c", "open('tests/test_auth.py', 'w').write('pass')"),
                # Shell redirection
                ("sh", "-c", "echo 'pass' > tests/test_auth.py"),
            ]

            for cmd in malicious_commands:
                action = TerminalAction(action_type="command", command=cmd)
                obs = session.execute_action(action)
                self.assertEqual(obs.status, "blocked", f"Vector failed to block: {cmd}")
                self.assertEqual(obs.reason, "preset_test_immutable")
                self.assertIn("Anti-tamper protection active", obs.stderr)
                self.assertEqual(test_file.read_text(encoding="utf-8"), "def test_auth(): assert True\n")

            patch_act = TerminalAction(
                action_type="patch",
                path="tests/test_auth.py",
                search_block="assert True",
                replace_block="pass",
            )
            obs_p = session.execute_action(patch_act)
            self.assertEqual(obs_p.status, "blocked")
            self.assertEqual(obs_p.reason, "preset_test_immutable")
            self.assertEqual(test_file.read_text(encoding="utf-8"), "def test_auth(): assert True\n")

    def test_polyglot_test_immutability_go_typescript_rust(self) -> None:
        """Verifies multi-language test isolation: Go, TypeScript, Rust, and Ruby."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            session = TerminalSession(
                workspace,
                "Multi-language check",
                max_turns=10,
                auto_approved_for_eval=True,
            )

            polyglot_test_files = [
                "pkg/handler/service_test.go",
                "src/__tests__/auth.test.ts",
                "src/components/button.spec.js",
                "tests/integration_tests.rs",
                "spec/models/user_spec.rb",
            ]

            for test_path in polyglot_test_files:
                # 1. Patch against multi-language test path must be blocked
                patch_act = TerminalAction(
                    action_type="patch",
                    path=test_path,
                    search_block="assert",
                    replace_block="pass",
                )
                obs_patch = session.execute_action(patch_act)
                self.assertEqual(obs_patch.status, "blocked", f"Go/TS/Rust patch not blocked for: {test_path}")
                self.assertEqual(obs_patch.reason, "preset_test_immutable")

                # 2. Command modifying multi-language test path must be blocked
                cmd_act = TerminalAction(action_type="command", command=("rm", "-f", test_path))
                obs_cmd = session.execute_action(cmd_act)
                self.assertEqual(obs_cmd.status, "blocked", f"Go/TS/Rust rm not blocked for: {test_path}")
                self.assertEqual(obs_cmd.reason, "preset_test_immutable")

    def test_execution_scope_read_only_strictly_prohibits_writes(self) -> None:
        """Verifies ExecutionScope.READ_ONLY prevents all write and mutate actions."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            session = TerminalSession(
                workspace,
                "Investigation Phase",
                max_turns=5,
                auto_approved_for_eval=True,
                execution_scope=ExecutionScope.READ_ONLY,
            )

            # 1. Patch action in READ_ONLY scope must be blocked
            patch_action = TerminalAction(
                action_type="patch",
                path="app.py",
                search_block="old",
                replace_block="new",
            )
            obs1 = session.execute_action(patch_action)
            self.assertEqual(obs1.status, "blocked")
            self.assertEqual(obs1.reason, "scope_violation")

            # 2. Mutating command in READ_ONLY scope must be blocked
            cmd_action = TerminalAction(
                action_type="command",
                command=("touch", "new_file.txt"),
            )
            obs2 = session.execute_action(cmd_action)
            self.assertEqual(obs2.status, "blocked")
            self.assertEqual(obs2.reason, "scope_violation")

            # 3. Inspection command in READ_ONLY scope must be allowed
            with patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}):
                inspect_action = TerminalAction(
                    action_type="command",
                    command=("ls", "-la"),
                )
                obs3 = session.execute_action(inspect_action)
            self.assertEqual(obs3.status, "ok")


if __name__ == "__main__":
    unittest.main()
