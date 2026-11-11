import unittest
from pathlib import Path


class DesignContractTests(unittest.TestCase):
    def test_design_md_covers_tui_and_web_gateway_surfaces(self):
        text = Path("DESIGN.md").read_text(encoding="utf-8")

        self.assertIn("Scope: `src/onecode/tui`, `src/onecode/web`", text)
        self.assertIn("Web Gateway", text)
        self.assertIn("shared dark terminal palette", text)
        self.assertIn("inline HTML", text)


if __name__ == "__main__":
    unittest.main()
