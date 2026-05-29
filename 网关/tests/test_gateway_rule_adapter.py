import unittest
from pathlib import Path

from agent_skill_dictionary.gateway_rule_adapter import (
    aggregate_gateway_statuses,
    build_gateway_rule,
)


class GatewayRuleAdapterTest(unittest.TestCase):
    def test_all_true_evidence_maps_to_pure_yang_continue(self):
        rule = build_gateway_rule(
            {
                "sovereignty": True,
                "upstream": True,
                "policy": True,
                "artifact": True,
                "execution": True,
                "time": True,
            }
        )

        self.assertEqual(rule["gateway_status_code"], 63)
        self.assertEqual(rule["gateway_status_binary"], "111111")
        self.assertEqual(rule["outer_trigram"], "111")
        self.assertEqual(rule["inner_trigram"], "111")
        self.assertEqual(rule["polarity_index"], 1.0)
        self.assertEqual(rule["transition_action"], "cooldown")
        self.assertEqual(rule["transition_reason"], "yang_overload_cooldown")
        self.assertEqual(rule["dispatch_decision"], "continue")

    def test_sovereignty_breach_maps_to_fire_halt_stop(self):
        rule = build_gateway_rule({"event": "sovereignty_breach"})

        self.assertEqual(rule["gateway_status_code"], 48)
        self.assertEqual(rule["gateway_status_binary"], "110000")
        self.assertEqual(rule["outer_trigram_name"], "LI")
        self.assertEqual(rule["inner_trigram_name"], "KUN")
        self.assertEqual(rule["transition_action"], "halt")
        self.assertEqual(rule["transition_reason"], "sovereignty_fire_boundary")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_upstream_timeout_maps_to_checkpoint_stop(self):
        rule = build_gateway_rule({"event": "upstream_timeout"})

        self.assertEqual(rule["gateway_status_code"], 17)
        self.assertEqual(rule["gateway_status_binary"], "010001")
        self.assertEqual(rule["outer_trigram_name"], "KAN")
        self.assertEqual(rule["inner_trigram_name"], "ZHEN")
        self.assertEqual(rule["transition_action"], "checkpoint")
        self.assertEqual(rule["transition_reason"], "network_water_preserves_resume_seed")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_policy_gap_maps_to_discover_stop(self):
        rule = build_gateway_rule({"event": "policy_gap"})

        self.assertEqual(rule["gateway_status_code"], 0)
        self.assertEqual(rule["transition_action"], "discover")
        self.assertEqual(rule["transition_reason"], "rule_gap_discovery")
        self.assertEqual(rule["dispatch_decision"], "stop")

    def test_entropy_aggregation_is_polarity_aware(self):
        success = aggregate_gateway_statuses([63, 63])
        failure = aggregate_gateway_statuses([0, 0])

        self.assertEqual(success["decision"], "accept_positive_polarity")
        self.assertEqual(success["gateway_status_code"], 63)
        self.assertEqual(success["dispatch_decision"], "continue")
        self.assertEqual(failure["decision"], "rollback_negative_polarity")
        self.assertEqual(failure["gateway_status_code"], 17)
        self.assertEqual(failure["reason"], "entropy_negative_polarity_rollback")
        self.assertEqual(failure["dispatch_decision"], "stop")

    def test_rule_adapter_keeps_python39_compatible_popcount(self):
        source = Path("agent_skill_dictionary/gateway_rule_adapter.py").read_text()

        self.assertNotIn(".bit_count(", source)


if __name__ == "__main__":
    unittest.main()
