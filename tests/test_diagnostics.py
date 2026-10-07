import unittest
from unittest.mock import patch, MagicMock, ANY

from onecode.kernel.diagnostics import (
    doctor_check,
    doctor_result_detail,
    doctor_rule_passed,
    run_doctor
)

class TestDiagnostics(unittest.TestCase):
    def test_doctor_check(self):
        result = doctor_check("test_check", True, {"key": "value"})
        self.assertEqual(result, {"name": "test_check", "passed": True, "detail": {"key": "value"}})

    def test_doctor_check_no_detail(self):
        result = doctor_check("test_check", False)
        self.assertEqual(result, {"name": "test_check", "passed": False, "detail": {}})

    def test_doctor_result_detail(self):
        result = {
            "run_id": "r1",
            "status": "ok",
            "reason": "done",
            "iching_status_code": 100,
            "iching_transition_action": "start",
            "iching_transition_reason": "init",
            "iching_profile": {
                "dispatch_decision": "allow"
            }
        }
        detail = doctor_result_detail(result)
        self.assertEqual(detail, {
            "run_id": "r1",
            "status": "ok",
            "reason": "done",
            "iching_status_code": 100,
            "iching_transition_action": "start",
            "iching_transition_reason": "init",
            "dispatch_decision": "allow"
        })

    @patch('onecode.kernel.diagnostics.IchingKernel')
    def test_doctor_rule_passed_true(self, mock_iching):
        mock_transition = MagicMock()
        mock_transition.action = "start"
        mock_transition.reason = "init"
        mock_iching.transition.return_value = mock_transition
        mock_iching.dispatch_decision.return_value = "allow"

        result = {
            "iching_status_code": 100,
            "iching_profile": {
                "status_code": 100,
                "transition": {
                    "action": "start",
                    "reason": "init"
                },
                "dispatch_decision": "allow"
            }
        }
        self.assertTrue(doctor_rule_passed(result))

    @patch('onecode.kernel.diagnostics.IchingKernel')
    def test_doctor_rule_passed_false(self, mock_iching):
        mock_transition = MagicMock()
        mock_transition.action = "start"
        mock_transition.reason = "init"
        mock_iching.transition.return_value = mock_transition
        mock_iching.dispatch_decision.return_value = "allow"

        result = {
            "iching_status_code": 100,
            "iching_profile": {
                "status_code": 100,
                "transition": {
                    "action": "stop", # Different action
                    "reason": "init"
                },
                "dispatch_decision": "allow"
            }
        }
        self.assertFalse(doctor_rule_passed(result))

    @patch('onecode.kernel.diagnostics.run_task')
    @patch('onecode.kernel.diagnostics.discover_project_context')
    @patch('onecode.kernel.diagnostics.inspect_runtime_config')
    @patch('onecode.kernel.diagnostics.discover_skill_context')
    @patch('onecode.kernel.diagnostics.recovery_status')
    @patch('onecode.kernel.diagnostics.deployment_boundary')
    @patch('onecode.kernel.diagnostics.doctor_rule_passed')
    def test_run_doctor_all_pass(
        self, mock_rule_passed, mock_deployment, mock_recovery,
        mock_skill, mock_runtime, mock_project, mock_run_task
    ):
        mock_rule_passed.return_value = True
        
        def run_task_side_effect(task, workspace, **kwargs):
            if task == "doctor write":
                (workspace / "src").mkdir(parents=True, exist_ok=True)
                (workspace / "src" / "doctor_asset.py").write_text("value = 1\n", encoding="utf-8")
                return {"status": "completed", "run_id": "r1", "reason": "", "iching_status_code": 0, "iching_transition_action": "", "iching_transition_reason": "", "iching_profile": {"dispatch_decision": ""}}
            if task == "doctor source":
                (workspace / "src").mkdir(parents=True, exist_ok=True)
                (workspace / "src" / "resume_asset.py").write_text("ready = True\n", encoding="utf-8")
                return {"status": "completed", "run_id": "r2"}
            if task == "doctor resume":
                return {"status": "skipped", "reason": "resumed_asset_ready", "run_id": "r3", "iching_status_code": 0, "iching_transition_action": "", "iching_transition_reason": "", "iching_profile": {"dispatch_decision": ""}}
            if task == "doctor breach":
                return {"status": "halted", "reason": "sovereignty_breach", "run_id": "r4", "iching_status_code": 0, "iching_transition_action": "", "iching_transition_reason": "", "iching_profile": {"dispatch_decision": ""}}
            if task == "doctor timeout":
                return {"status": "halted", "reason": "http_timeout", "run_id": "r5", "iching_status_code": 0, "iching_transition_action": "", "iching_transition_reason": "", "iching_profile": {"dispatch_decision": ""}}

        mock_run_task.side_effect = run_task_side_effect
        
        mock_project.return_value = {"status": "ok"}
        mock_runtime.return_value = {"status": "ok"}
        mock_skill.return_value = {"status": "ok"}
        mock_recovery.return_value = {"recommended_action": "retry_once"}
        mock_deployment.return_value = {"docker_ready": True}

        result = run_doctor()
        self.assertEqual(result["status"], "ok")

if __name__ == '__main__':
    unittest.main()
