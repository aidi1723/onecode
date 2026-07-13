import json
import unittest

from onecode.kernel.model_provider import (
    OpenAIChatCompletionsProvider,
    OpenAIResponsesProvider,
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


if __name__ == "__main__":
    unittest.main()
