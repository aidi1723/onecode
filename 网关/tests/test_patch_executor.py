import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.patch_executor import apply_controlled_patch


class PatchExecutorTest(unittest.TestCase):
    def test_apply_controlled_patch_writes_workspace_file_and_evidence(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            audit_log = workspace / "audit.log.jsonl"

            result = apply_controlled_patch(
                workspace,
                [{"path": "src/app.py", "content": "print('fixed')\n"}],
                audit_log_path=audit_log,
            )

            self.assertTrue(result["ok"])
            self.assertEqual((workspace / "src" / "app.py").read_text(encoding="utf-8"), "print('fixed')\n")
            self.assertEqual(result["changed_files"], ["src/app.py"])
            self.assertEqual(result["evidence"]["exit_code"], 0)
            self.assertEqual(len(read_audit_log(audit_log)), 1)

    def test_apply_controlled_patch_rejects_path_escape(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            with self.assertRaises(ValueError):
                apply_controlled_patch(
                    workspace,
                    [{"path": "../escape.txt", "content": "bad\n"}],
                )

    def test_apply_controlled_patch_rejects_unscoped_existing_file_overwrite(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "src").mkdir()
            (workspace / "src" / "app.py").write_text("print('original')\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                apply_controlled_patch(
                    workspace,
                    [{"path": "src/app.py", "content": "print('rewritten')\n"}],
                )

    def test_apply_controlled_patch_allows_existing_file_when_expected_sha256_matches(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "src").mkdir()
            target = workspace / "src" / "app.py"
            target.write_text("print('original')\n", encoding="utf-8")
            expected_sha256 = "bc1301140376ba45d85f23da83fcad2c78a9931fda9ca74e8e9696031b033e24"

            result = apply_controlled_patch(
                workspace,
                [
                    {
                        "path": "src/app.py",
                        "content": "print('rewritten')\n",
                        "expected_sha256": expected_sha256,
                    }
                ],
            )

            self.assertTrue(result["ok"])
            self.assertEqual(target.read_text(encoding="utf-8"), "print('rewritten')\n")


if __name__ == "__main__":
    unittest.main()
