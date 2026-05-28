import unittest
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel


class TestIchingKernel(unittest.TestCase):
    def test_hexagram_bitwise_收敛与自愈路由(self):
        status = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.DUI)
        self.assertEqual(status, 59)
        self.assertTrue(IchingKernel.should_skip(status))

        poisoned_status = IchingKernel.compute_status(IchingKernel.LI, IchingKernel.DUI)
        self.assertEqual(poisoned_status, 51)
        self.assertFalse(IchingKernel.should_skip(poisoned_status))

    def test_classify_outcome_maps_runtime_results_to_status_codes(self):
        self.assertEqual(
            IchingKernel.classify_outcome(status="halted", reason="sovereignty_breach"),
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

        water_over_write_momentum = IchingKernel.compute_status(IchingKernel.KAN, IchingKernel.ZHEN)
        water_transition = IchingKernel.transition(water_over_write_momentum)
        self.assertEqual(water_transition.status_code, water_over_write_momentum)
        self.assertEqual(water_transition.action, "checkpoint")
        self.assertEqual(water_transition.reason, "network_water_preserves_resume_seed")

        pure_qian = IchingKernel.compute_status(IchingKernel.QIAN, IchingKernel.QIAN)
        cooled_transition = IchingKernel.transition(pure_qian)
        self.assertEqual(cooled_transition.status_code, IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.QIAN))
        self.assertEqual(cooled_transition.action, "halt")
        self.assertEqual(cooled_transition.reason, "yang_overload_cooldown")

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

        self.assertEqual(transition.reason, "network_water_preserves_resume_seed")

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
        self.assertEqual(profile["inner_trigram_record"]["binary"], "011")
        self.assertEqual(profile["outer_trigram_record"]["binary"], "111")
        self.assertEqual(profile["trigram_records"][IchingKernel.LI]["element"], "fire")
        self.assertEqual(profile["outer_element"], "metal")
        self.assertEqual(profile["inner_element"], "metal")
        self.assertEqual(profile["element_relation"], "same")
        self.assertEqual(profile["element_dynamics"]["modulation"], "normal")
        self.assertEqual(profile["yin_yang"]["balance"], "yang_excess")
        self.assertEqual(profile["four_symbols"][0]["symbol"], "tai_yang")
        self.assertEqual(profile["transition"]["status_code"], IchingKernel.compute_status(IchingKernel.GEN, IchingKernel.DUI))
        self.assertEqual(profile["transition"]["reason"], "yang_overload_cooldown")
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
                "yin_yang",
                "four_symbols",
            ],
        )
        self.assertEqual(
            profile["rule_layers"]["correspondence_derived"],
            [
                "inner_element",
                "outer_element",
                "element_relation",
                "element_dynamics",
            ],
        )
        self.assertEqual(profile["rule_layers"]["onecode_runtime"], ["transition"])

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

        with self.assertRaises(ValueError):
            IchingKernel.flip_line(0b000000, -1)
        with self.assertRaises(ValueError):
            IchingKernel.flip_line(0b000000, 6)


if __name__ == "__main__":
    unittest.main()
