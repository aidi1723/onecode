import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_types import ViolationEvidence
from agent_skill_dictionary.build_mode_writer import safe_write


class BuildModeWriterTest(unittest.TestCase):
    def test_safe_write_creates_file_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "app/main.py", "print('ok')\n")
            self.assertTrue(evidence.ok)
            self.assertEqual(evidence.changed_files, ("app/main.py",))
            self.assertTrue((Path(tmp) / "app/main.py").exists())
            self.assertEqual(evidence.violation, None)

    def test_path_escape_returns_violation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "../outside.py", "bad")
            self.assertIsInstance(evidence, ViolationEvidence)
            self.assertEqual(evidence.reason, "path_escape")
            self.assertEqual(evidence.exit_code, 126)

    def test_absolute_path_escape_returns_violation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "/etc/passwd", "bad")
            self.assertIsInstance(evidence, ViolationEvidence)
            self.assertEqual(evidence.reason, "path_escape")

    def test_empty_path_returns_violation_instead_of_writing_workspace_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, "", "bad")
            self.assertIsInstance(evidence, ViolationEvidence)
            self.assertEqual(evidence.reason, "empty_path")

    def test_directory_path_returns_violation_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = safe_write(tmp, ".", "bad")
            self.assertIsInstance(evidence, ViolationEvidence)
            self.assertEqual(evidence.reason, "directory_path")


if __name__ == "__main__":
    unittest.main()
