import unittest

from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.tool_guard import preflight_tool_call


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class ToolPreflightTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_preflight_blocks_write_for_inspect(self):
        result = preflight_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="write_file",
            arguments={"path": "app.py"},
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["active_code"], "查")
        self.assertEqual(result["violations"][0]["reason"], "write_forbidden")

    def test_preflight_allows_read_for_inspect(self):
        result = preflight_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="read_file",
            arguments={"path": "app.py"},
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["violations"], [])

    def test_preflight_allows_native_inspect_card_for_inspect(self):
        result = preflight_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="native_inspect_card",
            arguments={"target": "sync_node.py"},
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["violations"], [])

    def test_preflight_blocks_tool_outside_root_allowlist(self):
        result = preflight_tool_call(
            self.dictionary,
            active_code="查",
            tool_name="execute_command",
            arguments={"command": "ls"},
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["root_opcode"], "查")
        self.assertEqual(result["violations"][0]["reason"], "tool_not_allowed_by_kernel_policy")

    def test_preflight_blocks_unknown_execution_code(self):
        result = preflight_tool_call(
            self.dictionary,
            active_code="未知",
            tool_name="read_file",
            arguments={"path": "app.py"},
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["violations"][0]["reason"], "unknown_execution_code")


if __name__ == "__main__":
    unittest.main()
