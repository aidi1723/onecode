import unittest

from agent_skill_dictionary.build_mode_topology import (
    edge_walk_path,
    hamming_distance,
    is_edge_transition,
    transition_axes,
)


class BuildModeTopologyTest(unittest.TestCase):
    def test_hamming_distance_counts_changed_axes(self):
        self.assertEqual(hamming_distance("111", "011"), 1)
        self.assertEqual(hamming_distance("111", "001"), 2)
        self.assertEqual(hamming_distance("111", "000"), 3)

    def test_edge_transition_allows_only_one_axis_change(self):
        self.assertTrue(is_edge_transition("111", "011"))
        self.assertFalse(is_edge_transition("111", "001"))

    def test_transition_axes_names_changed_bits(self):
        self.assertEqual(transition_axes("111", "001"), ("tool_axis", "context_axis"))

    def test_edge_walk_path_decomposes_diagonal_jump(self):
        self.assertEqual(edge_walk_path("111", "001"), ("111", "011", "001"))
        self.assertEqual(edge_walk_path("111", "000"), ("111", "011", "001", "000"))


if __name__ == "__main__":
    unittest.main()
