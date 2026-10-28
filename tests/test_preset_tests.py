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
        for path in ("tests/test_fee.py", "Tests/test_pay.py", "tests\\test_win.py", "tests", ".//tests/test_pay.py", "/tests/test_pay.py", "tests/../tests/test_pay.py"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError) as caught:
                    validate_model_plan(
                        {
                            "task": "keep the preset test",
                            "assets": [{"path": path, "content": "VALUE = 2\n"}],
                        }
                    )
                self.assertIn("tests/", str(caught.exception))
        for path in ("tests/test_fee.py", "Tests/test_pay.py", ".//tests/test_pay.py"):
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
        for path in ("tests/test_fee.py", ".//tests/test_pay.py"):
            with self.subTest(execution_step_path=path):
                with self.assertRaises(ValueError) as caught:
                    validate_model_plan(
                        {
                            "task": "hack via execution step",
                            "execution_plan": {
                                "steps": [
                                    {
                                        "id": "step-1",
                                        "description": "write test",
                                        "tool_calls": [
                                            {"tool_name": "write_text", "params": {"path": path, "content": "x = 1"}}
                                        ],
                                    }
                                ]
                            },
                        }
                    )
                self.assertIn("tests/", str(caught.exception))

    def test_plan_rejects_assets_importing_unittest_or_calling_exit(self):
        with self.assertRaises(ValueError) as caught:
            validate_model_plan(
                {
                    "task": "bad asset import",
                    "assets": [{"path": "src/bad.py", "content": "import unittest\n"}],
                }
            )
        self.assertIn("must not import unittest", str(caught.exception))

        with self.assertRaises(ValueError) as caught:
            validate_model_plan(
                {
                    "task": "bad dynamic import",
                    "assets": [{"path": "src/bad.py", "content": "u=__import__('unittest')\n"}],
                }
            )
        self.assertIn("must not import unittest", str(caught.exception))

        with self.assertRaises(ValueError) as caught:
            validate_model_plan(
                {
                    "task": "bad asset exit",
                    "assets": [{"path": "src/bad.py", "content": "import os\nos._exit(0)\n"}],
                }
            )
        self.assertIn("must not call _exit", str(caught.exception))

    def test_a_new_test_file_is_allowed_when_it_is_not_in_the_baseline(self):
        plan = validate_model_plan(
            {
                "task": "add a regression",
                "assets": [{"path": "tests/test_router.py", "content": "import unittest\n"}],
            },
            existing_preset_tests=set(),
        )
        self.assertEqual(plan.assets[0].path, "tests/test_router.py")
        with self.assertRaisesRegex(ValueError, "paths under tests/ are protected"):
            validate_model_plan(
                {
                    "task": "rewrite a preset test",
                    "assets": [{"path": "tests/test_fee.py", "content": "import unittest\n"}],
                },
                existing_preset_tests={"tests/test_fee.py"},
            )

    def test_adding_a_test_file_does_not_count_as_rewriting_the_baseline(self):
        from onecode.kernel.preset_tests import preset_test_baseline_changed

        before = {"tests/test_fee.py": "abc"}
        current = {"tests/test_fee.py": "abc", "tests/test_router.py": "def"}
        self.assertFalse(preset_test_baseline_changed(before, current))
        self.assertTrue(preset_test_baseline_changed(before, {"tests/test_fee.py": "changed"}))

    def test_preset_test_mismatch_uses_the_existing_verifier_halt(self):
        code = IchingKernel.classify_outcome("halted", "verifier_failed")
        self.assertEqual(code, IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))

    def test_verify_shell_write_skips_a_repository_with_no_unittest_collection(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            (workspace / "app").mkdir()
            (workspace / "app" / "policy.py").write_text("def allow():\n    return False\n", encoding="utf-8")
            original = {"status": "completed", "delivery_status": "deliverable", "reason": None}
            empty = SimpleNamespace(status="skipped", reason="no_unittest_collected")
            with patch(
                "onecode.kernel.verifier.run_two_stage_verifier",
                return_value=(empty, []),
            ):
                result = verify_shell_write(original, workspace)
        self.assertEqual(result["delivery_status"], "deliverable")
        self.assertEqual(result["status"], "completed")

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

    def test_verify_shell_write_records_blocked_tamper_attempt_and_preserves_authoritative_baseline(self):
        from onecode.kernel.preset_tests import authoritative_preset_test_hashes
        from onecode.kernel.run_inspection import read_global_wal_entries

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
            test_file.write_text("ORIGINAL = 1\n", encoding="utf-8")
            before = preset_test_hashes(workspace)
            # Run 1: Normal verified run records baseline
            r1 = run_task("write src/a.py", workspace=workspace, run_id="r1", write_path="src/a.py", write_content="A=1\n")
            with patch("onecode.kernel.verifier.run_verifier", return_value=passed):
                verify_shell_write(r1, workspace, before)

            # Now tamper with tests/test_fee.py
            test_file.write_text("TAMPERED = 2\n", encoding="utf-8")
            r2 = run_task("write src/b.py", workspace=workspace, run_id="r2", write_path="src/b.py", write_content="B=2\n")
            blocked = verify_shell_write(r2, workspace, before)
            self.assertEqual(blocked["status"], "halted")
            self.assertEqual(blocked["delivery_status"], "blocked")

            # Blocked attempt must be recorded in WAL
            entries, _, _ = read_global_wal_entries(workspace)
            r2_entry = next((e for e in reversed(entries) if e.get("rid") == "r2"), None)
            self.assertIsNotNone(r2_entry)
            self.assertEqual(r2_entry["st"], "halted")

            # Authoritative test hashes must still reflect ORIGINAL, not TAMPERED
            auth = authoritative_preset_test_hashes(workspace)
            self.assertEqual(auth["tests/test_fee.py"], hashlib.sha256(b"ORIGINAL = 1\n").hexdigest())

            # ledger_matches_workspace must catch the discrepancy
            self.assertEqual(ledger_matches_workspace(workspace), "preset_test_hash_mismatch")


if __name__ == "__main__":
    unittest.main()
