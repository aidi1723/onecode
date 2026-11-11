"""Unit tests for WorkspaceSnapshot and transactional rollback on failure."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from onecode.kernel.terminal_loop import run_terminal_session
from onecode.kernel.workspace_snapshot import WorkspaceSnapshot


class WorkspaceSnapshotTests(unittest.TestCase):
    def test_snapshot_restores_modified_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "app.py"
            target.write_text("def hello():\n    return 'initial'\n", encoding="utf-8")

            snapshot = WorkspaceSnapshot(workspace)
            snapshot.record_before_write("app.py")

            target.write_text("def hello():\n    return 'corrupted'\n", encoding="utf-8")
            self.assertIn("corrupted", target.read_text(encoding="utf-8"))

            res = snapshot.rollback()
            self.assertTrue(res["rolled_back"])
            self.assertIn("app.py", res["restored_files"])
            self.assertEqual(target.read_text(encoding="utf-8"), "def hello():\n    return 'initial'\n")

    def test_snapshot_removes_created_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            new_file = workspace / "dirty.py"

            snapshot = WorkspaceSnapshot(workspace)
            snapshot.record_before_write("dirty.py")

            new_file.write_text("uncommitted scratchpad\n", encoding="utf-8")
            self.assertTrue(new_file.exists())

            res = snapshot.rollback()
            self.assertTrue(res["rolled_back"])
            self.assertIn("dirty.py", res["removed_files"])
            self.assertFalse(new_file.exists())

    def test_snapshot_commit_clears_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "service.py"
            target.write_text("baseline\n", encoding="utf-8")

            snapshot = WorkspaceSnapshot(workspace)
            snapshot.record_before_write("service.py")
            target.write_text("updated\n", encoding="utf-8")

            commit_res = snapshot.commit()
            self.assertTrue(commit_res["committed"])

            res = snapshot.rollback()
            self.assertEqual(len(res["restored_files"]), 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "updated\n")

    def test_terminal_session_reverts_dirty_patch_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            src = workspace / "calc.py"
            src.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

            turns = [
                json.dumps({
                    "action_type": "patch",
                    "path": "calc.py",
                    "search_block": "    return a - b\n",
                    "replace_block": "    return a + b\n",
                }),
                # Turn 2: attempts to modify forbidden test path to trigger halt
                json.dumps({
                    "action_type": "command",
                    "command": ["rm", "-f", "tests/test_calc.py"],
                }),
            ]
            turn_iter = iter(turns)

            class HaltProvider:
                def complete(self, _prompt: str) -> str:
                    return next(turn_iter)

            res = run_terminal_session(
                "Fix add function",
                workspace,
                HaltProvider(),
                max_turns=3,
                auto_approved_for_eval=True,
                rollback_on_failure=True,
            )

            self.assertEqual(res["status"], "halted")
            self.assertIn("rollback", res)
            self.assertTrue(res["rollback"]["rolled_back"])
            self.assertIn("calc.py", res["rollback"]["restored_files"])
            # The corrupted/unverified patch must have been rolled back
            self.assertEqual(src.read_text(encoding="utf-8"), "def add(a, b):\n    return a - b\n")

    def test_terminal_session_keeps_clean_patch_on_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            src = workspace / "calc.py"
            src.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

            turns = [
                json.dumps({
                    "action_type": "patch",
                    "path": "calc.py",
                    "search_block": "    return a - b\n",
                    "replace_block": "    return a + b\n",
                }),
                json.dumps({
                    "action_type": "finish",
                    "explanation": "Fixed subtraction bug in add.",
                }),
            ]
            turn_iter = iter(turns)

            class FinishProvider:
                def complete(self, _prompt: str) -> str:
                    return next(turn_iter)

            res = run_terminal_session(
                "Fix add function",
                workspace,
                FinishProvider(),
                max_turns=3,
                auto_approved_for_eval=True,
                rollback_on_failure=True,
            )

            self.assertEqual(res["status"], "completed")
            self.assertNotIn("rollback", res)
            # The clean patch must be preserved
            self.assertEqual(src.read_text(encoding="utf-8"), "def add(a, b):\n    return a + b\n")


if __name__ == "__main__":
    unittest.main()
