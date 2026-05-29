import json
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_archive import finalize_manifest


class BuildModeArchiveTest(unittest.TestCase):
    def test_finalize_manifest_writes_hashes_without_lockdown_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir()
            (root / "app" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            evidence = finalize_manifest(root)
            self.assertEqual(evidence.readonly_status, "audit_only")
            manifest = root / evidence.manifest_path
            self.assertTrue(manifest.exists())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("app/main.py", data["sha256_map"])
            self.assertFalse(evidence.lockdown)


if __name__ == "__main__":
    unittest.main()
