import tempfile
import unittest
from pathlib import Path

from onecode.kernel.path_guard import PathGuardError
from onecode.kernel.sandbox import SandboxConfig


class HostStageTests(unittest.TestCase):
    def test_stage_writes_only_after_approval(self):
        from onecode.kernel.host_stage import stage_bytes

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with self.assertRaises(PermissionError):
                stage_bytes(workspace, "vendor/pkg.py", b"VALUE = 1\n", approved=False)
            path = stage_bytes(workspace, "vendor/pkg.py", b"VALUE = 1\n", approved=True)
            self.assertEqual(path.read_bytes(), b"VALUE = 1\n")

    def test_stage_refuses_escape(self):
        from onecode.kernel.host_stage import stage_bytes

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PathGuardError):
                stage_bytes(Path(tmp), "../outside.py", b"x", approved=True)

    def test_sandbox_network_stays_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(SandboxConfig(workspace=Path(tmp)).network, "none")
