import json
import unittest
from pathlib import Path

from agent_skill_dictionary.kernel_policy import ROOT_KERNEL_CODES
from agent_skill_dictionary.minimal_gateway_core import resolve_with_oneword_dict, rewrite_with_oneword_dict


ONEWORD_DICT_PATH = Path("agent_skill_dictionary/oneword_dict.json")


class MinimalGatewayMvpTest(unittest.TestCase):
    def test_oneword_dict_file_contains_eight_root_kernel_entries(self):
        data = json.loads(ONEWORD_DICT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(set(data["roots"]), ROOT_KERNEL_CODES)
        for code in ROOT_KERNEL_CODES:
            with self.subTest(code=code):
                entry = data["roots"][code]
                self.assertIn("system_prompt", entry)
                self.assertIn("temperature", entry)
                self.assertIn("allowed_tools", entry)
                self.assertIn("evidence_required", entry)
                self.assertIn("control_vector", entry)

    def test_minimal_gateway_filters_readonly_tools_for_inspect(self):
        body = {
            "model": "gpt-test",
            "temperature": 0.9,
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
                {"type": "function", "function": {"name": "grep_code"}},
            ],
        }

        rewritten, metadata = rewrite_with_oneword_dict(body)

        self.assertEqual(metadata["active_code"], "查")
        self.assertEqual(metadata["hexagram"], "离")
        self.assertEqual(rewritten["temperature"], 0.0)
        self.assertEqual(
            [tool["function"]["name"] for tool in rewritten["tools"]],
            ["read_file", "grep_code"],
        )
        self.assertIn("一字诀 MVP 网关已接管请求", rewritten["messages"][0]["content"])

    def test_minimal_gateway_halts_without_model_forwarding(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "停一下，人工确认后再继续"}],
        }

        _, metadata = rewrite_with_oneword_dict(body)

        self.assertEqual(metadata["active_code"], "停")
        self.assertTrue(metadata["halt_model_forwarding"])

    def test_minimal_gateway_maps_review_to_readonly_inspect_and_filters_tools(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "审：审查这个项目有没有风险"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
                {"type": "function", "function": {"name": "grep_code"}},
            ],
        }

        rewritten, metadata = rewrite_with_oneword_dict(body)

        self.assertEqual(metadata["active_code"], "查")
        self.assertEqual(metadata["requested_code"], "审")
        self.assertEqual(metadata["hexagram"], "离")
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["read_file", "grep_code"])

    def test_minimal_gateway_routes_low_confidence_to_prompt_state(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "帮我处理一下这个事情"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "send_user_message"}},
            ],
        }

        rewritten, metadata = rewrite_with_oneword_dict(body)

        self.assertEqual(metadata["active_code"], "问")
        self.assertLess(metadata["confidence"], 0.75)
        self.assertEqual(metadata["compile_reason"], "low_confidence_to_prompt")
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["send_user_message"])

    def test_resolve_with_oneword_dict_exposes_plan_without_upstream_call(self):
        plan = resolve_with_oneword_dict("审：审查这个项目有没有风险")

        self.assertEqual(plan["active_code"], "查")
        self.assertEqual(plan["requested_code"], "审")
        self.assertEqual(plan["hexagram"], "离")
        self.assertEqual(
            plan["allowed_tools"],
            ["native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"],
        )

    def test_summary_state_only_exposes_context_compression_tool(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "总：压缩上下文"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "compress_tokens"}},
                {"type": "function", "function": {"name": "grep_code"}},
            ],
        }

        rewritten, metadata = rewrite_with_oneword_dict(body)

        self.assertEqual(metadata["active_code"], "总")
        self.assertEqual(metadata["allowed_tools"], ["compress_tokens"])
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["compress_tokens"])


if __name__ == "__main__":
    unittest.main()
