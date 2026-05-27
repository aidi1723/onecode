import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file
from onecode.kernel.context import create_context
from onecode.kernel.resumption import ReadyAsset, ResumeState, load_resume_state
from onecode.kernel.runner import run_task


class ResumptionSkeletonTests(unittest.TestCase):
    def test_missing_manifest_returns_empty_resume_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = load_resume_state(Path(tmp), "missing-run")

            self.assertIsInstance(state, ResumeState)
            self.assertEqual(state.source_run_id, "missing-run")
            self.assertEqual(state.ready_assets, {})

    def test_ready_asset_records_source_metadata(self):
        asset = ReadyAsset(
            path="src/a.py",
            sha256="abc123",
            source_run_id="run-1",
            source_turn_index=2,
        )

        self.assertEqual(asset.path, "src/a.py")
        self.assertEqual(asset.sha256, "abc123")
        self.assertEqual(asset.source_run_id, "run-1")
        self.assertEqual(asset.source_turn_index, 2)


class ResumeManifestAuditTests(unittest.TestCase):
    def test_audit_load_valid_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            asset = workspace / "src" / "a.py"
            asset.parent.mkdir(parents=True)
            asset.write_text("x = 1\n", encoding="utf-8")
            asset_hash = sha256_file(asset)

            run_root = workspace / ".onecode" / "runs" / "source-run"
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir(parents=True)
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(asset), "sha256": asset_hash},
                    }
                ),
                encoding="utf-8",
            )
            (run_root / "manifest.json").write_text(
                json.dumps({"run_id": "source-run", "checkpoints": [{"path": str(checkpoint_path)}]}),
                encoding="utf-8",
            )

            state = load_resume_state(workspace, "source-run")

            self.assertIn("src/a.py", state.ready_assets)
            ready = state.ready_assets["src/a.py"]
            self.assertEqual(ready.sha256, asset_hash)
            self.assertEqual(ready.source_run_id, "source-run")
            self.assertEqual(ready.source_turn_index, 1)

    def test_audit_ignores_mismatched_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            asset = workspace / "src" / "bad.py"
            asset.parent.mkdir(parents=True)
            asset.write_text("changed\n", encoding="utf-8")

            run_root = workspace / ".onecode" / "runs" / "source-run"
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir(parents=True)
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(asset), "sha256": "wrong"},
                    }
                ),
                encoding="utf-8",
            )
            (run_root / "manifest.json").write_text(
                json.dumps({"run_id": "source-run", "checkpoints": [{"path": str(checkpoint_path)}]}),
                encoding="utf-8",
            )

            state = load_resume_state(workspace, "source-run")

            self.assertEqual(state.ready_assets, {})


class ResumeContextLifecycleTests(unittest.TestCase):
    def test_context_automatically_loads_resume_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            asset = workspace / "src" / "ready.py"
            asset.parent.mkdir(parents=True)
            asset.write_text("ready = True\n", encoding="utf-8")
            asset_hash = sha256_file(asset)

            run_root = workspace / ".onecode" / "runs" / "old_run_123"
            checkpoint_path = run_root / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir(parents=True)
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(asset), "sha256": asset_hash},
                    }
                ),
                encoding="utf-8",
            )
            (run_root / "manifest.json").write_text(
                json.dumps({"run_id": "old_run_123", "checkpoints": [{"path": str(checkpoint_path)}]}),
                encoding="utf-8",
            )

            context = create_context(
                workspace_root=workspace,
                http_timeout_seconds=60,
                run_id="retry-run",
                resume_from_run_id="old_run_123",
            )

            self.assertEqual(context.resume_from_run_id, "old_run_123")
            self.assertIsNotNone(context.resume_state)
            self.assertIn("src/ready.py", context.resume_state.ready_assets)
            self.assertEqual(context.resume_state.ready_assets["src/ready.py"].sha256, asset_hash)


class ResumeSkipRuleTests(unittest.TestCase):
    def test_runner_skips_ready_asset_and_writes_missing_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ready_asset = workspace / "src" / "mesh.py"
            ready_asset.parent.mkdir(parents=True)
            ready_asset.write_text("mesh = 'ready'\n", encoding="utf-8")
            ready_hash = sha256_file(ready_asset)

            old_run = workspace / ".onecode" / "runs" / "old-run"
            checkpoint_path = old_run / "checkpoints" / "0001.json"
            checkpoint_path.parent.mkdir(parents=True)
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(ready_asset), "sha256": ready_hash},
                    }
                ),
                encoding="utf-8",
            )
            (old_run / "manifest.json").write_text(
                json.dumps({"run_id": "old-run", "checkpoints": [{"path": str(checkpoint_path)}]}),
                encoding="utf-8",
            )

            skipped = run_task(
                "resume ready mesh",
                workspace=workspace,
                run_id="retry-ready",
                resume_from_run_id="old-run",
                write_path="src/mesh.py",
                write_content="mesh = 'should not overwrite'\n",
            )

            self.assertEqual(skipped["status"], "skipped")
            self.assertEqual(skipped["reason"], "resumed_asset_ready")
            self.assertTrue(skipped["resumed"])
            self.assertEqual(skipped["sha256"], ready_hash)
            self.assertEqual(ready_asset.read_text(encoding="utf-8"), "mesh = 'ready'\n")
            skipped_manifest = json.loads(Path(skipped["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(skipped_manifest["checkpoints"][0]["status"], "skipped")

            written = run_task(
                "resume missing test",
                workspace=workspace,
                run_id="retry-missing",
                resume_from_run_id="old-run",
                write_path="tests/test_mesh.py",
                write_content="def test_mesh():\n    assert True\n",
            )

            missing_asset = workspace / "tests" / "test_mesh.py"
            self.assertEqual(written["status"], "completed")
            self.assertFalse(written["resumed"])
            self.assertTrue(missing_asset.exists())
            self.assertEqual(missing_asset.read_text(encoding="utf-8"), "def test_mesh():\n    assert True\n")


if __name__ == "__main__":
    unittest.main()
