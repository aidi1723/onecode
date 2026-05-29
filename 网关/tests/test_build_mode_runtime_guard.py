import sys
import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_orchestrator import artifact_plan_for_request
from agent_skill_dictionary.build_mode_runtime_guard import run_guarded_runtime


class BuildModeRuntimeGuardTest(unittest.TestCase):
    def test_runtime_guard_quarantines_unplanned_file_created_by_absolute_python(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_guarded_runtime(
                [sys.executable, "-c", "from pathlib import Path; Path('fastapi').mkdir(); Path('fastapi/__init__.py').write_text('fake')"],
                workspace=root,
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["exit_code"], 126)
            self.assertEqual(result["reason"], "post_run_unplanned_artifacts")
            self.assertIn("fastapi/__init__.py", result["unplanned_paths"])
            self.assertFalse((root / "fastapi" / "__init__.py").exists())
            self.assertTrue((root / ".yizijue" / "quarantine" / "fastapi" / "__init__.py").exists())

    def test_runtime_guard_allows_required_artifact_creation(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_guarded_runtime(
                [sys.executable, "-c", "from pathlib import Path; Path('sync').mkdir(); Path('sync/models.py').write_text('ok')"],
                workspace=root,
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["exit_code"], 0)
            self.assertTrue((root / "sync" / "models.py").exists())
            self.assertFalse((root / ".yizijue" / "quarantine").exists())

    def test_runtime_guard_blocks_before_execution_when_workspace_already_polluted(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pytest.py").write_text("fake\n", encoding="utf-8")

            result = run_guarded_runtime(
                [sys.executable, "-c", "from pathlib import Path; Path('sync').mkdir(); Path('sync/models.py').write_text('must-not-run')"],
                workspace=root,
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "pre_run_unplanned_artifacts")
            self.assertIn("pytest.py", result["unplanned_paths"])
            self.assertFalse((root / "sync" / "models.py").exists())
            self.assertTrue((root / "pytest.py").exists())

    def test_runtime_guard_python_sentinel_uses_absolute_dictionary_path(self):
        plan = artifact_plan_for_request("修复 sync_node.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync_node.py").write_text("def sync_inventory():\n    pass\n", encoding="utf-8")

            result = run_guarded_runtime(
                ["python3", "-c", "print('sentinel-ok')"],
                workspace=root,
                artifact_plan=plan,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["exit_code"], 0)
            self.assertIn("sentinel-ok", result["stdout"])


if __name__ == "__main__":
    unittest.main()
