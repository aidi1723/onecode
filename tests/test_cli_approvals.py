from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.cycle_approvals import persist_pending_approval
from onecode.kernel.model_repair import _snapshot_workspace_files


class CliApprovalsTests(unittest.TestCase):
    def test_cli_approvals_list_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                exit_code = main(["approvals", "list", "--workspace", tmp])
            self.assertEqual(exit_code, 0)
            self.assertIn("Pending Approvals: 0", buf.getvalue())

    def test_cli_approvals_list_and_show_with_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            params = {
                "task": "coupon eligibility",
                "failing_checks": ["recently active churned user blocked"],
                "emitted_reasons": ["recently_active"],
            }
            rec = persist_pending_approval(ws, "clarify_decision_reason", params)
            aid = rec["id"]

            # 1. list
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                exit_code = main(["approvals", "list", "--workspace", tmp])
            self.assertEqual(exit_code, 0)
            out = buf.getvalue()
            self.assertIn("Pending Approvals: 1", out)
            self.assertIn(aid, out)
            self.assertIn("recently active churned user blocked", out)

            # 2. list --json
            buf_json = io.StringIO()
            with patch("sys.stdout", buf_json):
                exit_code = main(["approvals", "list", "--workspace", tmp, "--json"])
            self.assertEqual(exit_code, 0)
            data = json.loads(buf_json.getvalue())
            self.assertEqual(len(data.get("approvals", [])), 1)
            self.assertEqual(data["approvals"][0]["id"], aid)

            # 3. show
            buf_show = io.StringIO()
            with patch("sys.stdout", buf_show):
                exit_code = main(["approvals", "show", aid, "--workspace", tmp])
            self.assertEqual(exit_code, 0)
            self.assertIn(aid, buf_show.getvalue())

            # 4. show non-existent
            err_buf = io.StringIO()
            with patch("sys.stderr", err_buf):
                exit_code = main(["approvals", "show", "non_existent_id", "--workspace", tmp])
            self.assertEqual(exit_code, 1)

    def test_cli_approvals_resolve_and_regrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "app").mkdir(parents=True, exist_ok=True)
            (ws / "app" / "policy.py").write_text(
                'def evaluate(): return {"reason": "recently_active"}\n',
                encoding="utf-8",
            )
            snapshot = _snapshot_workspace_files(ws)

            # Create external host verifier outside workspace
            verifier_dir = Path(tempfile.mkdtemp())
            try:
                verifier_file = verifier_dir / "verifier.py"
                verifier_file.write_text(
                    'import os, json, sys; from pathlib import Path\n'
                    'ROOT = Path(os.environ["WORKSPACE"])\n'
                    'code = (ROOT / "app" / "policy.py").read_text()\n'
                    'LOG_DIR = Path(os.environ["LOG_DIR"])\n'
                    'LOG_DIR.mkdir(parents=True, exist_ok=True)\n'
                    'passed = "too_recently_active" in code\n'
                    'score = 1.0 if passed else 0.5\n'
                    'res = {"overall": score, "tests_passed": 1 if passed else 0, "tests_total": 1, "tests": [{"name": "slug", "passed": passed}]}\n'
                    '(LOG_DIR / "reward.json").write_text(json.dumps(res))\n'
                    '(LOG_DIR / "reward.txt").write_text(str(score))\n',
                    encoding="utf-8",
                )

                params = {
                    "task": "coupon eligibility",
                    "failing_checks": ["recently active churned user blocked"],
                    "emitted_reasons": ["recently_active"],
                    "best_snapshot": snapshot,
                    "stalled_reward": 0.5,
                    "run_metadata": {"host_verifier_path": str(verifier_file)},
                }
                rec = persist_pending_approval(ws, "clarify_decision_reason", params)
                aid = rec["id"]

                # Execute CLI resolve command
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    exit_code = main([
                        "approvals",
                        "resolve",
                        aid,
                        "--selected-slug",
                        "too_recently_active",
                        "--workspace",
                        tmp,
                    ])
                self.assertEqual(exit_code, 0)
                out = buf.getvalue()
                self.assertIn("resolved successfully", out)
                self.assertIn("Regraded Host Reward: 1.0", out)

                # Verify file in workspace was modified
                new_code = (ws / "app" / "policy.py").read_text(encoding="utf-8")
                self.assertIn("too_recently_active", new_code)
            finally:
                shutil.rmtree(verifier_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
