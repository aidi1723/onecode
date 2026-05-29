import unittest

from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.loader import load_dictionary, lookup_entry
from agent_skill_dictionary.validator import validate_dictionary


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"
ROOT_OPCODES = {"查", "修", "测", "卫", "停", "问", "记", "总"}


class OpcodePrimitivesTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_root_opcodes_exist_and_point_to_themselves(self):
        codes = {entry["code"] for entry in self.dictionary["entries"]}
        self.assertTrue(ROOT_OPCODES.issubset(codes))
        for code in ROOT_OPCODES:
            entry = lookup_entry(self.dictionary, code).raw
            self.assertEqual(entry["root_opcode"], code)

    def test_every_entry_has_opcode_fields(self):
        for entry in self.dictionary["entries"]:
            with self.subTest(code=entry["code"]):
                self.assertIn(entry["root_opcode"], ROOT_OPCODES)
                self.assertIsInstance(entry["opcode_vector"], dict)
                self.assertIsInstance(entry["inheritance_policy"], dict)
                self.assertGreaterEqual(len(entry["six_phase_workflow"]), 6)
                self.assertIsInstance(entry["transition_policy"], dict)

    def test_known_child_opcode_mapping(self):
        expected = {
            "解": "查",
            "审": "查",
            "源": "查",
            "搜": "查",
            "评": "查",
            "造": "修",
            "改": "修",
            "简": "修",
            "设": "修",
            "合": "卫",
            "隔": "卫",
            "部": "卫",
            "文": "记",
            "数": "记",
        }
        for code, root in expected.items():
            with self.subTest(code=code):
                self.assertEqual(lookup_entry(self.dictionary, code).raw["root_opcode"], root)

    def test_validator_rejects_child_permission_relaxation(self):
        broken = load_dictionary(DICTIONARY_PATH)
        for entry in broken["entries"]:
            if entry["code"] == "解":
                entry["tool_policy"]["write"] = "allowed"
        errors = validate_dictionary(broken)
        self.assertTrue(any("cannot relax root write policy" in error for error in errors))

    def test_gateway_injects_root_opcode_and_six_phase_workflow(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
        }
        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)
        system_message = rewritten["messages"][0]["content"]
        self.assertEqual(metadata["active_code"], "查")
        self.assertEqual(metadata["root_opcode"], "查")
        self.assertFalse(metadata["zero_tool_fast_path"])
        self.assertIn("根字 Opcode: 查", system_message)
        self.assertIn("六步工作流", system_message)
        self.assertIn("状态转移策略", system_message)

    def test_explain_child_opcode_uses_lightweight_zero_tool_prompt(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "解：解释一下这个模块的执行流程"}],
        }
        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)
        system_message = rewritten["messages"][0]["content"]
        self.assertEqual(metadata["active_code"], "解")
        self.assertEqual(metadata["root_opcode"], "查")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertIn("轻量零工具模式", system_message)
        self.assertNotIn("六步工作流", system_message)


if __name__ == "__main__":
    unittest.main()
