import unittest

from agent_skill_dictionary.loader import load_dictionary, lookup_entry
from agent_skill_dictionary.tool_guard import inspect_tool_calls


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class ToolGuardTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_read_only_code_blocks_write_file_tool_call(self):
        entry = lookup_entry(self.dictionary, "查")
        decision = inspect_tool_calls(
            entry,
            [{"name": "write_file", "arguments": {"path": "app.py"}}],
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.violations[0]["tool"], "write_file")
        self.assertEqual(decision.violations[0]["reason"], "write_forbidden")

    def test_source_code_blocks_dependency_install(self):
        entry = lookup_entry(self.dictionary, "源")
        decision = inspect_tool_calls(
            entry,
            [{"name": "install_dependency", "arguments": {"package": "leftpad"}}],
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.violations[0]["reason"], "dependency_install_forbidden")

    def test_fix_allows_scoped_write_but_blocks_dependency_install(self):
        entry = lookup_entry(self.dictionary, "修")
        write_decision = inspect_tool_calls(
            entry,
            [{"name": "write_file", "arguments": {"path": "src/app.py"}}],
        )
        install_decision = inspect_tool_calls(
            entry,
            [{"name": "install_dependency", "arguments": {"package": "requests"}}],
        )
        self.assertTrue(write_decision.allowed)
        self.assertFalse(install_decision.allowed)
        self.assertEqual(install_decision.violations[0]["reason"], "dependency_install_forbidden")

    def test_dangerous_shell_command_is_blocked(self):
        entry = lookup_entry(self.dictionary, "修")
        decision = inspect_tool_calls(
            entry,
            [{"name": "run_shell", "arguments": {"command": "rm -rf /tmp/demo"}}],
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.violations[0]["reason"], "dangerous_command")

    def test_unknown_tool_is_blocked_by_default(self):
        entry = lookup_entry(self.dictionary, "查")
        decision = inspect_tool_calls(
            entry,
            [{"name": "unknown_tool", "arguments": {}}],
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.violations[0]["reason"], "unknown_tool")


if __name__ == "__main__":
    unittest.main()
