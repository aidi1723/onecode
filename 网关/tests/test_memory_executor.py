import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.audit import read_audit_log
from agent_skill_dictionary.memory_executor import archive_markdown


class MemoryExecutorTest(unittest.TestCase):
    def test_archive_markdown_writes_file_inside_memory_dir_and_evidence(self):
        with TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir) / "memory"
            audit_log = Path(tmpdir) / "audit.log.jsonl"

            result = archive_markdown(
                "# Summary\n\nDone.\n",
                memory_dir=memory_dir,
                title="OneWord Summary",
                audit_log_path=audit_log,
            )

            output_path = Path(result["path"])
            self.assertTrue(result["ok"])
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.parent, memory_dir.resolve())
            self.assertIn("# Summary", output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["evidence"]["exit_code"], 0)
            self.assertEqual(len(read_audit_log(audit_log)), 1)


if __name__ == "__main__":
    unittest.main()
