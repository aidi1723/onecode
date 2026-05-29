import unittest

from agent_skill_dictionary.gateway_core import normalize_intent
from agent_skill_dictionary.loader import load_dictionary, lookup_entry


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class Phase2DictionaryTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_phase2_execution_codes_exist(self):
        for code in ["部", "数", "文", "合", "搜"]:
            with self.subTest(code=code):
                self.assertEqual(lookup_entry(self.dictionary, code).code, code)

    def test_deploy_intent_maps_to_deploy_code(self):
        result = normalize_intent("帮我部署一下这个服务，检查 CI 发布流程", self.dictionary)
        self.assertIn("部", result.codes)

    def test_data_intent_maps_to_data_code(self):
        result = normalize_intent("清洗这个 CSV 表格并整理数据", self.dictionary)
        self.assertIn("数", result.codes)

    def test_docs_intent_maps_to_docs_code(self):
        result = normalize_intent("帮我补一份 README 和接口文档", self.dictionary)
        self.assertIn("文", result.codes)

    def test_compliance_intent_maps_to_compliance_code(self):
        result = normalize_intent("检查一下许可证和合规风险", self.dictionary)
        self.assertIn("合", result.codes)

    def test_search_intent_maps_to_search_code(self):
        result = normalize_intent("搜索外部资料并查找相关文档", self.dictionary)
        self.assertIn("搜", result.codes)

    def test_compliance_is_read_only(self):
        compliance = lookup_entry(self.dictionary, "合")
        self.assertEqual(compliance.tool_policy["write"], "forbidden")
        self.assertEqual(compliance.tool_policy["dependency_install"], "forbidden")

    def test_search_requires_network_approval(self):
        search = lookup_entry(self.dictionary, "搜")
        self.assertEqual(search.tool_policy["network"], "approval_required")
        self.assertEqual(search.tool_policy["write"], "forbidden")


if __name__ == "__main__":
    unittest.main()
