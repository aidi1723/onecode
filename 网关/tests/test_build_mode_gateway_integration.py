import os
import unittest

from agent_skill_dictionary.gateway_server import apply_build_mode_request_policy
from agent_skill_dictionary.build_mode_intent import resolve_intent
from agent_skill_dictionary.build_mode_permissions import filter_tools_schema
from agent_skill_dictionary.build_mode_types import HEX_CREATE, HEX_PROMPT


class BuildModeGatewayIntegrationTest(unittest.TestCase):
    def test_feature_flag_can_route_build_task_to_create_permissions(self):
        os.environ["ONEWORD_BUILD_MODE"] = "1"
        evidence = resolve_intent({"messages": [{"role": "user", "content": "创建一个 FastAPI 项目并运行 pytest"}]})
        tools = [
            {"type": "function", "function": {"name": "write_file", "description": "x"}},
            {"type": "function", "function": {"name": "run_pytest", "description": "x"}},
        ]
        filtered = filter_tools_schema(evidence.hexagram, tools)
        self.assertEqual(evidence.hexagram, HEX_CREATE)
        self.assertEqual([item["function"]["name"] for item in filtered], ["write_file"])
        os.environ.pop("ONEWORD_BUILD_MODE", None)

    def test_feature_flag_can_route_prompt_to_zero_tools(self):
        evidence = resolve_intent({"messages": [{"role": "user", "content": "解释一下这个项目"}]})
        self.assertEqual(evidence.hexagram, HEX_PROMPT)
        self.assertEqual(filter_tools_schema(evidence.hexagram, [{"type": "function", "function": {"name": "write_file"}}]), [])

    def test_gateway_policy_is_noop_without_feature_flag(self):
        os.environ.pop("ONEWORD_BUILD_MODE", None)
        payload = {
            "messages": [{"role": "user", "content": "创建一个项目"}],
            "tools": [{"type": "function", "function": {"name": "run_pytest", "description": "x"}}],
        }
        rewritten, metadata = apply_build_mode_request_policy(payload, {})
        self.assertEqual(rewritten, payload)
        self.assertEqual(metadata, {})

    def test_gateway_policy_filters_tools_with_feature_flag(self):
        os.environ["ONEWORD_BUILD_MODE"] = "1"
        payload = {
            "messages": [{"role": "user", "content": "创建一个项目并运行 pytest"}],
            "tools": [
                {"type": "function", "function": {"name": "write_file", "description": "x"}},
                {"type": "function", "function": {"name": "run_pytest", "description": "x"}},
            ],
        }
        rewritten, metadata = apply_build_mode_request_policy(payload, {})
        self.assertEqual([item["function"]["name"] for item in rewritten["tools"]], ["write_file"])
        self.assertEqual(metadata["oneword_build_mode"]["hexagram"], HEX_CREATE)
        os.environ.pop("ONEWORD_BUILD_MODE", None)


if __name__ == "__main__":
    unittest.main()
