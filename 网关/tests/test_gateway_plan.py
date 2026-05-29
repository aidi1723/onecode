import unittest

from agent_skill_dictionary.gateway_plan import resolve_execution_plan
from agent_skill_dictionary.loader import load_dictionary


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class GatewayPlanTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_resolve_execution_plan_for_fix_and_test(self):
        plan = resolve_execution_plan("这个 bug 修一下，然后跑测试确认。", self.dictionary)
        self.assertEqual(plan["codes"], ["修", "测"])
        self.assertEqual(plan["execution_stack"], ["测", "修"])
        self.assertEqual(plan["active_code"], "修")
        self.assertEqual(plan["routing_target"], "debug_fix_workflow")
        self.assertEqual(plan["temperature"], 0.0)
        self.assertTrue(plan["verification_required"])
        self.assertEqual(plan["tool_policy"]["write"], "scoped_to_impact_files")

    def test_resolve_execution_plan_for_source_prefix(self):
        plan = resolve_execution_plan("源：检查依赖和 License 风险", self.dictionary)
        self.assertEqual(plan["codes"], ["源"])
        self.assertEqual(plan["active_code"], "源")
        self.assertEqual(plan["routing_target"], "source_audit_workflow")
        self.assertEqual(plan["tool_policy"]["dependency_install"], "forbidden")


if __name__ == "__main__":
    unittest.main()
