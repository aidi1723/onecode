import unittest

from onecode.kernel.run_id import validate_optional_run_id, validate_run_id


class RunIdValidationTests(unittest.TestCase):
    def test_accepts_single_segment_ascii_run_ids(self):
        self.assertEqual(validate_run_id("run-1"), "run-1")
        self.assertEqual(validate_run_id("run_1.2"), "run_1.2")
        self.assertEqual(validate_run_id("a" * 128), "a" * 128)

    def test_rejects_path_or_traversal_run_ids(self):
        for value in ("../run", "run/child", "run\\child", ".", "..", "-run", "_run"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid run_id"):
                    validate_run_id(value)

    def test_rejects_empty_non_ascii_and_oversized_run_ids(self):
        for value in ("", "运行-1", "a" * 129):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid run_id"):
                    validate_run_id(value)

    def test_optional_run_id_preserves_none_and_validates_values(self):
        self.assertIsNone(validate_optional_run_id(None))
        self.assertEqual(validate_optional_run_id("source-run"), "source-run")
        with self.assertRaisesRegex(ValueError, "invalid resume_from_run_id"):
            validate_optional_run_id("../source", field_name="resume_from_run_id")


if __name__ == "__main__":
    unittest.main()
