import unittest
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from onecode.kernel.cycle_approvals import persist_pending_approval, find_pending_approval

class TestCycleApprovals(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_signature_and_secret_location(self):
        configured = self.workspace / "onecode-home"
        configured.mkdir()
        with patch.dict(os.environ, {"ONECODE_HOME": str(configured)}, clear=False):
            record = persist_pending_approval(self.workspace, "test_tool", {"arg": "val"})
            self.assertIn("signature", record)

            record_path = next((self.workspace / ".onecode/pending-cycle").glob("*.json"))
            tampered = json.loads(record_path.read_text())
            tampered["params"]["arg"] = "malicious"
            record_path.write_text(json.dumps(tampered))

            found = find_pending_approval(self.workspace, "test_tool", {"arg": "val"})
            self.assertIsNone(found)

    def test_approval_secret_uses_onecode_home_not_path_home(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp) / "unix-home"
            configured = Path(tmp) / "onecode-home"
            home.mkdir()
            configured.mkdir()
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            with patch.dict(os.environ, {"ONECODE_HOME": str(configured)}, clear=False):
                with patch("pathlib.Path.home", return_value=home):
                    persist_pending_approval(workspace, "run_command", {"argv": ["echo", "1"]})
            self.assertTrue((configured / "approval-secret.key").is_file())
            self.assertEqual((configured / "approval-secret.key").stat().st_mode & 0o777, 0o600)
            self.assertFalse((home / ".onecode" / "approval-secret.key").exists())

    def test_corrupt_approval_secret_is_rejected_without_rewriting(self):
        with TemporaryDirectory() as tmp:
            configured = Path(tmp) / "onecode-home"
            configured.mkdir()
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            key_path = configured / "approval-secret.key"
            payload = b"not-hex\n"
            key_path.write_bytes(payload)
            with patch.dict(os.environ, {"ONECODE_HOME": str(configured)}, clear=False):
                with self.assertRaisesRegex(ValueError, "approval secret is corrupted or unreadable"):
                    persist_pending_approval(workspace, "run_command", {"argv": ["echo", "1"]})
            self.assertEqual(key_path.read_bytes(), payload)

if __name__ == "__main__":
    unittest.main()
