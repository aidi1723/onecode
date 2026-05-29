import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_skill_dictionary.audit import read_audit_log, verify_audit_chain
from agent_skill_dictionary.build_mode_expert_handoff import apply_expert_seed, apply_timeout_flash_seed
from agent_skill_dictionary.build_mode_orchestrator import artifact_plan_for_request


class BuildModeExpertHandoffTest(unittest.TestCase):
    def test_expert_seed_requires_authorization_token(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_expert_seed(
                workspace=tmp,
                artifact_plan=plan,
                token="wrong",
                changes={"sync/models.py": "VALUE = 1\n"},
                verify_command=[sys.executable, "-c", "raise SystemExit(0)"],
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "expert_token_invalid")

    def test_expert_seed_requires_failure_gate_state(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
            clear=False,
        ):
            result = apply_expert_seed(
                workspace=tmp,
                artifact_plan=plan,
                token="secret",
                changes={"sync/models.py": "VALUE = 1\n"},
                verify_command=[sys.executable, "-c", "raise SystemExit(0)"],
            )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "failure_gate_not_active")

    def test_expert_seed_applies_allowed_change_and_verifies_under_guard(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
            clear=False,
        ):
            root = Path(tmp)
            state_dir = root / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps({"consecutive_failures": 2, "repo_card": "failed"}),
                encoding="utf-8",
            )

            result = apply_expert_seed(
                workspace=root,
                artifact_plan=plan,
                token="secret",
                changes={"sync/models.py": "VALUE = 1\n"},
                verify_command=[sys.executable, "-c", "from pathlib import Path; assert Path('sync/models.py').exists()"],
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hexagram"], "000")
            self.assertEqual(result["write_results"][0]["status"], "ok")
            self.assertEqual(result["verify"]["status"], "completed")
            self.assertTrue((root / "sync" / "models.py").exists())
            audit_path = root / ".yizijue" / "audit.jsonl"
            records = read_audit_log(audit_path)
            self.assertEqual(records[-1]["source"], "expert_handoff")
            self.assertEqual(records[-1]["status"], "completed")
            self.assertEqual(records[-1]["hexagram"], "000")
            self.assertTrue(verify_audit_chain(audit_path)["valid"])

    def test_expert_seed_blocks_unplanned_dependency_shim(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
            clear=False,
        ):
            root = Path(tmp)
            state_dir = root / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps({"consecutive_failures": 2}),
                encoding="utf-8",
            )

            result = apply_expert_seed(
                workspace=root,
                artifact_plan=plan,
                token="secret",
                changes={"fastapi/__init__.py": "fake\n"},
                verify_command=[sys.executable, "-c", "raise SystemExit(0)"],
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "unplanned_artifact_path")
            self.assertFalse((root / "fastapi" / "__init__.py").exists())
            records = read_audit_log(root / ".yizijue" / "audit.jsonl")
            self.assertEqual(records[-1]["source"], "expert_handoff")
            self.assertEqual(records[-1]["status"], "blocked")
            self.assertEqual(records[-1]["reason"], "unplanned_artifact_path")

    def test_timeout_flash_seed_repairs_secure_b2b_sync_deadlock(self):
        plan = artifact_plan_for_request("修复 sync_node.py 同步死锁 Bug")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(Path("tests/fixtures/secure_b2b_ledger"), root, dirs_exist_ok=True)

            result = apply_timeout_flash_seed(
                workspace=root,
                artifact_plan=plan,
                timeout_result={
                    "status": "needs_fix",
                    "hexagram": "001",
                    "evidence": {
                        "exit_code": 124,
                        "pytest_status": "timeout",
                        "timed_out": True,
                        "failure_summary": "test_sync.py:17 in fail_post",
                    },
                },
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hexagram"], "100")
            self.assertEqual(result["next_hexagram"], "000")
            self.assertEqual(result["source"], "timeout_flash_expert_handoff")
            self.assertEqual(result["verify"]["exit_code"], 0)
            content = (root / "sync_node.py").read_text(encoding="utf-8")
            self.assertIn("attempts += 1", content)
            self.assertIn("return {\"ok\": False, \"attempts\": attempts}", content)


if __name__ == "__main__":
    unittest.main()
