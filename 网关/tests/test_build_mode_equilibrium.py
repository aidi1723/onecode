import unittest

from agent_skill_dictionary.build_mode_equilibrium import decide_equilibrium, measure_balance
from agent_skill_dictionary.build_mode_orchestrator import ArtifactGap, SECURE_RPC_MESH_PLAN


def _gap(present=()):
    present = tuple(present)
    missing = tuple(
        artifact.path
        for artifact in SECURE_RPC_MESH_PLAN.artifacts
        if artifact.path not in present
    )
    next_artifact = next(
        (artifact for artifact in SECURE_RPC_MESH_PLAN.artifacts if artifact.path in missing),
        None,
    )
    return ArtifactGap(
        plan=SECURE_RPC_MESH_PLAN,
        present_paths=present,
        missing_paths=missing,
        next_artifact=next_artifact,
    )


def _tool(name):
    return {"type": "function", "function": {"name": name}}


class BuildModeEquilibriumTest(unittest.TestCase):
    def test_missing_artifact_forces_incremental_create_write_channel(self):
        decision = decide_equilibrium(_gap(), {}, available_tools=[_tool("run_pytest")])

        self.assertEqual(decision.hexagram, "111")
        self.assertEqual(decision.source, "artifact_continuation_gate")
        self.assertEqual(decision.tool_name, "write_file")
        self.assertEqual(decision.target_path, "core/crypto.py")
        self.assertEqual(decision.balance.mode, "incremental_create")
        self.assertEqual(decision.balance.allowed_tool_names, ("write_file",))

    def test_complete_plan_without_prior_verify_forces_canonical_verify(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))

        decision = decide_equilibrium(gap, {}, available_tools=[_tool("apply_patch")])

        self.assertEqual(decision.hexagram, "001")
        self.assertEqual(decision.source, "artifact_verify_gate")
        self.assertEqual(decision.tool_name, "run_pytest")
        self.assertEqual(decision.balance.mode, "canonical_verify")

    def test_failed_verify_forces_scoped_repair_write_even_when_gap_is_zero(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))
        state = {
            "results": [
                {
                    "hexagram": "001",
                    "status": "needs_fix",
                    "exit_code": 1,
                    "failure_summary": "FAILED tests/test_mesh.py::test_encrypt",
                }
            ]
        }

        decision = decide_equilibrium(
            gap,
            state,
            repair_target_path="core/crypto.py",
            available_tools=[_tool("run_pytest")],
        )

        self.assertEqual(decision.hexagram, "111")
        self.assertEqual(decision.source, "artifact_repair_gate")
        self.assertEqual(decision.tool_name, "write_file")
        self.assertEqual(decision.target_path, "core/crypto.py")
        self.assertEqual(decision.balance.mode, "repair_create")
        self.assertEqual(decision.balance.violations, ())

    def test_successful_verify_forces_archive_lockdown(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))
        state = {"results": [{"hexagram": "001", "status": "completed", "exit_code": 0}]}

        decision = decide_equilibrium(gap, state, available_tools=[_tool("write_file")])

        self.assertEqual(decision.hexagram, "000")
        self.assertEqual(decision.source, "artifact_archive_gate")
        self.assertIsNone(decision.tool_name)
        self.assertTrue(decision.force_empty_tools)
        self.assertEqual(decision.balance.mode, "archive_lockdown")
        self.assertEqual(decision.balance.allowed_tool_names, ())

    def test_repair_write_success_returns_to_verify_instead_of_repair_loop(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))
        state = {
            "results": [
                {"hexagram": "001", "status": "needs_fix", "exit_code": 1},
                {"hexagram": "111", "status": "ok", "changed_files": ["core/crypto.py"]},
            ],
            "consecutive_failures": 1,
        }

        decision = decide_equilibrium(gap, state, available_tools=[_tool("write_file")])

        self.assertEqual(decision.hexagram, "001")
        self.assertEqual(decision.source, "artifact_verify_gate")
        self.assertEqual(decision.tool_name, "run_pytest")

    def test_observed_balance_reports_gap_without_write_channel(self):
        snapshot = measure_balance(_gap(("core/crypto.py",)), [_tool("run_pytest")])

        self.assertIn("gap_without_write_channel", snapshot.violations)

    def test_observed_balance_does_not_flag_scoped_repair_write_after_failed_verify(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))
        state = {"results": [{"hexagram": "001", "status": "needs_fix", "exit_code": 1}]}

        decision = decide_equilibrium(gap, state, available_tools=[_tool("write_file")])

        self.assertEqual(decision.balance.mode, "repair_create")
        self.assertNotIn("write_channel_after_gap_zero", decision.balance.violations)

    def test_repair_initial_balance_does_not_mark_write_after_gap_zero_as_violation(self):
        gap = _gap(("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"))
        state = {"results": [{"hexagram": "001", "status": "needs_fix", "exit_code": 1}]}

        decision = decide_equilibrium(gap, state, available_tools=[_tool("write_file")])

        initial_balance = decision.metadata["initial_balance"]
        self.assertNotIn("write_channel_after_gap_zero", initial_balance["violations"])


if __name__ == "__main__":
    unittest.main()
