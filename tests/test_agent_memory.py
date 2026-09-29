import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.agent_cycle import run_agent_cycle
from onecode.kernel.agent_memory import compact_agent_history, load_agent_memory, remember_turn


class AgentHistoryTests(unittest.TestCase):
    def test_over_budget_keeps_task_summary_and_last_two_turns(self):
        history = [
            {"tool_name": f"tool-{index}", "status": "completed", "reason": None, "blob": "x" * 40}
            for index in range(5)
        ]

        view = compact_agent_history("fix mesh", history, max_chars=80)

        self.assertEqual(view[0], {"role": "task", "text": "fix mesh"})
        self.assertEqual(view[1]["role"], "summary")
        self.assertEqual(view[1]["omitted_turns"], 3)
        self.assertEqual([item["tool_name"] for item in view[-2:]], ["tool-3", "tool-4"])
        self.assertNotIn("tool-0", json.dumps(view))

    def test_cycle_passes_compacted_history_to_the_model(self):
        seen = []

        def propose(history, allowed):
            seen.append(history)
            if len(seen) < 4:
                return [{"tool_name": "read_text", "params": {"path": f"file-{len(seen)}.md"}}]
            return []

        def execute(tool_name, params):
            return {"status": "completed", "reason": None, "content": "x" * 50}

        run_agent_cycle(propose=propose, execute=execute, max_turns=4, task="fix mesh", max_history_chars=60)

        self.assertEqual(seen[-1][0]["role"], "task")
        self.assertEqual(seen[-1][1]["role"], "summary")
        self.assertEqual(len(seen[-1]), 4)


class AgentMemoryTests(unittest.TestCase):
    def test_memory_requires_confirmation_and_refuses_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            record = {"text": "remember this"}

            self.assertFalse(remember_turn(workspace, record, confirmed=False, cycle="model_continue"))
            self.assertFalse(remember_turn(workspace, record, confirmed=True, cycle="stop"))
            self.assertFalse((workspace / ".onecode" / "memory.jsonl").exists())

            self.assertTrue(remember_turn(workspace, record, confirmed=True, cycle="model_continue"))
            loaded = load_agent_memory(workspace)

        self.assertEqual(loaded, [record])

    def test_resume_reads_memory_file_not_run_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            evidence = workspace / ".onecode" / "runs" / "run-1" / "trace.jsonl"
            evidence.parent.mkdir(parents=True)
            evidence.write_text('{"text":"run evidence"}\n', encoding="utf-8")
            remember_turn(workspace, {"text": "durable"}, confirmed=True, cycle="read_only_continue")

            loaded = load_agent_memory(workspace)

        self.assertEqual(loaded, [{"text": "durable"}])

    def test_completed_cycle_can_store_a_confirmed_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            def propose(history, allowed):
                if not history:
                    return [{"tool_name": "read_text", "params": {"path": "README.md"}}]
                return []

            def execute(tool_name, params):
                return {"status": "completed", "reason": None, "content": "mesh"}

            result = run_agent_cycle(
                propose=propose,
                execute=execute,
                task="fix mesh",
                workspace=workspace,
                remember=True,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(load_agent_memory(workspace), [{"role": "task", "text": "fix mesh"}])


if __name__ == "__main__":
    unittest.main()
