import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.checkpoint import sha256_file
from onecode.kernel.resumption import ReadyAsset, ResumeState, load_resume_state


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


if __name__ == "__main__":
    unittest.main()
