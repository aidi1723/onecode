import tomllib
import unittest
from pathlib import Path


class VersionTests(unittest.TestCase):
    def test_public_version_is_consistent(self):
        from onecode import __version__
        from onecode.tui.app import APP_VERSION
        from onecode.web.api import OneCodeRequestHandler

        project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(project["project"]["version"], "0.8.0")
        self.assertEqual(__version__, "0.8.0")
        self.assertEqual(APP_VERSION, "0.8.0")
        self.assertEqual(OneCodeRequestHandler.server_version, "OneCodeHTTP/0.8")


if __name__ == "__main__":
    unittest.main()
