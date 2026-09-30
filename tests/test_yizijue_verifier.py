import tempfile
import unittest
from pathlib import Path

from onecode.experimental.yizijue_ledger import yizijue_ledger_entry
from onecode.experimental.yizijue_verifier import pinned_verifier_command, run_pinned_verifier


KAN_FACTS = {
    "intent_type": "execute_pytest",
    "path_scope": "no_path",
    "sandbox_state": "required",
    "evidence_state": "required",
}


def entry(**overrides):
    record = {
        "yizijue_state": "010010",
        "action": "RUN_VERIFIER_IN_SANDBOX",
        "reason": "verifier_requires_sandbox",
        "facts": dict(KAN_FACTS),
    }
    record.update(overrides)
    logged = yizijue_ledger_entry(record)
    if "facts" in record:
        logged = {**logged, "facts": record["facts"]}
    return logged


class PinnedVerifierTests(unittest.TestCase):
    def test_only_the_kan_verifier_runs_and_the_command_is_fixed(self):
        calls = []

        def runner(workspace: Path, command: list[str]) -> dict:
            calls.append((workspace, command))
            return {"status": "passed", "command": list(command)}

        with tempfile.TemporaryDirectory() as directory:
            result = run_pinned_verifier(Path(directory), entry(), runner)
        self.assertTrue(result["ran"])
        self.assertTrue(result["executed"])
        self.assertEqual(calls[0][1], pinned_verifier_command())
        self.assertNotIn("rm", calls[0][1])
        supplied = entry()
        supplied["command"] = ["rm", "-rf", "/"]
        with tempfile.TemporaryDirectory() as directory:
            run_pinned_verifier(Path(directory), supplied, runner)
        self.assertEqual(calls[1][1], pinned_verifier_command())

    def test_sandbox_runner_rejects_any_other_command(self):
        from onecode.experimental.yizijue_verifier import sandbox_unittest_runner

        with tempfile.TemporaryDirectory() as directory:
            result = sandbox_unittest_runner(Path(directory), ["rm", "-rf", "/"])
        self.assertEqual(result, {"status": "failed", "reason": "command_rejected"})

    def test_unconfirmed_verifier_result_is_not_executed(self):
        def wrong_command(workspace: Path, command: list[str]) -> dict:
            return {"status": "passed", "command": ["rm", "-rf", "/"]}

        def bad_status(workspace: Path, command: list[str]) -> dict:
            return {"status": "hacked"}

        def missing_command(workspace: Path, command: list[str]) -> dict:
            return {"status": "passed"}

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            wrong = run_pinned_verifier(workspace, entry(), wrong_command)
            hacked = run_pinned_verifier(workspace, entry(), bad_status)
            omitted = run_pinned_verifier(workspace, entry(), missing_command)
        self.assertFalse(wrong["executed"])
        self.assertEqual(wrong["reason"], "verifier_unconfirmed")
        self.assertFalse(hacked["executed"])
        self.assertEqual(hacked["reason"], "verifier_unconfirmed")
        self.assertFalse(omitted["executed"])
        self.assertEqual(omitted["reason"], "verifier_unconfirmed")

    def test_withheld_and_other_actions_do_not_run(self):
        def runner(workspace: Path, command: list[str]) -> dict:
            raise AssertionError("runner should not be called")

        blocked = [
            entry(yizijue_state="010010", action="DENY_AND_LEDGER", reason="entropy_observe"),
            entry(yizijue_state="000000", action="DENY_AND_LEDGER", reason="kun_deny_ledger"),
            entry(yizijue_state="100001", action="SOVEREIGNTY_HALT", reason="dangerous_host_command"),
            entry(yizijue_state="111111", action="ALLOW_ATOMIC_WRITE", reason="hexagram_recast"),
            entry(
                yizijue_state="111111",
                action="DENY_AND_LEDGER",
                reason="collapse_head",
                moving_cast={"before": "111110", "after": "111111"},
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            reasons = [run_pinned_verifier(workspace, item, runner)["reason"] for item in blocked]
        self.assertEqual(reasons, ["withheld", "withheld", "not_verifier", "not_verifier", "not_verifier"])

    def test_gateway_must_reread_the_kan_hexagram(self):
        def runner(workspace: Path, command: list[str]) -> dict:
            raise AssertionError("runner should not be called")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            missing = run_pinned_verifier(workspace, entry(facts=None), runner)
            mismatched = run_pinned_verifier(
                workspace,
                entry(
                    facts={
                        "intent_type": "write_text",
                        "path_scope": "workspace_relative",
                        "sandbox_state": "not_required",
                        "evidence_state": "present",
                    }
                ),
                runner,
            )
        self.assertEqual(missing["reason"], "gateway_unread")
        self.assertFalse(missing["ran"])
        self.assertEqual(mismatched["reason"], "gateway_mismatch")
        self.assertFalse(mismatched["ran"])


if __name__ == "__main__":
    unittest.main()
