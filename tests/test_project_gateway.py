import unittest

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_gateway import project_gateway


def facts(**overrides: str) -> dict[str, str]:
    row = {
        "intent_type": "invalid_intent",
        "path_scope": "no_path",
        "sandbox_state": "not_required",
        "evidence_state": "required",
    }
    row.update(overrides)
    return row


class ProjectGatewayTests(unittest.TestCase):
    def test_pinned_codes_follow_gateway_contract(self):
        self.assertEqual(project_gateway(0b100001, facts(intent_type="bash_execution", path_scope="outside_workspace", sandbox_state="missing")), "SOVEREIGNTY_HALT")
        self.assertEqual(project_gateway(0b100001, facts(intent_type="write_text", path_scope="workspace_relative", evidence_state="present")), "SOVEREIGNTY_HALT")
        self.assertEqual(project_gateway(0b000000, facts()), "DENY_AND_LEDGER")
        self.assertEqual(
            project_gateway(0b111111, facts(intent_type="write_text", path_scope="workspace_relative", evidence_state="present")),
            "ALLOW_ATOMIC_WRITE",
        )
        self.assertEqual(
            project_gateway(0b111111, facts(intent_type="patch_text", path_scope="workspace_relative", sandbox_state="required", evidence_state="present")),
            "ALLOW_PATCH_WITH_SHA",
        )
        self.assertEqual(
            project_gateway(0b010010, facts(intent_type="execute_pytest", sandbox_state="required")),
            "RUN_VERIFIER_IN_SANDBOX",
        )

    def test_build_entry_does_not_allow_outside_write_or_pytest(self):
        self.assertEqual(
            project_gateway(0b111111, facts(intent_type="write_text", path_scope="outside_workspace", evidence_state="present")),
            "DENY_AND_LEDGER",
        )
        self.assertEqual(
            project_gateway(0b111111, facts(intent_type="execute_pytest", sandbox_state="required")),
            "DENY_AND_LEDGER",
        )

    def test_halt_code_is_not_an_allow_and_build_entry_write_is_not_halt(self):
        halt_facts = facts(intent_type="bash_execution", path_scope="outside_workspace", sandbox_state="missing")
        write_facts = facts(intent_type="write_text", path_scope="workspace_relative", evidence_state="present")
        self.assertNotEqual(project_gateway(33, halt_facts), "ALLOW_ATOMIC_WRITE")
        self.assertNotEqual(project_gateway(63, write_facts), "SOVEREIGNTY_HALT")

    def test_unmapped_codes_deny(self):
        for status_code in (1, 7, 32):
            self.assertEqual(project_gateway(status_code, facts()), "DENY_AND_LEDGER")
            self.assertEqual(
                project_gateway(status_code, facts(intent_type="write_text", path_scope="workspace_relative", evidence_state="present")),
                "DENY_AND_LEDGER",
            )

    def test_same_input_returns_one_action(self):
        row = facts(intent_type="patch_text", path_scope="workspace_relative", sandbox_state="required", evidence_state="present")
        self.assertEqual(project_gateway(0b111111, row), project_gateway(0b111111, dict(row)))

    def test_kernel_oracle_stays_separate_from_gateway_actions(self):
        self.assertEqual(IchingKernel.transition(0b100001).action, "activate")
        rewritten = IchingKernel.transition(0b111111)
        self.assertEqual(rewritten.action, "cooldown")
        self.assertEqual(rewritten.status_code, 39)
        self.assertEqual(IchingKernel.transition(0b010010).action, "activate")
        self.assertEqual(IchingKernel.transition(0b000000).action, "discover")

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            project_gateway(True, facts())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            project_gateway(64, facts())
        with self.assertRaises(ValueError):
            project_gateway(0, facts(intent_type="chat"))
        with self.assertRaises(ValueError):
            project_gateway(0, {**facts(), "confidence": "high"})
