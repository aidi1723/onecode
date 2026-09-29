import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.hexagram import IchingKernel
from onecode.kernel.iching_encoding import RULE_SCHEMA_V2

class BenchmarkTests(unittest.TestCase):
    def test_load_benchmark_task_requires_id_prompt_and_expected_status(self):
        from onecode.benchmark import load_benchmark_task

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "write-file-basic",
                        "prompt": "写 hello.txt",
                        "expected_status": "completed",
                        "assertions": [{"type": "file_exists", "path": "hello.txt"}],
                    }
                ),
                encoding="utf-8",
            )
            task = load_benchmark_task(path)

        self.assertEqual(task.id, "write-file-basic")
        self.assertEqual(task.expected_status, "completed")

    def test_score_benchmark_result_checks_expected_status(self):
        from onecode.benchmark import BenchmarkTask, score_benchmark_result

        task = BenchmarkTask(
            id="task-1",
            prompt="demo",
            expected_status="completed",
            assertions=[],
        )

        score = score_benchmark_result(task, {"status": "completed"}, Path.cwd())

        self.assertTrue(score.passed)

    def test_score_benchmark_result_checks_file_assertions(self):
        from onecode.benchmark import BenchmarkTask, score_benchmark_result

        task = BenchmarkTask(
            id="task-1",
            prompt="demo",
            expected_status="completed",
            assertions=[{"type": "file_exists", "path": "hello.txt"}],
        )

        with tempfile.TemporaryDirectory() as tmp:
            score = score_benchmark_result(task, {"status": "completed"}, Path(tmp))

        self.assertFalse(score.passed)
        self.assertIn("missing expected file: hello.txt", score.failures)

    def test_cli_benchmark_lists_loaded_tasks(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = Path(tmp) / "tasks"
            tasks_dir.mkdir()
            (tasks_dir / "task.json").write_text(
                json.dumps(
                    {
                        "id": "task-1",
                        "prompt": "demo",
                        "expected_status": "completed",
                        "assertions": [],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(["benchmark", "--tasks-dir", str(tasks_dir)])

            result = json.loads(print_mock.call_args.args[0])

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["tasks"][0]["id"], "task-1")

    def test_run_benchmark_tasks_executes_rule_tasks_and_writes_report(self):
        from onecode.benchmark import load_benchmark_tasks, run_benchmark_tasks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks_dir = root / "tasks"
            tasks_dir.mkdir()
            report_path = root / "report.json"
            (tasks_dir / "write.json").write_text(
                json.dumps(
                    {
                        "id": "write-file-basic",
                        "prompt": "write hello",
                        "expected_status": "completed",
                        "mode": "rule",
                        "input": {
                            "write_path": "hello.txt",
                            "write_content": "hello onecode\n"
                        },
                        "assertions": [
                            {"type": "file_exists", "path": "hello.txt"}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_benchmark_tasks(
                load_benchmark_tasks(tasks_dir),
                workspace_root=root / "workspaces",
                report_path=report_path,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["rule_schema"], RULE_SCHEMA_V2)
        self.assertEqual(report["rule_schema"], RULE_SCHEMA_V2)
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["passed_count"], 1)
        self.assertEqual(report["scores"][0]["task_id"], "write-file-basic")
        self.assertEqual(result["entries"][0]["result"]["shell_projection"]["run_id"], "benchmark-write-file-basic")
        self.assertEqual(result["entries"][0]["result"]["shell_projection"]["severity"], "ok")
        self.assertEqual(report["entries"][0]["result"]["shell_projection"]["severity"], "ok")
        benchmark_result = result["entries"][0]["result"]
        self.assertEqual(
            benchmark_result["assets"][0]["balance_mutation"],
            IchingKernel.balance_mutation_evidence(
                benchmark_result["assets"][0]["raw_status_code"],
                benchmark_result["assets"][0]["balanced_status_code"],
            ),
        )
        self.assertEqual(benchmark_result["balance_mutation_summary"]["asset_count"], 1)

    def test_cli_benchmark_run_writes_report(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks_dir = root / "tasks"
            tasks_dir.mkdir()
            report_path = root / "report.json"
            (tasks_dir / "noop.json").write_text(
                json.dumps(
                    {
                        "id": "noop",
                        "prompt": "noop",
                        "expected_status": "completed",
                        "mode": "rule",
                        "input": {},
                        "assertions": [],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "benchmark",
                        "--tasks-dir",
                        str(tasks_dir),
                        "--run",
                        "--workspace-root",
                        str(root / "workspaces"),
                        "--report",
                        str(report_path),
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])
            report_exists = report_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(report_exists)

    def test_run_benchmark_tasks_executes_trace_approval_and_sandbox_modes(self):
        from onecode.benchmark import BenchmarkTask, run_benchmark_tasks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_benchmark_tasks(
                [
                    BenchmarkTask(
                        id="trace",
                        prompt="trace",
                        expected_status="completed",
                        mode="trace",
                        input={},
                        assertions=[{"type": "file_exists", "path": ".onecode/trace.jsonl"}],
                    ),
                    BenchmarkTask(
                        id="approval",
                        prompt="approval",
                        expected_status="completed",
                        mode="approval",
                        input={},
                        assertions=[{"type": "file_exists", "path": ".onecode/approvals.jsonl"}],
                    ),
                    BenchmarkTask(
                        id="sandbox",
                        prompt="sandbox",
                        expected_status="completed",
                        mode="sandbox",
                        input={},
                        assertions=[],
                    ),
                ],
                workspace_root=root / "workspaces",
            )
            self.assertEqual(result["status"], "completed")
            for entry in result["entries"]:
                runtime_result = entry["result"]
                self.assertEqual(
                    runtime_result["assets"][0]["balance_mutation"],
                    IchingKernel.balance_mutation_evidence(
                        runtime_result["assets"][0]["raw_status_code"],
                        runtime_result["assets"][0]["balanced_status_code"],
                    ),
                )
                self.assertEqual(runtime_result["balance_mutation_summary"]["asset_count"], 1)
            self.assertEqual(result["passed_count"], 3)
            self.assertEqual(result["metrics"]["evidence_completeness"], 1.0)
            for entry in result["entries"]:
                self.assertTrue(Path(entry["result"]["ledger_path"]).exists())
                self.assertTrue(Path(entry["result"]["manifest_path"]).exists())

    def test_run_benchmark_rule_task_can_precreate_fixture_files(self):
        from onecode.benchmark import BenchmarkTask, run_benchmark_tasks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_benchmark_tasks(
                [
                    BenchmarkTask(
                        id="patch",
                        prompt="patch",
                        expected_status="completed",
                        mode="rule",
                        input={
                            "files": [
                                {"path": "src/app.py", "content": "VALUE = 1\n"}
                            ],
                            "patch_path": "src/app.py",
                            "search_block": "VALUE = 1",
                            "replace_block": "VALUE = 2",
                        },
                        assertions=[{"type": "file_exists", "path": "src/app.py"}],
                    )
                ],
                workspace_root=root / "workspaces",
            )
            patched = (root / "workspaces" / "patch" / "src" / "app.py").read_text(encoding="utf-8")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(patched, "VALUE = 2\n")

    def test_default_benchmark_task_set_runs_successfully(self):
        from onecode.benchmark import load_benchmark_tasks, run_benchmark_tasks

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_benchmark_tasks(
                load_benchmark_tasks(root / "benchmarks" / "tasks"),
                workspace_root=Path(tmp) / "workspaces",
                report_path=Path(tmp) / "report.json",
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_count"], 20)
        self.assertEqual(result["passed_count"], 20)

    def test_benchmark_report_includes_hallucination_metrics(self):
        from onecode.benchmark import BenchmarkTask, run_benchmark_tasks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_benchmark_tasks(
                [
                    BenchmarkTask(
                        id="safe-write",
                        prompt="safe write",
                        expected_status="completed",
                        mode="rule",
                        input={
                            "write_path": "safe.txt",
                            "write_content": "ok\n",
                        },
                        assertions=[
                            {"type": "file_exists", "path": "safe.txt"},
                            {"type": "evidence_complete"},
                        ],
                    ),
                    BenchmarkTask(
                        id="forbidden-path",
                        prompt="forbidden path",
                        expected_status="halted",
                        mode="rule",
                        input={
                            "write_path": "../escape.txt",
                            "write_content": "blocked\n",
                        },
                        assertions=[
                            {"type": "no_hallucination"},
                            {"type": "evidence_complete"},
                        ],
                    ),
                ],
                workspace_root=root / "workspaces",
            )

        metrics = result["metrics"]
        self.assertEqual(metrics["hallucination_failures"], 0)
        self.assertEqual(metrics["hallucination_rate"], 0.0)
        self.assertEqual(metrics["pass_at_1"], 1.0)
        self.assertEqual(metrics["asset_completeness"], 1.0)
        self.assertEqual(metrics["evidence_completeness"], 1.0)

    def test_benchmark_scores_missing_evidence_as_failure(self):
        from onecode.benchmark import BenchmarkTask, score_benchmark_result

        with tempfile.TemporaryDirectory() as tmp:
            task = BenchmarkTask(
                id="missing-evidence",
                prompt="demo",
                expected_status="completed",
                assertions=[{"type": "evidence_complete"}],
            )
            score = score_benchmark_result(
                task,
                {"status": "completed", "run_id": "missing-evidence"},
                Path(tmp),
            )

        self.assertFalse(score.passed)
        self.assertIn("missing ledger evidence", score.failures)
        self.assertIn("missing manifest evidence", score.failures)

    def test_evidence_completeness_metric_requires_actual_evidence_without_assertion(self):
        from onecode.benchmark import BenchmarkTask, run_baseline_benchmark_task, run_benchmark_task

        task = BenchmarkTask(
            id="write",
            prompt="write",
            expected_status="completed",
            mode="rule",
            input={
                "write_path": "hello.txt",
                "write_content": "hello\n",
            },
            assertions=[{"type": "file_exists", "path": "hello.txt"}],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, baseline_score = run_baseline_benchmark_task(task, root / "baseline")
            _, onecode_score = run_benchmark_task(task, root / "onecode")

        self.assertTrue(baseline_score.passed)
        self.assertFalse(baseline_score.evidence_complete)
        self.assertTrue(onecode_score.passed)
        self.assertTrue(onecode_score.evidence_complete)

    def test_evidence_completeness_accepts_wal_only_result(self):
        from onecode.benchmark import BenchmarkTask, run_benchmark_task

        task = BenchmarkTask(
            id="wal-evidence",
            prompt="noop",
            expected_status="completed",
            mode="rule",
            input={},
            assertions=[{"type": "evidence_complete"}],
        )

        with tempfile.TemporaryDirectory() as tmp:
            result, score = run_benchmark_task(task, Path(tmp))

        self.assertEqual(result["evidence_mode"], "wal")
        self.assertIsNone(result["ledger_path"])
        self.assertIsNone(result["manifest_path"])
        self.assertTrue(score.passed, score.failures)
        self.assertTrue(score.evidence_complete)

    def test_benchmark_rule_task_can_force_full_evidence(self):
        from onecode.benchmark import BenchmarkTask, run_benchmark_task

        task = BenchmarkTask(
            id="full-evidence",
            prompt="noop",
            expected_status="completed",
            mode="rule",
            input={
                "completed_evidence_mode": "full",
                "evidence_durability": "strict",
            },
            assertions=[{"type": "evidence_complete"}],
        )

        with tempfile.TemporaryDirectory() as tmp:
            result, score = run_benchmark_task(task, Path(tmp))
            ledger_exists = Path(result["ledger_path"]).exists()
            manifest_exists = Path(result["manifest_path"]).exists()

        self.assertEqual(result["evidence_mode"], "full")
        self.assertTrue(ledger_exists)
        self.assertTrue(manifest_exists)
        self.assertTrue(score.passed, score.failures)

    def test_compare_benchmark_tasks_reports_baseline_and_onecode_metrics(self):
        from onecode.benchmark import BenchmarkTask, compare_benchmark_tasks

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = compare_benchmark_tasks(
                [
                    BenchmarkTask(
                        id="write",
                        prompt="write",
                        expected_status="completed",
                        mode="rule",
                        input={
                            "write_path": "hello.txt",
                            "write_content": "hello\n",
                        },
                        assertions=[
                            {"type": "file_exists", "path": "hello.txt"},
                            {"type": "evidence_complete"},
                        ],
                    )
                ],
                workspace_root=root / "workspaces",
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["rule_schema"], RULE_SCHEMA_V2)
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["arms"]["onecode"]["metrics"]["pass_at_1"], 1.0)
        self.assertEqual(result["arms"]["onecode"]["metrics"]["evidence_completeness"], 1.0)
        self.assertEqual(result["arms"]["baseline"]["metrics"]["pass_at_1"], 0.0)
        self.assertEqual(result["arms"]["baseline"]["metrics"]["evidence_completeness"], 0.0)
        self.assertEqual(
            result["arms"]["onecode"]["entries"][0]["result"]["shell_projection"]["run_id"],
            "benchmark-write",
        )
        self.assertEqual(
            result["arms"]["baseline"]["entries"][0]["result"]["shell_projection"]["run_id"],
            "baseline-write",
        )
        self.assertEqual(result["delta"]["pass_at_1"], 1.0)
        self.assertEqual(result["delta"]["evidence_completeness"], 1.0)

    def test_cli_benchmark_compare_baseline_writes_ab_report(self):
        from onecode.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks_dir = root / "tasks"
            tasks_dir.mkdir()
            report_path = root / "ab-report.json"
            (tasks_dir / "write.json").write_text(
                json.dumps(
                    {
                        "id": "write",
                        "prompt": "write",
                        "expected_status": "completed",
                        "mode": "rule",
                        "input": {
                            "write_path": "hello.txt",
                            "write_content": "hello\n",
                        },
                        "assertions": [
                            {"type": "file_exists", "path": "hello.txt"},
                            {"type": "evidence_complete"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "benchmark",
                        "--tasks-dir",
                        str(tasks_dir),
                        "--compare-baseline",
                        "--workspace-root",
                        str(root / "workspaces"),
                        "--report",
                        str(report_path),
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "completed")
        self.assertIn("baseline", result["arms"])
        self.assertIn("onecode", report["arms"])

    def test_agent_local_tasks_record_pass_rate_turns_and_stop_reasons(self):
        from onecode.benchmark import agent_pass_rate_record, load_benchmark_tasks, run_benchmark_tasks

        tasks = load_benchmark_tasks(Path("benchmarks/tasks/agent"))
        self.assertEqual(len(tasks), 30)
        self.assertTrue(all(task.mode == "agent" for task in tasks))

        with tempfile.TemporaryDirectory() as tmp:
            report = run_benchmark_tasks(tasks, workspace_root=Path(tmp) / "workspaces")
        record = agent_pass_rate_record(report)

        self.assertEqual(record["task_count"], 30)
        self.assertEqual(record["passed_count"], 30)
        self.assertEqual(record["pass_rate"], 1.0)
        self.assertEqual(record["runner"], "scripted_oracle")
        self.assertFalse(record["claims_mainstream_parity"])
        reasons = {item["stop_reason"] for item in record["tasks"]}
        self.assertIn(None, reasons)
        self.assertIn("resource_budget_exceeded", reasons)
        self.assertIn("permission_denied", reasons)
        self.assertTrue(all(isinstance(item["turn_count"], int) and item["turn_count"] >= 1 for item in record["tasks"]))

    def test_swebench_lite_subset_does_not_claim_parity(self):
        from onecode.benchmark import SWEBENCH_LITE_SUBSET_IDS, swebench_lite_subset_report

        missing = swebench_lite_subset_report(Path("/no/such/swebench-lite.jsonl"))
        self.assertEqual(missing["status"], "not_connected")
        self.assertEqual(missing["loaded_count"], 0)
        self.assertFalse(missing["claims_mainstream_parity"])
        self.assertEqual(missing["subset_ids"], list(SWEBENCH_LITE_SUBSET_IDS))

        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "lite.jsonl"
            dataset.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "instance_id": SWEBENCH_LITE_SUBSET_IDS[0],
                                "repo": "django/django",
                                "problem_statement": "fix the lookup",
                            }
                        ),
                        json.dumps(
                            {
                                "instance_id": "not-in-subset",
                                "repo": "example/example",
                                "problem_statement": "ignore",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            loaded = swebench_lite_subset_report(dataset)

        self.assertEqual(loaded["status"], "loaded")
        self.assertEqual(loaded["loaded_count"], 1)
        self.assertEqual(loaded["instances"][0]["instance_id"], SWEBENCH_LITE_SUBSET_IDS[0])
        self.assertFalse(loaded["claims_mainstream_parity"])
        self.assertNotIn("pass_rate", loaded)

    def test_vendored_swebench_lite_subset_is_loaded_and_unscored(self):
        from onecode.benchmark import SWEBENCH_LITE_SUBSET_IDS, vendored_swebench_lite_subset_report

        report = vendored_swebench_lite_subset_report()

        self.assertEqual(report["status"], "loaded")
        self.assertEqual(report["loaded_count"], len(SWEBENCH_LITE_SUBSET_IDS))
        self.assertEqual(
            [item["instance_id"] for item in report["instances"]],
            list(SWEBENCH_LITE_SUBSET_IDS),
        )
        self.assertEqual(report["eval_status"], "not_executed")
        self.assertFalse(report["claims_mainstream_parity"])
        self.assertNotIn("pass_rate", report)

    def test_official_patch_harness_records_fail_then_pass_without_claiming_parity(self):
        import subprocess
        import sys

        from onecode.benchmark import evaluate_swebench_instance, summarize_swebench_eval

        with tempfile.TemporaryDirectory() as tmp:
            origin = Path(tmp) / "origin"
            origin.mkdir()
            subprocess.run(["git", "init"], cwd=origin, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "onecode@local.test"], cwd=origin, check=True)
            subprocess.run(["git", "config", "user.name", "OneCode"], cwd=origin, check=True)
            (origin / "sample.py").write_text("value = 0\n", encoding="utf-8")
            subprocess.run(["git", "add", "sample.py"], cwd=origin, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=origin, check=True, capture_output=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=origin, text=True).strip()
            (origin / "test_sample.py").write_text(
                "import sample\nraise SystemExit(0 if sample.value == 1 else 1)\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "-N", "test_sample.py"], cwd=origin, check=True)
            test_patch = subprocess.check_output(["git", "diff", "--no-ext-diff"], cwd=origin, text=True)
            (origin / "test_sample.py").unlink()
            subprocess.run(["git", "reset"], cwd=origin, check=True, capture_output=True)
            (origin / "sample.py").write_text("value = 1\n", encoding="utf-8")
            gold_patch = subprocess.check_output(["git", "diff", "--no-ext-diff"], cwd=origin, text=True)
            subprocess.run(["git", "checkout", "--", "sample.py"], cwd=origin, check=True)

            result = evaluate_swebench_instance(
                {
                    "instance_id": "local__sample-1",
                    "repo": str(origin),
                    "base_commit": base,
                    "test_patch": test_patch,
                    "patch": gold_patch,
                    "test_argv": ["{python}", "test_sample.py"],
                },
                Path(tmp) / "work",
                python=sys.executable,
                install=False,
            )
            summary = summarize_swebench_eval([result])

        self.assertNotEqual(result["before_returncode"], 0)
        self.assertEqual(result["after_returncode"], 0)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(summary["runner"], "official_gold_patch")
        self.assertEqual(summary["pass_rate"], 1.0)
        self.assertEqual(summary["eval_status"], "executed")
        self.assertFalse(summary["claims_mainstream_parity"])
