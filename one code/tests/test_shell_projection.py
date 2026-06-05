import unittest


class ShellProjectionTests(unittest.TestCase):
    def test_shell_projection_schema_is_explicit_and_stable(self):
        from onecode.kernel.shell_projection import (
            CONTROL_STATE_FIELDS,
            DELIVERY_STATE_FIELDS,
            EVIDENCE_REF_FIELDS,
            RESUME_STATE_FIELDS,
            RULE_STATE_FIELDS,
            SHELL_PROJECTION_FIELDS,
            SHELL_PROJECTION_VERSION,
            project_run_to_shell,
        )

        projection = project_run_to_shell({"run_id": "schema-run", "status": "completed"})

        self.assertEqual(SHELL_PROJECTION_VERSION, 1)
        self.assertEqual(tuple(projection.keys()), SHELL_PROJECTION_FIELDS)
        self.assertEqual(tuple(projection["rule_state"].keys()), RULE_STATE_FIELDS)
        self.assertEqual(tuple(projection["control_state"].keys()), CONTROL_STATE_FIELDS)
        self.assertEqual(tuple(projection["delivery_state"].keys()), DELIVERY_STATE_FIELDS)
        self.assertEqual(tuple(projection["evidence_ref"].keys()), EVIDENCE_REF_FIELDS)
        self.assertEqual(tuple(projection["resume_state"].keys()), RESUME_STATE_FIELDS)
        self.assertEqual(projection["version"], SHELL_PROJECTION_VERSION)

    def test_shell_projection_schema_payload_is_machine_readable(self):
        from onecode.kernel.shell_projection import shell_projection_schema

        schema = shell_projection_schema()

        self.assertEqual(schema["name"], "onecode.shell_projection")
        self.assertEqual(schema["version"], 1)
        self.assertEqual(schema["fields"]["severity"]["values"], ["blocked", "corrupt", "missing", "ok", "warning"])
        self.assertIn("rule_state", schema["fields"])
        self.assertIn("control_state", schema["fields"])
        self.assertIn("evidence_ref", schema["fields"])
        self.assertEqual(
            schema["nested_fields"]["control_state"],
            ["project_context_status", "runtime_config_status", "recovery_action"],
        )
        self.assertEqual(schema["nested_fields"]["resume_state"], ["resumed", "resumed_from"])

    def test_completed_result_projects_control_state_without_changing_severity(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "control-run",
                "status": "completed",
                "project_context": {"status": "ok", "summary": {"element": "wood"}},
                "runtime_config": {"status": "warning", "summary": {"element": "earth"}},
                "recovery_policy": {"recommended_action": "retry_once", "element": "fire"},
            }
        )

        self.assertEqual(projection["control_state"]["project_context_status"], "ok")
        self.assertEqual(projection["control_state"]["runtime_config_status"], "warning")
        self.assertEqual(projection["control_state"]["recovery_action"], "retry_once")
        self.assertEqual(projection["severity"], "ok")

    def test_control_state_falls_back_to_flat_fields(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "flat-control-run",
                "status": "completed",
                "project_context_status": "ok",
                "runtime_config_status": "warning",
                "recovery_action": "retry_once",
            }
        )

        self.assertEqual(projection["control_state"]["project_context_status"], "ok")
        self.assertEqual(projection["control_state"]["runtime_config_status"], "warning")
        self.assertEqual(projection["control_state"]["recovery_action"], "retry_once")

    def test_control_state_falls_through_unusable_nested_values(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "fallback-control-run",
                "status": "completed",
                "project_context": {"summary": {"element": "wood"}},
                "project_context_status": "ok",
                "runtime_config": {"status": "   ", "summary": {"element": "earth"}},
                "runtime_config_status": "warning",
                "recovery_policy": {"element": "fire"},
                "recovery": {"action": "repair_once"},
                "recovery_action": "retry_once",
            }
        )

        self.assertEqual(projection["control_state"]["project_context_status"], "ok")
        self.assertEqual(projection["control_state"]["runtime_config_status"], "warning")
        self.assertEqual(projection["control_state"]["recovery_action"], "repair_once")

    def test_wal_completed_result_projects_rule_and_evidence_state(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "wal-run",
                "status": "completed",
                "reason": None,
                "partial": False,
                "evidence_mode": "wal",
                "wal_path": "/tmp/work/.onecode/global-ledger.jsonl",
                "iching_status_code": 63,
                "iching_transition_action": "ALLOW",
                "iching_transition_reason": "complete",
                "decision": "allow",
                "delivery_status": "deliverable",
                "next_action": "idle",
                "requested_count": 1,
                "completed_count": 1,
                "skipped_count": 0,
                "failed_count": 0,
                "profile_sha256": "abc123",
            }
        )

        self.assertEqual(projection["version"], 1)
        self.assertEqual(projection["run_id"], "wal-run")
        self.assertEqual(projection["status_label"], "completed")
        self.assertEqual(projection["severity"], "ok")
        self.assertEqual(projection["next_action"], "idle")
        self.assertEqual(projection["rule_state"]["status_code"], 63)
        self.assertEqual(projection["rule_state"]["transition_action"], "ALLOW")
        self.assertEqual(projection["rule_state"]["dispatch_decision"], "allow")
        self.assertEqual(projection["delivery_state"]["status"], "deliverable")
        self.assertEqual(projection["delivery_state"]["completed_count"], 1)
        self.assertEqual(projection["evidence_ref"]["mode"], "wal")
        self.assertEqual(projection["evidence_ref"]["wal_path"], "/tmp/work/.onecode/global-ledger.jsonl")
        self.assertEqual(projection["evidence_ref"]["profile_sha256"], "abc123")
        self.assertIn("wal-run", projection["compact_message"])
        self.assertIn("completed", projection["compact_message"])

    def test_full_completed_result_projects_full_evidence_paths(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "full-run",
                "status": "completed",
                "evidence_mode": "full",
                "ledger_path": "/tmp/work/.onecode/runs/full-run/ledger.json",
                "manifest_path": "/tmp/work/.onecode/runs/full-run/manifest.json",
                "trace_path": "/tmp/work/.onecode/runs/full-run/trace.jsonl",
                "iching_status_code": 63,
                "iching_transition_action": "ALLOW",
            }
        )

        self.assertEqual(projection["severity"], "ok")
        self.assertEqual(projection["evidence_ref"]["mode"], "full")
        self.assertEqual(projection["evidence_ref"]["ledger_path"], "/tmp/work/.onecode/runs/full-run/ledger.json")
        self.assertEqual(projection["evidence_ref"]["manifest_path"], "/tmp/work/.onecode/runs/full-run/manifest.json")
        self.assertEqual(projection["evidence_ref"]["trace_path"], "/tmp/work/.onecode/runs/full-run/trace.jsonl")

    def test_halted_or_denied_result_projects_blocked_state(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "blocked-run",
                "status": "halted",
                "reason": "policy_denied",
                "partial": True,
                "delivery_status": "blocked",
                "next_action": "inspect",
                "iching_status_code": 16,
                "iching_transition_action": "HALT",
                "task_dispatch_decision": "deny",
            }
        )

        self.assertEqual(projection["status_label"], "halted")
        self.assertEqual(projection["severity"], "blocked")
        self.assertEqual(projection["next_action"], "inspect")
        self.assertEqual(projection["rule_state"]["dispatch_decision"], "deny")
        self.assertIn("policy_denied", projection["compact_message"])

    def test_corrupt_inspect_summary_projects_corrupt_path(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "bad-run",
                "status": "corrupt",
                "corrupt_path": "/tmp/work/.onecode/global-ledger.jsonl",
                "corrupt_reason": "global_wal_chain_hash_mismatch",
                "wal_path": "/tmp/work/.onecode/global-ledger.jsonl",
            }
        )

        self.assertEqual(projection["severity"], "corrupt")
        self.assertEqual(projection["next_action"], "inspect")
        self.assertEqual(projection["evidence_ref"]["mode"], "wal")
        self.assertEqual(projection["evidence_ref"]["corrupt_path"], "/tmp/work/.onecode/global-ledger.jsonl")
        self.assertIn("global_wal_chain_hash_mismatch", projection["compact_message"])

    def test_resume_skipped_result_projects_resume_state(self):
        from onecode.kernel.shell_projection import project_run_to_shell

        projection = project_run_to_shell(
            {
                "run_id": "resume-run",
                "status": "skipped",
                "reason": "task_resume_ready",
                "resumed": True,
                "resumed_from": "source-run",
                "next_action": "idle",
            }
        )

        self.assertEqual(projection["status_label"], "skipped")
        self.assertEqual(projection["resume_state"]["resumed"], True)
        self.assertEqual(projection["resume_state"]["resumed_from"], "source-run")

    def test_runs_payload_projection_keeps_original_payload_and_projects_each_run(self):
        from onecode.kernel.shell_projection import attach_shell_projection_to_runs_payload

        original = {
            "workspace": "/tmp/work",
            "runs": [
                {"run_id": "a", "status": "completed", "evidence_mode": "wal", "wal_path": "/tmp/wal.jsonl"},
                {"run_id": "b", "status": "corrupt", "corrupt_path": "/tmp/bad.json"},
            ],
        }

        projected = attach_shell_projection_to_runs_payload(original)

        self.assertIsNot(projected, original)
        self.assertNotIn("shell_projection", original["runs"][0])
        self.assertEqual(projected["workspace"], "/tmp/work")
        self.assertEqual(projected["runs"][0]["shell_projection"]["run_id"], "a")
        self.assertEqual(projected["runs"][0]["shell_projection"]["evidence_ref"]["mode"], "wal")
        self.assertEqual(projected["runs"][1]["shell_projection"]["severity"], "corrupt")


if __name__ == "__main__":
    unittest.main()
