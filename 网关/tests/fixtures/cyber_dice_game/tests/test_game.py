from __future__ import annotations

import unittest

import main


class CyberDiceGameTest(unittest.TestCase):
    def setUp(self):
        main.save_bank({"alice": 15, "bob": 40})

    def test_roll_dice_stays_inside_six_sided_range(self):
        for _ in range(100):
            value = main.roll_dice()
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 6)

    def test_dice_values_are_validated(self):
        with self.assertRaises(ValueError):
            main.settle_round("alice", 7, 1, 10)

    def test_losing_round_never_makes_balance_negative(self):
        result = main.settle_round("alice", 1, 6, 10)
        self.assertEqual(result["balance"], 0)
        self.assertEqual(main.load_bank()["alice"], 0)


if __name__ == "__main__":
    unittest.main()
