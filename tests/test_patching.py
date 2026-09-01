import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.runner import run_task
from onecode.kernel.patching import (
    PatchIntent,
    PatchRejected,
    apply_patch_preview,
    commit_patch,
)
from onecode.kernel.checkpoint import sha256_file


class PatchingTests(unittest.TestCase):
    def test_apply_patch_preview_replaces_unique_block_in_memory_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")

            preview = apply_patch_preview(
                workspace,
                PatchIntent(
                    path="src/mesh.py",
                    search_block="def status():\n    return False",
                    replace_block="def status():\n    return True",
                ),
            )

            self.assertEqual(preview.status, "ready")
            self.assertIn("return True", preview.content)
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return False\n")

    def test_apply_patch_preview_rejects_missing_or_ambiguous_search_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("x = 1\nx = 1\n", encoding="utf-8")

            with self.assertRaisesRegex(PatchRejected, "patch_search_not_found"):
                apply_patch_preview(
                    workspace,
                    PatchIntent(path="src/mesh.py", search_block="missing", replace_block="y = 2"),
                )

            with self.assertRaisesRegex(PatchRejected, "patch_search_ambiguous"):
                apply_patch_preview(
                    workspace,
                    PatchIntent(path="src/mesh.py", search_block="x = 1", replace_block="x = 2"),
                )

            self.assertEqual(target.read_text(encoding="utf-8"), "x = 1\nx = 1\n")

    def test_commit_patch_rejects_python_syntax_error_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")

            result = commit_patch(
                workspace,
                PatchIntent(
                    path="src/mesh.py",
                    search_block="return False",
                    replace_block="return (",
                ),
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "patch_compile_error")
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return False\n")

    def test_commit_patch_writes_valid_preview_through_path_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")
            pre_hash = sha256_file(target)

            result = commit_patch(
                workspace,
                PatchIntent(
                    path="src/mesh.py",
                    search_block="return False",
                    replace_block="return True",
                ),
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["path"], str(target.resolve()))
            self.assertIn("sha256", result)
            self.assertIn("pre_sha256", result)
            self.assertEqual(result["pre_sha256"], pre_hash)
            self.assertEqual(result["post_sha256"], result["sha256"])
            self.assertIn("search_block_sha256", result)
            self.assertIn("replace_block_sha256", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_commit_patch_rejects_path_traversal_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            outside = Path(tmp) / "outside.py"
            outside.write_text("x = 1\n", encoding="utf-8")

            result = commit_patch(
                workspace,
                PatchIntent(path="../outside.py", search_block="x = 1", replace_block="x = 2"),
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "sovereignty_breach")
            self.assertEqual(outside.read_text(encoding="utf-8"), "x = 1\n")

    def test_runner_executes_patch_text_through_ledger_and_path_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")

            result = run_task(
                "patch mesh status",
                workspace=workspace,
                run_id="patch-run",
                intent_type="patch_text",
                patch_path="src/mesh.py",
                search_block="return False",
                replace_block="return True",
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["intent_type"], "patch_text")
            self.assertEqual(result["payload"]["path"], "src/mesh.py")
            self.assertIn("sha256", result["payload"])
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return True\n")

    def test_runner_records_patch_compile_error_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "src" / "mesh.py"
            target.parent.mkdir()
            target.write_text("def status():\n    return False\n", encoding="utf-8")

            result = run_task(
                "patch mesh status",
                workspace=workspace,
                run_id="patch-compile-error",
                intent_type="patch_text",
                patch_path="src/mesh.py",
                search_block="return False",
                replace_block="return (",
            )

            self.assertEqual(result["status"], "halted")
            self.assertEqual(result["reason"], "patch_compile_error")
            self.assertEqual(result["intent_type"], "patch_text")
            self.assertEqual(target.read_text(encoding="utf-8"), "def status():\n    return False\n")

    def test_cli_run_patch_text_passes_patch_fields_to_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch(
                    "onecode.cli.run_task",
                    return_value={"status": "completed", "reason": None},
                ) as run_task_mock,
                patch("onecode.cli.IchingKernel.process_exit_code", return_value=0) as process_exit_code,
                patch("builtins.print"),
            ):
                exit_code = main(
                    [
                        "run",
                        "patch project",
                        "--workspace",
                        tmp,
                        "--run-id",
                        "patch-cli",
                        "--intent-type",
                        "patch_text",
                        "--patch-path",
                        "src/mesh.py",
                        "--search-block",
                        "return False",
                        "--replace-block",
                        "return True",
                    ]
                )

        self.assertEqual(exit_code, 0)
        run_task_mock.assert_called_once()
        _, kwargs = run_task_mock.call_args
        self.assertEqual(kwargs["workspace"], Path(tmp))
        self.assertEqual(kwargs["run_id"], "patch-cli")
        self.assertEqual(kwargs["intent_type"], "patch_text")
        self.assertEqual(kwargs["patch_path"], "src/mesh.py")
        self.assertEqual(kwargs["search_block"], "return False")
        self.assertEqual(kwargs["replace_block"], "return True")
        process_exit_code.assert_called_once_with(status="completed", reason=None)


if __name__ == "__main__":
    unittest.main()
