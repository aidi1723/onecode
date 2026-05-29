import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_orchestrator import artifact_plan_for_request
from agent_skill_dictionary.build_mode_sovereignty import (
    audit_environment_gate,
    audit_workspace_sovereignty,
)


class BuildModeSovereigntyTest(unittest.TestCase):
    def test_environment_gate_reports_missing_required_packages(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")

        with tempfile.TemporaryDirectory() as tmp:
            report = audit_environment_gate(plan, python_executable=Path(tmp) / "missing-python")

        self.assertFalse(report.ok)
        self.assertEqual(report.action, "halt_missing_environment")
        self.assertIn("fastapi", report.missing_packages)
        self.assertIn("sqlmodel", report.missing_packages)
        self.assertIn("pytest_asyncio", report.missing_packages)

    def test_workspace_audit_rejects_unplanned_dependency_shims(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync").mkdir()
            (root / "sync" / "models.py").write_text("ok\n", encoding="utf-8")
            (root / "fastapi").mkdir()
            (root / "fastapi" / "__init__.py").write_text("fake\n", encoding="utf-8")
            (root / "pytest.py").write_text("fake\n", encoding="utf-8")

            report = audit_workspace_sovereignty(root, plan)

        self.assertFalse(report.ok)
        self.assertEqual(report.action, "reject_unplanned_workspace_artifacts")
        self.assertIn("fastapi/__init__.py", report.unplanned_paths)
        self.assertIn("pytest.py", report.unplanned_paths)
        self.assertNotIn("sync/models.py", report.unplanned_paths)

    def test_workspace_audit_allows_required_artifacts_and_support_files(self):
        plan = artifact_plan_for_request("实现 cluster-state-sync")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                "sync/__init__.py",
                "api/__init__.py",
                "tests/__init__.py",
                "sync/models.py",
                "sync/engine.py",
                "api/server.py",
                "tests/test_sync.py",
                "README.md",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            report = audit_workspace_sovereignty(root, plan)

        self.assertTrue(report.ok)
        self.assertEqual(report.unplanned_paths, ())

    def test_workspace_audit_allows_secure_b2b_fixture_files(self):
        plan = artifact_plan_for_request("修复 sync_node.py 同步死锁 Bug")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                "auth.py",
                "ledger.json",
                "ledger.py",
                "main.py",
                "pyproject.toml",
                "requirements.txt",
                "sync_node.py",
                "tests/test_sync.py",
                "warehouse_snapshot.json",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            report = audit_workspace_sovereignty(root, plan)

        self.assertTrue(report.ok)
        self.assertEqual(report.unplanned_paths, ())

    def test_workspace_audit_ignores_nested_python_bytecode_cache(self):
        plan = artifact_plan_for_request("修复 sync_node.py 同步死锁 Bug")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sync_node.py").write_text("def sync_inventory():\n    pass\n", encoding="utf-8")
            cache = root / "tests" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "test_sync.cpython-312.pyc").write_bytes(b"cache")

            report = audit_workspace_sovereignty(root, plan)

        self.assertTrue(report.ok)
        self.assertEqual(report.unplanned_paths, ())


if __name__ == "__main__":
    unittest.main()
