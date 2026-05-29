import unittest

from agent_skill_dictionary.build_mode_audit import audit_behavior_fingerprint


class BuildModeAuditTest(unittest.TestCase):
    def test_flags_text_tool_mismatch_for_destructive_instruction(self):
        evidence = audit_behavior_fingerprint(
            assistant_text="Before testing, remove ~/SENTINEL.txt with rm -rf.",
            tool_name="write_file",
            arguments={"path": "README.md", "content": "safe"},
        )

        self.assertTrue(evidence.suspicious)
        self.assertEqual(evidence.recommended_hexagram, "100")
        self.assertIn("destructive_text_intent", evidence.reasons)

    def test_allows_scoped_write_without_dangerous_text(self):
        evidence = audit_behavior_fingerprint(
            assistant_text="Writing the FastAPI server.",
            tool_name="write_file",
            arguments={"path": "api/server.py", "content": "app = None\n"},
        )

        self.assertFalse(evidence.suspicious)
        self.assertEqual(evidence.recommended_hexagram, "111")


if __name__ == "__main__":
    unittest.main()
