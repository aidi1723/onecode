import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json

from onecode.web.api import (
    handle_onecode_project_status,
    handle_onecode_project_init,
    handle_onecode_runs_list,
    handle_onecode_metrics,
    handle_onecode_run_inspect,
    handle_onecode_run_resume,
    handle_onecode_plan_approval,
    handle_onecode_verifier_presets,
    handle_onecode_verifier_policy_get,
    handle_onecode_verifier_policy_write,
    handle_onecode_model_config_get,
    handle_onecode_model_config_write,
    handle_onecode_models_discover,
    handle_onecode_gateway_adjudicate,
    handle_onecode_doctor,
    handle_onecode_audit_self,
    handle_onecode_run_evidence,
    read_json_document,
    model_timeout_seconds_from_env,
    query_workspace_param,
    parse_limit,
    parse_window_seconds,
    direct_chat_completion,
    run_light_task
)

class TestWebApiHandlers(unittest.TestCase):
    @patch('onecode.web.api.workspace_from_value')
    def test_handle_project_status_error(self, mock_wf):
        mock_wf.side_effect = ValueError("bad")
        res, code = handle_onecode_project_status({})
        self.assertEqual(code, 400)
        self.assertEqual(res["error"]["message"], "bad")

    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.project_status_payload')
    @patch('subprocess.run')
    def test_handle_project_init(self, mock_run, mock_payload, mock_wf):
        mock_wf.return_value = Path("/tmp/mock")
        mock_payload.return_value = {"ok": True}
        res, code = handle_onecode_project_init({"git": True, "verifierPolicy": True})
        self.assertEqual(code, 200)

    @patch('onecode.web.api.workspace_from_value')
    def test_handle_runs_list_error(self, mock_wf):
        mock_wf.side_effect = ValueError("bad")
        res, code = handle_onecode_runs_list({})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.list_runs')
    @patch('onecode.web.api.attach_shell_projection_to_runs_payload')
    def test_handle_runs_list_success(self, mock_attach, mock_list, mock_wf):
        mock_wf.return_value = Path("/tmp/mock")
        mock_list.return_value = {"runs": [{"id": 1}, {"id": 2}]}
        mock_attach.return_value = {"runs": [{"id": 2}]}
        res, code = handle_onecode_runs_list({"limit": 1})
        self.assertEqual(code, 200)

    @patch('onecode.web.api.workspace_from_value')
    def test_handle_metrics_error(self, mock_wf):
        mock_wf.side_effect = ValueError("bad")
        res, code = handle_onecode_metrics({})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.global_wal_metrics_summary')
    def test_handle_metrics_success(self, mock_wal, mock_wf):
        mock_wf.return_value = Path("/tmp/mock")
        mock_wal.return_value = {"data": 1}
        res, code = handle_onecode_metrics({"window_seconds": 3600})
        self.assertEqual(code, 200)

    @patch('onecode.web.api.validate_run_id')
    def test_handle_run_inspect_error(self, mock_val):
        mock_val.side_effect = ValueError("bad run id")
        res, code = handle_onecode_run_inspect("123", {})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.validate_run_id')
    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.inspect_run')
    @patch('onecode.web.api.attach_shell_projection')
    def test_handle_run_inspect_success(self, mock_attach, mock_inspect, mock_wf, mock_val):
        mock_val.return_value = "123"
        mock_wf.return_value = Path("/tmp")
        mock_inspect.return_value = (0, {"run": 1})
        mock_attach.return_value = {"run": 1, "attached": True}
        res, code = handle_onecode_run_inspect("123", {})
        self.assertEqual(code, 200)

    @patch('onecode.web.api.validate_run_id')
    def test_handle_run_resume_error(self, mock_val):
        mock_val.side_effect = ValueError("bad")
        res, code = handle_onecode_run_resume("123", {})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.workspace_from_value')
    def test_handle_plan_approval_error(self, mock_wf):
        res, code = handle_onecode_plan_approval("abc", {"approved": "not_bool"})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.verifier_policy_presets_summary')
    def test_verifier_presets(self, mock_pre):
        mock_pre.return_value = {"presets": []}
        res, code = handle_onecode_verifier_presets()
        self.assertEqual(code, 200)

    @patch('onecode.web.api.workspace_from_value')
    def test_handle_verifier_policy_get_error(self, mock_wf):
        mock_wf.side_effect = ValueError("bad")
        res, code = handle_onecode_verifier_policy_get({})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.workspace_from_value')
    def test_handle_verifier_policy_write_error(self, mock_wf):
        mock_wf.side_effect = ValueError("bad")
        res, code = handle_onecode_verifier_policy_write({})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.read_model_config')
    def test_model_config_get(self, mock_read):
        mock_read.return_value = {"config": 1}
        res, code = handle_onecode_model_config_get()
        self.assertEqual(code, 200)

    @patch('onecode.web.api.write_model_config')
    def test_model_config_write(self, mock_write):
        mock_write.return_value = {"config": 2}
        res, code = handle_onecode_model_config_write({})
        self.assertEqual(code, 200)

    def test_models_discover_error(self):
        res, code = handle_onecode_models_discover({})
        self.assertEqual(code, 400)

    def test_gateway_adjudicate_error(self):
        res, code = handle_onecode_gateway_adjudicate({})
        self.assertEqual(code, 400)

    @patch('onecode.web.api.run_doctor')
    def test_doctor(self, mock_doctor):
        mock_doctor.return_value = {"ok": True}
        res, code = handle_onecode_doctor()
        self.assertEqual(code, 200)

    @patch('onecode.web.api.audit_self')
    def test_audit_self(self, mock_audit):
        mock_audit.return_value = {"audit": True}
        res, code = handle_onecode_audit_self()
        self.assertEqual(code, 200)

    @patch('onecode.web.api.validate_run_id')
    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.inspect_run')
    @patch('onecode.web.api.attach_shell_projection')
    def test_run_evidence_wal_only(self, mock_attach, mock_inspect, mock_wf, mock_val):
        mock_val.return_value = "123"
        mock_wf.return_value = Path("/tmp")
        mock_inspect.return_value = (0, {"run": 1})
        mock_attach.return_value = {"evidence_mode": "wal", "wal_path": "/wal"}
        res, code = handle_onecode_run_evidence("123", {})
        self.assertEqual(code, 200)
        self.assertEqual(res["ledger_error"], "wal_only")

    @patch('onecode.web.api.validate_run_id')
    @patch('onecode.web.api.workspace_from_value')
    @patch('onecode.web.api.inspect_run')
    @patch('onecode.web.api.attach_shell_projection')
    @patch('onecode.web.api.PathGuard.resolve_contained')
    @patch('onecode.web.api.read_json_document')
    def test_run_evidence_success(self, mock_read, mock_guard, mock_attach, mock_inspect, mock_wf, mock_val):
        mock_val.return_value = "123"
        mock_wf.return_value = Path("/tmp")
        mock_inspect.return_value = (0, {"run": 1})
        mock_attach.return_value = {"ledger_path": "l", "manifest_path": "m"}
        mock_guard.return_value = Path("/tmp/mock")
        mock_read.side_effect = [
            ({"l": 1}, None),
            ({"checkpoints": [{"path": "c"}]}, None),
            ({"c": 1}, None)
        ]
        res, code = handle_onecode_run_evidence("123", {})
        self.assertEqual(code, 200)
        self.assertEqual(res["ledger"], {"l": 1})


    def test_read_json_document(self):
        # mock missing
        val, err = read_json_document(Path("/does_not_exist"))
        self.assertEqual(err, "missing_file")

        # mock invalid
        with patch.object(Path, 'read_text', return_value="not json"):
            val, err = read_json_document(Path("/mock"))
            self.assertEqual(err, "invalid_json")

        # mock not dict
        with patch.object(Path, 'read_text', return_value="[]"):
            val, err = read_json_document(Path("/mock"))
            self.assertEqual(err, "not_object")

    @patch('os.environ.get')
    def test_model_timeout_seconds(self, mock_get):
        mock_get.return_value = "abc"
        with self.assertRaises(ValueError):
            model_timeout_seconds_from_env()

    def test_parse_limit(self):
        self.assertEqual(parse_limit(False), 20)
        self.assertEqual(parse_limit("abc"), 20)
        self.assertEqual(parse_limit(150), 100)

    def test_parse_window(self):
        self.assertEqual(parse_window_seconds(False), 60)
        self.assertEqual(parse_window_seconds("abc"), 60)

    @patch('onecode.web.api.run_task')
    def test_run_light_task(self, mock_run):
        mock_run.return_value = {"res": 1}
        res = run_light_task("task", workspace=Path("/tmp"))
        self.assertEqual(res, {"res": 1})

    @patch('urllib.request.urlopen')
    @patch('onecode.web.api.api_key_from_env')
    @patch('onecode.web.api.build_provider_config')
    def test_direct_chat_completion(self, mock_build, mock_key, mock_url):
        mock_config = MagicMock()
        mock_config.model = "m"
        mock_config.endpoint = "http://e"
        mock_build.return_value = mock_config
        mock_key.return_value = "key"

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "hello"}}]}'
        mock_url.return_value.__enter__.return_value = mock_response

        res = direct_chat_completion([{"role": "user", "content": "hi"}], model="m", provider_kind="pk", endpoint="http://e")
        self.assertEqual(res, "hello")

    @patch('urllib.request.urlopen')
    @patch('onecode.web.api.api_key_from_env')
    @patch('onecode.web.api.build_provider_config')
    def test_direct_chat_completion_timeout(self, mock_build, mock_key, mock_url):
        mock_config = MagicMock()
        mock_config.model = "m"
        mock_config.endpoint = "http://e"
        mock_build.return_value = mock_config
        mock_key.return_value = "key"
        
        mock_url.side_effect = TimeoutError("timeout")
        with self.assertRaises(TimeoutError):
            direct_chat_completion([{"role": "user", "content": "hi"}], model="m", provider_kind="pk", endpoint="http://e")

if __name__ == '__main__':
    unittest.main()
