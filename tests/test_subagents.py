import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel


class SubagentTests(unittest.TestCase):
    def test_more_than_three_subagents_stop_before_any_evidence(self):
        from onecode.kernel.subagents import run_read_only_subagents

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_read_only_subagents(
                workspace=workspace,
                agents=[{"id": f"a{index}", "task": "look"} for index in range(4)],
                propose=lambda task, history, allowed: [],
                execute=lambda name, params: {"status": "completed", "reason": None},
                max_turns=2,
            )
            evidence = workspace / ".onecode" / "subagents"

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["reason"], "resource_budget_exceeded")
        self.assertEqual(result["subagents"], [])
        self.assertFalse(evidence.exists())

    def test_subagents_are_read_only_with_separate_evidence_and_aggregated_status(self):
        from onecode.kernel.subagents import run_read_only_subagents

        calls = []

        def propose(task, history, allowed):
            if history:
                return []
            if task == "deny":
                return [{"tool_name": "write_text", "params": {"path": "x.txt", "content": "no"}}]
            return [{"tool_name": "read_text", "params": {"path": "a.txt"}}]

        def execute(name, params):
            calls.append(name)
            return {"status": "completed", "reason": None}

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_read_only_subagents(
                workspace=workspace,
                agents=[{"id": "reader", "task": "read"}, {"id": "writer", "task": "deny"}],
                propose=propose,
                execute=execute,
                max_turns=2,
            )
            reader_path = workspace / ".onecode" / "subagents" / "reader" / "result.json"
            writer_path = workspace / ".onecode" / "subagents" / "writer" / "result.json"
            reader = json.loads(reader_path.read_text(encoding="utf-8"))
            writer = json.loads(writer_path.read_text(encoding="utf-8"))

        self.assertEqual(calls, ["read_text"])
        self.assertEqual(reader["status"], "completed")
        self.assertEqual(writer["reason"], "permission_denied")
        self.assertEqual(
            result["status_code"],
            IchingKernel.aggregate_status(
                [
                    IchingKernel.classify_outcome("completed", None),
                    IchingKernel.classify_outcome("halted", "permission_denied"),
                ]
            ),
        )
        self.assertEqual(result["status"], "halted")
        self.assertNotEqual(result["subagents"][0]["evidence_dir"], result["subagents"][1]["evidence_dir"])

    def test_each_subagent_has_its_own_turn_budget(self):
        from onecode.kernel.subagents import run_read_only_subagents

        def propose(task, history, allowed):
            return [{"tool_name": "read_text", "params": {}}]

        with tempfile.TemporaryDirectory() as tmp:
            result = run_read_only_subagents(
                workspace=Path(tmp),
                agents=[{"id": "loop", "task": "keep"}],
                propose=propose,
                execute=lambda name, params: {"status": "completed", "reason": None},
                max_turns=1,
            )

        self.assertEqual(result["subagents"][0]["reason"], "resource_budget_exceeded")
        self.assertEqual(result["subagents"][0]["turn_count"], 1)
        self.assertEqual(
            result["status_code"],
            IchingKernel.aggregate_status([IchingKernel.classify_outcome("halted", "resource_budget_exceeded")]),
        )


if __name__ == "__main__":
    unittest.main()
