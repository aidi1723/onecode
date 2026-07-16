import unittest
from importlib.resources import files

from onecode.kernel.shell_projection import (
    SHELL_PROJECTION_FIELDS,
    project_run_to_shell,
    shell_projection_schema,
)


EXPECTED_CASE_NAMES = [
    "completed_full",
    "denied_full",
    "halted_resumable",
    "corrupt_evidence",
    "completed_wal_only",
    "legacy_missing_fields",
]
EXPECTED_V5_CASE_NAMES = [*EXPECTED_CASE_NAMES, "pending_approval"]


class ShellContractTests(unittest.TestCase):
    def _case(self, name):
        from onecode.contracts import load_shell_projection_v4_cases

        return next(case for case in load_shell_projection_v4_cases() if case["name"] == name)

    def test_shell_v4_contract_assets_are_declared_as_package_data(self):
        from pathlib import Path

        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('"onecode.contracts" = ["*.json"]', pyproject)

    def test_shell_v4_contract_assets_are_package_resources(self):
        contract_root = files("onecode.contracts")

        self.assertTrue(contract_root.joinpath("shell_projection_v4_schema.json").is_file())
        self.assertTrue(contract_root.joinpath("shell_projection_v4_cases.json").is_file())

    def test_shell_v5_contract_assets_are_package_resources(self):
        contract_root = files("onecode.contracts")

        self.assertTrue(contract_root.joinpath("shell_projection_v5_schema.json").is_file())
        self.assertTrue(contract_root.joinpath("shell_projection_v5_cases.json").is_file())

    def test_shell_v4_contract_assets_are_versioned_and_fresh(self):
        from onecode.contracts import (
            load_shell_projection_v4_cases,
            load_shell_projection_v4_schema,
        )

        schema = load_shell_projection_v4_schema()
        cases = load_shell_projection_v4_cases()

        self.assertEqual(schema["name"], "onecode.shell_projection")
        self.assertEqual(schema["version"], 4)
        self.assertEqual([case["name"] for case in cases], EXPECTED_CASE_NAMES)
        schema["version"] = 999
        cases[0]["name"] = "mutated"
        self.assertEqual(load_shell_projection_v4_schema()["version"], 4)
        self.assertEqual(load_shell_projection_v4_cases()[0]["name"], "completed_full")

    def test_current_shell_schema_matches_v5_public_fixture(self):
        from onecode.contracts import load_shell_projection_v5_schema

        self.assertEqual(shell_projection_schema(), load_shell_projection_v5_schema())

    def test_shell_v5_projection_cases_match_public_fixtures(self):
        from onecode.contracts import load_shell_projection_v5_cases

        cases = load_shell_projection_v5_cases()
        self.assertEqual([case["name"] for case in cases], EXPECTED_V5_CASE_NAMES)
        for case in cases:
            with self.subTest(case=case["name"]):
                self.assertEqual(project_run_to_shell(case["input"]), case["expected"])
                self.assertEqual(list(case["expected"]), list(SHELL_PROJECTION_FIELDS))

    def test_shell_v4_legacy_case_preserves_v1_and_empty_mutation_semantics(self):
        expected = self._case("legacy_missing_fields")["expected"]

        self.assertEqual(expected["rule_state"]["rule_schema"], "onecode-iching-v1")
        self.assertEqual(expected["balance_state"]["changed_bands"], [])
        self.assertIsNone(expected["balance_state"]["changed_asset_count"])
        self.assertIsNone(expected["balance_state"]["before_status_code"])

    def test_shell_v4_wal_case_restores_compact_aliases_without_inventing_bands(self):
        expected = self._case("completed_wal_only")["expected"]

        self.assertEqual(expected["rule_state"]["rule_schema"], "onecode-iching-v2")
        self.assertEqual(expected["balance_state"]["changed_asset_count"], 1)
        self.assertEqual(expected["balance_state"]["changed_line_count"], 1)
        self.assertEqual(expected["balance_state"]["changed_bands"], [])
        self.assertEqual(expected["balance_state"]["before_status_code"], 63)
        self.assertEqual(expected["balance_state"]["after_status_code"], 31)
        self.assertEqual(expected["control_state"]["skill_selection_reason"], "capability_match")
        self.assertEqual(expected["control_state"]["selected_skill_count"], 1)
        self.assertEqual(expected["evidence_ref"]["mode"], "wal")

    def test_descriptive_shell_evidence_does_not_change_authority_fields(self):
        base_input = {
            "run_id": "authority-base",
            "status": "completed",
            "rule_schema": "onecode-iching-v2",
            "iching_status_code": 63,
            "iching_transition_action": "allow",
            "task_dispatch_decision": "allow",
        }
        variants = [
            {
                **base_input,
                "balance_mutation_summary": {
                    "changed_asset_count": 1,
                    "total_changed_line_count": 1,
                    "changed_bands": ["heaven"],
                    "latest_before_status_code": 63,
                    "latest_after_status_code": 31,
                },
            },
            {
                **base_input,
                "ledger_path": ".onecode/runs/authority-base/ledger.json",
                "manifest_path": ".onecode/runs/authority-base/manifest.json",
                "trace_path": ".onecode/runs/authority-base/trace.jsonl",
                "profile_sha256": "c" * 64,
            },
            {
                **base_input,
                "skill_selection_reason": "capability_match",
                "selected_skill_count": 2,
                "skill_selection_sha256": "d" * 64,
            },
        ]
        base = project_run_to_shell(base_input)
        authority = self._authority_fields(base)

        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(self._authority_fields(project_run_to_shell(variant)), authority)

    @staticmethod
    def _authority_fields(projection):
        return (
            projection["severity"],
            projection["next_action"],
            projection["rule_state"]["transition_action"],
            projection["rule_state"]["transition_reason"],
            projection["rule_state"]["dispatch_decision"],
        )


if __name__ == "__main__":
    unittest.main()
