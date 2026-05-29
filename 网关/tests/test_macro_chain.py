import unittest

from agent_skill_dictionary.gateway_plan import resolve_execution_plan
from agent_skill_dictionary.loader import load_dictionary
from agent_skill_dictionary.macro_chain import compile_macro_chain


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class MacroChainTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_development_request_compiles_to_closed_loop_chain(self):
        chain = compile_macro_chain(
            "帮我写一个高效的异步日志模块，并确保在网络断开时不会丢失日志。"
        )

        self.assertEqual(chain.name, "feature_development_closed_loop")
        self.assertEqual(chain.codes, ["查", "造", "测", "修", "记", "总"])
        self.assertEqual(chain.root_opcodes, ["查", "修", "测", "修", "记", "总"])
        self.assertIn("查 -> 造 -> 测 -> 修 -> 记 -> 总", chain.summary)

    def test_security_risk_request_compiles_to_guard_halt_clarify_inspect(self):
        chain = compile_macro_chain("检测到脚本里有 rm -rf 和未知外联，先安全熔断并让人确认。")

        self.assertEqual(chain.name, "security_meltdown_closed_loop")
        self.assertEqual(chain.codes, ["卫", "停", "问", "查", "总"])
        self.assertEqual(chain.root_opcodes, ["卫", "停", "问", "查", "总"])

    def test_resolve_execution_plan_includes_macro_chain(self):
        plan = resolve_execution_plan(
            "帮我实现一个新接口，写完后跑测试并记录文档。",
            self.dictionary,
        )

        self.assertEqual(plan["macro_chain"]["codes"], ["查", "造", "测", "修", "记", "总"])
        self.assertEqual(plan["macro_chain"]["root_opcodes"], ["查", "修", "测", "修", "记", "总"])
        self.assertEqual(plan["macro_chain"]["initial_active_code"], "查")


if __name__ == "__main__":
    unittest.main()
