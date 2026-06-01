import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["passed_count"], 1)
        self.assertEqual(report["scores"][0]["task_id"], "write-file-basic")
        self.assertEqual(result["entries"][0]["result"]["shell_projection"]["run_id"], "benchmark-write-file-basic")
        self.assertEqual(result["entries"][0]["result"]["shell_projection"]["severity"], "ok")
        self.assertEqual(report["entries"][0]["result"]["shell_projection"]["severity"], "ok")

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
