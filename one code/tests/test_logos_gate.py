import time
import unittest
import tempfile
from pathlib import Path

from onecode.kernel.action_intent import ActionIntent
from onecode.kernel.context import create_context
from onecode.kernel.logos_gate import LogosGate
from onecode.kernel.permission_matrix import Decision


class LogosGateTests(unittest.TestCase):
    def test_run_bounded_action_returns_completed_result(self):
        gate = LogosGate(http_timeout_seconds=1)

        result = gate.run_bounded_action(lambda: {"value": 42})

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["partial"])
        self.assertIsNone(result["reason"])
        self.assertEqual(result["payload"], {"value": 42})

    def test_run_bounded_action_halts_on_timeout(self):
        gate = LogosGate(http_timeout_seconds=0.01)

        result = gate.run_bounded_action(lambda: time.sleep(0.05))

        self.assertEqual(result["status"], "halted")
        self.assertTrue(result["partial"])
        self.assertEqual(result["reason"], "http_timeout")
        self.assertEqual(result["payload"], {})

    def test_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            LogosGate(http_timeout_seconds=0)


class LogosGatePreflightTests(unittest.TestCase):
    def test_preflight_allows_scoped_write_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="preflight-allowed")
            gate = LogosGate(http_timeout_seconds=1)

            decision = gate.preflight(context, ActionIntent.write_text("src/a.py", "x"))

            self.assertEqual(decision.decision, Decision.ALLOWED)
            self.assertIsNone(decision.reason)
            self.assertEqual(decision.intent_type, "write_text")
            self.assertEqual(decision.evidence_required, ["path", "sha256"])

    def test_preflight_denies_bash_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="preflight-denied")
            gate = LogosGate(http_timeout_seconds=1)

            decision = gate.preflight(context, ActionIntent.bash_execution("echo no"))

            self.assertEqual(decision.decision, Decision.DENIED)
            self.assertEqual(decision.reason, "permission_denied")

    def test_preflight_halts_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="preflight-halted")
            gate = LogosGate(http_timeout_seconds=1)

            decision = gate.preflight(context, ActionIntent.write_text("../outside.txt", "blocked"))

            self.assertEqual(decision.decision, Decision.HALTED)
            self.assertEqual(decision.reason, "sovereignty_breach")


if __name__ == "__main__":
    unittest.main()
