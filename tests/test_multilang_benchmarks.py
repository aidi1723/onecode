"""Tests for multi-language benchmark task suites (Go, TypeScript, Rust)."""
from __future__ import annotations

from pathlib import Path
import unittest

from onecode.benchmark import load_benchmark_tasks, run_benchmark_tasks


class MultiLangBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.tasks_dir = cls.repo_root / "benchmarks" / "tasks"

    def test_golang_suite_completes_all_tasks(self) -> None:
        go_tasks = load_benchmark_tasks(self.tasks_dir / "golang")
        self.assertEqual(len(go_tasks), 10)
        res = run_benchmark_tasks(go_tasks)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["passed_count"], 10)
        self.assertEqual(res["failed_count"], 0)

    def test_typescript_suite_completes_all_tasks(self) -> None:
        ts_tasks = load_benchmark_tasks(self.tasks_dir / "typescript")
        self.assertEqual(len(ts_tasks), 10)
        res = run_benchmark_tasks(ts_tasks)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["passed_count"], 10)
        self.assertEqual(res["failed_count"], 0)

    def test_rust_suite_completes_all_tasks(self) -> None:
        rs_tasks = load_benchmark_tasks(self.tasks_dir / "rust")
        self.assertEqual(len(rs_tasks), 10)
        res = run_benchmark_tasks(rs_tasks)
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["passed_count"], 10)
        self.assertEqual(res["failed_count"], 0)


if __name__ == "__main__":
    unittest.main()
