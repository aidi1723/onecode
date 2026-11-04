import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.model_provider import ModelPlan, ModelPlanPatch


class HostRepairFeedbackTests(unittest.TestCase):
    def test_sanitized_summary_keeps_the_failing_name_and_drops_expected_text(self) -> None:
        from onecode.kernel.model_guidance import sanitize_host_failure_summary

        detail = {
            "tests_passed": 0,
            "tests_total": 1,
            "tests": [
                {
                    "name": "marker",
                    "passed": False,
                    "detail": "expected SECRET_42 got None",
                }
            ],
        }
        summary = sanitize_host_failure_summary(detail)
        self.assertIn("marker", summary)
        self.assertIn("[FAIL]", summary)
        self.assertNotIn("SECRET_42", summary)
        self.assertNotIn("expected", summary.lower())

    def test_external_host_grade_repairs_without_copying_the_verifier(self) -> None:
        from onecode.kernel.model_repair import _finish_verified_task

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "app.py").write_text("VALUE = 0\n", encoding="utf-8")
            verifier = root / "verifier.py"
            verifier.write_text(
                "import json, os\n"
                "from pathlib import Path\n"
                "workspace = Path(os.environ['WORKSPACE'])\n"
                "log_dir = Path(os.environ['LOG_DIR'])\n"
                "text = (workspace / 'app.py').read_text(encoding='utf-8')\n"
                "ok = 'FIXED' in text\n"
                "tests = [{'name': 'marker', 'passed': ok, 'detail': 'expected SECRET_42'}]\n"
                "if not ok:\n"
                "    tests.append({'name': 'kept', 'passed': True})\n"
                "passed = 1 if ok else 1\n"
                "total = 1 if ok else 2\n"
                "report = {\n"
                "    'overall': 1.0 if ok else 0.5,\n"
                "    'tests_passed': passed,\n"
                "    'tests_total': total,\n"
                "    'tests': tests,\n"
                "}\n"
                "(log_dir / 'reward.json').write_text(json.dumps(report))\n"
                "(log_dir / 'reward.txt').write_text(('1.0' if ok else '0.5') + '\\n')\n",
                encoding="utf-8",
            )
            prompts: list[str] = []

            def _plan(*_args, task: str, **_kwargs):
                prompts.append(task)
                plan = ModelPlan(
                    task="repair",
                    patches=[
                        ModelPlanPatch(
                            path="app.py",
                            search_block="VALUE = 0\n",
                            replace_block="VALUE = 0\nFIXED = 1\n",
                        )
                    ],
                )
                return plan, None

            def _execute(_plan, **kwargs):
                target = kwargs["workspace"] / "app.py"
                target.write_text("VALUE = 0\nFIXED = 1\n", encoding="utf-8")
                return {"status": "completed", "reason": None, "assets": []}

            with patch("onecode.kernel.model_planning.traced_provider_plan_retrying", side_effect=_plan), \
                 patch("onecode.kernel.model_planning.execute_model_plan", side_effect=_execute):
                result = _finish_verified_task(
                    {"status": "completed", "reason": None, "run_id": "host-repair"},
                    "update the implementation",
                    workspace,
                    None,
                    2,
                    object(),
                    object(),
                    workspace / "trace.jsonl",
                    object(),
                    "test-model",
                    30.0,
                    {"safe_agent": {}},
                    "host-repair",
                    None,
                    {"bureau_turn_budget": 2, "host_verifier_path": str(verifier)},
                    False,
                    None,
                    None,
                )
            self.assertEqual(result.get("host_reward"), 1.0)
            self.assertGreaterEqual(result.get("repair_attempt_count", 0), 1)
            self.assertTrue(prompts)
            self.assertNotIn("SECRET_42", "\n".join(prompts))
            self.assertIn("marker", "\n".join(prompts))
            self.assertFalse((workspace / "verifier.py").exists())
            self.assertNotIn("SECRET_42", (workspace / "app.py").read_text(encoding="utf-8"))

    def test_safety_rejection_restores_the_higher_scoring_snapshot(self) -> None:
        from onecode.kernel.model_repair import _deliver_best_repair, _snapshot_workspace_files

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("GOOD\n", encoding="utf-8")
            snapshot = _snapshot_workspace_files(workspace)
            (workspace / "app.py").write_text("DAMAGED\n", encoding="utf-8")
            delivered = _deliver_best_repair(
                workspace,
                {"status": "halted", "reason": "repair_plan_cannot_modify_protected_files", "host_reward": 0.1429},
                {"status": "completed", "reason": None, "host_reward": 1.0},
                snapshot,
            )
            self.assertEqual((workspace / "app.py").read_text(encoding="utf-8"), "GOOD\n")
            self.assertEqual(delivered["host_reward"], 1.0)
            self.assertEqual(delivered["status"], "completed")
            self.assertFalse(delivered.get("partial"))

    def test_partial_host_score_stays_completed(self) -> None:
        from onecode.kernel.model_repair import _deliver_best_repair, _snapshot_workspace_files

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "app.py").write_text("PARTIAL\n", encoding="utf-8")
            snapshot = _snapshot_workspace_files(workspace)
            delivered = _deliver_best_repair(
                workspace,
                {"status": "halted", "reason": "verifier_failed", "host_reward": 0.7692},
                {"status": "halted", "reason": "verifier_failed", "host_reward": 0.7692},
                snapshot,
            )
            self.assertEqual(delivered["status"], "completed")
            self.assertTrue(delivered["partial"])
            self.assertEqual(delivered["verifier_status"], "partial")
            self.assertEqual(delivered["host_reward"], 0.7692)
            self.assertEqual((workspace / "app.py").read_text(encoding="utf-8"), "PARTIAL\n")

    def test_testing_repair_prompt_forbids_source_edits(self) -> None:
        from onecode.kernel.model_repair import _build_repair_prompt_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tests").mkdir()
            prompt, _span, _cooldown, _code = _build_repair_prompt_context(
                "只补测试。不要改 formatting.py",
                workspace,
                {"status": "halted", "reason": "verifier_failed", "verifier_results": []},
                1,
                {},
                None,
                False,
            )
        self.assertIn("Modify tests only", prompt)
        self.assertIn("formatting.py", prompt)
        self.assertNotIn("Change the implementation so the existing tests pass.", prompt)


if __name__ == "__main__":
    unittest.main()
