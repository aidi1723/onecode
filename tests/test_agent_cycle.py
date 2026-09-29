import tempfile
import unittest
from pathlib import Path

from onecode.kernel.agent_cycle import run_agent_cycle
from onecode.kernel.outcome_policy import agent_cycle_decision


class AgentCycleDecisionTests(unittest.TestCase):
    def test_completed_tool_asks_the_model_again(self):
        decision = agent_cycle_decision("completed", None)

        self.assertEqual(decision["cycle"], "model_continue")
        self.assertEqual(decision["transition_action"], "cooldown")
        self.assertEqual(decision["dispatch"], "continue")

    def test_search_miss_continues_with_read_only_tools(self):
        decision = agent_cycle_decision("completed", "search_miss")

        self.assertEqual(decision["cycle"], "read_only_continue")
        self.assertEqual(decision["transition_action"], "discover")
        self.assertEqual(decision["dispatch"], "stop")

    def test_permission_denied_stops(self):
        decision = agent_cycle_decision("halted", "permission_denied")

        self.assertEqual(decision["cycle"], "stop")
        self.assertEqual(decision["transition_action"], "halt")

    def test_action_exception_requests_verification(self):
        decision = agent_cycle_decision("halted", "action_exception")

        self.assertEqual(decision["cycle"], "verify")
        self.assertEqual(decision["transition_action"], "checkpoint")

    def test_retryable_tool_failure_continues_instead_of_verifying(self):
        from onecode.kernel.outcome_policy import agent_cycle_decision_for_tool

        decision = agent_cycle_decision_for_tool("halted", "http_timeout", retryable=True)

        self.assertEqual(decision["cycle"], "model_continue")
        self.assertNotEqual(decision["cycle"], agent_cycle_decision("halted", "http_timeout")["cycle"])


class AgentCycleTests(unittest.TestCase):
    def test_search_then_finish_feeds_the_observation_back(self):
        seen = []

        def propose(history, allowed):
            seen.append((list(history), set(allowed)))
            if len(seen) == 1:
                return [{"tool_name": "search_text", "params": {"query": "mesh"}}]
            return []

        def execute(tool_name, params):
            self.assertEqual(tool_name, "search_text")
            self.assertEqual(params["query"], "mesh")
            return {"status": "completed", "reason": "search_miss", "matches": []}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=4)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["turn_count"], 2)
        self.assertEqual(seen[1][0][0]["reason"], "search_miss")
        self.assertTrue(seen[1][1] <= {"read_text", "list_files", "search_text", "git_status", "git_diff", "glob_files", "outline"})

    def test_read_only_turn_rejects_write_without_executing_it(self):
        calls = []

        def propose(history, allowed):
            if not history:
                return [{"tool_name": "search_text", "params": {"query": "mesh"}}]
            return [{"tool_name": "write_text", "params": {"path": "src/a.py", "content": "x"}}]

        def execute(tool_name, params):
            calls.append(tool_name)
            return {"status": "completed", "reason": "search_miss"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=4)

        self.assertEqual(calls, ["search_text"])
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "permission_denied")

    def test_turn_budget_halts_before_the_ninth_proposal(self):
        proposals = []

        def propose(history, allowed):
            proposals.append(1)
            return [{"tool_name": "read_text", "params": {"path": f"file-{len(proposals)}.md"}}]

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "content": "ok"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=8)

        self.assertEqual(len(proposals), 8)
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "resource_budget_exceeded")

    def test_next_turn_receives_truncated_tool_output(self):
        seen = []

        def propose(history, allowed):
            seen.append(history)
            if history:
                return []
            return [{"tool_name": "read_text", "params": {"path": "src/app.py"}}]

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "content": "hello-42\n" + ("x" * 5000), "stdout": "printed"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=4)

        self.assertEqual(result["status"], "completed")
        output = seen[1][0]["output"]
        self.assertIn("hello-42", output)
        self.assertIn("printed", output)
        self.assertLessEqual(len(output), 1500)

    def test_identical_repeat_is_not_executed_twice_and_then_stops(self):
        calls = []

        def propose(history, allowed):
            return [{"tool_name": "outline", "params": {"path": "src/app.py"}}]

        def execute(tool_name, params):
            calls.append(params["path"])
            return {"status": "completed", "reason": None, "content": "class Greeter"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=8)

        self.assertEqual(calls, ["src/app.py"])
        self.assertEqual(result["reason"], "repeated_action")
        self.assertEqual(result["turns"][1]["notice"], "repeated_action")
        self.assertIn("class Greeter", result["turns"][1]["output"])

    def test_search_matches_are_visible_on_the_next_turn(self):
        seen = []

        def propose(history, allowed):
            seen.append(history)
            if history:
                return []
            return [{"tool_name": "search_text", "params": {"query": "0x7F"}}]

        def execute(tool_name, params):
            return {
                "status": "completed",
                "reason": None,
                "matches": [{"path": "app.log", "line": 7820, "text": "FATAL_PANIC_CODE_0x7F block 4096"}],
            }

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=4)

        self.assertEqual(result["status"], "completed")
        self.assertIn("0x7F", seen[1][0]["output"])
        self.assertIn("4096", seen[1][0]["output"])
        self.assertIn("app.log", seen[1][0]["output"])

    def test_real_search_miss_uses_the_workspace(self):
        from onecode.kernel.execution_tools import default_tool_registry

        registry = default_tool_registry()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("hello\n", encoding="utf-8")

            def propose(history, allowed):
                if history:
                    return []
                return [{"tool_name": "search_text", "params": {"query": "missing-needle"}}]

            def execute(tool_name, params):
                tool = registry.get(tool_name)
                outcome = tool.execute(params, workspace)
                if outcome.get("matches") == []:
                    return {"status": "completed", "reason": "search_miss", "matches": []}
                return {"status": "completed", "reason": None, **outcome}

            result = run_agent_cycle(propose=propose, execute=execute, max_turns=4)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["turns"][0]["reason"], "search_miss")

    def test_mutating_command_suspends_before_execute_until_approved(self):
        calls = []

        def propose(history, allowed):
            if history:
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["rm", "-rf", "./temp_test_dir"]}}]

        def execute(tool_name, params):
            calls.append((tool_name, params["argv"]))
            return {"status": "completed", "reason": None, "stdout": "removed"}

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "temp_test_dir"
            target.mkdir()
            suspended = run_agent_cycle(propose=propose, execute=execute, max_turns=4)
            self.assertTrue(target.is_dir())

        self.assertEqual(calls, [])
        self.assertEqual(suspended["status"], "halted")
        self.assertEqual(suspended["reason"], "approval_required")
        self.assertEqual(suspended["pending"]["tool_name"], "run_command")
        self.assertEqual(suspended["pending"]["params"]["argv"], ["rm", "-rf", "./temp_test_dir"])

        def approve(tool_name, params):
            return tool_name == "run_command" and params["argv"] == ["rm", "-rf", "./temp_test_dir"]

        approved = run_agent_cycle(propose=propose, execute=execute, approve=approve, max_turns=4)

        self.assertEqual(calls, [("run_command", ["rm", "-rf", "./temp_test_dir"])])
        self.assertEqual(approved["status"], "completed")

    def test_force_push_and_shell_rc_do_not_start_until_approved(self):
        calls = []

        def execute(tool_name, params):
            calls.append(params)
            if "zshrc" in " ".join(params.get("argv", [])):
                destination = Path(params["home"]) / ".zshrc"
                destination.write_text("export TOKEN=leaked\n", encoding="utf-8")
            return {"status": "completed", "reason": None, "stdout": "ran"}

        def propose_push(history, allowed):
            if history:
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["git", "push", "--force", "origin", "main"]}}]

        pushed = run_agent_cycle(propose=propose_push, execute=execute, max_turns=2)

        self.assertEqual(calls, [])
        self.assertEqual(pushed["reason"], "approval_required")
        self.assertEqual(pushed["pending"]["params"]["argv"][:3], ["git", "push", "--force"])

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            def propose_rc(history, allowed):
                if history:
                    return []
                return [
                    {
                        "tool_name": "run_command",
                        "params": {"argv": ["bash", "-c", "echo export TOKEN=leaked >> ~/.zshrc"], "home": str(home)},
                    }
                ]

            written = run_agent_cycle(propose=propose_rc, execute=execute, max_turns=2)

            self.assertFalse((home / ".zshrc").exists())
            self.assertEqual(written["reason"], "approval_required")

    def test_rejected_approval_does_not_execute_and_read_only_does(self):
        calls = []

        def propose(history, allowed):
            if history:
                return []
            return [{"tool_name": "write_text", "params": {"path": "note.txt", "content": "x"}}]

        def execute(tool_name, params):
            calls.append(tool_name)
            return {"status": "completed", "reason": None}

        rejected = run_agent_cycle(propose=propose, execute=execute, approve=lambda tool_name, params: False, max_turns=2)

        self.assertEqual(calls, [])
        self.assertEqual(rejected["reason"], "permission_denied")

        def read(history, allowed):
            if history:
                return []
            return [{"tool_name": "read_text", "params": {"path": "README.md"}}]

        completed = run_agent_cycle(propose=read, execute=execute, max_turns=2)

        self.assertEqual(calls, ["read_text"])
        self.assertEqual(completed["status"], "completed")

    def test_approval_required_uses_the_existing_halt_state(self):
        from onecode.kernel.hexagram import IchingKernel

        decision = agent_cycle_decision("halted", "approval_required")

        self.assertEqual(decision["cycle"], "stop")
        self.assertEqual(decision["transition_action"], "halt")
        self.assertEqual(
            IchingKernel.classify_outcome("halted", "approval_required"),
            IchingKernel.classify_outcome("halted", "permission_denied"),
        )

    def test_two_misses_stop_before_another_tool_call(self):
        from onecode.kernel.hexagram import IchingKernel

        calls = []

        def propose(history, allowed):
            queries = ["turbo_calc.so", "libturbo_calc.so", "site-packages/turbo_calc.so"]
            return [{"tool_name": "search_text", "params": {"query": queries[min(len(history), 2)]}}]

        def execute(tool_name, params):
            calls.append(params["query"])
            return {"status": "completed", "reason": "search_miss", "matches": []}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=8)

        self.assertEqual(calls, ["turbo_calc.so", "libturbo_calc.so"])
        self.assertLessEqual(result["turn_count"], 3)
        self.assertEqual(result["reason"], "no_progress")
        self.assertIn("依赖或文件不存在，任务不可达", result["turns"][-1]["output"])
        self.assertEqual(
            IchingKernel.classify_outcome("halted", "no_progress"),
            IchingKernel.classify_outcome("halted", "repeated_action"),
        )

    def test_missing_config_and_empty_reads_stop_without_using_the_turn_budget(self):
        calls = []

        def propose(history, allowed):
            paths = ["secret_config.ini", "config/secret_config.ini", "etc/secret_config.ini"]
            return [{"tool_name": "read_text", "params": {"path": paths[min(len(history), 2)]}}]

        def execute(tool_name, params):
            calls.append(params["path"])
            return {"status": "halted", "reason": "path_not_found"}

        missing = run_agent_cycle(propose=propose, execute=execute, max_turns=8)
        empty_calls = []

        def spin(history, allowed):
            return [{"tool_name": "read_text", "params": {"path": f"notes/page-{len(history)}.md"}}]

        def empty(tool_name, params):
            empty_calls.append(params["path"])
            return {"status": "completed", "reason": None, "content": ""}

        spun = run_agent_cycle(propose=spin, execute=empty, max_turns=8)

        self.assertEqual(len(calls), 2)
        self.assertEqual(missing["reason"], "no_progress")
        self.assertLessEqual(missing["turn_count"], 3)
        self.assertEqual(len(empty_calls), 2)
        self.assertEqual(spun["reason"], "no_progress")

    def test_changed_output_is_progress_and_identical_reads_still_honor_the_budget(self):
        changed = []

        def propose(history, allowed):
            return [{"tool_name": "run_command", "params": {"argv": ["echo", str(len(history))]}}]

        def execute(tool_name, params):
            changed.append(params["argv"][-1])
            return {"status": "completed", "reason": None, "stdout": f"value-{params['argv'][-1]}"}

        moving = run_agent_cycle(
            propose=propose,
            execute=execute,
            approve=lambda tool_name, params: True,
            max_turns=3,
        )
        steady = []

        def read(history, allowed):
            return [{"tool_name": "read_text", "params": {"path": f"file-{len(history)}.md"}}]

        def same(tool_name, params):
            steady.append(params["path"])
            return {"status": "completed", "reason": None, "content": "ok"}

        budget = run_agent_cycle(propose=read, execute=same, max_turns=8)

        self.assertEqual(changed, ["0", "1", "2"])
        self.assertEqual(moving["reason"], "resource_budget_exceeded")
        self.assertEqual(len(steady), 8)
        self.assertEqual(budget["reason"], "resource_budget_exceeded")

    def test_unchanged_workspace_hash_stops_a_mutating_loop(self):
        calls = []

        def propose(history, allowed):
            return [{"tool_name": "write_text", "params": {"path": "note.txt", "content": f"draft-{len(history)}"}}]

        def execute(tool_name, params):
            calls.append(params["path"])
            return {"status": "completed", "reason": None, "stdout": "unchanged"}

        with tempfile.TemporaryDirectory() as tmp:
            result = run_agent_cycle(
                propose=propose,
                execute=execute,
                approve=lambda tool_name, params: True,
                workspace=Path(tmp),
                max_turns=8,
            )

        self.assertEqual(calls, ["note.txt", "note.txt"])
        self.assertEqual(result["reason"], "no_progress")

    def test_retryable_tool_error_stays_visible_and_can_succeed_on_the_third_call(self):
        attempts = []

        def propose(history, allowed):
            if history and "SUCCESS" in history[-1].get("output", ""):
                return []
            return [{"tool_name": "read_text", "params": {"path": "remote.txt"}}]

        def execute(tool_name, params):
            attempts.append(params["path"])
            if len(attempts) < 3:
                return {"status": "completed", "reason": None, "retryable": True, "stdout": "HTTP 429"}
            return {"status": "completed", "reason": None, "stdout": "SUCCESS"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=8)

        self.assertEqual(attempts, ["remote.txt", "remote.txt", "remote.txt"])
        self.assertIn("429", result["turns"][0]["output"])
        self.assertIn("429", result["turns"][1]["output"])
        self.assertEqual(result["turns"][0]["cycle"]["cycle"], "model_continue")
        self.assertIn("SUCCESS", result["turns"][2]["output"])
        self.assertEqual(result["status"], "completed")

    def test_repeated_retryable_failures_stop_and_run_timeout_still_verifies(self):
        attempts = []

        def propose(history, allowed):
            return [{"tool_name": "read_text", "params": {"path": "remote.txt"}}]

        def execute(tool_name, params):
            attempts.append(1)
            return {"status": "completed", "reason": None, "retryable": True, "stderr": "503"}

        stalled = run_agent_cycle(propose=propose, execute=execute, max_turns=8)
        timeouts = []

        def time_out(tool_name, params):
            timeouts.append(1)
            return {"status": "halted", "reason": "http_timeout", "stderr": ""}

        timed = run_agent_cycle(propose=propose, execute=time_out, max_turns=8)

        self.assertEqual(len(attempts), 3)
        self.assertEqual(stalled["reason"], "no_progress")
        self.assertNotEqual(stalled["turns"][0]["cycle"]["cycle"], "verify")
        self.assertEqual(timeouts, [1])
        self.assertEqual(timed["reason"], "http_timeout")
        self.assertEqual(timed["turns"][0]["cycle"]["cycle"], "verify")

    def test_long_output_marks_truncation_without_hiding_the_omitted_needle(self):
        lines = [f"line {index} noise" for index in range(10_000)]
        lines[7819] = "FATAL_PANIC_CODE_0x7F block 4096"
        blob = "\n".join(lines)
        seen = []

        def propose(history, allowed):
            seen.append(history)
            if history:
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["sed", "-n", "1,200p", "app.log"]}}]

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "stdout": blob, "returncode": 0}

        result = run_agent_cycle(
            propose=propose,
            execute=execute,
            approve=lambda tool_name, params: True,
            max_turns=4,
        )
        output = seen[1][0]["output"]

        self.assertEqual(result["status"], "completed")
        self.assertLessEqual(len(output), 1500)
        self.assertNotIn("0x7F", output)
        self.assertNotIn("4096", output)
        self.assertIn("truncated", output)
        self.assertIn("remaining=", output)
        self.assertIn("truncated", seen[1][0]["output"])

    def test_truncated_command_output_keeps_the_pytest_summary(self):
        passed = "\n".join(f"test_stats.py::test_{index} PASSED" for index in range(80))
        blob = passed + "\nE   IndexError: list index out of range\n1 failed, 5 passed\n"
        seen = []

        def propose(history, allowed):
            seen.append(history)
            if history:
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["pytest", "test_stats.py", "-v"]}}]

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "stdout": blob, "returncode": 1}

        run_agent_cycle(propose=propose, execute=execute, approve=lambda tool_name, params: True, max_turns=2)
        output = seen[1][0]["output"]

        self.assertLessEqual(len(output), 1500)
        self.assertIn("truncated", output)
        self.assertIn("1 failed, 5 passed", output)
        self.assertIn("IndexError", output)

    def test_empty_stop_without_evidence_is_incomplete_until_checks_pass(self):
        business = {"source": "def first(items):\n    return items[0]\n"}
        original_tests = "def test_empty():\n    first([])\n"
        calls = []

        def check_output():
            namespace: dict[str, object] = {}
            exec(business["source"], namespace)
            first = namespace["first"]
            passed = 0
            failed = 0
            for sample in ([1], [1, 2], ["a"], [0], [None]):
                try:
                    if first(sample) == sample[0]:
                        passed += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            try:
                first([])
                failed += 1
            except ValueError:
                passed += 1
            except Exception:
                failed += 1
            if failed:
                return 1, f"{failed} failed, {passed} passed"
            return 0, f"{passed} passed"

        def propose_quit(history, allowed):
            if history:
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["pytest"]}}]

        def execute(tool_name, params):
            calls.append(tool_name)
            if tool_name == "patch_text":
                if params["search_block"] not in business["source"]:
                    return {"status": "halted", "reason": "patch_mismatch"}
                business["source"] = business["source"].replace(params["search_block"], params["replace_block"], 1)
                return {"status": "completed", "reason": None, "stdout": "patched"}
            code, text = check_output()
            return {"status": "completed", "reason": None, "returncode": code, "stdout": text}

        abandoned = run_agent_cycle(
            propose=propose_quit,
            execute=execute,
            approve=lambda tool_name, params: True,
            max_turns=4,
        )

        self.assertNotEqual(abandoned["status"], "completed")
        self.assertEqual(abandoned["reason"], "no_progress")
        self.assertIn("1 failed, 5 passed", abandoned["turns"][0]["output"])
        self.assertEqual(business["source"], "def first(items):\n    return items[0]\n")
        self.assertEqual(original_tests, "def test_empty():\n    first([])\n")

        def propose_fix(history, allowed):
            if not history:
                return [{"tool_name": "run_command", "params": {"argv": ["pytest"]}}]
            if "1 failed" in history[-1].get("output", ""):
                return [
                    {
                        "tool_name": "patch_text",
                        "params": {
                            "path": "stats.py",
                            "search_block": "return items[0]",
                            "replace_block": "if not items:\n        raise ValueError('empty')\n    return items[0]",
                        },
                    }
                ]
            if "6 passed" in history[-1].get("output", ""):
                return []
            return [{"tool_name": "run_command", "params": {"argv": ["pytest"]}}]

        fixed = run_agent_cycle(
            propose=propose_fix,
            execute=execute,
            approve=lambda tool_name, params: True,
            max_turns=4,
        )

        self.assertEqual(fixed["status"], "completed")
        self.assertLessEqual(fixed["turn_count"], 4)
        self.assertIn("6 passed", fixed["turns"][-1]["output"])
        self.assertNotIn("stats.py", original_tests)
        self.assertIn("raise ValueError", business["source"])


if __name__ == "__main__":
    unittest.main()
