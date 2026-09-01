import tomllib
import unittest
from hashlib import sha256
from pathlib import Path


class LicenseTests(unittest.TestCase):
    def test_project_declares_gpl_v3_only_consistently(self):
        license_text = Path("LICENSE").read_text(encoding="utf-8")
        project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertTrue(license_text.lstrip().startswith("GNU GENERAL PUBLIC LICENSE\n                       Version 3"))
        self.assertIn("Everyone is permitted to copy and distribute verbatim copies", license_text)
        self.assertEqual(
            sha256(Path("LICENSE").read_bytes()).hexdigest(),
            "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
        )
        self.assertEqual(project["project"]["license"], "GPL-3.0-only")
        self.assertIn("GNU General Public License, Version 3", readme)
        self.assertNotIn("Apache License, Version 2.0", readme)


if __name__ == "__main__":
    unittest.main()
