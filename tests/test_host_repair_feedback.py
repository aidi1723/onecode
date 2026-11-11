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

    def test_tests_directory_repair_asks_for_a_new_test_asset(self) -> None:
        from onecode.kernel.model_provider import ModelPlanAsset
        from onecode.kernel.model_repair import _build_repair_prompt_context, _validate_repair_plan_safety

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "click_like").mkdir()
            (workspace / "click_like" / "options.py").write_text("def parse():\n    return None\n", encoding="utf-8")
            prompt, _span, _cooldown, _code = _build_repair_prompt_context(
                "麻烦只在 tests 下面补一组回归测试，主逻辑先别动。",
                workspace,
                {"status": "halted", "reason": "verifier_failed", "verifier_results": []},
                1,
                {},
                None,
                False,
            )
        self.assertIn("tests/<new_test>.py", prompt)
        self.assertIn("fix the test", prompt)
        self.assertNotIn("Change the implementation so the existing tests pass.", prompt)
        self.assertNotIn("Do NOT include execution_plan or assets.", prompt)
        asset_plan = ModelPlan(
            task="modify tests only",
            assets=[ModelPlanAsset(path="tests/test_options.py", content="import unittest\n")],
        )
        source_plan = ModelPlan(
            task="modify tests only",
            assets=[ModelPlanAsset(path="click_like/options.py", content="def parse():\n    return 1\n")],
        )
        task = "麻烦只在 tests 下面补一组回归测试，主逻辑先别动。"
        self.assertIsNone(_validate_repair_plan_safety(asset_plan, task)[0])
        self.assertEqual(_validate_repair_plan_safety(source_plan, task)[0], "repair_plan_must_use_patches_only")

    def test_a_low_score_on_a_test_only_task_does_not_rewrite_the_implementation(self) -> None:
        from onecode.kernel.model_repair import _build_repair_prompt_context, _task_repair_posture

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            prompt, _span, _cooldown, _code = _build_repair_prompt_context(
                "麻烦只在 tests 下面补一组回归测试，主逻辑先别动。",
                workspace,
                {"status": "halted", "reason": "verifier_failed", "host_reward": 0.18, "verifier_results": []},
                1,
                {},
                None,
                False,
            )
        self.assertNotIn("MACRO-REPLAN", prompt)
        self.assertIn("fix the test", prompt)
        self.assertEqual(_task_repair_posture("implement the parser", 0.18), "macro")

    def test_flat_scores_stop_and_rising_scores_extend_the_budget(self) -> None:
        from onecode.kernel.model_repair import repair_budget_after_score

        extended, flat, stop = repair_budget_after_score(3, 0.5385, 0.9231, 0)
        self.assertEqual(extended, 4)
        self.assertEqual(flat, 0)
        self.assertFalse(stop)

        near_full, _, near_stop = repair_budget_after_score(3, 0.90, 0.92, 0)
        self.assertEqual(near_full, 4)
        self.assertFalse(near_stop)

        capped, _, _ = repair_budget_after_score(5, 0.20, 0.50, 0)
        self.assertEqual(capped, 5)

        from onecode.kernel.model_repair import _micro_line_limit, _validate_repair_plan_safety
        from onecode.kernel.model_provider import ModelPlanPatch

        wide = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="a\n", replace_block="".join(f"x{i} = {i}\n" for i in range(16)))],
        )
        allowed, _ = _validate_repair_plan_safety(wide, "update the implementation", micro_patch=True, micro_line_limit=_micro_line_limit(0.92))
        rejected, _ = _validate_repair_plan_safety(wide, "update the implementation", micro_patch=True, micro_line_limit=_micro_line_limit(0.98))
        self.assertIsNone(allowed)
        self.assertEqual(rejected, "repair_plan_exceeds_micro_patch")

        _, once, still_going = repair_budget_after_score(3, 0.2632, 0.2632, 0)
        self.assertEqual(once, 1)
        self.assertFalse(still_going)
        _, twice, stopped = repair_budget_after_score(3, 0.2632, 0.2632, 1)
        self.assertEqual(twice, 2)
        self.assertTrue(stopped)

        dropped, drop_flat, drop_stop = repair_budget_after_score(3, 0.80, 0.20, 0)
        self.assertEqual(dropped, 3)
        self.assertEqual(drop_flat, 1)
        self.assertFalse(drop_stop)
        _, drop_twice, drop_stopped = repair_budget_after_score(3, 0.80, 0.20, 1)
        self.assertTrue(drop_stopped)

    def test_failure_summary_keeps_a_key_error_and_drops_expected_text(self) -> None:
        from onecode.kernel.model_guidance import sanitize_host_failure_summary

        detail = {
            "tests_passed": 12,
            "tests_total": 13,
            "tests": [
                {"name": "test_policy", "passed": False, "detail": "KeyError: 'effective_date'"},
                {"name": "test_secret", "passed": False, "detail": "expected SECRET_42"},
            ],
        }
        summary = sanitize_host_failure_summary(detail)
        self.assertIn("12/13", summary)
        self.assertIn("[FAIL] test_policy (KeyError: 'effective_date')", summary)
        self.assertIn("[FAIL] test_secret", summary)
        self.assertNotIn("SECRET_42", summary)

    def test_assertion_error_keeps_the_class_and_drops_the_comparison(self) -> None:
        from onecode.kernel.model_guidance import sanitize_host_failure_summary

        detail = {
            "tests_passed": 9,
            "tests_total": 10,
            "tests": [
                {"name": "test_edge", "passed": False, "detail": "AssertionError: 1 != 2"},
                {"name": "test_kind", "passed": False, "detail": "TypeError: expected str"},
            ],
        }
        summary = sanitize_host_failure_summary(detail)
        self.assertIn("[FAIL] test_edge (AssertionError)", summary)
        self.assertIn("[FAIL] test_kind (TypeError)", summary)
        self.assertNotIn("1 != 2", summary)
        self.assertNotIn("expected", summary.lower())

    def test_failure_summary_keeps_call_arguments_and_drops_the_expected_value(self) -> None:
        from onecode.kernel.model_guidance import sanitize_host_failure_summary

        detail = {
            "tests_passed": 11,
            "tests_total": 12,
            "tests": [
                {
                    "name": "test_header",
                    "passed": False,
                    "detail": "AssertionError: set('Bad:Name', 'x') expected 'reject'",
                },
                {
                    "name": "test_secret",
                    "passed": False,
                    "args": ["SECRET_42"],
                    "detail": "expected SECRET_42",
                },
            ],
        }
        summary = sanitize_host_failure_summary(detail)
        self.assertIn("[FAIL] test_header (AssertionError) args set('Bad:Name', 'x')", summary)
        self.assertNotIn("reject", summary)
        self.assertNotIn("SECRET_42", summary)
        self.assertNotIn("expected", summary.lower())

    def _run_scripted_repair(self, start: str, decision: str, plans: list[ModelPlan], budget: int = 4) -> tuple[dict, list[str], Path]:
        from onecode.kernel.model_repair import _finish_verified_task

        root = Path(tempfile.mkdtemp())
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "app.py").write_text(start, encoding="utf-8")
        verifier = root / "verifier.py"
        verifier.write_text(
            "import json, os\n"
            "from pathlib import Path\n"
            "workspace = Path(os.environ['WORKSPACE'])\n"
            "log_dir = Path(os.environ['LOG_DIR'])\n"
            "text = (workspace / 'app.py').read_text(encoding='utf-8')\n"
            f"{decision}\n"
            "tests = []\n"
            "for i in range(total):\n"
            "    ok = i < passed\n"
            "    detail = '' if ok else 'AssertionError: 1 != 2'\n"
            "    tests.append({'name': 'case_%s' % i, 'passed': ok, 'detail': detail})\n"
            "score = passed / total\n"
            "report = {'overall': score, 'tests_passed': passed, 'tests_total': total, 'tests': tests}\n"
            "(log_dir / 'reward.json').write_text(json.dumps(report))\n"
            "(log_dir / 'reward.txt').write_text(str(score) + '\\n')\n",
            encoding="utf-8",
        )
        prompts: list[str] = []
        queued = list(plans)

        def _plan(*_args, task: str, **_kwargs):
            prompts.append(task)
            return queued.pop(0), None

        def _execute(plan, **kwargs):
            target = kwargs["workspace"] / "app.py"
            target.write_text(plan.patches[0].replace_block, encoding="utf-8")
            return {"status": "completed", "reason": None, "assets": []}

        with patch("onecode.kernel.model_planning.traced_provider_plan_retrying", side_effect=_plan), \
             patch("onecode.kernel.model_planning.execute_model_plan", side_effect=_execute):
            result = _finish_verified_task(
                {"status": "completed", "reason": None, "run_id": "scripted"},
                "update the implementation",
                workspace,
                None,
                budget,
                object(),
                object(),
                workspace / "trace.jsonl",
                object(),
                "test-model",
                30.0,
                {"safe_agent": {}},
                "scripted",
                None,
                {"bureau_turn_budget": budget, "host_verifier_path": str(verifier)},
                False,
                None,
                None,
            )
        return result, prompts, workspace

    def test_a_score_drop_restores_the_best_file_and_stops(self) -> None:
        bad = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="GOOD\n", replace_block="BAD\n")],
        )
        result, prompts, workspace = self._run_scripted_repair(
            "GOOD\n",
            "passed, total = (4, 5) if 'GOOD' in text else (1, 5)",
            [bad, bad, bad, bad],
        )
        self.assertEqual(result.get("host_reward"), 0.8)
        self.assertEqual((workspace / "app.py").read_text(encoding="utf-8"), "GOOD\n")
        self.assertEqual(len(prompts), 2)
        self.assertIn("GOOD", prompts[1])
        self.assertNotIn("BAD", prompts[1])
        self.assertNotIn("1 != 2", "\n".join(prompts))

    def test_a_rising_score_does_not_claim_the_repair_stalled(self) -> None:
        step = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="VALUE = 0\n", replace_block="STEP\n")],
        )
        done = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="STEP\n", replace_block="FIXED\n")],
        )
        result, prompts, _workspace = self._run_scripted_repair(
            "VALUE = 0\n",
            "passed, total = (2, 2) if 'FIXED' in text else ((7, 10) if 'STEP' in text else (1, 2))",
            [step, done],
            budget=3,
        )
        self.assertEqual(result.get("host_reward"), 1.0)
        self.assertEqual(len(prompts), 2)
        self.assertNotIn("STALLED PROGRESS", prompts[1])
        self.assertNotIn("STALLED MICRO", prompts[1])

    def test_low_score_asks_for_a_rewrite_and_high_score_rejects_a_wide_patch(self) -> None:
        rewrite = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="return 0\n", replace_block="return 1\nFIXED = 1\n")],
        )
        low, low_prompts, _workspace = self._run_scripted_repair(
            "def compute():\n    return 0\n",
            "passed, total = (1, 1) if 'FIXED' in text else (1, 4)",
            [rewrite],
        )
        self.assertEqual(low.get("host_reward"), 1.0)
        self.assertIn("MACRO-REPLAN", low_prompts[0])
        self.assertNotIn("MICRO-PATCH ONLY", low_prompts[0])

        wide = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="VALUE = 0\n", replace_block="".join(f"x{i} = {i}\n" for i in range(41)))],
        )
        narrow = ModelPlan(
            task="repair",
            patches=[ModelPlanPatch(path="app.py", search_block="VALUE = 0\n", replace_block="VALUE = 0\nFIXED = 1\n")],
        )
        high, high_prompts, _workspace = self._run_scripted_repair(
            "VALUE = 0\n",
            "passed, total = (1, 1) if 'FIXED' in text else (9, 10)",
            [wide, narrow],
        )
        self.assertEqual(high.get("host_reward"), 1.0)
        self.assertIn("MICRO-PATCH ONLY", high_prompts[0])
        self.assertIn("repair_plan_exceeds_micro_patch", high_prompts[1])
        self.assertNotIn("1 != 2", "\n".join(high_prompts))


if __name__ == "__main__":
    unittest.main()
