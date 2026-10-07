import unittest
import json
import hashlib
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
        with patch("pathlib.Path.home", return_value=self.workspace / "fake_home"):
            record = persist_pending_approval(self.workspace, "test_tool", {"arg": "val"})
            self.assertIn("signature", record)
            
            # Check secret is in fake_home outside workspace logic (though here it's inside fake_home)
            workspace_hash = hashlib.sha256(str(self.workspace.resolve()).encode("utf-8")).hexdigest()
            secret_path = self.workspace / "fake_home" / ".onecode" / "workspaces" / workspace_hash / "pending.secret"
            self.assertTrue(secret_path.exists())
            
            # Tamper the record
            record_path = next((self.workspace / ".onecode/pending-cycle").glob("*.json"))
            tampered = json.loads(record_path.read_text())
            tampered["params"]["arg"] = "malicious"
            record_path.write_text(json.dumps(tampered))
            
            # Find should return None due to signature mismatch
            found = find_pending_approval(self.workspace, "test_tool", {"arg": "malicious"})
            self.assertIsNone(found)

if __name__ == "__main__":
    unittest.main()
