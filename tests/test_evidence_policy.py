import unittest


class EvidencePolicyTests(unittest.TestCase):
    def test_critical_event_families_default_to_full_capture(self):
        from onecode.kernel.evidence_policy import CaptureMode, RiskTier, classify_event

        for event_type in (
            "approval_decision",
            "path_guard_decision",
            "physical_write",
            "patch_application",
            "verifier_result",
            "task_finalization",
            "resume_classification",
        ):
            with self.subTest(event_type=event_type):
                classification = classify_event(event_type)

                self.assertEqual(classification.risk_tier, RiskTier.CRITICAL)
                self.assertEqual(classification.capture_mode, CaptureMode.FULL)
                self.assertTrue(classification.commit_coupled)

    def test_scheduler_and_heartbeat_events_are_lightweight(self):
        from onecode.kernel.evidence_policy import CaptureMode, RiskTier, classify_event

        scheduler = classify_event("scheduler_state_transition")
        heartbeat = classify_event("heartbeat")

        self.assertEqual(scheduler.risk_tier, RiskTier.MEDIUM)
        self.assertEqual(scheduler.capture_mode, CaptureMode.COMPACT)
        self.assertFalse(scheduler.commit_coupled)
        self.assertEqual(heartbeat.risk_tier, RiskTier.LOW)
        self.assertEqual(heartbeat.capture_mode, CaptureMode.AGGREGATE)
        self.assertFalse(heartbeat.commit_coupled)

    def test_runner_internal_events_are_classified_without_fail_closed_overhead(self):
        from onecode.kernel.evidence_policy import CaptureMode, RiskTier, classify_event

        for event_type in ("tool_call_started", "tool_call_completed", "checkpoint_written"):
            with self.subTest(event_type=event_type):
                classification = classify_event(event_type)

                self.assertEqual(classification.risk_tier, RiskTier.MEDIUM)
                self.assertEqual(classification.capture_mode, CaptureMode.COMPACT)
                self.assertFalse(classification.commit_coupled)

        completed = classify_event("run_completed")
        self.assertEqual(completed.risk_tier, RiskTier.CRITICAL)
        self.assertEqual(completed.capture_mode, CaptureMode.FULL)
        self.assertTrue(completed.commit_coupled)

    def test_unknown_event_family_fails_closed_to_full_critical(self):
        from onecode.kernel.evidence_policy import CaptureMode, RiskTier, classify_event

        classification = classify_event("new_unclassified_runtime_event")

        self.assertEqual(classification.risk_tier, RiskTier.CRITICAL)
        self.assertEqual(classification.capture_mode, CaptureMode.FULL)
        self.assertTrue(classification.commit_coupled)
        self.assertEqual(classification.reason, "unknown_event_family_fail_closed")


if __name__ == "__main__":
    unittest.main()
