import unittest

from onecode.kernel.action_intent import ActionIntent
from onecode.kernel.hexagram import BUILD_ENTRY
from onecode.kernel.permission_matrix import Decision, PermissionMatrix


class PermissionMatrixTests(unittest.TestCase):
    def test_allows_write_text_in_build_entry_state(self):
        decision = PermissionMatrix().evaluate(BUILD_ENTRY, ActionIntent.write_text("src/a.py", "x"))

        self.assertEqual(decision.decision, Decision.ALLOWED)
        self.assertIsNone(decision.reason)
        self.assertEqual(decision.evidence_required, ["path", "sha256"])

    def test_allows_patch_text_in_build_entry_state(self):
        decision = PermissionMatrix().evaluate(BUILD_ENTRY, ActionIntent.patch_text("src/a.py", "old", "new"))

        self.assertEqual(decision.decision, Decision.ALLOWED)
        self.assertIsNone(decision.reason)
        self.assertEqual(decision.evidence_required, ["path", "sha256"])

    def test_denies_bash_execution_in_build_entry_state(self):
        decision = PermissionMatrix().evaluate(BUILD_ENTRY, ActionIntent.bash_execution("echo no"))

        self.assertEqual(decision.decision, Decision.DENIED)
        self.assertEqual(decision.reason, "permission_denied")
        self.assertEqual(decision.intent_type, "bash_execution")

    def test_denies_execute_pytest_in_build_entry_state(self):
        decision = PermissionMatrix().evaluate(BUILD_ENTRY, ActionIntent.execute_pytest("tests"))

        self.assertEqual(decision.decision, Decision.DENIED)
        self.assertEqual(decision.reason, "permission_denied")

    def test_allows_noop_in_build_entry_state(self):
        decision = PermissionMatrix().evaluate(BUILD_ENTRY, ActionIntent.noop())

        self.assertEqual(decision.decision, Decision.ALLOWED)
        self.assertEqual(decision.evidence_required, [])


if __name__ == "__main__":
    unittest.main()
