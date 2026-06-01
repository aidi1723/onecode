import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ListRunsCliTests(unittest.TestCase):
    def test_cli_list_runs_returns_empty_list_for_new_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            completed = subprocess.run(
                [sys.executable, "-m", "onecode.cli", "list-runs", "--workspace", tmp],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)

            self.assertEqual(result["workspace"], tmp)
            self.assertEqual(result["runs"], [])

    def test_cli_list_runs_prints_existing_run_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            for run_id in ["run-b", "run-a"]:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "onecode.cli",
                        "run",
                        f"source {run_id}",
                        "--workspace",
                        tmp,
                        "--run-id",
                        run_id,
                        "--write-path",
                        f"src/{run_id}.py",
                        "--write-content",
                        "value = 1\n",
                    ],
                    env=env,
                    text=True,
                    capture_output=True,
                    check=True,
                )

            completed = subprocess.run(
                [sys.executable, "-m", "onecode.cli", "list-runs", "--workspace", tmp],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)

            self.assertEqual([run["run_id"] for run in result["runs"]], ["run-a", "run-b"])
            self.assertEqual([run["status"] for run in result["runs"]], ["completed", "completed"])
            self.assertTrue(all(run["evidence_mode"] == "wal" for run in result["runs"]))
            self.assertTrue(all(run["checkpoint_count"] is None for run in result["runs"]))
            self.assertTrue(all(run["wal_path"] for run in result["runs"]))
            self.assertTrue(all(run["shell_projection"]["severity"] == "ok" for run in result["runs"]))
            self.assertTrue(all(run["shell_projection"]["evidence_ref"]["mode"] == "wal" for run in result["runs"]))

    def test_cli_list_runs_includes_corrupt_run_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            run_root = Path(tmp) / ".onecode" / "runs" / "corrupt-run"
            run_root.mkdir(parents=True)
            (run_root / "manifest.json").write_text("{not json", encoding="utf-8")
            (run_root / "ledger.json").write_text('{"status": "completed"}', encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "-m", "onecode.cli", "list-runs", "--workspace", tmp],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)

            self.assertEqual(len(result["runs"]), 1)
            self.assertEqual(result["runs"][0]["run_id"], "corrupt-run")
            self.assertEqual(result["runs"][0]["status"], "corrupt")
            self.assertIn("manifest.json", result["runs"][0]["corrupt_path"])


if __name__ == "__main__":
    unittest.main()
