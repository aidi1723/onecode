import unittest

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


if __name__ == "__main__":
    unittest.main()
