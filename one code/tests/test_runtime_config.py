import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.runtime_config import inspect_runtime_config, parse_rules_import


class RuntimeConfigInspectionTests(unittest.TestCase):
    def test_missing_optional_configs_report_not_found_without_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            home = Path(tmp) / "home"
            with patch.dict("os.environ", {"ONECODE_HOME": str(home)}, clear=False):
                report = inspect_runtime_config(workspace)

        self.assertEqual(report["status"], "ok")
        self.assertEqual([item["status"] for item in report["files"]], ["not_found", "not_found", "not_found"])
        self.assertEqual(report["summary"]["loaded_count"], 0)
        self.assertEqual(report["summary"]["element"], "earth")

    def test_valid_and_invalid_sibling_configs_are_reported_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            config_dir = workspace / ".onecode"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text(json.dumps({"rulesImport": "none"}), encoding="utf-8")
            (config_dir / "config.local.json").write_text("{bad json", encoding="utf-8")
            home = Path(tmp) / "home"
            with patch.dict("os.environ", {"ONECODE_HOME": str(home)}, clear=False):
                report = inspect_runtime_config(workspace)

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["summary"]["loaded_count"], 1)
        self.assertEqual(report["summary"]["load_error_count"], 1)
        self.assertEqual(report["effective"]["rulesImport"], "none")
        self.assertEqual(
            report["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.KAN),
        )

    def test_parse_rules_import_accepts_string_and_list_forms(self):
        self.assertEqual(parse_rules_import({"rulesImport": "none"}).mode, "none")
        self.assertEqual(parse_rules_import({"rulesImport": ["cursor", "copilot"]}).frameworks, ("cursor", "copilot"))
        self.assertEqual(parse_rules_import({}).mode, "auto")


if __name__ == "__main__":
    unittest.main()
