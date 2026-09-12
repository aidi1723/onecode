import tomllib
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_wheel_assets import main as check_wheel_assets


class PackagingTests(unittest.TestCase):
    def test_pyproject_declares_onecode_console_script(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertEqual(data["project"]["name"], "onecode")
        self.assertEqual(data["project"]["requires-python"], ">=3.11")
        self.assertEqual(data["project"]["scripts"]["onecode"], "onecode.cli:main")

    def test_tui_dependency_is_optional_and_version_aligned(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        requirements = Path("requirements-tui.txt").read_text(encoding="utf-8")

        self.assertEqual(data["project"].get("dependencies", []), [])
        self.assertEqual(data["project"]["optional-dependencies"]["tui"], ["textual==8.2.7"])
        self.assertIn("textual==8.2.7", requirements)

    def test_tui_styles_are_declared_as_package_data(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertTrue(Path("src/onecode/tui/styles.tcss").exists())
        self.assertEqual(
            data["tool"]["setuptools"]["package-data"]["onecode.tui"],
            ["styles.tcss"],
        )

    def test_wheel_asset_checker_requires_tui_styles(self):
        with TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "onecode-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("onecode/tui/styles.tcss", "Screen {}\n")
                for asset in (
                    "onecode/contracts/shell_projection_v4_schema.json",
                    "onecode/contracts/shell_projection_v4_cases.json",
                    "onecode/contracts/shell_projection_v5_schema.json",
                    "onecode/contracts/shell_projection_v5_cases.json",
                ):
                    archive.writestr(asset, "{}")

            with redirect_stdout(StringIO()):
                self.assertEqual(check_wheel_assets([tmp]), 0)

    def test_wheel_asset_checker_rejects_missing_tui_styles(self):
        with TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "onecode-0.1.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("onecode/tui/app.py", "")

            with redirect_stderr(StringIO()):
                self.assertEqual(check_wheel_assets([tmp]), 1)

    def test_bin_onecode_script_exists_and_loads_src_entrypoint(self):
        script = Path("bin/onecode")

        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111)
        text = script.read_text(encoding="utf-8")
        self.assertIn("src", text)
        self.assertIn("onecode.cli", text)


if __name__ == "__main__":
    unittest.main()
