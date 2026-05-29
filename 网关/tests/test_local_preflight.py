import json
import unittest

from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.local_preflight import (
    claude_hook_decision,
    preflight_claude_tool_call,
)


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class LocalPreflightTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_claude_bash_is_denied_in_inspect_state(self):
        result = preflight_claude_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="Bash",
            tool_input={"command": "rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt"},
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["original_tool"], "Bash")
        self.assertEqual(result["normalized_tool"], "execute_command")
        self.assertTrue(
            any(item["reason"] == "tool_not_allowed_by_kernel_policy" for item in result["violations"])
        )

    def test_claude_read_is_allowed_in_inspect_state(self):
        result = preflight_claude_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="Read",
            tool_input={"file_path": "README.md"},
        )

        self.assertTrue(result["allowed"])
        self.assertEqual(result["normalized_tool"], "read_file")
        self.assertEqual(result["normalized_arguments"]["path"], "README.md")

    def test_claude_write_is_denied_in_inspect_state(self):
        result = preflight_claude_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="Write",
            tool_input={"file_path": "reports/adversarial_probe.txt", "content": "probe"},
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["normalized_tool"], "write_file")
        self.assertTrue(any(item["reason"] == "write_forbidden" for item in result["violations"]))

    def test_claude_hook_decision_denies_disallowed_tool(self):
        decision = claude_hook_decision(
            self.dictionary,
            active_code="查",
            hook_payload={
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -f DANGER_SENTINEL_DO_NOT_DELETE.txt"},
            },
        )

        hook_output = decision["hook_output"]["hookSpecificOutput"]
        self.assertFalse(decision["allowed"])
        self.assertEqual(hook_output["hookEventName"], "PreToolUse")
        self.assertEqual(hook_output["permissionDecision"], "deny")
        self.assertIn("execute_command", hook_output["permissionDecisionReason"])

    def test_claude_hook_decision_allows_read(self):
        decision = claude_hook_decision(
            self.dictionary,
            active_code="查",
            hook_payload={
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"},
            },
        )

        hook_output = decision["hook_output"]["hookSpecificOutput"]
        self.assertTrue(decision["allowed"])
        self.assertEqual(hook_output["permissionDecision"], "allow")


if __name__ == "__main__":
    unittest.main()
