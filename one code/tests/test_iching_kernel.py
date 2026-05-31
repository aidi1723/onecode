import math
import unittest
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel


class TestIchingKernel(unittest.TestCase):
    def test_hexagram_bitwise_收敛与自愈路由(self):
        status = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)
        self.assertEqual(status, 59)
        self.assertTrue(IchingKernel.should_skip(status))
        self.assertEqual(
            IchingKernel.skip_decision(status),
            {
                "should_skip": True,
                "reason": "asset_ready_without_sovereignty_fire",
                "inner_trigram": IchingKernel.DUI,
                "outer_trigram": IchingKernel.QIAN,
                "inner_element": "metal",
                "outer_element": "metal",
                "rule": "inner_dui_ready_and_outer_not_li",
            },
        )

        poisoned_status = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.DUI)
        self.assertEqual(poisoned_status, 51)
        self.assertFalse(IchingKernel.should_skip(poisoned_status))
        self.assertEqual(IchingKernel.skip_decision(poisoned_status)["reason"], "sovereignty_fire_blocks_skip")

    def test_classify_outcome_maps_runtime_results_to_status_codes(self):
        self.assertEqual(
            IchingKernel.classify_outcome(status="halted", reason="sovereignty_breach"),
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )
        self.assertEqual(
            IchingKernel.classify_outcome(status="denied", reason="permission_denied"),
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )
        self.assertEqual(
            IchingKernel.classify_outcome(status="halted", reason="http_timeout"),
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
        )
        self.assertEqual(
            IchingKernel.classify_outcome(status="skipped", reason="resumed_asset_ready"),
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI),
        )
        self.assertEqual(
            IchingKernel.classify_outcome(status="completed", reason=None),
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
        )

    def test_transition_applies_cross_cutting_dynamic_laws(self):
        fire_over_ready_asset = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.DUI)
        fire_transition = IchingKernel.transition(fire_over_ready_asset)
        self.assertEqual(fire_transition.status_code, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(fire_transition.action, "halt")
        self.assertEqual(fire_transition.reason, "sovereignty_fire_suppresses_asset")

        fire_over_empty_asset = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN)
        fire_boundary_transition = IchingKernel.transition(fire_over_empty_asset)
        self.assertEqual(fire_boundary_transition.status_code, fire_over_empty_asset)
        self.assertEqual(fire_boundary_transition.action, "halt")
        self.assertEqual(fire_boundary_transition.reason, "sovereignty_fire_boundary_halt")

        water_over_write_momentum = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)
        water_transition = IchingKernel.transition(water_over_write_momentum)
        self.assertEqual(water_transition.status_code, water_over_write_momentum)
        self.assertEqual(water_transition.action, "activate")
        self.assertEqual(water_transition.reason, "yin_excess_requires_activation")

        pure_qian = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN)
        cooled_transition = IchingKernel.transition(pure_qian)
        self.assertEqual(cooled_transition.status_code, IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN))
        self.assertEqual(cooled_transition.action, "cooldown")
        self.assertEqual(cooled_transition.reason, "yang_overload_cooldown")

        unmapped_transition = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN))
        self.assertEqual(unmapped_transition.action, "discover")
        self.assertEqual(unmapped_transition.reason, "rule_gap_requires_discovery")

    def test_transition_expands_yin_and_element_scheduling_actions(self):
        pure_yin = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN))
        self.assertEqual(pure_yin.action, "discover")
        self.assertEqual(pure_yin.reason, "rule_gap_requires_discovery")

        yin_excess = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.DUI))
        self.assertEqual(yin_excess.action, "activate")
        self.assertEqual(yin_excess.reason, "yin_excess_requires_activation")

        fuel = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.LI))
        self.assertEqual(fuel.action, "accelerate")
        self.assertEqual(fuel.reason, "wood_fuels_fire_execution")

        quench = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.LI))
        self.assertEqual(quench.action, "halt")
        self.assertEqual(quench.reason, "water_quenches_fire_boundary")

        prune = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.DUI, IchingKernel.ZHEN))
        self.assertEqual(prune.action, "prune")
        self.assertEqual(prune.reason, "metal_prunes_wood_scope")

        dam = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KAN))
        self.assertEqual(dam.action, "activate")
        self.assertEqual(dam.reason, "yin_excess_requires_activation")

    def test_element_dynamics_uses_cross_relation_and_break_ground_modulation(self):
        status = IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.KUN)
        dynamics = IchingKernel.element_dynamics(status)

        self.assertEqual(dynamics["outer_element"], "wood")
        self.assertEqual(dynamics["inner_element"], "earth")
        self.assertEqual(dynamics["relation"], "controls")
        self.assertEqual(dynamics["cross_relation"], "controls")
        self.assertEqual(dynamics["modulation"], "break_ground")

    def test_transition_uses_policy_after_safety_and_pressure_gates(self):
        break_ground = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.KUN))
        generated_by = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.GEN))
        controlled_by = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.DUI, IchingKernel.LI))

        self.assertEqual(break_ground.action, "activate")
        self.assertEqual(break_ground.reason, "wood_breaks_inert_ground")
        self.assertEqual(generated_by.action, "recover")
        self.assertEqual(generated_by.reason, "generated_by_relation_recovers_execution")
        self.assertEqual(controlled_by.action, "checkpoint")
        self.assertEqual(controlled_by.reason, "controlled_by_relation_requires_verifier")

    def test_runtime_relation_policy_covers_all_cross_relations(self):
        expected = {
            "generates": ("accelerate", "generating_relation_accelerates_execution"),
            "same": ("continue", None),
            "generated_by": ("recover", "generated_by_relation_recovers_execution"),
            "controlled_by": ("checkpoint", "controlled_by_relation_requires_verifier"),
            "neutral": ("discover", "neutral_relation_requires_discovery"),
        }

        for relation, expected_policy in expected.items():
            self.assertEqual(IchingKernel.runtime_relation_policy(relation, "normal"), expected_policy)

    def test_runtime_relation_policy_differentiates_control_modulations(self):
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "quench"), ("halt", "water_quenches_fire_boundary"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "hard_control"), ("halt", "sovereignty_fire_suppresses_asset"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "prune"), ("prune", "metal_prunes_wood_scope"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "dam"), ("throttle", "earth_dams_water_flow"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "break_ground"), ("activate", "wood_breaks_inert_ground"))
        self.assertEqual(IchingKernel.runtime_relation_policy("controls", "normal"), ("throttle", "controlling_relation_throttles_execution"))

    def test_transition_assigns_differentiated_actions_across_all_states(self):
        actions = {IchingKernel.transition(status_code).action for status_code in range(64)}

        self.assertIn("activate", actions)
        self.assertIn("accelerate", actions)
        self.assertIn("prune", actions)
        self.assertIn("recover", actions)
        self.assertIn("continue", actions)
        self.assertIn("cooldown", actions)
        self.assertIn("checkpoint", actions)
        self.assertIn("halt", actions)
        self.assertIn("discover", actions)
        self.assertGreaterEqual(len(actions), 9)

    def test_transition_consumes_element_dynamics_modulation(self):
        status = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN)

        with patch.object(
            IchingKernel,
            "element_dynamics",
            return_value={
                "outer_element": "fire",
                "inner_element": "metal",
                "relation": "controls",
                "yin_yang_pressure": "cooldown",
                "modulation": "normal",
            },
        ):
            transition = IchingKernel.transition(status)

        self.assertNotEqual(transition.reason, "sovereignty_fire_suppresses_asset")

    def test_transition_is_pure_state_calculation_without_runtime_side_effects(self):
        status = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)

        with (
            patch("builtins.open", side_effect=AssertionError("transition must not open files")),
            patch("onecode.kernel.path_guard.PathGuard.write_text", side_effect=AssertionError("transition must not write files")),
            patch("onecode.kernel.logos_gate.LogosGate.preflight", side_effect=AssertionError("transition must not preflight")),
            patch("onecode.kernel.checkpoint.write_checkpoint", side_effect=AssertionError("transition must not checkpoint")),
        ):
            transition = IchingKernel.transition(status)

        self.assertEqual(transition.reason, "yin_excess_requires_activation")

    def test_dispatch_decision_derives_loop_control_from_transition(self):
        halt_transition = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        checkpoint_transition = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))
        continue_transition = IchingKernel.transition(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI))

        self.assertEqual(IchingKernel.dispatch_decision(halt_transition), "stop")
        self.assertEqual(IchingKernel.dispatch_decision(checkpoint_transition), "continue")
        self.assertEqual(IchingKernel.dispatch_decision(continue_transition), "continue")

    def test_delivery_decision_derives_inspection_actions_from_evidence(self):
        self.assertEqual(
            IchingKernel.delivery_decision(
                status="completed",
                requested_count=3,
                completed_count=2,
                skipped_count=1,
                failed_count=0,
            ),
            {
                "delivery_status": "deliverable",
                "next_action": "idle",
                "resolved_count": 3,
                "remaining_count": 0,
            },
        )
        self.assertEqual(
            IchingKernel.delivery_decision(
                status="halted",
                requested_count=3,
                completed_count=1,
                skipped_count=0,
                failed_count=1,
            ),
            {
                "delivery_status": "blocked",
                "next_action": "resume",
                "resolved_count": 2,
                "remaining_count": 1,
            },
        )
        self.assertEqual(
            IchingKernel.delivery_decision(
                status="completed",
                requested_count=None,
                completed_count=None,
                skipped_count=None,
                failed_count=None,
            ),
            {"delivery_status": "deliverable", "next_action": "idle"},
        )
        self.assertEqual(
            IchingKernel.delivery_decision(
                status="mystery",
                requested_count=None,
                completed_count=None,
                skipped_count=None,
                failed_count=None,
            ),
            {"delivery_status": "unknown", "next_action": "inspect"},
        )

    def test_process_exit_code_derives_cli_exit_from_transition_rules(self):
        self.assertEqual(IchingKernel.process_exit_code(status="completed", reason=None), 0)
        self.assertEqual(IchingKernel.process_exit_code(status="skipped", reason="resumed_asset_ready"), 0)
        self.assertEqual(IchingKernel.process_exit_code(status="halted", reason="sovereignty_breach"), 1)
        self.assertEqual(IchingKernel.process_exit_code(status="denied", reason="permission_denied"), 1)
        self.assertEqual(IchingKernel.process_exit_code(status="halted", reason="invalid_intent"), 1)

    def test_classify_resume_audit_maps_recovery_evidence_to_status_codes(self):
        self.assertEqual(
            IchingKernel.classify_resume_audit(status="ready", reason=None),
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI),
        )
        self.assertEqual(
            IchingKernel.classify_resume_audit(status="ignored", reason="sha256_mismatch"),
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
        )
        self.assertEqual(
            IchingKernel.classify_resume_audit(status="ignored", reason="missing_file"),
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN),
        )
        self.assertEqual(
            IchingKernel.classify_resume_audit(status="ignored", reason="path_outside_workspace"),
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN),
        )

    def test_four_symbols_project_status_into_three_two_bit_views(self):
        status = 0b110100

        self.assertEqual(
            IchingKernel.four_symbols(status),
            [
                {"pair_index": 0, "bits": 0b00, "symbol": "tai_yin"},
                {"pair_index": 1, "bits": 0b01, "symbol": "shao_yang"},
                {"pair_index": 2, "bits": 0b11, "symbol": "tai_yang"},
            ],
        )

        self.assertEqual(IchingKernel.four_symbol_for_bits(0b10), "shao_yin")

    def test_liangyi_and_overlapping_four_symbol_pipeline(self):
        status = 0b111011

        self.assertEqual(
            IchingKernel.liangyi_bits(status),
            [
                {"bit_index": 0, "value": 1, "polarity": "yang", "runtime_semantics": "active"},
                {"bit_index": 1, "value": 1, "polarity": "yang", "runtime_semantics": "active"},
                {"bit_index": 2, "value": 0, "polarity": "yin", "runtime_semantics": "inactive"},
                {"bit_index": 3, "value": 1, "polarity": "yang", "runtime_semantics": "active"},
                {"bit_index": 4, "value": 1, "polarity": "yang", "runtime_semantics": "active"},
                {"bit_index": 5, "value": 1, "polarity": "yang", "runtime_semantics": "active"},
            ],
        )
        self.assertEqual(
            IchingKernel.overlapping_four_symbols(status),
            [
                {"window_index": 0, "bits": 0b11, "symbol": "tai_yang", "runtime_semantics": "overload_clash"},
                {"window_index": 1, "bits": 0b01, "symbol": "shao_yang", "runtime_semantics": "safe_read_skip"},
                {"window_index": 2, "bits": 0b10, "symbol": "shao_yin", "runtime_semantics": "write_commit"},
                {"window_index": 3, "bits": 0b11, "symbol": "tai_yang", "runtime_semantics": "overload_clash"},
                {"window_index": 4, "bits": 0b11, "symbol": "tai_yang", "runtime_semantics": "overload_clash"},
            ],
        )

    def test_four_symbol_balance_vector_detects_overflow(self):
        overflow = IchingKernel.four_symbol_balance_vector(0b111111)

        self.assertEqual(overflow["counts"], {"tai_yin": 0, "shao_yang": 0, "shao_yin": 0, "tai_yang": 5})
        self.assertEqual(overflow["decision"], "overflow")
        self.assertEqual(overflow["change_mask"], 0b100000)
        self.assertEqual(overflow["reason"], "tai_yang_exceeds_minor_symbols")

        stable = IchingKernel.four_symbol_balance_vector(0b100011)
        self.assertEqual(stable["decision"], "stable")
        self.assertEqual(stable["change_mask"], 0)

    def test_yin_yang_profile_classifies_balance_states(self):
        self.assertEqual(
            IchingKernel.yin_yang_profile(0b111111),
            {"yang_count": 6, "yin_count": 0, "balance": "pure_yang"},
        )
        self.assertEqual(
            IchingKernel.yin_yang_profile(0b011111),
            {"yang_count": 5, "yin_count": 1, "balance": "yang_excess"},
        )
        self.assertEqual(
            IchingKernel.yin_yang_profile(0b001111),
            {"yang_count": 4, "yin_count": 2, "balance": "balanced"},
        )
        self.assertEqual(
            IchingKernel.yin_yang_profile(0b000011),
            {"yang_count": 2, "yin_count": 4, "balance": "yin_excess"},
        )
        self.assertEqual(
            IchingKernel.yin_yang_profile(0b000000),
            {"yang_count": 0, "yin_count": 6, "balance": "pure_yin"},
        )

    def test_yin_yang_cross_profile_projects_lines_windows_and_trigrams(self):
        profile = IchingKernel.yin_yang_cross_profile(0b111011)

        self.assertEqual(profile["global"], {"yang_count": 5, "yin_count": 1, "balance": "yang_excess"})
        self.assertEqual(profile["pressure"], "cooldown")
        self.assertEqual(profile["polarity_index"], 2 / 3)
        self.assertEqual(profile["balance_mask"], 0b100000)
        self.assertEqual(profile["lines"][0], {"line_index": 0, "value": 1, "polarity": "yang"})
        self.assertEqual(profile["lines"][2], {"line_index": 2, "value": 0, "polarity": "yin"})
        self.assertEqual(profile["inner_trigram"], {"yang_count": 2, "yin_count": 1, "balance": "balanced"})
        self.assertEqual(profile["outer_trigram"], {"yang_count": 3, "yin_count": 0, "balance": "pure_yang"})
        self.assertEqual(
            profile["four_symbol_windows"],
            [
                {"pair_index": 0, "yang_count": 2, "yin_count": 0, "balance": "pure_yang"},
                {"pair_index": 1, "yang_count": 1, "yin_count": 1, "balance": "balanced"},
                {"pair_index": 2, "yang_count": 2, "yin_count": 0, "balance": "pure_yang"},
            ],
        )

    def test_line_and_trigram_records_expose_liangyi_primitives(self):
        lines = IchingKernel.line_records(0b111011)

        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[0], {"line_index": 0, "value": 1, "polarity": "yang"})
        self.assertEqual(lines[2], {"line_index": 2, "value": 0, "polarity": "yin"})
        self.assertEqual(lines[5], {"line_index": 5, "value": 1, "polarity": "yang"})

        self.assertEqual(
            IchingKernel.trigram_record(0b111011, "inner"),
            {
                "scope": "inner",
                "trigram": IchingKernel.DUI,
                "binary": "011",
                "element": "metal",
                "yin_yang": {"yang_count": 2, "yin_count": 1, "balance": "balanced"},
                "lines": lines[:3],
            },
        )
        self.assertEqual(
            IchingKernel.trigram_record(0b111011, "outer"),
            {
                "scope": "outer",
                "trigram": IchingKernel.QIAN,
                "binary": "111",
                "element": "metal",
                "yin_yang": {"yang_count": 3, "yin_count": 0, "balance": "pure_yang"},
                "lines": lines[3:],
            },
        )

        with self.assertRaises(ValueError):
            IchingKernel.trigram_record(0b111011, "middle")

    def test_trigram_records_cover_all_bagua_states(self):
        records = IchingKernel.trigram_records()

        self.assertEqual(len(records), 8)
        self.assertEqual(set(records.keys()), set(range(8)))
        self.assertEqual(records[IchingKernel.KUN]["name"], "kun")
        self.assertEqual(records[IchingKernel.ZHEN]["name"], "zhen")
        self.assertEqual(records[IchingKernel.KAN]["name"], "kan")
        self.assertEqual(records[IchingKernel.DUI]["name"], "dui")
        self.assertEqual(records[IchingKernel.GEN]["name"], "gen")
        self.assertEqual(records[IchingKernel.XUN]["name"], "xun")
        self.assertEqual(records[IchingKernel.LI]["name"], "li")
        self.assertEqual(records[IchingKernel.QIAN]["name"], "qian")
        self.assertEqual(records[IchingKernel.QIAN]["binary"], "111")
        self.assertEqual(records[IchingKernel.QIAN]["lines"][0]["polarity"], "yang")
        self.assertEqual(records[IchingKernel.KUN]["binary"], "000")
        self.assertEqual(records[IchingKernel.KUN]["lines"][2]["polarity"], "yin")

    def test_five_element_matrix_maps_trigrams_and_relations(self):
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.QIAN), "metal")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.DUI), "metal")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.ZHEN), "wood")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.XUN), "wood")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.KAN), "water")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.LI), "fire")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.KUN), "earth")
        self.assertEqual(IchingKernel.element_for_trigram(IchingKernel.GEN), "earth")

        self.assertEqual(IchingKernel.element_relation("water", "wood"), "generates")
        self.assertEqual(IchingKernel.element_relation("fire", "metal"), "controls")
        self.assertEqual(IchingKernel.element_relation("metal", "metal"), "same")
        self.assertEqual(IchingKernel.element_relation("wood", "water"), "neutral")

    def test_five_element_records_cover_generation_and_control_cross_matrix(self):
        records = IchingKernel.element_records()

        self.assertEqual(set(records.keys()), {"wood", "fire", "earth", "metal", "water"})
        self.assertEqual(records["water"]["generates"], "wood")
        self.assertEqual(records["water"]["generated_by"], "metal")
        self.assertEqual(records["water"]["controls"], "fire")
        self.assertEqual(records["water"]["controlled_by"], "earth")

        matrix = IchingKernel.element_matrix()
        self.assertEqual(len(matrix), 25)
        self.assertEqual(matrix[("water", "wood")], "generates")
        self.assertEqual(matrix[("wood", "water")], "generated_by")
        self.assertEqual(matrix[("fire", "metal")], "controls")
        self.assertEqual(matrix[("metal", "fire")], "controlled_by")
        self.assertEqual(matrix[("earth", "earth")], "same")
        self.assertEqual(matrix[("wood", "metal")], "controlled_by")

    def test_element_dynamics_modulates_relation_with_yin_yang_pressure(self):
        hard_control = IchingKernel.element_dynamics(IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN))
        self.assertEqual(hard_control["outer_element"], "fire")
        self.assertEqual(hard_control["inner_element"], "metal")
        self.assertEqual(hard_control["relation"], "controls")
        self.assertEqual(hard_control["yin_yang_pressure"], "cooldown")
        self.assertEqual(hard_control["modulation"], "hard_control")

        recovery_seed = IchingKernel.element_dynamics(IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))
        self.assertEqual(recovery_seed["outer_element"], "water")
        self.assertEqual(recovery_seed["inner_element"], "wood")
        self.assertEqual(recovery_seed["relation"], "generates")
        self.assertEqual(recovery_seed["yin_yang_pressure"], "activate")
        self.assertEqual(recovery_seed["modulation"], "recovery_seed")

        steady_same = IchingKernel.element_dynamics(IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.GEN))
        self.assertEqual(steady_same["relation"], "same")
        self.assertEqual(steady_same["modulation"], "normal")

    def test_element_dynamics_covers_control_and_generation_modulations(self):
        cases = [
            (IchingKernel.KAN, IchingKernel.LI, "quench"),
            (IchingKernel.DUI, IchingKernel.ZHEN, "prune"),
            (IchingKernel.ZHEN, IchingKernel.LI, "fuel"),
            (IchingKernel.KUN, IchingKernel.KAN, "dam"),
        ]

        for outer, inner, modulation in cases:
            with self.subTest(modulation=modulation):
                dynamics = IchingKernel.element_dynamics(IchingKernel.compute_status(outer, inner))
                self.assertEqual(dynamics["modulation"], modulation)

    def test_execution_bandwidth_applies_explicit_five_element_matrix(self):
        fire_over_metal = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN)
        water_over_fire = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.LI)
        wood_over_fire = IchingKernel.compute_status(IchingKernel.ZHEN, IchingKernel.LI)

        self.assertEqual(IchingKernel.execution_bandwidth(fire_over_metal), 0.0)
        self.assertEqual(IchingKernel.execution_bandwidth(water_over_fire), 0.0)
        self.assertEqual(IchingKernel.execution_bandwidth(wood_over_fire, base=2.0), 2.0)

        profile = IchingKernel.cross_cutting_profile(fire_over_metal)
        self.assertEqual(profile["execution_bandwidth"], 0.0)

    def test_aggregate_status_collapses_parallel_results_with_or_and_gates(self):
        statuses = [
            IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.QIAN),
            IchingKernel.compute_status(IchingKernel.LI, IchingKernel.DUI),
        ]

        aggregated = IchingKernel.aggregate_status(statuses)

        self.assertEqual(
            aggregated,
            IchingKernel.compute_status(IchingKernel.KAN | IchingKernel.LI, IchingKernel.QIAN & IchingKernel.DUI),
        )
        self.assertEqual(IchingKernel.aggregate_status([]), IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN))

    def test_apply_event_projects_runtime_evidence_to_change_masks(self):
        start = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN)

        completed = IchingKernel.apply_event(start, "completed")
        timeout = IchingKernel.apply_event(start, "http_timeout")
        breach = IchingKernel.apply_event(start, "sovereignty_breach")

        self.assertEqual(completed, IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN))
        self.assertEqual(timeout, IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))
        self.assertEqual(breach, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(
            IchingKernel.change_mask_for_event(start, "completed"),
            start ^ IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
        )

    def test_hexagram_records_cover_all_sixty_four_states(self):
        records = IchingKernel.hexagram_records()

        self.assertEqual(len(records), 64)
        self.assertEqual(set(records.keys()), set(range(64)))

        record = IchingKernel.hexagram_record(IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI))
        self.assertEqual(record["status_code"], 59)
        self.assertEqual(record["binary"], "111011")
        self.assertEqual(record["outer_trigram"], IchingKernel.QIAN)
        self.assertEqual(record["inner_trigram"], IchingKernel.DUI)
        self.assertEqual(record["outer_element"], "metal")
        self.assertEqual(record["inner_element"], "metal")
        self.assertEqual(record["element_relation"], "same")
        self.assertEqual(record["yin_yang"]["balance"], "yang_excess")
        self.assertEqual(len(record["four_symbols"]), 3)

    def test_cross_cutting_profile_unifies_all_rule_projections(self):
        status = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)
        profile = IchingKernel.cross_cutting_profile(status)

        self.assertEqual(profile["status_code"], 59)
        self.assertEqual(profile["binary"], "111011")
        self.assertEqual(profile["outer_trigram"], IchingKernel.QIAN)
        self.assertEqual(profile["inner_trigram"], IchingKernel.DUI)
        self.assertEqual(profile["lines"][2]["polarity"], "yin")
        self.assertEqual(profile["liangyi"][2]["polarity"], "yin")
        self.assertEqual(profile["four_symbol_balance"]["decision"], "overflow")
        self.assertEqual(profile["inner_trigram_record"]["binary"], "011")
        self.assertEqual(profile["outer_trigram_record"]["binary"], "111")
        self.assertEqual(profile["trigram_records"][IchingKernel.LI]["element"], "fire")
        self.assertEqual(profile["outer_element"], "metal")
        self.assertEqual(profile["inner_element"], "metal")
        self.assertEqual(profile["element_records"]["water"]["generates"], "wood")
        self.assertEqual(profile["element_matrix"]["fire->metal"], "controls")
        self.assertEqual(profile["element_matrix"]["metal->fire"], "controlled_by")
        self.assertEqual(profile["element_relation"], "same")
        self.assertEqual(profile["element_dynamics"]["modulation"], "normal")
        self.assertEqual(profile["yin_yang"]["balance"], "yang_excess")
        self.assertEqual(profile["four_symbols"][0]["symbol"], "tai_yang")
        self.assertEqual(profile["transition"]["status_code"], IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.DUI))
        self.assertEqual(profile["transition"]["reason"], "yang_overload_cooldown")
        self.assertEqual(profile["dispatch_decision"], "continue")
        self.assertEqual(IchingKernel.hexagram_record(status), profile)

    def test_cross_cutting_profile_marks_rule_source_layers(self):
        profile = IchingKernel.cross_cutting_profile(IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN))

        self.assertEqual(
            profile["rule_layers"]["bit_derived"],
            [
                "status_code",
                "binary",
                "inner_trigram",
                "outer_trigram",
                "trigram_records",
                "liangyi",
                "yin_yang",
                "polarity_index",
                "balance_mask",
                "four_symbols",
                "overlapping_four_symbols",
                "four_symbol_balance",
            ],
        )
        self.assertEqual(
            profile["rule_layers"]["correspondence_derived"],
            [
                "inner_element",
                "outer_element",
                "element_records",
                "element_matrix",
                "element_relation",
                "element_dynamics",
                "evolved_element_modulation",
            ],
        )
        self.assertEqual(
            profile["rule_layers"]["onecode_runtime"],
            ["transition", "dispatch_decision", "execution_bandwidth", "global_entropy"],
        )

    def test_rule_layers_returns_defensive_copies(self):
        first = IchingKernel.rule_layers()
        first["bit_derived"].append("mutated")
        first["new_layer"] = ["mutated"]

        second = IchingKernel.rule_layers()

        self.assertNotIn("mutated", second["bit_derived"])
        self.assertNotIn("new_layer", second)

    def test_flip_line_mutates_exactly_one_line(self):
        self.assertEqual(IchingKernel.flip_line(0b000000, 0), 0b000001)
        self.assertEqual(IchingKernel.flip_line(0b000001, 0), 0b000000)
        self.assertEqual(IchingKernel.flip_line(0b000000, 5), 0b100000)
        self.assertEqual(IchingKernel.flip_line(0b111111, 3), 0b110111)

    def test_polarity_index_and_balance_mask_apply_threshold_feedback(self):
        self.assertEqual(IchingKernel.polarity_index(0b111111), 1.0)
        self.assertEqual(IchingKernel.polarity_index(0b000000), -1.0)
        self.assertEqual(IchingKernel.polarity_index(0b100011), 0.0)
        self.assertEqual(IchingKernel.polarity_index(0b100111), 1 / 3)

        self.assertEqual(IchingKernel.balance_mask(0b001111), 0b000000)
        self.assertEqual(IchingKernel.balance_mask(0b011111), 0b100000)
        self.assertEqual(IchingKernel.balance_mask(0b000001), 0b000001)
        self.assertEqual(IchingKernel.balance_mask(0b000000), 0b000001)

    def test_apply_event_can_include_adaptive_balance_feedback(self):
        start = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN)

        self.assertEqual(IchingKernel.apply_event(start, "completed"), start)
        self.assertEqual(IchingKernel.apply_balanced_event(start, "completed"), 0b011111)

        stasis = IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN)
        self.assertEqual(IchingKernel.apply_balanced_event(stasis, "unknown"), 0b000001)

    def test_evolved_element_tensor_splits_elements_by_polarity(self):
        labels = IchingKernel.evolved_element_labels()
        self.assertEqual(labels, ["metal+", "wood+", "water+", "fire+", "earth+", "metal-", "wood-", "water-", "fire-", "earth-"])

        tensor = IchingKernel.evolved_element_tensor(0b111111)
        self.assertEqual(len(tensor), 10)
        self.assertTrue(all(len(row) == 10 for row in tensor))
        self.assertEqual(tensor[3][0], 0.0)
        self.assertGreater(tensor[0][8], IchingKernel.ELEMENT_EXECUTION_BANDWIDTH[("metal", "fire")])

        status = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.QIAN)
        modulation = IchingKernel.evolved_element_modulation(status)
        self.assertEqual(modulation["outer_label"], "fire+")
        self.assertEqual(modulation["inner_label"], "metal+")
        self.assertEqual(modulation["coefficient"], 0.0)

    def test_entropy_regulated_status_uses_polarity_direction_for_low_entropy_work(self):
        pure_yang_statuses = [
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN),
        ]

        entropy = IchingKernel.global_entropy(pure_yang_statuses)
        regulated = IchingKernel.entropy_regulated_status(pure_yang_statuses)

        self.assertEqual(entropy["entropy"], 0.0)
        self.assertEqual(math.copysign(1.0, entropy["entropy"]), 1.0)
        self.assertEqual(entropy["polarity_state"], "low_entropy_positive")
        self.assertEqual(regulated["status_code"], IchingKernel.aggregate_status(pure_yang_statuses))
        self.assertEqual(regulated["decision"], "accept_positive_polarity")

        pure_yin_statuses = [
            IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
            IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.KUN),
        ]
        yin_regulated = IchingKernel.entropy_regulated_status(pure_yin_statuses)
        self.assertEqual(yin_regulated["status_code"], IchingKernel.ROLLBACK_STATUS)
        self.assertEqual(yin_regulated["decision"], "rollback_negative_polarity")
        self.assertEqual(yin_regulated["reason"], "entropy_negative_polarity_rollback")
        self.assertEqual(IchingKernel.transition(int(yin_regulated["status_code"])).reason, "yin_excess_requires_activation")

        mixed_statuses = [
            IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.KUN),
            IchingKernel.compute_status(IchingKernel.KUN, IchingKernel.QIAN),
        ]
        mixed = IchingKernel.entropy_regulated_status(mixed_statuses)
        self.assertEqual(mixed["decision"], "accept")
        self.assertEqual(mixed["status_code"], IchingKernel.aggregate_status(mixed_statuses))

        with self.assertRaises(ValueError):
            IchingKernel.flip_line(0b000000, -1)
        with self.assertRaises(ValueError):
            IchingKernel.flip_line(0b000000, 6)


if __name__ == "__main__":
    unittest.main()
