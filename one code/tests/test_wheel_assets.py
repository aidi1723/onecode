import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ASSETS = {
    "onecode/tui/styles.tcss",
    "onecode/contracts/shell_projection_v4_schema.json",
    "onecode/contracts/shell_projection_v4_cases.json",
    "onecode/contracts/shell_projection_v5_schema.json",
    "onecode/contracts/shell_projection_v5_cases.json",
}


class WheelAssetTests(unittest.TestCase):
    def test_missing_public_resource_fails(self):
        for missing in sorted(ASSETS):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                wheel = Path(tmp) / "onecode-0.0.0-py3-none-any.whl"
                with zipfile.ZipFile(wheel, "w") as archive:
                    for asset in ASSETS - {missing}:
                        archive.writestr(asset, "fixture")
                result = subprocess.run(
                    [sys.executable, "scripts/check_wheel_assets.py", tmp],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(missing, result.stderr)

    def test_complete_public_resources_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "onecode-0.0.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                for asset in ASSETS:
                    archive.writestr(asset, "fixture")
            result = subprocess.run(
                [sys.executable, "scripts/check_wheel_assets.py", tmp],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
