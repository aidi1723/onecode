import json
import unittest
from unittest.mock import patch

from onecode.kernel.model_provider import (
    ModelProviderTimeout,
    OpenAIChatCompletionsProvider,
    OpenAIResponsesProvider,
    json_object_from_model_text,
    validate_model_plan,
)


def system_contract(payload: dict) -> str:
    if "input" in payload:
        return payload["input"][0]["content"]
    return payload["messages"][0]["content"]


class ModelProviderContractTests(unittest.TestCase):
    def test_both_providers_receive_same_tools_and_safe_agent_context(self):
        planning_context = {
            "task_mode": "read_task",
            "safe_agent": {
                "schema_version": 2,
                "selected_skills": ["code-test-regression"],
                "safety_boundary": "method_only",
            },
        }

        responses = OpenAIResponsesProvider("key").request_payload(
            "check", model="m", planning_context=planning_context
        )
        chat = OpenAIChatCompletionsProvider("key").request_payload(
            "check", model="m", planning_context=planning_context
        )

        self.assertEqual(system_contract(responses), system_contract(chat))
        contract = system_contract(responses)
        self.assertIn("read_text", contract)
        self.assertIn("run_command", contract)
        self.assertIn("code-test-regression", contract)
        self.assertIn("method_only", contract)
        self.assertNotIn("API key", contract)

    def test_chat_plan_accepts_json_wrapped_in_fences(self):
        provider = OpenAIChatCompletionsProvider("key", endpoint="https://example.test/v1/chat/completions")
        plan = provider.parse_response(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "```json\n"
                            '{"task": "write", "assets": [{"path": "src/a.py", "content": "x = 1\\n"}]}\n'
                            "```"
                        },
                    }
                ]
            }
        )

        self.assertEqual(plan.task, "write")
        self.assertEqual(plan.assets[0].content, "x = 1\n")

    def test_chat_plan_reads_text_blocks(self):
        provider = OpenAIChatCompletionsProvider("key", endpoint="https://example.test/v1/chat/completions")
        plan = provider.parse_response(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": '{"task": "write", "assets": [{"path": "src/a.py", "content": "y = 1\\n"}]}',
                                }
                            ]
                        },
                    }
                ]
            }
        )

        self.assertEqual(plan.assets[0].path, "src/a.py")

    def test_truncated_chat_plan_names_the_cutoff(self):
        provider = OpenAIChatCompletionsProvider("key", endpoint="https://example.test/v1/chat/completions")
        with self.assertRaisesRegex(ValueError, "model response was truncated"):
            provider.parse_response(
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": '{"task": "write", "assets": ['},
                        }
                    ]
                }
            )

    def test_unclosed_plan_text_is_truncated(self):
        with self.assertRaisesRegex(ValueError, "model response was truncated"):
            json_object_from_model_text('{"task": "write", "assets": [')

    def test_plan_json_can_follow_a_short_preface(self):
        payload = json_object_from_model_text(
            'plan follows\n{"task": "explain", "no_action": {"reason": "none"}}\n'
        )

        self.assertEqual(payload["task"], "explain")

    def test_pytest_and_relative_imports_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not import pytest"):
            validate_model_plan(
                {"task": "test", "assets": [{"path": "tests/test_a.py", "content": "import pytest\n"}]}
            )
        with self.assertRaisesRegex(ValueError, "must not use a relative import"):
            validate_model_plan(
                {
                    "task": "test",
                    "assets": [{"path": "src/rooms.py", "content": "from .intervals import overlaps\n"}],
                }
            )

    def test_src_import_requires_the_module_in_the_plan(self):
        with self.assertRaisesRegex(ValueError, "imports missing module cart"):
            validate_model_plan(
                {
                    "task": "test",
                    "assets": [{"path": "tests/test_cart.py", "content": "from src.cart import Cart\n"}],
                }
            )
        plan = validate_model_plan(
            {
                "task": "test",
                "assets": [
                    {"path": "src/cart.py", "content": "class Cart:\n    pass\n"},
                    {"path": "tests/test_cart.py", "content": "from src.cart import Cart\n"},
                ],
            }
        )

        self.assertEqual(len(plan.assets), 2)

    def test_model_plan_accepts_explicit_no_action(self):
        plan = validate_model_plan(
            {"task": "explain", "no_action": {"reason": "no workspace action"}}
        )

        self.assertEqual(plan.no_action_reason, "no workspace action")
        self.assertEqual(plan.assets, [])
        self.assertEqual(plan.execution_steps, [])

    def test_planning_contract_is_json_serializable(self):
        payload = OpenAIChatCompletionsProvider("key").request_payload(
            "check",
            model="m",
            planning_context={"task_mode": "read_task", "safe_agent": {"schema_version": 2}},
        )

        json.dumps(payload)


class ModelProviderTimeoutTests(unittest.TestCase):
    def test_responses_timeout_is_typed(self):
        provider = OpenAIResponsesProvider("key", endpoint="http://model.test/responses")
        with patch("onecode.kernel.model_provider._SAFE_OPENER.open", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(ModelProviderTimeout, "model request timed out"):
                provider.create_plan("check", model="m", http_timeout_seconds=1)

    def test_chat_timeout_is_typed(self):
        provider = OpenAIChatCompletionsProvider(
            "key", endpoint="http://model.test/chat/completions"
        )
        with patch("onecode.kernel.model_provider._SAFE_OPENER.open", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(ModelProviderTimeout, "model request timed out"):
                provider.create_plan("check", model="m", http_timeout_seconds=1)


if __name__ == "__main__":
    unittest.main()
