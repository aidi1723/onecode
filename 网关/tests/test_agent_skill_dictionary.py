from pathlib import Path
import unittest

from agent_skill_dictionary import load_dictionary, lookup_entry
from agent_skill_dictionary.validator import validate_dictionary, validate_project_files


DICTIONARY_PATH = Path("agent_skill_dictionary/programming-agent-skill-dictionary.json")


class AgentSkillDictionaryTest(unittest.TestCase):
    def setUp(self):
        self.data = load_dictionary(DICTIONARY_PATH)

    def test_dictionary_validates_without_errors(self):
        self.assertEqual(validate_dictionary(self.data), [])

    def test_project_validation_includes_guard_policy(self):
        self.assertEqual(validate_project_files(), [])

    def test_project_validation_includes_trigram_contract(self):
        self.assertEqual(validate_project_files(), [])

    def test_source_code_is_read_only_and_blocks_dependency_install(self):
        source = lookup_entry(self.data, "源")
        self.assertEqual(source.tool_policy["write"], "forbidden")
        self.assertEqual(source.tool_policy["dependency_install"], "forbidden")
        self.assertEqual(source.routing_target, "source_audit_workflow")

    def test_guard_code_is_distinct_from_source_code(self):
        source = lookup_entry(self.data, "源")
        guard = lookup_entry(self.data, "卫")
        self.assertEqual(source.routing_target, "source_audit_workflow")
        self.assertEqual(guard.routing_target, "security_guard_workflow")
        self.assertIn("license_review", source.raw["bound_skill_patterns"])
        self.assertIn("dangerous_action_blocking", guard.raw["bound_skill_patterns"])

    def test_fix_melts_down_to_inspect_after_retries(self):
        fix = lookup_entry(self.data, "修")
        self.assertEqual(fix.model_policy["max_retry_limit"], 3)
        self.assertEqual(fix.fallback["on_max_retry_exceeded"], "MELT_DOWN_TO_查")

    def test_read_only_codes_forbid_write(self):
        for code in ["查", "审", "源", "卫", "隔"]:
            entry = lookup_entry(self.data, code)
            self.assertEqual(entry.tool_policy["write"], "forbidden")


if __name__ == "__main__":
    unittest.main()
