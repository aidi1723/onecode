import os
import shutil
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from onecode.kernel.deployment_boundary import _docker_daemon_ready, deployment_boundary

class TestDeploymentBoundary(unittest.TestCase):
    @patch('shutil.which')
    def test_docker_daemon_ready_no_docker(self, mock_which):
        mock_which.return_value = None
        self.assertFalse(_docker_daemon_ready())
        mock_which.assert_called_with("docker")

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_docker_daemon_ready_success(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/docker"
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        self.assertTrue(_docker_daemon_ready())

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_docker_daemon_ready_timeout(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/docker"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker info", timeout=3)
        self.assertFalse(_docker_daemon_ready())

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_docker_daemon_ready_os_error(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/docker"
        mock_run.side_effect = OSError("No such file or directory")
        self.assertFalse(_docker_daemon_ready())
        
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_docker_daemon_ready_failure_exit_code(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/docker"
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_run.return_value = mock_process
        self.assertFalse(_docker_daemon_ready())

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto", "ONECODE_ALLOW_UNAUTHENTICATED": "false", "ONECODE_API_TOKEN": "token"}, clear=True)
    def test_deployment_boundary_auto_ready(self, mock_docker_ready):
        mock_docker_ready.return_value = True
        result = deployment_boundary()
        self.assertEqual(result["command_sandbox"], "auto")
        self.assertTrue(result["docker_ready"])
        self.assertTrue(result["sandbox_effective"])
        self.assertFalse(result["unauthenticated_local"])
        self.assertTrue(result["api_token_set"])
        self.assertTrue(result["production_ready"])

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto", "ONECODE_ALLOW_UNAUTHENTICATED": "1", "ONECODE_API_TOKEN": "token"}, clear=True)
    def test_deployment_boundary_unauthenticated(self, mock_docker_ready):
        mock_docker_ready.return_value = True
        result = deployment_boundary()
        self.assertTrue(result["unauthenticated_local"])
        self.assertFalse(result["production_ready"])

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto", "ONECODE_ALLOW_UNAUTHENTICATED": "false", "ONECODE_API_TOKEN": ""}, clear=True)
    def test_deployment_boundary_no_token(self, mock_docker_ready):
        mock_docker_ready.return_value = True
        result = deployment_boundary()
        self.assertFalse(result["api_token_set"])
        self.assertFalse(result["production_ready"])

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "docker", "ONECODE_ALLOW_UNAUTHENTICATED": "false", "ONECODE_API_TOKEN": "token"}, clear=True)
    def test_deployment_boundary_sandbox_docker(self, mock_docker_ready):
        mock_docker_ready.return_value = False # Docker not ready but sandbox forced
        result = deployment_boundary()
        self.assertEqual(result["command_sandbox"], "docker")
        self.assertTrue(result["sandbox_effective"])
        self.assertFalse(result["production_ready"]) # Since docker_ready is False

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host", "ONECODE_ALLOW_UNAUTHENTICATED": "false", "ONECODE_API_TOKEN": "token"}, clear=True)
    def test_deployment_boundary_sandbox_host(self, mock_docker_ready):
        mock_docker_ready.return_value = True
        result = deployment_boundary()
        self.assertEqual(result["command_sandbox"], "host")
        self.assertFalse(result["sandbox_effective"])
        self.assertFalse(result["production_ready"])

    @patch('onecode.kernel.deployment_boundary._docker_daemon_ready')
    @patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "invalid_mode", "ONECODE_ALLOW_UNAUTHENTICATED": "false", "ONECODE_API_TOKEN": "token"}, clear=True)
    def test_deployment_boundary_invalid_mode_fallback(self, mock_docker_ready):
        mock_docker_ready.return_value = True
        result = deployment_boundary()
        self.assertEqual(result["command_sandbox"], "auto")

if __name__ == '__main__':
    unittest.main()
