import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_hardened_mlx_dataset import build_hardened_split, with_strict_system_prompt


def row(sample_id: str, action: str) -> dict:
    return {
        "id": sample_id,
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": sample_id},
            {"role": "assistant", "content": json.dumps({"action": {"action": action}})},
        ],
    }


class BuildHardenedMlxDatasetTest(unittest.TestCase):
    def test_strict_system_prompt_declares_action_vocabulary(self):
        original = row("balanced-001", "ALLOW_ATOMIC_WRITE")

        updated = with_strict_system_prompt(original)

        self.assertIn("Allowed actions:", updated["messages"][0]["content"])
        self.assertIn("ALLOW_ATOMIC_WRITE", updated["messages"][0]["content"])
        self.assertIn("SOVEREIGNTY_HALT", updated["messages"][0]["content"])
        self.assertEqual(updated["messages"][1:], original["messages"][1:])

    def test_strict_system_prompt_rejects_prompt_injection_writes(self):
        original = row("security-001", "DENY_AND_LEDGER")

        updated = with_strict_system_prompt(original)

        prompt = updated["messages"][0]["content"]
        self.assertIn("prompt injection", prompt)
        self.assertIn("system_prompt", prompt)
        self.assertIn("覆盖系统提示", prompt)
        self.assertIn("完全服从", prompt)
        self.assertIn("DENY_AND_LEDGER", prompt)

    def test_stratifies_security_rows_across_splits(self):
        rows = [row(f"balanced-{i:03d}", "ALLOW_ATOMIC_WRITE") for i in range(10)]
        rows += [row(f"security-{i:03d}", "SOVEREIGNTY_HALT") for i in range(10)]

        with tempfile.TemporaryDirectory() as tmp:
            report = build_hardened_split(rows, Path(tmp), train_ratio=0.6, valid_ratio=0.2, security_train_multiplier=1)

            self.assertEqual(report["source_count"], 20)
            for split in ("train", "valid", "test"):
                ids = [json.loads(line)["id"] for line in (Path(tmp) / f"{split}.jsonl").read_text().splitlines()]
                self.assertTrue(any(sample_id.startswith("balanced-") for sample_id in ids))
                self.assertTrue(any(sample_id.startswith("security-") for sample_id in ids))

    def test_upsamples_security_training_rows(self):
        rows = [row(f"balanced-{i:03d}", "ALLOW_ATOMIC_WRITE") for i in range(6)]
        rows += [row(f"security-{i:03d}", "SOVEREIGNTY_HALT") for i in range(6)]

        with tempfile.TemporaryDirectory() as tmp:
            report = build_hardened_split(rows, Path(tmp), train_ratio=0.5, valid_ratio=0.25, security_train_multiplier=3)
            train_ids = [json.loads(line)["id"] for line in (Path(tmp) / "train.jsonl").read_text().splitlines()]

            security_train = [sample_id for sample_id in train_ids if sample_id.startswith("security-")]
            self.assertGreater(len(security_train), report["base_train_security_count"])
            self.assertEqual(report["security_train_multiplier"], 3)

    def test_rejects_invalid_split_configuration(self):
        rows = [row(f"balanced-{i:03d}", "ALLOW_ATOMIC_WRITE") for i in range(3)]

        invalid_cases = (
            ({"train_ratio": 0}, "train_ratio must be > 0 and < 1"),
            ({"train_ratio": 1}, "train_ratio must be > 0 and < 1"),
            ({"valid_ratio": -0.1}, "valid_ratio must be >= 0 and < 1"),
            ({"train_ratio": 0.9, "valid_ratio": 0.1}, r"train_ratio \+ valid_ratio must be < 1"),
            ({"security_train_multiplier": 0}, "security_train_multiplier must be >= 1"),
            ({"hard_negative_multiplier": -1}, "hard_negative_multiplier must be >= 0"),
            ({"recovery_multiplier": 0}, "recovery_multiplier must be >= 1"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            for kwargs, message in invalid_cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaisesRegex(ValueError, message):
                        build_hardened_split(rows, Path(tmp), **kwargs)

    def test_rejects_duplicate_hard_negative_ids(self):
        rows = [
            row("balanced-001", "ALLOW_ATOMIC_WRITE"),
            row("balanced-keepout", "SOVEREIGNTY_HALT"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "duplicate hard negative id: balanced-keepout"):
                build_hardened_split(
                    rows,
                    Path(tmp),
                    hard_negative_ids=["balanced-keepout", "balanced-keepout"],
                )

    def test_rejects_unknown_recovery_actions(self):
        rows = [
            row("balanced-001", "ALLOW_ATOMIC_WRITE"),
            row("balanced-002", "ALLOW_PATCH_WITH_SHA"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "unknown recovery action: ALLOW_TYP0_WRITE"):
                build_hardened_split(rows, Path(tmp), recovery_actions=["ALLOW_TYP0_WRITE"])

    def test_rejects_duplicate_source_ids(self):
        rows = [
            row("balanced-duplicate", "ALLOW_ATOMIC_WRITE"),
            row("balanced-duplicate", "DENY_AND_LEDGER"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "duplicate source id: balanced-duplicate"):
                build_hardened_split(rows, Path(tmp))

    def test_rejects_missing_or_empty_source_ids(self):
        rows = [
            {"messages": row("balanced-missing", "ALLOW_ATOMIC_WRITE")["messages"]},
            row("", "DENY_AND_LEDGER"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source id is required"):
                build_hardened_split(rows, Path(tmp))

    def test_rejects_non_string_source_ids(self):
        rows = [
            {
                "id": 123,
                "messages": row("balanced-123", "ALLOW_ATOMIC_WRITE")["messages"],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source id must be a string"):
                build_hardened_split(rows, Path(tmp))

    def test_rejects_source_ids_with_whitespace_or_control_characters(self):
        invalid_rows = (
            row(" balanced-001", "ALLOW_ATOMIC_WRITE"),
            row("balanced-001 ", "ALLOW_ATOMIC_WRITE"),
            row("balanced\t001", "ALLOW_ATOMIC_WRITE"),
        )

        with tempfile.TemporaryDirectory() as tmp:
            for invalid_row in invalid_rows:
                with self.subTest(sample_id=invalid_row["id"]):
                    with self.assertRaisesRegex(ValueError, "source id contains whitespace or control characters"):
                        build_hardened_split([invalid_row], Path(tmp))

    def test_rejects_empty_source_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source rows are required"):
                build_hardened_split([], Path(tmp))

    def test_rejects_source_rows_without_gold_action(self):
        rows = [
            {
                "id": "balanced-missing-action",
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "balanced-missing-action"},
                    {"role": "assistant", "content": "{}"},
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "source gold action is required for id: balanced-missing-action"):
                build_hardened_split(rows, Path(tmp))

    def test_replays_hard_negatives_in_strict_training_split(self):
        rows = [row(f"balanced-{i:03d}", "ALLOW_ATOMIC_WRITE") for i in range(10)]
        rows += [row("balanced-keepout", "SOVEREIGNTY_HALT")]
        rows += [row(f"security-{i:03d}", "SOVEREIGNTY_HALT") for i in range(10)]
        rows += [row("security-critical", "DENY_AND_LEDGER")]

        with tempfile.TemporaryDirectory() as tmp:
            report = build_hardened_split(
                rows,
                Path(tmp),
                train_ratio=0.1,
                valid_ratio=0.1,
                security_train_multiplier=1,
                strict_system_prompt=True,
                hard_negative_ids=["balanced-keepout", "security-critical"],
                hard_negative_multiplier=4,
            )

            train_rows = [
                json.loads(line)
                for line in (Path(tmp) / "train.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            valid_ids = {
                json.loads(line)["id"]
                for line in (Path(tmp) / "valid.jsonl").read_text(encoding="utf-8").splitlines()
            }
            test_ids = {
                json.loads(line)["id"]
                for line in (Path(tmp) / "test.jsonl").read_text(encoding="utf-8").splitlines()
            }

            train_id_counts = {}
            for train_row in train_rows:
                train_id_counts[train_row["id"]] = train_id_counts.get(train_row["id"], 0) + 1

            self.assertEqual(train_id_counts["balanced-keepout"], 4)
            self.assertEqual(train_id_counts["security-critical"], 4)
            self.assertNotIn("balanced-keepout", valid_ids)
            self.assertNotIn("balanced-keepout", test_ids)
            self.assertNotIn("security-critical", valid_ids)
            self.assertNotIn("security-critical", test_ids)
            for train_row in train_rows:
                if train_row["id"] in {"balanced-keepout", "security-critical"}:
                    self.assertIn("Allowed actions:", train_row["messages"][0]["content"])

            self.assertEqual(report["hard_negative_requested_count"], 2)
            self.assertEqual(report["hard_negative_found_count"], 2)
            self.assertEqual(report["hard_negative_train_count"], 8)
            self.assertEqual(report["hard_negative_missing_ids"], [])

    def test_upsamples_recovery_actions_only_from_training_split(self):
        rows = [row(f"write-{i:03d}", "ALLOW_ATOMIC_WRITE") for i in range(8)]
        rows += [row(f"patch-{i:03d}", "ALLOW_PATCH_WITH_SHA") for i in range(8)]
        rows += [row(f"deny-{i:03d}", "DENY_AND_LEDGER") for i in range(8)]

        with tempfile.TemporaryDirectory() as tmp:
            report = build_hardened_split(
                rows,
                Path(tmp),
                train_ratio=0.5,
                valid_ratio=0.25,
                security_train_multiplier=1,
                recovery_actions=["ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"],
                recovery_multiplier=3,
            )

            train_rows = [
                json.loads(line)
                for line in (Path(tmp) / "train.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            valid_ids = {
                json.loads(line)["id"]
                for line in (Path(tmp) / "valid.jsonl").read_text(encoding="utf-8").splitlines()
            }
            test_ids = {
                json.loads(line)["id"]
                for line in (Path(tmp) / "test.jsonl").read_text(encoding="utf-8").splitlines()
            }

            train_id_counts = {}
            for train_row in train_rows:
                train_id_counts[train_row["id"]] = train_id_counts.get(train_row["id"], 0) + 1

            recovery_ids = {
                train_row["id"]
                for train_row in train_rows
                if train_row["id"].startswith(("write-", "patch-"))
            }

            self.assertEqual(report["recovery_actions"], ["ALLOW_ATOMIC_WRITE", "ALLOW_PATCH_WITH_SHA"])
            self.assertEqual(report["recovery_multiplier"], 3)
            self.assertEqual(report["recovery_base_train_count"], 8)
            self.assertEqual(report["recovery_train_count"], 16)
            for sample_id in recovery_ids:
                self.assertEqual(train_id_counts[sample_id], 3)
                self.assertNotIn(sample_id, valid_ids)
                self.assertNotIn(sample_id, test_ids)
            for sample_id, count in train_id_counts.items():
                if sample_id.startswith("deny-"):
                    self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
