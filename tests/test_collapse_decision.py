import json
import unittest
from pathlib import Path

from onecode.kernel.collapse_decision import (
    FAIL_STATE,
    collapse_decision,
    collapse_should_defer,
    expected_calibration_error,
)
from onecode.kernel.prompt_rules import classify_prompt


def _one_hot(size: int, index: int) -> list[float]:
    values = [0.0] * size
    values[index] = 1.0
    return values


class CollapseDecisionTests(unittest.TestCase):
    def test_confident_observed_write_stays_on_the_gateway(self):
        decision = collapse_decision(
            _one_hot(64, 0b111111),
            _one_hot(5, 0),
            _one_hot(3, 0),
            _one_hot(3, 1),
            _one_hot(3, 1),
            threshold=0.5,
        )

        self.assertFalse(decision["abstained"])
        self.assertEqual(decision["action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(decision["yizijue_state"], "111111")

    def test_flat_or_unobserved_state_collapses_to_the_failure_code(self):
        flat = [1.0 / 64] * 64
        decision = collapse_decision(
            flat,
            _one_hot(5, 0),
            _one_hot(3, 0),
            _one_hot(3, 1),
            _one_hot(3, 1),
            threshold=0.5,
        )
        self.assertTrue(decision["abstained"])
        self.assertEqual(decision["status_code"], FAIL_STATE)
        self.assertEqual(decision["action"], "DENY_AND_LEDGER")

        unseen = _one_hot(64, 0b000111)
        unseen_decision = collapse_decision(
            unseen,
            _one_hot(5, 0),
            _one_hot(3, 0),
            _one_hot(3, 1),
            _one_hot(3, 1),
            threshold=0.5,
        )
        self.assertTrue(unseen_decision["abstained"])
        self.assertEqual(unseen_decision["action"], "DENY_AND_LEDGER")

    def test_calibration_error_is_zero_for_a_perfect_split(self):
        self.assertEqual(expected_calibration_error([1.0, 0.0], [True, False]), 0.0)

    def test_allow_from_the_head_is_not_authorized(self):
        allowed = collapse_decision(
            _one_hot(64, 0b111111),
            _one_hot(5, 0),
            _one_hot(3, 0),
            _one_hot(3, 1),
            _one_hot(3, 1),
            threshold=0.3,
        )
        denied = collapse_decision(
            _one_hot(64, 0b000000),
            _one_hot(5, 4),
            _one_hot(3, 2),
            _one_hot(3, 1),
            _one_hot(3, 0),
            threshold=0.3,
        )

        self.assertFalse(collapse_should_defer(allowed))
        self.assertFalse(collapse_should_defer(denied))
        self.assertEqual(denied["action"], "DENY_AND_LEDGER")

    def test_four_known_leaks_remain_pytest_rules(self):
        paths = [
            Path("/Volumes/MacSSD/模型训练/yizijue-qwen06b/data/train_messages_distilled_clean_schema_writes.jsonl"),
            Path("/Volumes/MacSSD/模型训练/yizijue-qwen06b/data/train_messages_distilled_clean_schema_writes_v2.jsonl"),
        ]
        if not any(path.exists() for path in paths):
            self.skipTest("distilled dataset is not mounted")
        wanted = {
            "security-distill-000119",
            "security-distill-000154",
            "security-distill-000239",
            "security-distill-000256",
        }
        found = {}
        for path in paths:
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("id") in wanted and row["id"] not in found:
                    found[row["id"]] = next(message["content"] for message in row["messages"] if message["role"] == "user")
        self.assertEqual(set(found), wanted)
        for sample_id, text in found.items():
            rule = classify_prompt(text)
            self.assertIsNotNone(rule, sample_id)
            self.assertEqual(rule.rule_id, "host_execution", sample_id)
            self.assertEqual(rule.reason, "dangerous_host_command")
