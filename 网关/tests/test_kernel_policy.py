import unittest

from agent_skill_dictionary.gateway_core import should_halt_model_forwarding
from agent_skill_dictionary.gateway_core import rewrite_chat_completion_request
from agent_skill_dictionary.kernel_policy import (
    ROOT_KERNEL_CODES,
    filter_allowed_tools,
    get_kernel_policy,
    verify_evidence_chain,
)
from agent_skill_dictionary.loader import load_dictionary


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class KernelPolicyTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_every_root_opcode_has_kernel_policy(self):
        self.assertEqual(ROOT_KERNEL_CODES, {"查", "修", "测", "卫", "停", "问", "记", "总"})
        for code in ROOT_KERNEL_CODES:
            with self.subTest(code=code):
                policy = get_kernel_policy(code)
                self.assertEqual(policy.code, code)
                self.assertIsInstance(policy.hexagram, str)
                self.assertIsInstance(policy.allowed_tools, tuple)
                self.assertGreaterEqual(len(policy.evidence_required), 1)
                self.assertIn("temperature", policy.model_overrides)

    def test_filter_allowed_tools_physically_removes_unlisted_tools(self):
        tools = [
            {"type": "function", "function": {"name": "read_file"}},
            {"type": "function", "function": {"name": "write_file"}},
            {"type": "function", "function": {"name": "grep_code"}},
        ]

        filtered = filter_allowed_tools(tools, get_kernel_policy("查"))

        names = [tool["function"]["name"] for tool in filtered]
        self.assertEqual(names, ["read_file", "grep_code"])

    def test_rewrite_request_filters_tools_and_injects_kernel_rule(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "查：看看这个模块结构"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "查")
        self.assertEqual(metadata["kernel_policy"]["hexagram"], "离")
        self.assertEqual(rewritten["temperature"], 0.0)
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["read_file"])
        self.assertIn("内核行为规训", rewritten["messages"][0]["content"])
        self.assertIn("绝对只读模式", rewritten["messages"][0]["content"])

    def test_summary_policy_only_allows_context_compression_tool(self):
        tools = [
            {"type": "function", "function": {"name": "read_file"}},
            {"type": "function", "function": {"name": "compress_tokens"}},
            {"type": "function", "function": {"name": "grep_code"}},
        ]

        filtered = filter_allowed_tools(tools, get_kernel_policy("总"))

        self.assertEqual([tool["function"]["name"] for tool in filtered], ["compress_tokens"])

    def test_halt_policy_blocks_model_forwarding(self):
        policy = get_kernel_policy("停")
        self.assertTrue(policy.halt_model_forwarding)
        self.assertEqual(policy.allowed_tools, ())

    def test_rewrite_halt_request_marks_model_forwarding_as_blocked(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "停一下，触发熔断等待人工确认。"}],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "停")
        self.assertTrue(should_halt_model_forwarding(metadata))
        self.assertEqual(rewritten.get("tools"), None)

    def test_evidence_verifier_rejects_missing_required_fields(self):
        policy = get_kernel_policy("测")
        missing = verify_evidence_chain(policy, {"Test_Stdout_Log": "ok"})
        complete = verify_evidence_chain(
            policy,
            {
                "Test_Stdout_Log": "ok",
                "Coverage_Percentage": 91,
                "Exit_Code": 0,
            },
        )

        self.assertFalse(missing.allowed)
        self.assertEqual(missing.missing_fields, ["Coverage_Percentage", "Exit_Code"])
        self.assertTrue(complete.allowed)


if __name__ == "__main__":
    unittest.main()
