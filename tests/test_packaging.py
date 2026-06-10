import tomllib
import unittest
from pathlib import Path


class PackagingTests(unittest.TestCase):
    def test_pyproject_declares_onecode_console_script(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertEqual(data["project"]["name"], "onecode")
        self.assertEqual(data["project"]["requires-python"], ">=3.11")
        self.assertEqual(data["project"]["scripts"]["onecode"], "onecode.cli:main")

    def test_pyproject_includes_builtin_integrations_in_source_distribution(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["tool"]["setuptools"]["include-package-data"], True)
        self.assertEqual(
            data["tool"]["setuptools"]["package-data"]["onecode"],
            ["integrations/skills/*/*.md"],
        )

        manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("recursive-include integrations/skills *.md", manifest)
        self.assertIn("recursive-include src/onecode/integrations/skills *.md", manifest)

    def test_tui_dependency_is_optional_and_version_aligned(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        requirements = Path("requirements-tui.txt").read_text(encoding="utf-8")

        self.assertEqual(data["project"].get("dependencies", []), [])
        self.assertEqual(data["project"]["optional-dependencies"]["tui"], ["textual==8.2.7"])
        self.assertIn("textual==8.2.7", requirements)

    def test_bin_onecode_script_exists_and_loads_src_entrypoint(self):
        script = Path("bin/onecode")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)
        text = script.read_text(encoding="utf-8")
        self.assertIn("src", text)
        self.assertIn("onecode.cli", text)


if __name__ == "__main__":
    unittest.main()
