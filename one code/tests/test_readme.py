import unittest
from pathlib import Path


class ReadmeTests(unittest.TestCase):
    def test_readme_documents_core_cli_and_verification_paths(self):
        readme = Path("README.md")

        self.assertTrue(readme.exists())
        text = readme.read_text(encoding="utf-8")

        for snippet in [
            "bash scripts/verify.sh",
            "python3 -m onecode.cli doctor",
            "python3 -m onecode.cli run",
            "python3 -m onecode.cli inspect",
            "python3 -m onecode.cli list-runs",
            "--resume-from",
            "--write-text",
        ]:
            self.assertIn(snippet, text)


if __name__ == "__main__":
    unittest.main()
