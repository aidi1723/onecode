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
            return [{"tool_name": "read_text", "params": {"path": "README.md"}}]

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "content": "ok"}

        result = run_agent_cycle(propose=propose, execute=execute, max_turns=8)

        self.assertEqual(len(proposals), 8)
        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "resource_budget_exceeded")

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


if __name__ == "__main__":
    unittest.main()
