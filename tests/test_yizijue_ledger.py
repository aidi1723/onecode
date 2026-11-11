import json
import tempfile
import unittest
from pathlib import Path

from onecode.experimental.yizijue_ledger import append_yizijue_ledger, yizijue_ledger_entry


class YiZiJueLedgerTests(unittest.TestCase):
    def test_observe_and_kun_are_different_records_and_neither_executes(self):
        observe = yizijue_ledger_entry(
            {"yizijue_state": "010010", "action": "DENY_AND_LEDGER", "reason": "entropy_observe"}
        )
        kun = yizijue_ledger_entry(
            {"yizijue_state": "000000", "action": "DENY_AND_LEDGER", "reason": "kun_deny_ledger"}
        )
        self.assertNotEqual(observe["reason"], kun["reason"])
        self.assertEqual(observe["cycle"], "stop")
        self.assertEqual(kun["cycle"], "stop")
        self.assertFalse(observe["executed"])
        self.assertFalse(kun["executed"])
        verifier = yizijue_ledger_entry(
            {"yizijue_state": "010010", "action": "RUN_VERIFIER_IN_SANDBOX", "reason": "verifier_requires_sandbox"}
        )
        allowed = yizijue_ledger_entry(
            {"yizijue_state": "111111", "action": "ALLOW_ATOMIC_WRITE", "reason": "hexagram_recast"}
        )
        self.assertEqual(verifier["cycle"], "verify")
        self.assertEqual(allowed["cycle"], "stop")
        self.assertFalse(verifier["executed"])
        self.assertFalse(allowed["executed"])
        self.assertEqual(observe["symbolic_transition"]["action"], "activate")
        self.assertEqual(allowed["action"], "ALLOW_ATOMIC_WRITE")
        self.assertEqual(allowed["symbolic_transition"]["action"], "cooldown")
        self.assertEqual(allowed["symbolic_transition"]["status_code"], "100111")
        with self.assertRaises(ValueError):
            yizijue_ledger_entry(
                {"yizijue_state": "000000", "action": "DENY_AND_LEDGER", "reason": "entropy_observe"}
            )

    def test_workspace_ledger_appends_without_touching_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            append_yizijue_ledger(
                workspace,
                {
                    "yizijue_state": "111110",
                    "action": "DENY_AND_LEDGER",
                    "reason": "entropy_observe",
                    "moving_cast": {"before": "111110", "after": "111111", "moving": [0]},
                },
            )
            lines = (workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        self.assertEqual(entry["moving_cast"]["after"], "111111")
        self.assertEqual(entry["action"], "DENY_AND_LEDGER")
        self.assertEqual(entry["symbolic_transition"]["status_code"], "100110")
        self.assertFalse(entry["executed"])

    def test_decision_is_copied_to_the_service_ledger(self):
        import os

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            service_ledger = workspace / "service.jsonl"
            previous = os.environ.get("YIZIJUE_LEDGER")
            os.environ["YIZIJUE_LEDGER"] = str(service_ledger)
            try:
                append_yizijue_ledger(
                    workspace,
                    {
                        "yizijue_state": "010010",
                        "action": "DENY_AND_LEDGER",
                        "reason": "entropy_observe",
                    },
                )
            finally:
                if previous is None:
                    os.environ.pop("YIZIJUE_LEDGER", None)
                else:
                    os.environ["YIZIJUE_LEDGER"] = previous
            recorded = json.loads((workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8"))
            copied = json.loads(service_ledger.read_text(encoding="utf-8"))
        self.assertEqual(copied, recorded)
        self.assertEqual(recorded["reason"], "entropy_observe")
        self.assertFalse(recorded["executed"])

    def test_moving_cast_from_another_hexagram_is_not_recorded(self):
        entry = yizijue_ledger_entry(
            {
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
                "moving_cast": {"before": "111110", "after": "111111"},
            }
        )
        self.assertEqual(entry["yizijue_state"], "010010")
        self.assertEqual(entry["action"], "RUN_VERIFIER_IN_SANDBOX")
        self.assertIsNone(entry["moving_cast"])
        self.assertFalse(entry["executed"])
        forged = yizijue_ledger_entry(
            {
                "yizijue_state": "111110",
                "action": "DENY_AND_LEDGER",
                "reason": "collapse_head",
                "moving_cast": {"before": "111110", "after": "111111", "moving": []},
            }
        )
        self.assertEqual(forged["yizijue_state"], "111110")
        self.assertEqual(forged["action"], "DENY_AND_LEDGER")
        self.assertIsNone(forged["moving_cast"])
        self.assertFalse(forged["executed"])
        carried = yizijue_ledger_entry(
            {
                "yizijue_state": "111110",
                "action": "DENY_AND_LEDGER",
                "reason": "collapse_head",
                "moving_cast": {
                    "before": "111110",
                    "after": "111111",
                    "moving": [0],
                    "action": "ALLOW_ATOMIC_WRITE",
                    "yizijue_state": "111111",
                },
            }
        )
        self.assertEqual(carried["action"], "DENY_AND_LEDGER")
        self.assertEqual(carried["yizijue_state"], "111110")
        self.assertEqual(set(carried["moving_cast"]), {"before", "after", "moving"})
        self.assertFalse(carried["executed"])
        with self.assertRaises(ValueError):
            yizijue_ledger_entry(carried)

    def test_effect_line_records_only_a_pinned_execution(self):
        from onecode.experimental.yizijue_ledger import append_yizijue_effect, yizijue_effect_entry
        from onecode.experimental.yizijue_verifier import pinned_verifier_command
        from onecode.kernel.checkpoint import sha256_text

        verifier = yizijue_effect_entry(
            {
                "effect": "verifier",
                "yizijue_state": "010010",
                "action": "RUN_VERIFIER_IN_SANDBOX",
                "reason": "verifier_requires_sandbox",
                "ran": True,
                "command": pinned_verifier_command(),
            }
        )
        withheld = yizijue_effect_entry(
            {
                "effect": "write",
                "yizijue_state": "010010",
                "action": "DENY_AND_LEDGER",
                "reason": "entropy_observe",
                "ran": False,
            }
        )
        self.assertTrue(verifier["executed"])
        self.assertEqual(verifier["command"], pinned_verifier_command())
        self.assertFalse(withheld["executed"])
        with self.assertRaises(ValueError):
            yizijue_effect_entry(
                {
                    "effect": "verifier",
                    "yizijue_state": "010010",
                    "action": "RUN_VERIFIER_IN_SANDBOX",
                    "reason": "verifier_requires_sandbox",
                    "ran": True,
                }
            )
        written = yizijue_effect_entry(
            {
                "effect": "write",
                "yizijue_state": "111111",
                "action": "ALLOW_ATOMIC_WRITE",
                "reason": "hexagram_recast",
                "ran": True,
                "path": "notes/today.txt",
                "sha256": sha256_text("三条笔记"),
            }
        )
        self.assertTrue(written["executed"])
        self.assertEqual(written["path"], "notes/today.txt")
        with self.assertRaises(ValueError):
            yizijue_effect_entry(
                {
                    "effect": "write",
                    "yizijue_state": "111111",
                    "action": "ALLOW_ATOMIC_WRITE",
                    "reason": "sha_mismatch",
                    "ran": True,
                }
            )
        with self.assertRaises(ValueError):
            yizijue_effect_entry(
                {
                    "effect": "verifier",
                    "yizijue_state": "010010",
                    "action": "RUN_VERIFIER_IN_SANDBOX",
                    "reason": "verifier_unconfirmed",
                    "ran": True,
                }
            )
        with tempfile.TemporaryDirectory() as directory:
            path = append_yizijue_effect(Path(directory), verifier)
            recorded = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(recorded["kind"], "yizijue_effect")
        self.assertEqual(recorded["effect"], "verifier")

    def test_effect_is_copied_to_the_service_ledger(self):
        import os

        from onecode.experimental.yizijue_ledger import append_yizijue_effect, yizijue_effect_entry
        from onecode.experimental.yizijue_verifier import pinned_verifier_command

        effect = {
            "effect": "verifier",
            "yizijue_state": "010010",
            "action": "RUN_VERIFIER_IN_SANDBOX",
            "reason": "verifier_requires_sandbox",
            "ran": True,
            "command": pinned_verifier_command(),
        }
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            service_ledger = workspace / "service.jsonl"
            previous = os.environ.get("YIZIJUE_LEDGER")
            os.environ["YIZIJUE_LEDGER"] = str(service_ledger)
            try:
                append_yizijue_effect(workspace, effect)
            finally:
                if previous is None:
                    os.environ.pop("YIZIJUE_LEDGER", None)
                else:
                    os.environ["YIZIJUE_LEDGER"] = previous
            copied = json.loads(service_ledger.read_text(encoding="utf-8"))
            stored = json.loads((workspace / ".onecode" / "yizijue-ledger.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(copied, stored)
        self.assertTrue(copied["executed"])
        self.assertEqual(copied["command"], pinned_verifier_command())
        self.assertEqual(yizijue_effect_entry(effect)["effect"], "verifier")


if __name__ == "__main__":
    unittest.main()
