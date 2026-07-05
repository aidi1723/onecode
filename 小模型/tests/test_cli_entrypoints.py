import subprocess
import sys
import unittest


class CliEntrypointsTest(unittest.TestCase):
    def test_build_distilled_training_set_help_does_not_require_onecode(self):
        result = subprocess.run(
            [sys.executable, "scripts/build_distilled_training_set.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Merge adjudicated YiZiJue distillation rows", result.stdout)

    def test_distill_openai_compatible_help_does_not_require_onecode(self):
        result = subprocess.run(
            [sys.executable, "scripts/distill_openai_compatible.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Generate teacher rows", result.stdout)

    def test_build_distilled_training_set_reports_missing_onecode_without_traceback(self):
        result = subprocess.run(
            [sys.executable, "scripts/build_distilled_training_set.py"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("onecode package is required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_distill_openai_compatible_reports_missing_onecode_without_traceback(self):
        result = subprocess.run(
            [sys.executable, "scripts/distill_openai_compatible.py"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("onecode package is required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
