import unittest

from agent_skill_dictionary.kernel_contract import (
    HexagramRouter,
    KernelContractError,
    assert_postflight_contract,
    assert_preflight_contract,
    assert_runtime_contract,
    validate_summary_contract,
)


class KernelContractTest(unittest.TestCase):
    def test_preflight_contract_rejects_unmasked_write_tool_in_inspect_state(self):
        with self.assertRaises(KernelContractError) as caught:
            assert_preflight_contract(
                "查",
                {
                    "tools": [
                        {"type": "function", "function": {"name": "read_file"}},
                        {"type": "function", "function": {"name": "write_file"}},
                    ]
                },
            )

        self.assertEqual(caught.exception.reason, "preflight_tool_not_allowed")

    def test_postflight_contract_rejects_success_handoff_after_failed_verify(self):
        with self.assertRaises(KernelContractError) as caught:
            assert_postflight_contract(
                "测",
                {
                    "exit_code": 1,
                    "next_suggested_state": "记",
                },
            )

        self.assertEqual(caught.exception.reason, "postflight_invalid_failure_route")

    def test_contract_rejects_write_tool_in_inspect_state(self):
        with self.assertRaises(KernelContractError) as caught:
            assert_runtime_contract(
                active_opcode="查",
                model_request={
                    "tools": [
                        {"type": "function", "function": {"name": "read_file"}},
                        {"type": "function", "function": {"name": "edit_scoped_file"}},
                    ]
                },
                sandbox_response={},
            )

        self.assertEqual(caught.exception.reason, "tool_not_allowed")

    def test_contract_requires_verify_tool_in_test_state(self):
        with self.assertRaises(KernelContractError) as caught:
            assert_runtime_contract(
                active_opcode="测",
                model_request={"tools": [{"type": "function", "function": {"name": "read_file"}}]},
                sandbox_response={},
            )

        self.assertEqual(caught.exception.reason, "required_tool_missing")

    def test_contract_rejects_success_route_after_nonzero_exit(self):
        with self.assertRaises(KernelContractError) as caught:
            assert_runtime_contract(
                active_opcode="测",
                model_request={"tools": [{"type": "function", "function": {"name": "run_pytest"}}]},
                sandbox_response={"exit_code": 1, "next_suggested_state": "总"},
            )

        self.assertEqual(caught.exception.reason, "invalid_failure_route")

    def test_contract_accepts_valid_verify_failure_route(self):
        assert_runtime_contract(
            active_opcode="测",
            model_request={"tools": [{"type": "function", "function": {"name": "run_pytest"}}]},
            sandbox_response={"exit_code": 1, "next_suggested_state": "修"},
        )

    def test_summary_contract_requires_structured_handoff_fields(self):
        with self.assertRaises(KernelContractError) as caught:
            validate_summary_contract({"remaining_risk": "low"})

        self.assertEqual(caught.exception.reason, "summary_contract_missing_fields")
        self.assertIn("implemented_patch_sha256", caught.exception.details["missing_fields"])

    def test_summary_contract_accepts_structured_handoff(self):
        validated = validate_summary_contract(
            {
                "implemented_patch_sha256": "0" * 64,
                "remaining_risk": "low",
                "next_opcode_recommendation": "记",
            }
        )

        self.assertEqual(validated["remaining_risk"], "low")

    def test_hexagram_router_zero_tool_for_earth_over_fire(self):
        route = HexagramRouter.determine_skill_mount("101", "000")

        self.assertEqual(route["hexagram_code"], "000101")
        self.assertEqual(route["action"], "ZERO_TOOL_BYPASS")
        self.assertEqual(route["allowed_skills"], [])
        self.assertEqual(route["force_tools"], [])

    def test_hexagram_router_zero_tool_clarify_for_earth_over_lake(self):
        route = HexagramRouter.determine_skill_mount("110", "000")

        self.assertEqual(route["hexagram_code"], "000110")
        self.assertEqual(route["action"], "ZERO_TOOL_CLARIFY")
        self.assertEqual(route["allowed_skills"], [])
        self.assertEqual(route["force_tools"], [])

    def test_hexagram_router_launches_guard_for_wind_over_water(self):
        route = HexagramRouter.determine_skill_mount("010", "011")

        self.assertEqual(route["hexagram_code"], "011010")
        self.assertEqual(route["action"], "LAUNCH_PHYSICAL_GUARD")
        self.assertEqual(route["force_tools"], ["run_security_scan"])
        self.assertIn("osv_scanner_scan", route["allowed_skills"])
        self.assertIn("semgrep_audit", route["allowed_skills"])

    def test_hexagram_router_launches_sandbox_for_wind_over_thunder(self):
        route = HexagramRouter.determine_skill_mount("100", "011")

        self.assertEqual(route["hexagram_code"], "011100")
        self.assertEqual(route["action"], "LAUNCH_ISOLATED_SANDBOX")
        self.assertEqual(route["force_tools"], ["run_pytest_in_sandbox", "edit_scoped_file"])

    def test_hexagram_router_defaults_to_human_halt(self):
        route = HexagramRouter.determine_skill_mount("111", "101")

        self.assertEqual(route["action"], "FORCE_HALT_TO_HUMAN")
        self.assertEqual(route["allowed_skills"], [])
        self.assertEqual(route["force_tools"], [])


if __name__ == "__main__":
    unittest.main()
