import unittest

from onecode.experimental.moving_cast import cast_from_lines
from onecode.kernel.hexagram import IchingKernel


class MovingCastTests(unittest.TestCase):
    def test_static_lines_keep_the_hexagram(self):
        cast = cast_from_lines([8, 8, 8, 7, 7, 7])
        self.assertEqual(cast["before"], 0b111000)
        self.assertEqual(cast["moving"], [])
        self.assertEqual(cast["after"], 0b111000)

    def test_old_yin_and_old_yang_flip_through_the_kernel(self):
        cast = cast_from_lines([6, 7, 8, 9, 8, 7])
        self.assertEqual(cast["moving"], [0, 3])
        self.assertEqual(cast["before"] & 1, 0)
        self.assertEqual((cast["before"] >> 3) & 1, 1)
        self.assertEqual(cast["after"], IchingKernel.mutate_lines(cast["before"], [0, 3]))
        self.assertNotEqual(cast["after"], cast["before"])
        self.assertLessEqual(cast["after"], 63)

    def test_line_motion_tokens_follow_each_line_name(self):
        ordered = list("初爻老阴，动；二爻少阳，静；三爻少阴，静；四爻老阳，动；五爻少阳，静；上爻少阴，静。")
        reversed_lines = list("上爻少阴，静。五爻少阳，静。四爻老阳，动。三爻少阴，静。二爻少阳，静。初爻属于老阴，此爻动。")
        from onecode.experimental.moving_cast import motion_token_indexes

        ordered_at = motion_token_indexes(ordered)
        reversed_at = motion_token_indexes(reversed_lines)
        self.assertEqual(ordered[ordered_at[0]], "阴")
        self.assertEqual(ordered[ordered_at[1]], "阳")
        self.assertEqual(reversed_lines[reversed_at[0]], "阴")
        self.assertEqual(reversed_lines[reversed_at[5]], "阴")

    def test_every_changed_hexagram_stays_inside_sixty_four(self):
        for index in range(4**6):
            values = []
            remainder = index
            for _ in range(6):
                values.append((6, 7, 8, 9)[remainder % 4])
                remainder //= 4
            after = cast_from_lines(values)["after"]
            self.assertIsInstance(after, int)
            self.assertGreaterEqual(after, 0)
            self.assertLessEqual(after, 63)


if __name__ == "__main__":
    unittest.main()
