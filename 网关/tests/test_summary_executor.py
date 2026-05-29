import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.summary_executor import summarize_active_context


class SummaryExecutorTest(unittest.TestCase):
    def test_summarize_active_context_writes_markdown_and_evidence(self):
        with TemporaryDirectory() as tmpdir:
            audit_log = Path(tmpdir) / "audit.log.jsonl"
            active_context = {
                "original_request": "帮我看看项目结构",
                "current_state": "总",
                "last_state": "查",
                "last_evidence_sha256": "a" * 64,
                "last_exit_code": 0,
                "inspect_files": ["README.md", "app.py"],
                "inspect_snippets": {"README.md": "# Demo\n"},
                "verification_exit_code": None,
                "guard_risk": "high",
                "guard_findings": [
                    {
                        "file": "script.sh",
                        "line": 1,
                        "pattern": "curl pipe shell",
                        "severity": "high",
                    }
                ],
            }

            result = summarize_active_context(active_context, audit_log_path=audit_log)

            self.assertTrue(result["ok"])
            self.assertIn("# OneWord Handoff Summary", result["markdown"])
            self.assertIn("帮我看看项目结构", result["markdown"])
            self.assertIn("README.md", result["markdown"])
            self.assertIn("Guard Risk", result["markdown"])
            self.assertIn("script.sh:1", result["markdown"])
            self.assertEqual(result["evidence"]["exit_code"], 0)
            self.assertEqual(len(read_audit_log(audit_log)), 1)

    def test_summarize_active_context_prefers_native_inspect_card_over_snippets(self):
        active_context = {
            "original_request": "检查 sync_node.py",
            "current_state": "总",
            "last_state": "查",
            "inspect_files": ["sync_node.py"],
            "native_inspect_card_text": (
                "[State]: 101-INSPECT | [Target]: sync_node.py\n"
                "[Symbols]: sync_node.py:4:async def sync_inventory\n"
                "[Risks]: sync_node.py:6:while True\n"
            ),
            "inspect_snippets": {"sync_node.py": "NOISY_LOG\n" * 500},
        }

        result = summarize_active_context(active_context)

        self.assertIn("## Native Inspect Card", result["markdown"])
        self.assertIn("[State]: 101-INSPECT", result["markdown"])
        self.assertIn("while True", result["markdown"])
        self.assertNotIn("NOISY_LOG", result["markdown"])
        self.assertLess(len(result["markdown"]), 1200)


if __name__ == "__main__":
    unittest.main()
