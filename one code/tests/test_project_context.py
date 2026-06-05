import hashlib
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.project_context import RulesImport, discover_project_context


class ProjectContextDiscoveryTests(unittest.TestCase):
    def test_discovers_sorted_rule_files_and_dedupes_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / "AGENTS.md").write_text("root rule\n", encoding="utf-8")
            rules = workspace / ".onecode" / "rules"
            rules.mkdir(parents=True)
            (rules / "b.md").write_text("shared b\n", encoding="utf-8")
            (rules / "a.txt").write_text("shared a\n", encoding="utf-8")
            (rules / "dup.mdc").write_text("shared a\n\n", encoding="utf-8")

            report = discover_project_context(workspace)

        self.assertEqual(report["status"], "ok")
        self.assertEqual([item["path"] for item in report["memory_files"]], ["AGENTS.md", ".onecode/rules/a.txt", ".onecode/rules/b.md"])
        self.assertEqual(report["summary"]["file_count"], 3)
        self.assertEqual(report["summary"]["deduped_count"], 1)
        self.assertEqual(report["summary"]["element"], "wood")
        self.assertEqual(report["summary"]["yin_yang_pressure"], "stable")
        self.assertEqual(
            report["iching_status_code"],
            IchingKernel.compute_status(IchingKernel.XUN, IchingKernel.ZHEN),
        )
        self.assertEqual(len(report["memory_files"][0]["content_sha256"]), 64)

    def test_local_rules_are_reported_as_local_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            local_rules = workspace / ".onecode" / "rules.local"
            local_rules.mkdir(parents=True)
            (local_rules / "personal.md").write_text("personal local rule\n", encoding="utf-8")

            report = discover_project_context(workspace)

        self.assertEqual(report["memory_files"][0]["origin"], "local")
        self.assertEqual(report["memory_files"][0]["source"], "onecode_rules_local")
        self.assertTrue(report["memory_files"][0]["contributes"])

    def test_imported_framework_rules_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / ".cursorrules").write_text("cursor rule\n", encoding="utf-8")
            github = workspace / ".github"
            github.mkdir()
            (github / "copilot-instructions.md").write_text("copilot rule\n", encoding="utf-8")

            disabled = discover_project_context(workspace, rules_import=RulesImport.none())
            selected = discover_project_context(workspace, rules_import=RulesImport.list(["copilot"]))

        self.assertEqual(disabled["memory_files"], [])
        self.assertEqual([item["source"] for item in selected["memory_files"]], ["copilot_instructions"])

    def test_project_context_metadata_does_not_expose_raw_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("secret-ish instruction\n", encoding="utf-8")

            report = discover_project_context(workspace)

        item = report["memory_files"][0]
        self.assertNotIn("content", item)
        self.assertEqual(item["chars"], len("secret-ish instruction\n"))
        self.assertEqual(item["content_sha256"], hashlib.sha256(b"secret-ish instruction\n").hexdigest())


if __name__ == "__main__":
    unittest.main()
