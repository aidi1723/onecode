import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.gateway_core import (
    annotate_chat_completion_response,
    block_disallowed_anthropic_response,
    block_disallowed_tool_response,
    build_execution_stack,
    build_stream_tool_block_response,
    StreamBufferInterceptor,
    normalize_intent,
    inject_native_inspect_context,
    rewrite_anthropic_messages_request,
    rewrite_chat_completion_request,
    stream_not_supported_response,
)
from agent_skill_dictionary.kernel_contract import assert_preflight_contract
from agent_skill_dictionary.loader import load_dictionary


DICTIONARY_PATH = "agent_skill_dictionary/programming-agent-skill-dictionary.json"


class GatewayCoreTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = load_dictionary(DICTIONARY_PATH)

    def test_normalize_bug_and_test_request_to_fix_then_test(self):
        result = normalize_intent("这个 bug 修一下，然后跑测试确认。", self.dictionary)
        self.assertEqual(result.codes, ["修", "测"])
        self.assertGreaterEqual(result.confidence, 0.75)

    def test_normalize_build_test_summary_request_starts_with_creation(self):
        result = normalize_intent(
            "实现 ephemeral-mesh-kv 三节点 TTL Mesh 缓存环，跑测试并输出总结。",
            self.dictionary,
        )
        self.assertEqual(result.codes, ["造", "测", "总"])
        self.assertGreaterEqual(result.confidence, 0.75)

    def test_build_execution_stack_pushes_reverse_execution_order(self):
        stack = build_execution_stack(["修", "测"])
        self.assertEqual(stack, ["测", "修"])

    def test_rewrite_chat_request_injects_active_rule_and_locks_temperature(self):
        body = {
            "model": "gpt-test",
            "temperature": 0.8,
            "messages": [
                {"role": "user", "content": "这个 bug 修一下，然后跑测试确认。"}
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["codes"], ["修", "测"])
        self.assertEqual(metadata["execution_stack"], ["测", "修"])
        self.assertEqual(metadata["active_code"], "修")
        self.assertEqual(rewritten["temperature"], 0.0)
        self.assertEqual(rewritten["messages"][0]["role"], "system")
        self.assertIn("执行字: 修", rewritten["messages"][0]["content"])
        self.assertIn("禁止动作", rewritten["messages"][0]["content"])
        self.assertIn("参考工作流模式", rewritten["messages"][0]["content"])
        self.assertIn("专业运行逻辑", rewritten["messages"][0]["content"])
        self.assertEqual(rewritten["messages"][1]["role"], "user")

    def test_rewritten_chat_request_passes_kernel_preflight_contract(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [
                {"type": "function", "function": {"name": "native_inspect_card"}},
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
                {"type": "function", "function": {"name": "execute_command"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["native_inspect_card"])
        assert_preflight_contract(metadata["root_opcode"], rewritten)

    def test_inspect_request_keeps_legacy_read_tool_when_native_card_is_unavailable(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "查")
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["read_file"])

    def test_explain_request_uses_zero_tool_fast_path(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "解：解释一下这个函数是什么意思"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "write_file"}},
                {"type": "function", "function": {"name": "bash"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["active_code"], "解")
        self.assertEqual(metadata["root_opcode"], "查")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertEqual(metadata["hexagram_route"]["action"], "ZERO_TOOL_BYPASS")
        self.assertEqual(metadata["hexagram_route"]["hexagram_code"], "000101")
        self.assertEqual(rewritten["tools"], [])
        self.assertEqual(rewritten["max_tokens"], 150)
        self.assertIn("轻量零工具模式", rewritten["messages"][0]["content"])
        self.assertIn("Max 120 Chinese words", rewritten["messages"][0]["content"])
        self.assertNotIn("根字 Workflow 摘要", rewritten["messages"][0]["content"])
        self.assertLess(len(rewritten["messages"][0]["content"]), 900)

    def test_clarify_request_uses_zero_tool_budgeted_fast_path(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "问：这个需求不明确，请整理成一个简短的澄清问题。"}],
            "tools": [
                {"type": "function", "function": {"name": "send_user_message"}},
                {"type": "function", "function": {"name": "write_file"}},
                {"type": "function", "function": {"name": "bash"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["active_code"], "问")
        self.assertEqual(metadata["root_opcode"], "问")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertEqual(metadata["hexagram_route"]["action"], "ZERO_TOOL_CLARIFY")
        self.assertEqual(metadata["hexagram_route"]["hexagram_code"], "000110")
        self.assertEqual(rewritten["tools"], [])
        self.assertEqual(rewritten["max_tokens"], 150)
        self.assertIn("轻量零工具模式", rewritten["messages"][0]["content"])
        self.assertLess(len(rewritten["messages"][0]["content"]), 900)

    def test_guard_request_routes_to_physical_guard_hexagram(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "卫：检查依赖库有没有高危 CVE"}],
            "tools": [
                {"type": "function", "function": {"name": "dependency_security_scan"}},
                {"type": "function", "function": {"name": "bash"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "卫")
        self.assertEqual(metadata["hexagram_route"]["hexagram_code"], "011010")
        self.assertEqual(metadata["hexagram_route"]["action"], "LAUNCH_PHYSICAL_GUARD")
        self.assertEqual([tool["function"]["name"] for tool in rewritten["tools"]], ["dependency_security_scan"])

    def test_fix_then_test_request_routes_to_isolated_sandbox_hexagram(self):
        body = {
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "这个 bug 修一下，然后跑测试确认。"}],
            "tools": [
                {"type": "function", "function": {"name": "read_file"}},
                {"type": "function", "function": {"name": "edit_scoped_file"}},
                {"type": "function", "function": {"name": "run_pytest"}},
            ],
        }

        rewritten, metadata = rewrite_chat_completion_request(body, self.dictionary)

        self.assertEqual(metadata["codes"], ["修", "测"])
        self.assertEqual(metadata["root_opcode"], "修")
        self.assertEqual(metadata["hexagram_route"]["hexagram_code"], "011100")
        self.assertEqual(metadata["hexagram_route"]["action"], "LAUNCH_ISOLATED_SANDBOX")
        self.assertEqual(
            [tool["function"]["name"] for tool in rewritten["tools"]],
            ["read_file", "edit_scoped_file"],
        )

    def test_rewrite_anthropic_messages_filters_tools_and_injects_system(self):
        body = {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [
                {"name": "native_inspect_card", "input_schema": {"type": "object"}},
                {"name": "read_file", "input_schema": {"type": "object"}},
                {"name": "write_file", "input_schema": {"type": "object"}},
                {"name": "bash", "input_schema": {"type": "object"}},
            ],
        }

        rewritten, metadata = rewrite_anthropic_messages_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "查")
        self.assertIn("一字诀网关已接管本次请求。", rewritten["system"])
        self.assertEqual([tool["name"] for tool in rewritten["tools"]], ["native_inspect_card"])
        self.assertEqual(rewritten["temperature"], 0.0)

    def test_inspect_anthropic_messages_injects_native_tool_for_claude_read_tools(self):
        body = {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [
                {
                    "name": "Read",
                    "description": "Very long Claude Code read tool instructions." * 200,
                    "input_schema": {"type": "object"},
                },
                {
                    "name": "Bash",
                    "description": "Very long Claude Code bash tool instructions." * 200,
                    "input_schema": {"type": "object"},
                },
            ],
        }

        rewritten, metadata = rewrite_anthropic_messages_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "查")
        self.assertEqual([tool["name"] for tool in rewritten["tools"]], ["native_inspect_card"])
        self.assertLess(len(rewritten["tools"][0].get("description", "")), 180)
        self.assertTrue(metadata["shadow_tool_injection"]["applied"])
        self.assertEqual(metadata["shadow_tool_injection"]["source_tools"], ["Bash", "Read"])

    def test_anthropic_explain_request_uses_zero_tool_fast_path(self):
        body = {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "解：解释一下这个函数是什么意思"}],
            "tools": [
                {"name": "read_file", "input_schema": {"type": "object"}},
                {"name": "write_file", "input_schema": {"type": "object"}},
                {"name": "bash", "input_schema": {"type": "object"}},
            ],
        }

        rewritten, metadata = rewrite_anthropic_messages_request(body, self.dictionary)

        self.assertEqual(metadata["active_code"], "解")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertEqual(metadata["hexagram_route"]["action"], "ZERO_TOOL_BYPASS")
        self.assertEqual(rewritten["tools"], [])
        self.assertEqual(rewritten["max_tokens"], 150)
        self.assertIn("轻量零工具模式", rewritten["system"])
        self.assertLess(len(rewritten["system"]), 900)

    def test_anthropic_clarify_request_uses_zero_tool_budgeted_fast_path(self):
        body = {
            "model": "claude-test",
            "messages": [{"role": "user", "content": "问：这个需求不明确，请整理成一个简短的澄清问题。"}],
            "tools": [
                {"name": "send_user_message", "input_schema": {"type": "object"}},
                {"name": "write_file", "input_schema": {"type": "object"}},
                {"name": "bash", "input_schema": {"type": "object"}},
            ],
        }

        rewritten, metadata = rewrite_anthropic_messages_request(body, self.dictionary)

        self.assertEqual(metadata["active_code"], "问")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertEqual(metadata["hexagram_route"]["action"], "ZERO_TOOL_CLARIFY")
        self.assertEqual(rewritten["tools"], [])
        self.assertEqual(rewritten["max_tokens"], 150)
        self.assertIn("轻量零工具模式", rewritten["system"])

    def test_rewrite_anthropic_messages_preserves_existing_system_under_kernel_rule(self):
        body = {
            "model": "claude-test",
            "system": "Existing project instruction.",
            "messages": [{"role": "user", "content": "总结当前进度"}],
            "tools": [{"name": "compress_tokens", "input_schema": {"type": "object"}}],
        }

        rewritten, metadata = rewrite_anthropic_messages_request(body, self.dictionary)

        self.assertEqual(metadata["root_opcode"], "总")
        self.assertIn("一字诀网关已接管本次请求。", rewritten["system"])
        self.assertIn("Existing project instruction.", rewritten["system"])
        self.assertEqual([tool["name"] for tool in rewritten["tools"]], ["compress_tokens"])

    def test_explicit_source_prefix_wins_over_keywords(self):
        result = normalize_intent("源：检查一下依赖和 License 风险", self.dictionary)
        self.assertEqual(result.codes, ["源"])

    def test_control_intents_normalize_to_control_codes(self):
        cases = {
            "这个需求不明确，先问清楚": ["问"],
            "失败太多了，先停一下等人工审批": ["停"],
            "记一下这个架构决策": ["记"],
            "评估一下这个方案靠谱吗": ["评"],
            "总结当前进度，做个交接摘要": ["总"],
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                result = normalize_intent(message, self.dictionary)
                self.assertEqual(result.codes, expected)

    def test_repair_test_summary_request_keeps_sequential_action_order(self):
        result = normalize_intent(
            "修复 sync_node.py 同步死锁 Bug，跑测试，输出架构与风险总结。",
            self.dictionary,
        )

        self.assertEqual(result.codes, ["修", "测", "总"])

    def test_build_request_with_pause_button_does_not_route_to_halt(self):
        result = normalize_intent(
            "造：从零做一个小游戏，必须包含 start、pause、restart 三个按钮，也要有暂停按钮文案。",
            self.dictionary,
        )

        self.assertEqual(result.codes, ["造"])

    def test_unprefixed_build_request_with_pause_button_does_not_route_to_halt(self):
        result = normalize_intent(
            "从零做一个浏览器小游戏，必须包含开始按钮、暂停按钮和重新开始按钮。",
            self.dictionary,
        )

        self.assertIn("造", result.codes)
        self.assertNotEqual(result.codes, ["停"])

    def test_summary_intent_wins_over_design_asset_keyword(self):
        result = normalize_intent("总结并沉淀当前项目的全部设计资产", self.dictionary)

        self.assertEqual(result.codes, ["总"])

    def test_annotate_response_blocks_forbidden_tool_call(self):
        body = {
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
        }
        _, metadata = rewrite_chat_completion_request(body, self.dictionary)
        payload = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": "{\"path\":\"app.py\"}",
                                },
                            }
                        ]
                    }
                }
            ]
        }

        annotated = annotate_chat_completion_response(payload, metadata, self.dictionary)

        self.assertTrue(annotated["yizijue_gateway"]["blocked"])
        self.assertFalse(annotated["yizijue_gateway"]["tool_guard"]["allowed"])
        self.assertEqual(
            annotated["yizijue_gateway"]["tool_guard"]["violations"][0]["reason"],
            "write_forbidden",
        )

    def test_zero_tool_fast_path_skips_response_tool_audit(self):
        body = {
            "messages": [{"role": "user", "content": "解：解释一下这个函数是什么意思"}],
            "tools": [{"type": "function", "function": {"name": "write_file"}}],
        }
        _, metadata = rewrite_chat_completion_request(body, self.dictionary)
        payload = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {"name": "write_file", "arguments": "{}"},
                            }
                        ]
                    }
                }
            ]
        }

        annotated = annotate_chat_completion_response(payload, metadata, self.dictionary)

        self.assertNotIn("blocked", annotated["yizijue_gateway"])
        self.assertTrue(annotated["yizijue_gateway"]["tool_guard"]["allowed"])
        self.assertEqual(annotated["yizijue_gateway"]["tool_guard"]["inspected_tool_calls"], 0)
        self.assertEqual(annotated["yizijue_gateway"]["tool_guard"]["mode"], "bypassed_zero_tool")

    def test_block_disallowed_tool_response_soft_rewrites_tool_calls(self):
        body = {
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
        }
        _, metadata = rewrite_chat_completion_request(body, self.dictionary)
        payload = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": "{\"path\":\"app.py\"}",
                                },
                            }
                        ]
                    }
                }
            ]
        }

        rewritten, status_code = block_disallowed_tool_response(payload, metadata, self.dictionary)

        self.assertEqual(status_code, 200)
        self.assertTrue(rewritten["yizijue_gateway"]["blocked"])
        self.assertEqual(rewritten["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertFalse(rewritten["yizijue_gateway"]["tool_guard"]["allowed"])
        message = rewritten["choices"][0]["message"]
        self.assertNotIn("tool_calls", message)
        self.assertIn("Kernel Notice", message["content"])
        self.assertIn("unauthorized tool execution", message["content"])

    def test_block_disallowed_anthropic_response_soft_rewrites_tool_use(self):
        body = {
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
        }
        _, metadata = rewrite_anthropic_messages_request(body, self.dictionary)
        payload = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I need to edit that file."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "write_file",
                    "input": {"path": "app.py", "content": "unsafe"},
                },
            ],
        }

        rewritten, status_code = block_disallowed_anthropic_response(
            payload,
            metadata,
            self.dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(rewritten["yizijue_gateway"]["blocked"])
        self.assertEqual(rewritten["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertFalse(rewritten["yizijue_gateway"]["tool_guard"]["allowed"])
        self.assertEqual(rewritten["content"][0]["type"], "text")
        self.assertIn("Kernel Notice", rewritten["content"][0]["text"])
        self.assertNotIn("tool_use", str(rewritten["content"]))

    def test_inspect_anthropic_read_tool_use_shadow_rewrites_to_native_card(self):
        body = {
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
        }
        _, metadata = rewrite_anthropic_messages_request(body, self.dictionary)
        payload = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_read",
                    "name": "Read",
                    "input": {"file_path": "README.md"},
                },
            ],
        }

        rewritten, status_code = block_disallowed_anthropic_response(
            payload,
            metadata,
            self.dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(rewritten["yizijue_gateway"]["response_mode"], "shadow_native_inspect")
        self.assertTrue(rewritten["yizijue_gateway"]["shadow_tool_mapping"]["applied"])
        self.assertEqual(rewritten["content"][0]["type"], "text")
        self.assertIn("[State]: 101-INSPECT", rewritten["content"][0]["text"])
        self.assertNotIn("tool_use", str(rewritten["content"]))

    def test_inspect_anthropic_native_tool_use_shadow_rewrites_to_text_card(self):
        body = {
            "messages": [{"role": "user", "content": "查：看看项目结构"}],
            "tools": [{"name": "native_inspect_card", "input_schema": {"type": "object"}}],
        }
        _, metadata = rewrite_anthropic_messages_request(body, self.dictionary)
        payload = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_native",
                    "name": "native_inspect_card",
                    "input": {"target": "sync_node.py"},
                },
            ],
        }

        rewritten, status_code = block_disallowed_anthropic_response(
            payload,
            metadata,
            self.dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(rewritten["yizijue_gateway"]["response_mode"], "shadow_native_inspect")
        self.assertEqual(rewritten["content"][0]["type"], "text")
        self.assertIn("[State]: 101-INSPECT", rewritten["content"][0]["text"])
        self.assertNotIn("tool_use", str(rewritten["content"]))

    def test_native_inspect_context_injection_clears_claude_tools_for_inspect(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "gateway_server.py").write_text(
                "def create_app():\n    return 'ok'\n",
                encoding="utf-8",
            )
            body = {
                "model": "claude-test",
                "messages": [{"role": "user", "content": "查：请输出深入审计报告"}],
                "tools": [
                    {"name": "Read", "input_schema": {"type": "object"}},
                    {"name": "Bash", "input_schema": {"type": "object"}},
                ],
            }
            payload, metadata = rewrite_anthropic_messages_request(body, self.dictionary)
            metadata["workspace"] = str(workspace)

            enriched = inject_native_inspect_context(payload, metadata)

            self.assertEqual(enriched["tools"], [])
            self.assertIn("[State]: 101-INSPECT", enriched["system"])
            self.assertIn("gateway_server.py", enriched["system"])
            self.assertIn("Return the final answer directly", enriched["system"])
            self.assertIn("<function_calls>", enriched["system"])
            self.assertTrue(metadata["native_context_injection"]["applied"])

    def test_inspect_shadow_rewrite_uses_workspace_native_card_when_available(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "sync_node.py").write_text(
                "import httpx\n\nasync def sync_inventory():\n    while True:\n        return None\n",
                encoding="utf-8",
            )
            body = {"messages": [{"role": "user", "content": "查：看看项目结构"}]}
            _, metadata = rewrite_anthropic_messages_request(body, self.dictionary)
            metadata["workspace"] = str(workspace)
            payload = {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "sync_node.py"},
                    }
                ]
            }

            rewritten, status_code = block_disallowed_anthropic_response(
                payload,
                metadata,
                self.dictionary,
            )

            self.assertEqual(status_code, 200)
            text = rewritten["content"][0]["text"]
            self.assertIn("sync_inventory", text)
            self.assertIn("while True", text)
            self.assertLessEqual(len(text), 1200)

    def test_stream_not_supported_response_is_actionable(self):
        payload, status_code = stream_not_supported_response({"active_code": "查"})

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"]["type"], "yizijue_stream_not_supported")
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["active_code"], "查")

    def test_stream_interceptor_blocks_openai_tool_calls_across_chunk_boundary(self):
        interceptor = StreamBufferInterceptor({"active_code": "查", "root_opcode": "查"})

        self.assertIsNone(interceptor.feed(b'data: {"choices":[{"delta":{"tool_'))
        violation = interceptor.feed(b'calls":[{"function":{"name":"write_file"}}]}}]}\n\n')

        self.assertIsNotNone(violation)
        self.assertEqual(violation["type"], "openai_tool_calls")
        self.assertEqual(violation["active_code"], "查")

    def test_stream_interceptor_blocks_anthropic_tool_use(self):
        interceptor = StreamBufferInterceptor({"active_code": "卫", "root_opcode": "卫"})

        violation = interceptor.feed('event: content_block_start\ndata: {"type":"tool_use","name":"bash"}\n\n')

        self.assertIsNotNone(violation)
        self.assertEqual(violation["type"], "anthropic_tool_use")

    def test_stream_interceptor_allows_non_guard_states(self):
        interceptor = StreamBufferInterceptor({"active_code": "修", "root_opcode": "修"})

        violation = interceptor.feed(b'data: {"choices":[{"delta":{"tool_calls":[]}}]}\n\n')

        self.assertIsNone(violation)

    def test_stream_tool_block_response_uses_soft_notice_payload(self):
        payload, status_code = build_stream_tool_block_response(
            {"active_code": "查"},
            {"type": "openai_tool_calls", "active_code": "查"},
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertIn("Kernel Notice", payload["choices"][0]["delta"]["content"])


if __name__ == "__main__":
    unittest.main()
