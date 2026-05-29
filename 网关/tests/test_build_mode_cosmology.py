import unittest

from agent_skill_dictionary.build_mode_cosmology import (
    FOUR象_SCOPE_MAP,
    MUTUAL_OVERCOMING_EDGES,
    MUTUAL_GENERATION_EDGES,
    TWO_FORCES,
    cosmology_profile,
    validate_cosmology_contract,
)
from agent_skill_dictionary.build_mode_v3_balancer import BAGUA_ELEMENT_MAP


class BuildModeCosmologyTest(unittest.TestCase):
    def test_two_forces_four_scopes_bagua_and_five_elements_are_total(self):
        self.assertEqual(set(TWO_FORCES), {"yin", "yang"})
        self.assertEqual(set(FOUR象_SCOPE_MAP), {"00", "01", "10", "11"})
        self.assertEqual(set(BAGUA_ELEMENT_MAP), {"000", "001", "010", "011", "100", "101", "110", "111"})
        self.assertEqual(validate_cosmology_contract(), [])

    def test_each_hexagram_profile_has_operational_roles(self):
        create = cosmology_profile("111")
        halt = cosmology_profile("100")
        prompt = cosmology_profile("011")

        self.assertEqual(create.force, "yang")
        self.assertEqual(create.scope, "11")
        self.assertEqual(create.element, "金")
        self.assertEqual(create.permission_role, "scoped_privilege")
        self.assertEqual(halt.force, "yin")
        self.assertEqual(halt.permission_role, "privilege_revocation")
        self.assertEqual(prompt.scope, "01")
        self.assertEqual(prompt.resource_role, "derivative_watchdog")

    def test_generation_and_overcoming_edges_have_valid_hexagram_targets(self):
        all_codes = set(BAGUA_ELEMENT_MAP)
        for source, target, reason in [*MUTUAL_GENERATION_EDGES, *MUTUAL_OVERCOMING_EDGES]:
            self.assertIn(source, all_codes, reason)
            self.assertIn(target, all_codes, reason)


if __name__ == "__main__":
    unittest.main()
