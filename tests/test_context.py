import tempfile
import unittest
from pathlib import Path

from onecode.kernel.context import OneCodeContext, create_context
from onecode.kernel.hexagram import BUILD_ENTRY


class ContextTests(unittest.TestCase):
    def test_create_context_initializes_run_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            resolved_workspace = workspace.resolve()
            context = create_context(workspace_root=workspace, http_timeout_seconds=60, run_id="run-test")

            self.assertIsInstance(context, OneCodeContext)
            self.assertEqual(context.run_id, "run-test")
            self.assertEqual(context.workspace_root, resolved_workspace)
            self.assertEqual(context.state, BUILD_ENTRY)
            self.assertEqual(context.turn_index, 0)
            self.assertEqual(context.evidence_root, resolved_workspace / ".onecode" / "runs" / "run-test")
            self.assertEqual(context.manifest_path, context.evidence_root / "manifest.json")
            self.assertTrue((context.evidence_root / "checkpoints").is_dir())

    def test_rejects_non_positive_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                create_context(workspace_root=Path(tmp), http_timeout_seconds=0, run_id="bad")


if __name__ == "__main__":
    unittest.main()
