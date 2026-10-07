import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

from onecode.web.api import OneCodeRequestHandler

class TestWebHttp(unittest.TestCase):
    def setUp(self):
        self.request = MagicMock()
        self.client_address = ('127.0.0.1', 12345)
        self.server = MagicMock()
        self.server.server_address = ('127.0.0.1', 8080)
        
    def build_handler(self, method, path, body=b'', headers=None):
        if headers is None:
            headers = {}
        headers['Content-Length'] = str(len(body))
        
        class MockHandler(OneCodeRequestHandler):
            def __init__(self, request, client_address, server):
                self.rfile = BytesIO(body)
                self.wfile = BytesIO()
                self.command = method
                self.path = path
                self.headers = headers
                self.client_address = client_address
                self.server = server
                self._local_boundary_allowed = lambda: True
                
            def send_response(self, code, message=None):
                self.status_code = code
                
            def send_header(self, keyword, value):
                pass
                
            def end_headers(self):
                pass

            def setup(self):
                pass

            def finish(self):
                pass
                
        handler = MockHandler(self.request, self.client_address, self.server)
        return handler

    @patch('onecode.web.api.request_authorized')
    def test_do_GET_unauthorized(self, mock_auth):
        mock_auth.return_value = False
        handler = self.build_handler('GET', '/v1/onecode/project/status')
        handler.do_GET()
        self.assertEqual(handler.status_code, 401)
        
    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_project_status')
    def test_do_GET_project_status(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"status": "ok"}, 200)
        handler = self.build_handler('GET', '/v1/onecode/project/status?workspace=foo')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_runs_list')
    def test_do_GET_runs(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"runs": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/runs?workspace=foo&limit=10')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_metrics')
    def test_do_GET_metrics(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"metrics": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/metrics?workspace=foo')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_verifier_presets')
    def test_do_GET_verifier_presets(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"presets": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/verifier/presets')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_verifier_policy_get')
    def test_do_GET_verifier_policy(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"policy": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/verifier/policy?workspace=foo')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_model_config_get')
    def test_do_GET_model_config(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"config": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/model-config')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_doctor')
    def test_do_POST_doctor(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"doctor": []}, 200)
        handler = self.build_handler('POST', '/v1/onecode/doctor', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_audit_self')
    def test_do_POST_audit_self(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"audit": []}, 200)
        handler = self.build_handler('POST', '/v1/onecode/audit-self', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_run_inspect')
    def test_do_GET_run_inspect(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"run": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/runs/123/inspect?workspace=foo')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_run_evidence')
    def test_do_GET_run_evidence(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"evidence": []}, 200)
        handler = self.build_handler('GET', '/v1/onecode/runs/123/evidence?workspace=foo')
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    def test_do_GET_not_found(self, mock_auth):
        mock_auth.return_value = True
        handler = self.build_handler('GET', '/v1/not/found')
        handler.do_GET()
        self.assertEqual(handler.status_code, 404)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_project_init')
    def test_do_POST_project_init(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/project/init', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_verifier_policy_write')
    def test_do_POST_verifier_policy(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/verifier/policy', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_model_config_write')
    def test_do_POST_model_config(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/model-config', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_models_discover')
    def test_do_POST_models_discover(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/models/discover', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_run_resume')
    def test_do_POST_run_resume(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/runs/123/resume', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_plan_approval')
    def test_do_POST_plan_approval(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/plans/123/approval', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

    @patch('onecode.web.api.request_authorized')
    @patch('onecode.web.api.handle_onecode_gateway_adjudicate')
    def test_do_POST_gateway(self, mock_handle, mock_auth):
        mock_auth.return_value = True
        mock_handle.return_value = ({"ok": True}, 200)
        handler = self.build_handler('POST', '/v1/onecode/gateway/adjudicate', body=b'{}')
        handler.do_POST()
        self.assertEqual(handler.status_code, 200)

if __name__ == '__main__':
    unittest.main()
