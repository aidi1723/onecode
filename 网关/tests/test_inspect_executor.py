import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.inspect_executor import build_native_inspect_card, inspect_workspace


class InspectExecutorTest(unittest.TestCase):
    def test_inspect_workspace_lists_text_files_and_writes_evidence(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "src").mkdir()
            (workspace / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (workspace / "__pycache__").mkdir()
            (workspace / "__pycache__" / "ignored.pyc").write_bytes(b"cache")
            audit_log = workspace / "audit.log.jsonl"

            result = inspect_workspace(workspace, audit_log_path=audit_log)

            self.assertTrue(result["ok"])
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["files"], ["README.md", "src/app.py"])
            self.assertIn("README.md", result["snippets"])
            self.assertEqual(result["native_card"]["state"], "101-INSPECT")
            self.assertIn("[State]: 101-INSPECT", result["native_card_text"])
            self.assertEqual(result["evidence"]["exit_code"], 0)
            self.assertEqual(len(read_audit_log(audit_log)), 1)

    def test_inspect_workspace_skips_runtime_and_dependency_directories(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "agent_skill_dictionary").mkdir()
            (workspace / "agent_skill_dictionary" / "runner.py").write_text("print('runner')\n", encoding="utf-8")
            (workspace / ".venv-gateway" / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
            (workspace / ".venv-gateway" / "lib" / "python3.12" / "site-packages" / "noise.py").write_text(
                "print('dependency noise')\n",
                encoding="utf-8",
            )
            (workspace / ".oneword").mkdir()
            (workspace / ".oneword" / "audit.jsonl").write_text("{}\n", encoding="utf-8")
            (workspace / "dist").mkdir()
            (workspace / "dist" / "bundle.py").write_text("print('built')\n", encoding="utf-8")

            result = inspect_workspace(workspace)

            self.assertEqual(result["files"], ["README.md", "agent_skill_dictionary/runner.py"])
            self.assertNotIn(".venv-gateway/lib/python3.12/site-packages/noise.py", result["files"])
            self.assertNotIn(".oneword/audit.jsonl", result["files"])
            self.assertNotIn("dist/bundle.py", result["files"])

    def test_native_inspect_card_extracts_symbolic_repo_map(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "sync_node.py").write_text(
                "\n".join(
                    [
                        "import httpx",
                        "from ledger import Ledger",
                        "",
                        "class SyncNode:",
                        "    async def sync_inventory(self):",
                        "        while True:",
                        "            await httpx.AsyncClient().get('https://example.test')",
                    ]
                ),
                encoding="utf-8",
            )
            (workspace / "ledger.py").write_text(
                "def record_order(order):\n    return order\n",
                encoding="utf-8",
            )

            card = build_native_inspect_card(workspace, target="sync_node.py", max_chars=900)

            self.assertEqual(card["state"], "101-INSPECT")
            self.assertEqual(card["target"], "sync_node.py")
            self.assertIn("sync_node.py:4:class SyncNode", card["symbols"])
            self.assertIn("sync_node.py:5:async def sync_inventory", card["symbols"])
            self.assertIn("sync_node.py:1:import httpx", card["imports"])
            self.assertIn("sync_node.py:2:from ledger import Ledger", card["imports"])
            self.assertIn("sync_node.py:6:while True", card["risks"])
            self.assertLessEqual(len(card["text"]), 900)

    def test_native_inspect_card_is_short_even_for_large_workspace(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            for index in range(80):
                (workspace / f"module_{index}.py").write_text(
                    f"import os\n\ndef function_{index}():\n    return {index}\n",
                    encoding="utf-8",
                )

            card = build_native_inspect_card(workspace, max_chars=700)

            self.assertLessEqual(len(card["text"]), 700)
            self.assertLessEqual(len(card["files"]), 30)
            self.assertIn("[State]: 101-INSPECT", card["text"])
            self.assertIn("[Files]:", card["text"])
            self.assertIn("[Symbols]:", card["text"])

    def test_native_inspect_card_keeps_symbols_and_risks_when_truncated(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            for index in range(50):
                (workspace / f"very_long_module_name_{index}.py").write_text(
                    f"import subprocess\n\ndef function_{index}():\n    while True:\n        return subprocess.run(['echo', '{index}'])\n",
                    encoding="utf-8",
                )

            card = build_native_inspect_card(workspace, max_chars=500)

            self.assertLessEqual(len(card["text"]), 500)
            self.assertIn("[Files]:", card["text"])
            self.assertIn("[Symbols]:", card["text"])
            self.assertIn("[Imports]:", card["text"])
            self.assertIn("[Risks]:", card["text"])
            self.assertIn("while True", card["text"])


if __name__ == "__main__":
    unittest.main()
