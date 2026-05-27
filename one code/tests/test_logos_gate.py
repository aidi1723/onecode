import time
import unittest

from onecode.kernel.logos_gate import LogosGate


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


if __name__ == "__main__":
    unittest.main()
