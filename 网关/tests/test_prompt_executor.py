import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.prompt_executor import create_confirmation_ticket


class PromptExecutorTest(unittest.TestCase):
    def test_create_confirmation_ticket_writes_json_and_evidence(self):
        with TemporaryDirectory() as tmpdir:
            ticket_dir = Path(tmpdir) / "tickets"
            audit_log = Path(tmpdir) / "audit.log.jsonl"

            result = create_confirmation_ticket(
                {"original_request": "这个需求不明确", "current_state": "问"},
                ticket_dir=ticket_dir,
                audit_log_path=audit_log,
            )

            ticket_path = Path(result["path"])
            ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertTrue(result["needs_human"])
            self.assertEqual(ticket["status"], "pending_human_confirmation")
            self.assertEqual(ticket["active_context"]["current_state"], "问")
            self.assertEqual(result["evidence"]["exit_code"], 4)
            self.assertEqual(len(read_audit_log(audit_log)), 1)


if __name__ == "__main__":
    unittest.main()
