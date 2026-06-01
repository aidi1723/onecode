from pathlib import Path
import unittest


class SourceHygieneTests(unittest.TestCase):
    def test_contributing_forbids_leaked_sources(self):
        text = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

        self.assertIn("Leaked, mirrored, or DMCA-risk Claude Code source repositories are forbidden", text)
        self.assertIn("Every OneCode source file must be independently authored", text)


if __name__ == "__main__":
    unittest.main()
