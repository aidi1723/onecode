import unittest
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel


PALACE_STATES = {
    0: (0, 1, 3, 7, 15, 31, 23, 16),
    1: (9, 8, 10, 14, 6, 22, 30, 25),
    2: (18, 19, 17, 21, 29, 13, 5, 2),
    3: (27, 26, 24, 28, 20, 4, 12, 11),
    4: (36, 37, 39, 35, 43, 59, 51, 52),
    5: (45, 44, 46, 42, 34, 50, 58, 61),
    6: (54, 55, 53, 49, 57, 41, 33, 38),
    7: (63, 62, 60, 56, 48, 32, 40, 47),
}
PALACE_NAMES = ("kun", "zhen", "kan", "dui", "gen", "li", "xun", "qian")
PALACE_ELEMENTS = ("earth", "wood", "water", "metal", "earth", "fire", "wood", "metal")
STAGES = ("pure", "first", "second", "third", "fourth", "fifth", "travel", "return")
WORLD_LINES = (5, 0, 1, 2, 3, 4, 3, 2)


class PalaceReferenceTests(unittest.TestCase):
    def test_all_64_states_match_independent_reference(self):
        states = [state for sequence in PALACE_STATES.values() for state in sequence]
        self.assertEqual(len(states), 64)
        self.assertEqual(set(states), set(range(64)))
        for palace, sequence in PALACE_STATES.items():
            for index, state in enumerate(sequence):
                with self.subTest(palace=palace, state=state):
                    info = IchingKernel.palace_attribution(state)
                    self.assertEqual(info["palace"], palace)
                    self.assertEqual(info["palace_name"], PALACE_NAMES[palace])
                    self.assertEqual(info["palace_element"], PALACE_ELEMENTS[palace])
                    self.assertEqual(info["world_line"], WORLD_LINES[index])
                    self.assertEqual(info["response_line"], (WORLD_LINES[index] + 3) % 6)
                    self.assertEqual(info["palace_stage"], STAGES[index])

    def test_legacy_hexagram_type_remains_three_valued(self):
        for sequence in PALACE_STATES.values():
            for index, state in enumerate(sequence):
                info = IchingKernel.palace_attribution(state)
                expected = "pure" if index == 0 else "return" if index == 7 else "travel"
                self.assertEqual(info["hexagram_type"], expected)

    def test_corrected_qian_palace_drives_six_relatives(self):
        expected = {
            62: ["parent", "offspring", "brother", "officer", "brother", "parent"],
            60: ["parent", "officer", "brother", "officer", "brother", "parent"],
        }
        for state, relatives in expected.items():
            profile = IchingKernel.six_relatives_profile(state)
            self.assertEqual(profile["palace"], 7)
            self.assertEqual(profile["palace_element"], "metal")
            self.assertEqual([line["relative"] for line in profile["lines"]], relatives)

    def test_transition_is_independent_from_reference_attribution(self):
        baseline = [IchingKernel.transition(state) for state in range(64)]
        with patch.object(IchingKernel, "palace_attribution", side_effect=AssertionError("reference used")):
            self.assertEqual([IchingKernel.transition(state) for state in range(64)], baseline)

    def test_invalid_status_is_rejected(self):
        for state in (-1, 64, True, None, "63", 1.5):
            with self.subTest(state=state), self.assertRaises(ValueError):
                IchingKernel.palace_attribution(state)
