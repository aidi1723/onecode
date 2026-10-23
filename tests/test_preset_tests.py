import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.model_provider import validate_model_plan
from onecode.kernel.preset_tests import preset_test_hashes
from onecode.kernel.run_inspection import ledger_matches_workspace
from onecode.kernel.runner import run_task
from onecode.kernel.verifier import VerifierResult
from onecode.web.api import verify_shell_write


class PresetTestGuardTests(unittest.TestCase):
    def test_preset_test_hash_changes_when_the_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "tests" / "test_fee.py"
            target.parent.mkdir()
            target.write_text("VALUE = 1\n", encoding="utf-8")
            before = preset_test_hashes(root)
            target.write_text("VALUE = 2\n", encoding="utf-8")
            self.assertNotEqual(before, preset_test_hashes(root))
            self.assertEqual(before["tests/test_fee.py"], hashlib.sha256(b"VALUE = 1\n").hexdigest())

    def test_a_plan_that_writes_under_tests_is_invalid(self):
        for path in ("tests/test_fee.py", "Tests/test_pay.py", "tests\\test_win.py", "tests"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError) as caught:
                    validate_model_plan(
                        {
                            "task": "keep the preset test",
                            "assets": [{"path": path, "content": "VALUE = 2\n"}],
                        }
                    )
                self.assertIn("tests/", str(caught.exception))
        for path in ("tests/test_fee.py", "Tests/test_pay.py"):
            with self.subTest(patch_path=path):
                with self.assertRaises(ValueError) as caught:
                    validate_model_plan(
                        {
                            "task": "keep the preset test",
                            "patches": [
                                {
                                    "path": path,
                                    "search_block": "VALUE = 1\n",
                                    "replace_block": "VALUE = 2\n",
                                }
                            ],
                        }
                    )
                self.assertIn("tests/", str(caught.exception))

    def test_preset_test_mismatch_uses_the_existing_verifier_halt(self):
        code = IchingKernel.classify_outcome("halted", "verifier_failed")
        self.assertEqual(code, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))

    def test_verify_shell_write_blocks_delivery_when_preset_test_changes_without_running_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            test_file = workspace / "tests" / "test_fee.py"
            test_file.parent.mkdir()
            test_file.write_text("VALUE = 1\n", encoding="utf-8")
            before = preset_test_hashes(workspace)
            test_file.write_text("VALUE = 2\n", encoding="utf-8")
            with patch("onecode.kernel.verifier.run_verifier") as mocked_verifier:
                blocked = verify_shell_write(
                    {"status": "completed", "delivery_status": "deliverable"},
                    workspace,
                    before,
                )
            mocked_verifier.assert_not_called()
            self.assertEqual(blocked["status"], "halted")
            self.assertEqual(blocked["reason"], "verifier_failed")
            self.assertEqual(blocked["delivery_status"], "blocked")
            self.assertTrue(blocked["preset_tests_changed"])

    def test_verify_shell_write_records_preset_test_hashes_for_ledger_check(self):
        passed = VerifierResult(
            id="python-unittest",
            status="passed",
            reason=None,
            failure_kind=None,
            exit_code=0,
            duration_ms=1,
            stdout_tail="OK",
            stderr_tail="",
            stdout_sha256="0" * 64,
            stderr_sha256="0" * 64,
            cwd=".",
            command=["python3", "-m", "unittest"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            test_file = workspace / "tests" / "test_fee.py"
            test_file.parent.mkdir()
            test_file.write_text("import unittest\n", encoding="utf-8")
            before = preset_test_hashes(workspace)
            result = run_task(
                "write src/fee.py",
                workspace=workspace,
                run_id="verified-fee",
                write_path="src/fee.py",
                write_content="RATE = 8\n",
            )
            with patch("onecode.kernel.verifier.run_verifier", return_value=passed):
                verified = verify_shell_write(result, workspace, before)
            self.assertEqual(verified["delivery_status"], "deliverable")
            self.assertIsNone(ledger_matches_workspace(workspace))
            test_file.write_text("import unittest\n# changed\n", encoding="utf-8")
            self.assertEqual(ledger_matches_workspace(workspace), "preset_test_hash_mismatch")

    def test_verify_shell_write_runs_targeted_verifier_for_modified_file(self):
        from onecode.kernel.runner import run_task
        from onecode.kernel.verifier import VerifierResult
        from onecode.web.api import verify_shell_write

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_fee.py").write_text("import unittest\n", encoding="utf-8")
            before = preset_test_hashes(workspace)
            result = run_task(
                "write src/fee.py",
                workspace=workspace,
                run_id="verified-targeted-fee",
                write_path="src/fee.py",
                write_content="RATE = 8\n",
            )

            runs: list[str] = []

            def fake_run(ws, spec, **kwargs):
                runs.append(spec.id)
                return VerifierResult(
                    id=spec.id,
                    status="passed",
                    reason=None,
                    failure_kind=None,
                    exit_code=0,
                    duration_ms=10,
                    stdout_tail="OK",
                    stderr_tail="",
                    stdout_sha256="",
                    stderr_sha256="",
                    cwd=".",
                    command=spec.command,
                )

            with patch("onecode.kernel.verifier.run_verifier", side_effect=fake_run):
                verified = verify_shell_write(result, workspace, before)

            self.assertEqual(verified["delivery_status"], "deliverable")
            self.assertEqual(runs, ["python-unittest-targeted", "python-unittest"])


if __name__ == "__main__":
    unittest.main()
