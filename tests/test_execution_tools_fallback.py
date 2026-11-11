import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from onecode.kernel.execution_tools import _run_command

class TestExecutionToolsFallback(unittest.TestCase):
    @patch("onecode.kernel.execution_tools._docker_daemon_ready", return_value=False)
    @patch("onecode.kernel.execution_tools.subprocess.Popen")
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto"}, clear=True)
    def test_auto_fallback_emits_warning(self, mock_popen, mock_ready):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("stdout", "stderr")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        code, out, err = _run_command(["echo", "hi"], Path("/tmp"), 10)
        mock_popen.assert_not_called()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "sandbox_required")

    @patch("onecode.kernel.execution_tools._docker_daemon_ready", return_value=True)
    @patch("onecode.kernel.sandbox.run_in_reused_sandbox")
    @patch("onecode.kernel.execution_tools.subprocess.Popen")
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto"}, clear=True)
    def test_docker_fails_emits_warning(self, mock_popen, mock_run_sandbox, mock_ready):
        mock_run_sandbox.side_effect = OSError("docker failed")
        
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("stdout", "stderr")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        code, out, err = _run_command(["echo", "hi"], Path("/tmp"), 10)
        mock_popen.assert_not_called()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(err, "sandbox_required")
        
    @patch("onecode.kernel.execution_tools.subprocess.Popen")
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}, clear=True)
    def test_explicit_host_no_warning(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("stdout", "stderr")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        code, out, err = _run_command(["echo", "hi"], Path("/tmp"), 10)
        self.assertNotIn("[WARNING: Docker sandbox unavailable", err)

if __name__ == "__main__":
    unittest.main()
