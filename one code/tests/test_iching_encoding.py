import unittest

from onecode.kernel.iching_encoding import (
    ACTIVE_RULE_SCHEMA,
    CANONICAL_TRIGRAMS,
    LEGACY_TRIGRAMS,
    RULE_SCHEMA_V1,
    RULE_SCHEMA_V2,
    canonical_encoding_certificate,
    convert_status,
    convert_trigram,
    trigram_table,
    validate_status,
    validate_trigram,
)


class IchingEncodingTests(unittest.TestCase):
    def test_schema_tables_preserve_legacy_and_canonical_trigram_meanings(self):
        self.assertEqual(
            dict(CANONICAL_TRIGRAMS),
            {
                "kun": 0b000,
                "zhen": 0b001,
                "kan": 0b010,
                "dui": 0b011,
                "gen": 0b100,
                "li": 0b101,
                "xun": 0b110,
                "qian": 0b111,
            },
        )
        self.assertEqual(LEGACY_TRIGRAMS["xun"], 0b101)
        self.assertEqual(LEGACY_TRIGRAMS["li"], 0b110)
        self.assertNotEqual(RULE_SCHEMA_V1, RULE_SCHEMA_V2)
        self.assertEqual(ACTIVE_RULE_SCHEMA, RULE_SCHEMA_V2)

    def test_schema_tables_are_read_only_and_unknown_schema_is_rejected(self):
        self.assertIs(trigram_table(RULE_SCHEMA_V1), LEGACY_TRIGRAMS)
        self.assertIs(trigram_table(RULE_SCHEMA_V2), CANONICAL_TRIGRAMS)
        with self.assertRaises(TypeError):
            CANONICAL_TRIGRAMS["li"] = 0b110
        with self.assertRaises(ValueError):
            trigram_table("onecode-iching-v3")

    def test_trigram_and_status_validation_rejects_boolean_and_out_of_range_values(self):
        for value in (True, False, -1, 8):
            with self.subTest(trigram=value):
                with self.assertRaises(ValueError):
                    validate_trigram(value)
        for value in (True, False, -1, 64):
            with self.subTest(status=value):
                with self.assertRaises(ValueError):
                    validate_status(value)
        self.assertEqual(validate_trigram(7), 7)
        self.assertEqual(validate_status(63), 63)

    def test_trigram_conversion_preserves_names_across_rule_schemas(self):
        for name, legacy_value in LEGACY_TRIGRAMS.items():
            with self.subTest(name=name):
                canonical_value = convert_trigram(legacy_value, RULE_SCHEMA_V1, RULE_SCHEMA_V2)
                self.assertEqual(canonical_value, CANONICAL_TRIGRAMS[name])
                self.assertEqual(
                    convert_trigram(canonical_value, RULE_SCHEMA_V2, RULE_SCHEMA_V1),
                    legacy_value,
                )

    def test_status_conversion_round_trips_all_sixty_four_states(self):
        for legacy_status in range(64):
            with self.subTest(status=legacy_status):
                canonical_status = convert_status(legacy_status, RULE_SCHEMA_V1, RULE_SCHEMA_V2)
                self.assertEqual(
                    convert_status(canonical_status, RULE_SCHEMA_V2, RULE_SCHEMA_V1),
                    legacy_status,
                )

    def test_status_conversion_converts_inner_and_outer_trigrams_structurally(self):
        legacy_li_over_kun = (LEGACY_TRIGRAMS["li"] << 3) | LEGACY_TRIGRAMS["kun"]
        canonical_li_over_kun = (CANONICAL_TRIGRAMS["li"] << 3) | CANONICAL_TRIGRAMS["kun"]
        legacy_xun_over_li = (LEGACY_TRIGRAMS["xun"] << 3) | LEGACY_TRIGRAMS["li"]
        canonical_xun_over_li = (CANONICAL_TRIGRAMS["xun"] << 3) | CANONICAL_TRIGRAMS["li"]

        self.assertEqual(
            convert_status(legacy_li_over_kun, RULE_SCHEMA_V1, RULE_SCHEMA_V2),
            canonical_li_over_kun,
        )
        self.assertEqual(
            convert_status(legacy_xun_over_li, RULE_SCHEMA_V1, RULE_SCHEMA_V2),
            canonical_xun_over_li,
        )
        self.assertEqual(convert_status(0, RULE_SCHEMA_V1, RULE_SCHEMA_V2), 0)
        self.assertEqual(convert_status(63, RULE_SCHEMA_V1, RULE_SCHEMA_V2), 63)

    def test_canonical_certificate_proves_line_and_complement_invariants(self):
        certificate = canonical_encoding_certificate()

        self.assertEqual(certificate["schema"], RULE_SCHEMA_V2)
        self.assertEqual(certificate["trigram_count"], 8)
        self.assertEqual(certificate["invalid_line_patterns"], [])
        self.assertEqual(certificate["invalid_complement_pairs"], [])
        self.assertEqual(
            certificate["complement_pairs"],
            [
                ["kun", "qian"],
                ["zhen", "xun"],
                ["kan", "li"],
                ["dui", "gen"],
            ],
        )
        self.assertTrue(certificate["valid"])


if __name__ == "__main__":
    unittest.main()
