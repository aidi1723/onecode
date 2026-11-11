import unittest

from onecode.kernel.hexagram import (
    BUILD_ENTRY,
    COMPLETE,
    HexagramStatusCode,
    is_valid_hexagram_code,
)


class HexagramStatusTests(unittest.TestCase):
    def test_accepts_exactly_six_binary_digits(self):
        code = HexagramStatusCode("101000")

        self.assertEqual(str(code), "101000")
        self.assertTrue(is_valid_hexagram_code("101000"))

    def test_rejects_non_binary_or_wrong_length_values(self):
        for value in ["10100", "1010000", "10100x", "", "abcdef"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    HexagramStatusCode(value)

    def test_core_constants_are_valid_status_codes(self):
        self.assertEqual(str(BUILD_ENTRY), "111111")
        self.assertEqual(str(COMPLETE), "000000")


if __name__ == "__main__":
    unittest.main()
