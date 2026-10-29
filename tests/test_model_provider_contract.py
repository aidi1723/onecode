import json
import os
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
        content = payload["input"][0]["content"]
        if isinstance(content, list):
            return str(content[0]["text"])
        return str(content)
    return str(payload["messages"][0]["content"])


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
        self.assertIn("execution_plan.steps", contract)

    def test_asset_prompt_drops_execution_plan_and_unittest_when_the_file_is_not_a_test(self):
        from onecode.kernel.model_loop import initial_asset_prompt
        from onecode.kernel.model_provider import canonical_planning_prompt

        prompt = initial_asset_prompt("fix the fee", "src/fee.py")
        system = canonical_planning_prompt(task=prompt)
        self.assertIn("Do not import unittest", prompt)
        self.assertNotIn("Use unittest, not pytest.", prompt)
        self.assertNotIn("execution_plan.steps", system)
        self.assertNotIn("unittest module", system)
        kept = canonical_planning_prompt(task="check the repository")
        self.assertIn("execution_plan.steps", kept)
        self.assertIn("unittest module", kept)

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
                {"task": "test", "assets": [{"path": "src/a.py", "content": "import pytest\n"}]}
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
                    "assets": [{"path": "src/checkout.py", "content": "from src.cart import Cart\n"}],
                }
            )
        plan = validate_model_plan(
            {
                "task": "test",
                "assets": [{"path": "src/checkout.py", "content": "from src.cart import Cart\n"}],
            },
            known_modules={"cart"},
        )
        self.assertEqual(plan.assets[0].path, "src/checkout.py")
        plan = validate_model_plan(
            {
                "task": "test",
                "assets": [
                    {"path": "src/cart.py", "content": "class Cart:\n    pass\n"},
                    {"path": "src/checkout.py", "content": "from src.cart import Cart\n"},
                ],
            }
        )

        self.assertEqual(len(plan.assets), 2)

    def test_empty_patch_replace_block_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "replace_block must be a non-empty string"):
            validate_model_plan(
                {
                    "task": "edit",
                    "patches": [{"path": "src/a.py", "search_block": "x = 1\n", "replace_block": ""}],
                }
            )

    def test_model_plan_accepts_explicit_no_action(self):
        plan = validate_model_plan(
            {"task": "explain", "no_action": {"reason": "no workspace action"}}
        )

        self.assertEqual(plan.no_action_reason, "no workspace action")
        self.assertEqual(plan.assets, [])
        self.assertEqual(plan.execution_steps, [])

    def test_responses_payload_can_drop_schema_for_a_gateway_cache_key(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ONECODE_PROMPT_CACHE_KEY", None)
            os.environ.pop("ONECODE_RESPONSES_TEXT_FORMAT", None)
            default_payload = OpenAIResponsesProvider("key").request_payload("check", model="m")
        self.assertEqual(
            default_payload["input"][1]["content"],
            [{"type": "input_text", "text": "check"}],
        )
        self.assertNotIn("prompt_cache_key", default_payload)
        self.assertEqual(default_payload["text"]["format"]["type"], "json_schema")

        with patch.dict(
            os.environ,
            {"ONECODE_PROMPT_CACHE_KEY": "any", "ONECODE_RESPONSES_TEXT_FORMAT": "off"},
        ):
            plain = OpenAIResponsesProvider("key").request_payload("check", model="m")
        self.assertEqual(plain["prompt_cache_key"], "any")
        self.assertNotIn("text", plain)
        self.assertFalse(plain["stream"])

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

    def test_chat_text_completion_sends_the_onecode_user_agent(self):
        from onecode.kernel.model_provider import complete_model_text

        captured: dict[str, object] = {}

        class Response:
            def read(self, _size: int = -1) -> bytes:
                return json.dumps({"choices": [{"message": {"content": "{\"tools\":[]}"}}]}).encode("utf-8")

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

        def opener(request, timeout):  # type: ignore
            captured["agent"] = request.get_header("User-agent")
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        with patch("onecode.kernel.model_provider._SAFE_OPENER.open", side_effect=opener):
            text = complete_model_text(
                provider_kind="chat",
                endpoint="http://model.test/v1/chat/completions",
                model="m",
                api_key="key",
                prompt="read the fare",
                timeout_seconds=0.1,
            )

        self.assertEqual(text, '{"tools":[]}')
        self.assertEqual(captured["agent"], "onecode/0.8")
        self.assertEqual(captured["timeout"], 0.1)
        self.assertIn("read the fare", captured["body"]["messages"][0]["content"])

    def test_origin_error_is_retried_once(self):
        import io
        import urllib.error

        from onecode.kernel.model_provider import _post_model_json

        calls = {"count": 0}

        class Response:
            def read(self, _size: int = -1) -> bytes:
                return b'{"ok": true}'

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

        def opener(_request, timeout):  # type: ignore
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.HTTPError(
                    "https://example.test",
                    520,
                    "Origin Error",
                    hdrs=None,
                    fp=io.BytesIO(b""),
                )
            return Response()

        with patch("onecode.kernel.model_provider._SAFE_OPENER.open", side_effect=opener):
            payload = _post_model_json("https://example.test/v1/responses", "key", {"model": "m"}, 1)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(calls["count"], 2)

    def test_origin_error_is_retried_twice(self):
        import io
        import urllib.error

        from onecode.kernel.model_provider import _post_model_json

        calls = {"count": 0}

        class Response:
            def read(self, _size: int = -1) -> bytes:
                return b'{"ok": true}'

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *_args: object) -> bool:
                return False

        def opener(_request, timeout):  # type: ignore
            del timeout
            calls["count"] += 1
            if calls["count"] < 3:
                raise urllib.error.HTTPError(
                    "https://example.test",
                    520,
                    "Origin Error",
                    hdrs=None,
                    fp=io.BytesIO(b""),
                )
            return Response()

        with patch("onecode.kernel.model_provider._SAFE_OPENER.open", side_effect=opener):
            payload = _post_model_json("https://example.test/v1/responses", "key", {"model": "m"}, 1)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(calls["count"], 3)


if __name__ == "__main__":
    unittest.main()
