import tempfile
import unittest
from pathlib import Path

from onecode.experimental.yizijue_write import run_pinned_write, unique_patch_text, workspace_writer
from onecode.kernel.checkpoint import sha256_text


WRITE_FACTS = {
    "intent_type": "write_text",
    "path_scope": "workspace_relative",
    "sandbox_state": "not_required",
    "evidence_state": "present",
}


def allow_entry(**overrides):
    entry = {
        "yizijue_state": "111111",
        "action": "ALLOW_ATOMIC_WRITE",
        "reason": "hexagram_recast",
        "cycle": "stop",
        "executed": False,
        "facts": dict(WRITE_FACTS),
        "evidence": {"path": "notes/today.txt", "sha256": sha256_text("三条笔记")},
    }
    entry.update(overrides)
    return entry


class PinnedWriteTests(unittest.TestCase):
    def test_qian_allow_writes_only_when_the_hash_matches(self):
        calls = []

        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            calls.append((relative_path, content))
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"path": relative_path}

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            denied = run_pinned_write(workspace, allow_entry(), "别的内容", writer)
            accepted = run_pinned_write(workspace, allow_entry(), "三条笔记", writer)
        self.assertFalse(denied["ran"])
        self.assertEqual(denied["reason"], "sha_mismatch")
        self.assertEqual(calls, [("notes/today.txt", "三条笔记")])
        self.assertTrue(accepted["executed"])

    def test_withheld_halt_and_moved_qian_do_not_write(self):
        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            raise AssertionError("writer should not be called")

        blocked = [
            allow_entry(yizijue_state="010010", action="DENY_AND_LEDGER", reason="entropy_observe", cycle="stop"),
            allow_entry(yizijue_state="000000", action="DENY_AND_LEDGER", reason="kun_deny_ledger", cycle="stop"),
            allow_entry(yizijue_state="100001", action="SOVEREIGNTY_HALT", reason="dangerous_host_command", cycle="stop"),
            allow_entry(
                yizijue_state="111110",
                action="DENY_AND_LEDGER",
                reason="collapse_head",
                cycle="stop",
                moving_cast={"before": "111110", "after": "111111"},
            ),
            allow_entry(evidence={"path": "../outside.txt", "sha256": sha256_text("三条笔记")}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            reasons = [run_pinned_write(workspace, item, "三条笔记", writer)["reason"] for item in blocked]
        self.assertEqual(
            reasons,
            ["withheld", "withheld", "not_write", "not_write", "path_rejected"],
        )

    def test_workspace_writer_stays_inside_the_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = run_pinned_write(workspace, allow_entry(), "三条笔记", workspace_writer)
            self.assertEqual((workspace / "notes" / "today.txt").read_text(encoding="utf-8"), "三条笔记")
            self.assertEqual(result["result"]["sha256"], sha256_text("三条笔记"))

    def test_written_bytes_must_match_the_decision_hash(self):
        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            target = workspace / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("别的内容", encoding="utf-8")
            return {"path": relative_path, "sha256": sha256_text(content)}

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = run_pinned_write(workspace, allow_entry(), "三条笔记", writer)
            self.assertFalse(result["executed"])
            self.assertEqual(result["reason"], "sha_mismatch")
            self.assertEqual((workspace / "notes" / "today.txt").read_text(encoding="utf-8"), "别的内容")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)

            def noop(workspace: Path, relative_path: str, content: str) -> dict:
                return {"path": relative_path}

            missing = run_pinned_write(workspace, allow_entry(), "三条笔记", noop)
            self.assertFalse(missing["executed"])
            self.assertEqual(missing["reason"], "sha_mismatch")
            self.assertFalse((workspace / "notes" / "today.txt").exists())

    def test_repository_control_files_are_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            for relative in (".env", ".git/config", ".onecode/ledger.jsonl", "Makefile"):
                entry = allow_entry(evidence={"path": relative, "sha256": sha256_text("三条笔记")})
                result = run_pinned_write(workspace, entry, "三条笔记", workspace_writer)
                self.assertEqual(result["reason"], "path_rejected")
                self.assertFalse(result["ran"])
            self.assertFalse((workspace / ".env").exists())
            self.assertFalse((workspace / ".git").exists())
            self.assertFalse((workspace / ".onecode").exists())
            self.assertFalse((workspace / "Makefile").exists())

    def test_patch_writes_only_a_unique_search_block(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            target = workspace / "src" / "app.py"
            target.parent.mkdir()
            target.write_text("keep alpha tail", encoding="utf-8")
            updated = unique_patch_text(workspace, "src/app.py", "alpha", "beta")
            self.assertEqual(updated, "keep beta tail")
            entry = allow_entry(
                action="ALLOW_PATCH_WITH_SHA",
                facts={**WRITE_FACTS, "intent_type": "patch_text"},
                evidence={"path": "src/app.py", "post_sha256": sha256_text(updated or "")},
            )
            result = run_pinned_write(workspace, entry, updated or "", workspace_writer)
            self.assertTrue(result["ran"])
            self.assertEqual(target.read_text(encoding="utf-8"), "keep beta tail")
            target.write_text("alpha and alpha", encoding="utf-8")
            self.assertIsNone(unique_patch_text(workspace, "src/app.py", "alpha", "beta"))
            self.assertEqual(target.read_text(encoding="utf-8"), "alpha and alpha")

    def test_gateway_must_reread_the_qian_hexagram(self):
        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            raise AssertionError("writer should not be called")

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            missing = run_pinned_write(workspace, allow_entry(facts=None), "三条笔记", writer)
            mismatched = run_pinned_write(
                workspace,
                allow_entry(
                    facts={
                        "intent_type": "execute_pytest",
                        "path_scope": "no_path",
                        "sandbox_state": "required",
                        "evidence_state": "required",
                    }
                ),
                "三条笔记",
                writer,
            )
        self.assertEqual(missing["reason"], "gateway_unread")
        self.assertFalse(missing["ran"])
        self.assertEqual(mismatched["reason"], "gateway_mismatch")
        self.assertFalse(mismatched["ran"])

    def test_moving_cast_cannot_grant_the_write(self):
        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            raise AssertionError("writer should not be called")

        entry = allow_entry(
            yizijue_state="111110",
            action="DENY_AND_LEDGER",
            reason="collapse_head",
            moving_cast={
                "before": "111110",
                "after": "111111",
                "moving": [0],
                "action": "ALLOW_ATOMIC_WRITE",
                "yizijue_state": "111111",
                "facts": dict(WRITE_FACTS),
                "evidence": {"path": "notes/today.txt", "sha256": sha256_text("三条笔记")},
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            result = run_pinned_write(Path(directory), entry, "三条笔记", writer)
        self.assertFalse(result["ran"])
        self.assertEqual(result["reason"], "not_write")

    def test_blocked_write_reason_does_not_write(self):
        def writer(workspace: Path, relative_path: str, content: str) -> dict:
            raise AssertionError("a blocked decision must not write")

        for reason in ("sha_mismatch", "yizijue_admission_rejected"):
            entry = allow_entry(reason=reason)
            with tempfile.TemporaryDirectory() as directory:
                result = run_pinned_write(Path(directory), entry, "三条笔记", writer)
            self.assertFalse(result["ran"])
            self.assertEqual(result["reason"], "withheld")


if __name__ == "__main__":
    unittest.main()
