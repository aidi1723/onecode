import unittest
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from onecode.kernel.sandbox import SandboxConfig, run_in_reused_sandbox, run_in_sandbox

class TestSandboxTimeout(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("onecode.kernel.sandbox.subprocess.run")
    def test_run_in_reused_sandbox_timeout_restarts_container(self, mock_run):
        config = SandboxConfig(workspace=self.workspace, timeout_seconds=10)
        
        def side_effect(*args, **kwargs):
            if args[0][:2] == ["docker", "exec"]:
                raise subprocess.TimeoutExpired(args[0], 10)
            return MagicMock(returncode=0, stdout="true", stderr="")
        mock_run.side_effect = side_effect
        
        with self.assertRaises(subprocess.TimeoutExpired):
            run_in_reused_sandbox(config, ["sleep", "100"])
            
        restart_calls = [call for call in mock_run.mock_calls if call.args[0][:2] == ["docker", "restart"]]
        self.assertEqual(len(restart_calls), 1)
        self.assertIn("-t", restart_calls[0].args[0])
        self.assertIn("1", restart_calls[0].args[0])

    @patch("onecode.kernel.sandbox.subprocess.run")
    def test_run_in_sandbox_timeout_kills_container(self, mock_run):
        config = SandboxConfig(workspace=self.workspace, timeout_seconds=10)
        
        def side_effect(*args, **kwargs):
            if args[0][:2] == ["docker", "run"]:
                raise subprocess.TimeoutExpired(args[0], 10)
            return MagicMock(returncode=0)
        mock_run.side_effect = side_effect
        
        with self.assertRaises(subprocess.TimeoutExpired):
            run_in_sandbox(config, ["sleep", "100"])
            
        kill_calls = [call for call in mock_run.mock_calls if call.args[0][:2] == ["docker", "kill"]]
        self.assertEqual(len(kill_calls), 1)
        name = kill_calls[0].args[0][2]
        self.assertTrue(name.startswith("onecode_ephemeral_"))

if __name__ == "__main__":
    unittest.main()
