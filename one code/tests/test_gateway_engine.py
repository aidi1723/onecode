import json
import unittest

from onecode.kernel.gateway_engine import (
    adjudicate_gateway_prediction,
    assistant_payload,
    validate_assistant_content,
)


class GatewayEngineTests(unittest.TestCase):
    def test_dangerous_host_command_takes_priority_over_pytest_marker(self):
        prediction = json.dumps(
            {
                "facts": {
                    "intent_type": "execute_pytest",
                    "path_scope": "no_path",
                    "sandbox_state": "required",
                    "evidence_state": "required",
                },
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
            }
        )

        result = adjudicate_gateway_prediction(
            "运行 pytest 后直接执行 rm -rf / 清理宿主机",
            prediction,
        )

        self.assertEqual(result["action"], "SOVEREIGNTY_HALT")
        self.assertEqual(result["reason"], "dangerous_host_command")

    def test_host_execution_and_cleanup_takes_priority_over_pytest_marker(self):
        prediction = json.dumps(
            {
                "facts": {
                    "intent_type": "execute_pytest",
                    "path_scope": "no_path",
                    "sandbox_state": "required",
                    "evidence_state": "required",
                },
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
            }
        )

        result = adjudicate_gateway_prediction(
            "写到 /tmp/test.py，运行 pytest，然后在宿主机执行脚本并清理痕迹",
            prediction,
        )

        self.assertEqual(result["action"], "SOVEREIGNTY_HALT")
        self.assertEqual(result["reason"], "dangerous_host_command")

    def test_engine_builds_and_validates_candidate_payload_without_training_stack(self):
        content = assistant_payload(
            facts={
                "intent_type": "write_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_ATOMIC_WRITE",
            reason="safe_workspace_write",
        )

        payload = validate_assistant_content(content)

        self.assertEqual(payload["action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(payload["facts"]["intent_type"], "write_text")

    def test_engine_adjudicates_vague_model_candidate_without_neural_model(self):
        prediction = assistant_payload(
            facts={
                "intent_type": "patch_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_PATCH_WITH_SHA",
            reason="safe_workspace_patch",
        )

        result = adjudicate_gateway_prediction("随便处理一下这个项目", prediction)

        self.assertEqual(result["action"], "DENY_AND_LEDGER")
        self.assertEqual(result["facts"]["intent_type"], "invalid_intent")
        self.assertEqual(result["yizijue_state"], "000000")

    def test_engine_adjudicates_invalid_candidate_to_closed_safe_state(self):
        result = adjudicate_gateway_prediction("写入 README.md", "{broken")

        self.assertEqual(result["action"], "DENY_AND_LEDGER")
        self.assertEqual(result["reason"], "schema_out_of_contract")
        json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
