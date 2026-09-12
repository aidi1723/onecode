import json
import select
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.approval_plans import claim_approval_plan, finalize_approval_plan, persist_approval_plan
from onecode.kernel.model_provider import ModelPlan, ModelPlanAsset
from onecode.web.api import execute_model_plan, handle_onecode_plan_approval


class ApprovalRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.environment = patch.dict("os.environ", {
            "ONECODE_WORKSPACE_ROOT": str(self.workspace),
            "ONECODE_ALLOWED_WORKSPACE_ROOTS": str(self.workspace),
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.stored = persist_approval_plan(self.workspace, ModelPlan(
            task="approval recovery", assets=[ModelPlanAsset(path="out.txt", content="done")],
        ), model_metadata={})
        self.body = {"workspace": str(self.workspace), "approved": True}

    def approve(self):
        return handle_onecode_plan_approval(self.stored.plan_id, self.body)

    def test_execution_exception_is_archived_without_replay_or_secret_leak(self):
        def fail_after_effect(*args, **kwargs):
            (self.workspace / "partial.txt").write_text("side effect", encoding="utf-8")
            raise OSError("TOKEN=private-fixture")

        with patch("onecode.web.api.execute_model_plan", side_effect=fail_after_effect) as execute:
            failed, status = self.approve()
            replay, replay_status = self.approve()
        self.assertEqual(status, 500)
        self.assertEqual(replay_status, 409)
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(replay["error"]["message"], "approval_plan_already_resolved")
        self.assertTrue((self.workspace / "partial.txt").exists())
        archive = self.workspace / ".onecode/approval-plans" / self.stored.path.name
        document = json.loads(archive.read_text(encoding="utf-8"))
        self.assertEqual(document["decision"], "approved")
        self.assertEqual(document["result"]["status"], "halted")
        self.assertIsNone(document["result"]["completed_count"])
        self.assertNotIn("private-fixture", json.dumps([failed, document]))
        self.assertFalse((self.workspace / ".onecode/executing-plans" / self.stored.path.name).exists())

    def test_duplicate_request_does_not_execute_or_isolate_live_plan(self):
        entered, release = threading.Event(), threading.Event()

        def gated_execute(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise AssertionError("test executor was not released")
            return execute_model_plan(*args, **kwargs)

        with patch("onecode.web.api.execute_model_plan", side_effect=gated_execute) as execute:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.approve)
                try:
                    self.assertTrue(entered.wait(5))
                    rejected, status = self.approve()
                    self.assertEqual(status, 409)
                    self.assertEqual(rejected["error"]["message"], "approval_plan_in_progress")
                    self.assertFalse((self.workspace / ".onecode/interrupted-plans").exists())
                finally:
                    release.set()
                result, status = future.result(timeout=5)
        self.assertEqual((status, result["status"]), (200, "completed"))
        self.assertEqual(execute.call_count, 1)
        self.assertEqual((self.workspace / "out.txt").read_text(), "done")

    def test_abandoned_claim_is_isolated_and_cannot_be_replayed(self):
        claimed = claim_approval_plan(self.workspace, self.stored.plan_id)
        with patch("onecode.web.api.execute_model_plan") as execute:
            interrupted, status = self.approve()
            _, replay_status = self.approve()
        self.assertEqual(status, 409)
        self.assertEqual(interrupted["error"]["type"], "approval_execution_interrupted")
        self.assertEqual(replay_status, 409)
        execute.assert_not_called()
        self.assertFalse(claimed.path.exists())
        self.assertTrue((self.workspace / ".onecode/interrupted-plans" / claimed.path.name).exists())

    def test_archive_takes_precedence_over_interrupted_cleanup(self):
        claimed = claim_approval_plan(self.workspace, self.stored.plan_id)
        raw = claimed.path.read_bytes()
        archive = finalize_approval_plan(claimed, "approved", {"status": "completed", "completed_count": 1})
        claimed.path.write_bytes(raw)
        with patch("onecode.web.api.execute_model_plan") as execute:
            result, status = self.approve()
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["message"], "approval_plan_already_resolved")
        execute.assert_not_called()
        self.assertEqual(json.loads(archive.read_text())["result"]["status"], "completed")

    def test_invalid_claim_does_not_remain_falsely_in_progress(self):
        self.stored.path.write_text("not-json", encoding="utf-8")
        with patch("onecode.web.api.execute_model_plan") as execute:
            _, status = self.approve()
            replay, replay_status = self.approve()
        self.assertEqual(status, 400)
        self.assertIn(replay_status, (400, 409))
        self.assertNotEqual(replay["error"]["message"], "approval_plan_in_progress")
        execute.assert_not_called()

    def test_storage_failure_keeps_claim_for_nonreplaying_recovery(self):
        with patch("onecode.web.api.finalize_approval_plan", side_effect=OSError("disk unavailable")):
            failed, status = self.approve()
        self.assertEqual(status, 500)
        self.assertEqual(failed["error"]["type"], "approval_storage_unavailable")
        self.assertEqual((self.workspace / "out.txt").read_text(), "done")
        with patch("onecode.web.api.execute_model_plan") as execute:
            interrupted, status = self.approve()
        self.assertEqual(status, 409)
        self.assertEqual(interrupted["error"]["type"], "approval_execution_interrupted")
        execute.assert_not_called()

    def test_storage_would_block_is_not_misreported_as_live_executor(self):
        with patch("onecode.web.api.finalize_approval_plan", side_effect=BlockingIOError("storage busy")):
            failed, status = self.approve()
        self.assertEqual(status, 500)
        self.assertEqual(failed["error"]["type"], "approval_storage_unavailable")

    def test_expired_plan_is_quarantined_without_execution(self):
        with patch("onecode.kernel.approval_plans.time.time", return_value=self.stored.created_at + 3601):
            with patch("onecode.web.api.execute_model_plan") as execute:
                failed, status = self.approve()
                replay, replay_status = self.approve()
        self.assertEqual(status, 400)
        self.assertEqual(failed["error"]["message"], "approval_plan_expired")
        self.assertEqual(replay_status, 409)
        self.assertEqual(replay["error"]["message"], "approval_plan_already_resolved")
        execute.assert_not_called()

    def test_wrong_workspace_plan_cannot_execute(self):
        other = self.workspace / "other"
        other.mkdir()
        pending = other / ".onecode/pending-plans" / self.stored.path.name
        pending.parent.mkdir(parents=True)
        pending.write_bytes(self.stored.path.read_bytes())
        with patch("onecode.web.api.execute_model_plan") as execute:
            failed, status = handle_onecode_plan_approval(
                self.stored.plan_id, {"workspace": str(other), "approved": True},
            )
        self.assertEqual(status, 400)
        self.assertEqual(failed["error"]["message"], "approval_plan_workspace_mismatch")
        execute.assert_not_called()
        self.assertTrue((other / ".onecode/interrupted-plans" / self.stored.path.name).exists())

    def test_process_lock_distinguishes_live_executor_from_terminated_executor(self):
        code = """
import sys
from pathlib import Path
from onecode.kernel.approval_plans import approval_plan_lock, claim_approval_plan
workspace, plan_id = Path(sys.argv[1]), sys.argv[2]
with approval_plan_lock(workspace, plan_id):
    claim_approval_plan(workspace, plan_id)
    print('claimed', flush=True)
    sys.stdin.read()
"""
        process = subprocess.Popen([sys.executable, "-c", code, str(self.workspace), self.stored.plan_id],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 5)
            self.assertTrue(ready, "child did not report its claim")
            self.assertEqual(process.stdout.readline().strip(), "claimed")
            live, status = self.approve()
            self.assertEqual(status, 409)
            self.assertEqual(live["error"]["message"], "approval_plan_in_progress")
            process.terminate()
            process.communicate(timeout=5)
            with patch("onecode.web.api.execute_model_plan") as execute:
                abandoned, status = self.approve()
            self.assertEqual(status, 409)
            self.assertEqual(abandoned["error"]["type"], "approval_execution_interrupted")
            execute.assert_not_called()
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
