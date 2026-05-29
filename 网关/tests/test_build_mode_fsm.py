import unittest

from agent_skill_dictionary.build_mode_fsm import guarded_next_hexagram, next_hexagram
from agent_skill_dictionary.build_mode_types import (
    HEX_CORRECT,
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    FeedbackEvidence,
    SandboxEvidence,
    TransitionPlanEvidence,
    ViolationEvidence,
    WriteEvidence,
)


class BuildModeFsmTest(unittest.TestCase):
    def test_create_write_success_goes_to_verify(self):
        evidence = WriteEvidence(True, ("app/main.py",), "/w", "a" * 64)
        self.assertEqual(next_hexagram(HEX_CREATE, evidence), HEX_VERIFY)

    def test_create_violation_goes_to_halt(self):
        evidence = ViolationEvidence("write:../x", "path_escape", "scoped_writer")
        self.assertEqual(next_hexagram(HEX_CREATE, evidence), HEX_HALT)

    def test_verify_success_goes_to_return(self):
        evidence = SandboxEvidence(0, "passed", "a" * 64, "b" * 64, 10)
        self.assertEqual(next_hexagram(HEX_VERIFY, evidence), HEX_RETURN)

    def test_verify_failure_goes_to_correct(self):
        evidence = SandboxEvidence(1, "failed", "a" * 64, "b" * 64, 10)
        self.assertEqual(next_hexagram(HEX_VERIFY, evidence), HEX_CORRECT)

    def test_verify_repeated_failure_goes_to_halt_after_two_cycles(self):
        evidence = SandboxEvidence(1, "failed", "a" * 64, "b" * 64, 10)
        self.assertEqual(next_hexagram(HEX_VERIFY, evidence, consecutive_failures=2), HEX_HALT)

    def test_correct_feedback_goes_to_inspect(self):
        evidence = FeedbackEvidence("needs_fix", HEX_CORRECT, HEX_INSPECT, "failed")
        self.assertEqual(next_hexagram(HEX_CORRECT, evidence), HEX_INSPECT)

    def test_archive_success_goes_to_summary_label(self):
        evidence = ArchiveEvidence(".yizijue/manifest.json", {"a": "b" * 64}, "audit_only", False)
        self.assertEqual(next_hexagram(HEX_RETURN, evidence), "总")


class BuildModeGuardedFsmTest(unittest.TestCase):
    def test_guarded_transition_records_edge_walk_for_diagonal_jump(self):
        evidence = WriteEvidence(True, ("app/main.py",), "/w", "a" * 64)
        plan = guarded_next_hexagram("111", "001", evidence)

        self.assertIsInstance(plan, TransitionPlanEvidence)
        self.assertEqual(plan.source_hexagram, "111")
        self.assertEqual(plan.target_hexagram, "001")
        self.assertEqual(plan.edge_path, ("111", "011", "001"))
        self.assertFalse(plan.emergency_override)

    def test_guarded_transition_allows_emergency_violation_to_halt(self):
        violation = ViolationEvidence("rm -rf /", "dangerous_command", "path_sentinel")
        plan = guarded_next_hexagram("111", "100", violation, emergency_override=True)

        self.assertEqual(plan.target_hexagram, "100")
        self.assertEqual(plan.edge_path, ("111", "100"))
        self.assertTrue(plan.emergency_override)


if __name__ == "__main__":
    unittest.main()
