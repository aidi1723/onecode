import unittest

from onecode.experimental.hexagram_recast import apply_hexagram_recast, parse_hexagram


FACTS = {
    "intent_type": "write_text",
    "path_scope": "workspace_relative",
    "sandbox_state": "not_required",
    "evidence_state": "present",
}


def observed_decision() -> dict:
    return {
        "observe": True,
        "abstained": True,
        "yizijue_state": "010010",
        "status_code": 0b010010,
        "facts": FACTS,
        "action": "DENY_AND_LEDGER",
        "projected_action": "ALLOW_ATOMIC_WRITE",
    }


class HexagramRecastTests(unittest.TestCase):
    def test_only_a_hexagram_is_accepted(self):
        self.assertEqual(parse_hexagram("111111"), 0b111111)
        self.assertEqual(parse_hexagram(0), 0)
        for rejected in ("ALLOW_ATOMIC_WRITE", "64", "1111111", True, None, ""):
            with self.assertRaises(ValueError):
                parse_hexagram(rejected)

    def test_committed_recast_is_read_by_the_gateway(self):
        updated = apply_hexagram_recast(observed_decision(), "111111")
        self.assertEqual(updated["yizijue_state"], "111111")
        self.assertEqual(updated["action"], "ALLOW_ATOMIC_WRITE")
        self.assertFalse(updated["observe"])
        self.assertEqual(updated["recast_from"], "010010")

    def test_an_action_name_keeps_the_observe_withhold(self):
        updated = apply_hexagram_recast(observed_decision(), "ALLOW_ATOMIC_WRITE")
        self.assertTrue(updated["recast_rejected"])
        self.assertEqual(updated["action"], "DENY_AND_LEDGER")
        self.assertEqual(updated["yizijue_state"], "010010")

    def test_a_firm_cast_ignores_recast(self):
        firm = observed_decision()
        firm["observe"] = False
        firm["action"] = "SOVEREIGNTY_HALT"
        firm["yizijue_state"] = "100001"
        self.assertEqual(apply_hexagram_recast(firm, "111111")["action"], "SOVEREIGNTY_HALT")


if __name__ == "__main__":
    unittest.main()
