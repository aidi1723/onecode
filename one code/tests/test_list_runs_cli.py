import json
import os
import subprocess
import sys
import tempfile
import unittest


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
            self.assertTrue(all(run["checkpoint_count"] == 1 for run in result["runs"]))


if __name__ == "__main__":
    unittest.main()
