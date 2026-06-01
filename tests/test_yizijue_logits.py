import unittest

from onecode.kernel.yizijue_logits import (
    apply_token_id_policy_to_logits,
    state_token_id_policy,
    state_token_policy,
    text_policy_to_token_id_policy,
    token_policy_for_basis,
    token_id_policy_for_basis,
    validate_state_token_id_policy,
    validate_state_token_policy,
    YiZiJueLogitsProcessor,
)


class FakeTokenizer:
    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.calls: list[dict] = []

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        self.calls.append({"text": text, "add_special_tokens": add_special_tokens})
        ids = []
        for part in text.split("_"):
            key = part or text
            if key not in self.vocab:
                self.vocab[key] = len(self.vocab) + 10
            ids.append(self.vocab[key])
        return ids


class FakeScores:
    def __init__(self, rows):
        self.rows = [list(row) for row in rows]

    def __getitem__(self, key):
        row_selector, token_id = key
        if row_selector != slice(None, None, None):
            raise AssertionError("expected all rows selector")
        return [row[token_id] for row in self.rows]

    def __setitem__(self, key, value):
        row_selector, token_id = key
        if row_selector != slice(None, None, None):
            raise AssertionError("expected all rows selector")
        if isinstance(value, list):
            for row, item in zip(self.rows, value, strict=True):
                row[token_id] = item
        else:
            for row in self.rows:
                row[token_id] = value


class YiZiJueLogitsPolicyTests(unittest.TestCase):
    def test_danger_state_blocks_allow_tokens_and_prefers_halt(self):
        policy = state_token_policy("100001")

        self.assertIn("SOVEREIGNTY_HALT", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])
        self.assertIn("ALLOW_PATCH_WITH_SHA", policy["forbidden_text"])
        self.assertEqual(policy["state"], "100001")

    def test_verifier_state_prefers_sandbox_action(self):
        policy = state_token_policy("010010")

        self.assertIn("RUN_VERIFIER_IN_SANDBOX", policy["preferred_text"])
        self.assertIn("sandbox_required", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])

    def test_safe_write_state_prefers_allow_but_keeps_halt_available(self):
        policy = state_token_policy("111111")

        self.assertIn("ALLOW_ATOMIC_WRITE", policy["preferred_text"])
        self.assertIn("ALLOW_PATCH_WITH_SHA", policy["preferred_text"])
        self.assertNotIn("SOVEREIGNTY_HALT", policy["forbidden_text"])

    def test_unknown_state_falls_back_to_deny_policy(self):
        policy = state_token_policy("001101")

        self.assertIn("DENY_AND_LEDGER", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])

    def test_policy_for_basis_uses_state_label_specific_hints(self):
        policy = token_policy_for_basis(
            {
                "projection": "ambiguous_request",
                "state": "000000",
                "state_label": "kun_clarify_boundary",
                "transition": "clarify_required",
                "rule": "ambiguous requests must ask for target, scope, and verification",
            }
        )

        self.assertIn("clarify", policy["preferred_text"])
        self.assertIn("请说明", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])

    def test_policy_for_basis_consumes_rich_rule_chain_hints(self):
        policy = token_policy_for_basis(
            {
                "projection": "verification_request",
                "state": "010010",
                "state_label": "kan_sandbox_verifier",
                "transition": "sandbox_required",
                "rule": "verification commands must run in a sandbox",
                "yin_yang": {"balance": "yin_excess", "pressure": "activate"},
                "trigrams": {"outer": "kan", "inner": "kan"},
                "elements": {"outer": "water", "inner": "water", "relation": "same", "modulation": "normal"},
            }
        )

        self.assertIn("yin_excess", policy["preferred_text"])
        self.assertIn("activate", policy["preferred_text"])
        self.assertIn("same", policy["preferred_text"])
        self.assertIn("normal", policy["preferred_text"])
        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])

    def test_policy_for_basis_filters_rich_hints_that_conflict_with_forbidden_text(self):
        policy = token_policy_for_basis(
            {
                "projection": "verification_request",
                "state": "010010",
                "state_label": "kan_sandbox_verifier",
                "transition": "sandbox_required",
                "rule": "verification commands must run in a sandbox",
                "yin_yang": {"balance": "yin_excess", "pressure": "ALLOW_ATOMIC_WRITE"},
                "trigrams": {"outer": "kan", "inner": "kan"},
                "elements": {
                    "outer": "water",
                    "inner": "water",
                    "relation": "same",
                    "modulation": "ALLOW_PATCH_WITH_SHA",
                },
            }
        )

        self.assertIn("ALLOW_ATOMIC_WRITE", policy["forbidden_text"])
        self.assertIn("ALLOW_PATCH_WITH_SHA", policy["forbidden_text"])
        self.assertNotIn("ALLOW_ATOMIC_WRITE", policy["preferred_text"])
        self.assertNotIn("ALLOW_PATCH_WITH_SHA", policy["preferred_text"])
        self.assertIn("yin_excess", policy["preferred_text"])
        self.assertIn("same", policy["preferred_text"])

    def test_validate_state_token_policy_rejects_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "unknown policy fields"):
            validate_state_token_policy(
                {
                    "state": "000000",
                    "preferred_text": ["DENY_AND_LEDGER"],
                    "forbidden_text": ["ALLOW_ATOMIC_WRITE"],
                    "unexpected": [],
                }
            )

    def test_text_policy_to_token_id_policy_encodes_all_fragments_without_special_tokens(self):
        tokenizer = FakeTokenizer()
        text_policy = {
            "state": "100001",
            "preferred_text": ["SOVEREIGNTY_HALT"],
            "forbidden_text": ["ALLOW_ATOMIC_WRITE"],
        }

        policy = text_policy_to_token_id_policy(text_policy, tokenizer)

        self.assertEqual(policy["state"], "100001")
        self.assertTrue(policy["preferred_token_ids"])
        self.assertTrue(policy["forbidden_token_ids"])
        self.assertEqual({call["add_special_tokens"] for call in tokenizer.calls}, {False})

    def test_state_token_id_policy_uses_state_policy(self):
        tokenizer = FakeTokenizer()

        policy = state_token_id_policy("010010", tokenizer)

        self.assertEqual(policy["state"], "010010")
        self.assertTrue(policy["preferred_token_ids"])
        self.assertTrue(policy["forbidden_token_ids"])

    def test_token_id_policy_for_basis_includes_basis_specific_text_ids(self):
        tokenizer = FakeTokenizer()

        policy = token_id_policy_for_basis(
            {
                "projection": "ambiguous_request",
                "state": "000000",
                "state_label": "kun_clarify_boundary",
                "transition": "clarify_required",
                "rule": "ambiguous requests must ask for target, scope, and verification",
            },
            tokenizer,
        )

        clarify_ids = tokenizer.encode("clarify", add_special_tokens=False)
        self.assertTrue(set(clarify_ids).issubset(set(policy["preferred_token_ids"])))

    def test_validate_state_token_id_policy_rejects_non_int_ids(self):
        with self.assertRaisesRegex(ValueError, "preferred_token_ids must be an integer list"):
            validate_state_token_id_policy(
                {
                    "state": "000000",
                    "preferred_token_ids": ["bad"],
                    "forbidden_token_ids": [1],
                }
            )

    def test_apply_token_id_policy_to_logits_biases_preferred_and_blocks_forbidden(self):
        logits = [0.0, 1.0, 2.0, 3.0]
        policy = {
            "state": "100001",
            "preferred_token_ids": [1],
            "forbidden_token_ids": [2],
        }

        controlled = apply_token_id_policy_to_logits(logits, policy, preferred_bias=4.5)

        self.assertEqual(controlled[0], 0.0)
        self.assertEqual(controlled[1], 5.5)
        self.assertEqual(controlled[2], float("-inf"))
        self.assertEqual(controlled[3], 3.0)

    def test_apply_token_id_policy_to_logits_does_not_mutate_input(self):
        logits = [0.0, 1.0, 2.0]
        policy = {
            "state": "010010",
            "preferred_token_ids": [0],
            "forbidden_token_ids": [1],
        }

        controlled = apply_token_id_policy_to_logits(logits, policy)

        self.assertEqual(logits, [0.0, 1.0, 2.0])
        self.assertNotEqual(controlled, logits)

    def test_apply_token_id_policy_to_logits_ignores_out_of_range_ids(self):
        logits = [0.0, 1.0]
        policy = {
            "state": "000000",
            "preferred_token_ids": [20],
            "forbidden_token_ids": [21],
        }

        controlled = apply_token_id_policy_to_logits(logits, policy)

        self.assertEqual(controlled, logits)

    def test_transformers_logits_processor_modifies_2d_scores_in_place(self):
        scores = FakeScores([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]])
        processor = YiZiJueLogitsProcessor(
            {
                "state": "100001",
                "preferred_token_ids": [1],
                "forbidden_token_ids": [2],
            },
            preferred_bias=2.5,
        )

        returned = processor(input_ids=None, scores=scores)

        self.assertIs(returned, scores)
        self.assertEqual(scores.rows[0], [0.0, 3.5, float("-inf")])
        self.assertEqual(scores.rows[1], [3.0, 6.5, float("-inf")])

    def test_transformers_logits_processor_ignores_out_of_range_ids(self):
        scores = FakeScores([[0.0, 1.0]])
        processor = YiZiJueLogitsProcessor(
            {
                "state": "000000",
                "preferred_token_ids": [10],
                "forbidden_token_ids": [11],
            }
        )

        processor(input_ids=None, scores=scores)

        self.assertEqual(scores.rows, [[0.0, 1.0]])


if __name__ == "__main__":
    unittest.main()
