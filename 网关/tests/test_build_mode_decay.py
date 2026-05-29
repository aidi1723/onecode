import unittest

from agent_skill_dictionary.build_mode_decay import compute_decay_gate


class BuildModeDecayTest(unittest.TestCase):
    def test_repeated_tracebacks_lower_threshold_to_one(self):
        previous = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg\n6 failed"
        current = "FAILED tests/test_mesh.py::test_duplicate - TypeError: bad arg\n6 failed"

        evidence = compute_decay_gate(previous, current, base_threshold=3)

        self.assertGreaterEqual(evidence.similarity_ratio, 0.95)
        self.assertEqual(evidence.dynamic_threshold, 1)
        self.assertTrue(evidence.deadlock_suspected)

    def test_different_failure_keeps_base_threshold(self):
        previous = "FAILED tests/test_a.py::test_a - AssertionError: alpha"
        current = "FAILED tests/test_b.py::test_b - ImportError: beta"

        evidence = compute_decay_gate(previous, current, base_threshold=3)

        self.assertEqual(evidence.dynamic_threshold, 3)
        self.assertFalse(evidence.deadlock_suspected)


if __name__ == "__main__":
    unittest.main()
