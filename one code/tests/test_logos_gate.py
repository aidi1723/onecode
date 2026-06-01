import time
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

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

    def test_run_bounded_action_halts_on_action_exception(self):
        gate = LogosGate(http_timeout_seconds=1)

        def failing_action():
            raise RuntimeError("disk write failed")

        result = gate.run_bounded_action(failing_action)

        self.assertEqual(result["status"], "halted")
        self.assertTrue(result["partial"])
        self.assertEqual(result["reason"], "action_exception")
        self.assertEqual(result["payload"]["error_type"], "RuntimeError")
        self.assertEqual(result["payload"]["error_message_tail"], "disk write failed")

    def test_timeout_rebuilds_executor_before_next_action(self):
        gate = LogosGate(http_timeout_seconds=0.05)
        try:
            timed_out = gate.run_bounded_action(lambda: time.sleep(0.3))
            recovered = gate.run_bounded_action(lambda: {"value": "fresh"})
        finally:
            gate.close()

        self.assertEqual(timed_out["reason"], "http_timeout")
        self.assertEqual(recovered["status"], "completed")
        self.assertEqual(recovered["payload"], {"value": "fresh"})

    def test_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            LogosGate(http_timeout_seconds=0)

    def test_run_bounded_action_reuses_executor_until_closed(self):
        created = []
        real_executor = __import__("concurrent.futures").futures.ThreadPoolExecutor

        def tracking_executor(*args, **kwargs):
            executor = real_executor(*args, **kwargs)
            created.append(executor)
            return executor

        with patch("onecode.kernel.logos_gate.ThreadPoolExecutor", side_effect=tracking_executor):
            gate = LogosGate(http_timeout_seconds=1)
            self.assertEqual(gate.run_bounded_action(lambda: {"value": 1})["status"], "completed")
            self.assertEqual(gate.run_bounded_action(lambda: {"value": 2})["status"], "completed")
            gate.close()

        self.assertEqual(len(created), 1)
        self.assertTrue(created[0]._shutdown)

    def test_context_manager_closes_executor(self):
        with LogosGate(http_timeout_seconds=1) as gate:
            self.assertEqual(gate.run_bounded_action(lambda: {"value": 1})["status"], "completed")
            executor = gate._executor

        self.assertIsNotNone(executor)
        self.assertTrue(executor._shutdown)

    def test_executor_pool_uses_configured_capacity(self):
        gate = LogosGate(http_timeout_seconds=1, executor_pool_size=3)

        try:
            self.assertEqual(gate.executor_pool_size, 3)
            self.assertEqual(gate.executor()._max_workers, 3)
        finally:
            gate.close()

    def test_executor_pool_reports_yin_yang_polarity(self):
        gate = LogosGate(http_timeout_seconds=1, executor_pool_size=4)

        try:
            self.assertEqual(
                gate.pool_polarity(busy_count=0),
                {"capacity": 4, "busy": 0, "idle": 4, "delta_phi": -1.0, "flow_control": "activate"},
            )
            self.assertEqual(
                gate.pool_polarity(busy_count=4),
                {"capacity": 4, "busy": 4, "idle": 0, "delta_phi": 1.0, "flow_control": "throttle"},
            )
            self.assertEqual(
                gate.pool_polarity(busy_count=2),
                {"capacity": 4, "busy": 2, "idle": 2, "delta_phi": 0.0, "flow_control": "stable"},
            )
            self.assertEqual(gate.next_executor_slot([1, 0, 1, 0]), 1)
            self.assertIsNone(gate.next_executor_slot([1, 1, 1, 1]))
        finally:
            gate.close()


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

    def test_preflight_allows_scoped_patch_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="preflight-patch-allowed")
            gate = LogosGate(http_timeout_seconds=1)

            decision = gate.preflight(context, ActionIntent.patch_text("src/a.py", "old", "new"))

            self.assertEqual(decision.decision, Decision.ALLOWED)
            self.assertIsNone(decision.reason)
            self.assertEqual(decision.intent_type, "patch_text")
            self.assertEqual(
                decision.evidence_required,
                [
                    "path",
                    "pre_sha256",
                    "post_sha256",
                    "search_block_sha256",
                    "replace_block_sha256",
                ],
            )

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

    def test_preflight_halts_patch_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="preflight-patch-halted")
            gate = LogosGate(http_timeout_seconds=1)

            decision = gate.preflight(context, ActionIntent.patch_text("../outside.txt", "old", "new"))

            self.assertEqual(decision.decision, Decision.HALTED)
            self.assertEqual(decision.reason, "sovereignty_breach")


if __name__ == "__main__":
    unittest.main()
