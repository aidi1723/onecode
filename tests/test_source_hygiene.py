from pathlib import Path
import unittest


class SourceHygieneTests(unittest.TestCase):
    def test_source_hygiene_spec_forbids_leaked_sources(self):
        spec = Path("docs/superpowers/specs/2026-05-27-onecode-v0.1-alpha-kernel-design.md")
        text = spec.read_text(encoding="utf-8")

        self.assertIn("Leaked, mirrored, or DMCA-risk Claude Code source repositories are forbidden", text)
        self.assertIn("Every OneCode source file must be independently authored", text)


if __name__ == "__main__":
    unittest.main()
