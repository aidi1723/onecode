"""Tests for Harbor benchmark adapter CLI and agent mode dispatch."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import harbor_adapter  # noqa: E402
import harbor_scheduler  # noqa: E402


class TestHarborAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.workspace = self.root / "workspace"
        self.task_package = self.root / "task_pkg"
        self.hidden_tests = self.task_package / "tests"
        self.log_dir = self.root / "logs"

        self.workspace.mkdir(parents=True, exist_ok=True)
        self.task_package.mkdir(parents=True, exist_ok=True)
        self.hidden_tests.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        (self.task_package / "instruction.md").write_text("Fix everything", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_dry_run_records_agent_mode(self) -> None:
        rec_classic = harbor_adapter.run_harbor_task(
            task_id="dry-1",
            task_package=self.task_package,
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            dry_run=True,
            agent_mode="classic",
        )
        self.assertEqual(rec_classic["agent_mode"], "classic")
        self.assertEqual(rec_classic["status"], "dry_run")

        rec_term = harbor_adapter.run_harbor_task(
            task_id="dry-2",
            task_package=self.task_package,
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            dry_run=True,
            agent_mode="terminal",
        )
        self.assertEqual(rec_term["agent_mode"], "terminal")
        self.assertEqual(rec_term["status"], "dry_run")
        reward_txt = (self.log_dir / "reward.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(reward_txt, "0.0")

    def test_cli_parser_defaults_and_choices(self) -> None:
        with patch.object(sys, "argv", [
            "harbor_adapter.py",
            "--task-id", "t-1",
            "--task-package", str(self.task_package),
            "--workspace", str(self.workspace),
            "--log-dir", str(self.log_dir),
            "--agent-mode", "terminal",
            "--dry-run",
        ]):
            code = harbor_adapter.main()
            self.assertEqual(code, 0)
            reward_json = json.loads((self.log_dir / "reward.json").read_text(encoding="utf-8"))
            self.assertEqual(reward_json["agent_mode"], "terminal")
            self.assertEqual(reward_json["task_id"], "t-1")


class TestHarborSchedulerAdversarialGrading(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.workspace = self.root / "workspace"
        self.hidden_tests = self.root / "hidden_tests"
        self.log_dir = self.root / "logs"

        self.workspace.mkdir(parents=True, exist_ok=True)
        self.hidden_tests.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        verifier_content = """import json, os, subprocess, sys
from pathlib import Path

root = Path(os.environ.get("WORKSPACE", "/workspace"))
log_dir = Path(os.environ.get("LOG_DIR", "/log_dir"))

target = root / "app.py"
if target.is_file():
    subprocess.run([sys.executable, str(target)], cwd=str(root), capture_output=True)

passed = target.exists() and "SECRET_42" in target.read_text(encoding="utf-8")
tests = [{"name": "secret_check", "passed": passed}]
total = 1
passed_count = 1 if passed else 0
overall = float(passed_count / total)

reward = {
    "overall": overall,
    "tests_passed": passed_count,
    "tests_total": total,
    "test_status": "pass" if passed else "fail",
    "tests": tests,
}
(log_dir / "reward.json").write_text(json.dumps(reward, indent=2), encoding="utf-8")
if not passed:
    sys.exit(1)
(log_dir / "reward.txt").write_text(str(overall), encoding="utf-8")
sys.exit(0)
"""
        (self.hidden_tests / "verifier.py").write_text(verifier_content, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_genuine_solution_evaluates_successfully(self) -> None:
        (self.workspace / "app.py").write_text("SECRET_42 = True\n", encoding="utf-8")
        res = harbor_scheduler.run_stage2_evaluation(
            task_id="task-genuine",
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            use_docker=False,
        )
        self.assertTrue(res["passed"])
        self.assertEqual(res["host_reward"], 1.0)
        self.assertEqual(res["tests_passed"], 1)

    def test_adversarial_reward_forgery_is_detected_and_failed(self) -> None:
        """Adversary tries to forge reward.txt to 1.0 while implementation fails tests."""
        (self.workspace / "app.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "log_dir = Path(os.environ.get('LOG_DIR', '/log_dir'))\n"
            "(log_dir / 'reward.txt').write_text('1.0', encoding='utf-8')\n",
            encoding="utf-8",
        )
        res = harbor_scheduler.run_stage2_evaluation(
            task_id="task-adv-reward",
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            use_docker=False,
        )
        self.assertFalse(res["passed"])
        self.assertEqual(res["host_reward"], 0.0)
        self.assertIn("reward_forgery_detected", res.get("security_violation", ""))

    def test_adversarial_test_tampering_is_detected_and_failed(self) -> None:
        """Adversary tries to modify verifier.py or test assertions directly."""
        baseline_hashes = harbor_scheduler.snapshot_test_hashes(self.hidden_tests)
        # Mutate verifier file
        (self.hidden_tests / "verifier.py").write_text("import sys; sys.exit(0)\n", encoding="utf-8")

        intact, msg = harbor_scheduler.verify_test_hashes(baseline_hashes, self.hidden_tests)
        self.assertFalse(intact)
        self.assertIn("tampered", msg)

        # Also test runtime tampering detection when run_stage2_evaluation runs
        (self.hidden_tests / "verifier.py").write_text(
            "import os, json, sys; from pathlib import Path\n"
            "log_dir = Path(os.environ.get('LOG_DIR', '/log_dir'))\n"
            "(log_dir / 'reward.json').write_text('{\"overall\":1.0,\"tests_passed\":1,\"tests_total\":1,\"test_status\":\"pass\"}')\n"
            "(log_dir / 'reward.txt').write_text('1.0')\n"
            "# Tamper hidden verifier during grading:\n"
            "Path(__file__).write_text('// tampered')\n"
            "sys.exit(0)\n",
            encoding="utf-8",
        )
        res = harbor_scheduler.run_stage2_evaluation(
            task_id="task-adv-tamper",
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            use_docker=False,
        )
        self.assertFalse(res["passed"])
        self.assertEqual(res["host_reward"], 0.0)
        self.assertEqual(res.get("security_violation"), "test_tampering_detected")

    def test_adversarial_sys_path_hijacking_is_detected_and_failed(self) -> None:
        """Adversary places a malicious json.py in workspace root to hijack verifier imports."""
        (self.workspace / "json.py").write_text(
            "def dumps(*args, **kwargs):\n    return '{\"overall\": 1.0, \"tests_passed\": 1, \"tests_total\": 1, \"test_status\": \"pass\"}'\n",
            encoding="utf-8",
        )
        res = harbor_scheduler.run_stage2_evaluation(
            task_id="task-adv-hijack",
            workspace=self.workspace,
            hidden_tests=self.hidden_tests,
            log_dir=self.log_dir,
            use_docker=False,
        )
        self.assertFalse(res["passed"])
        self.assertEqual(res["host_reward"], 0.0)
        self.assertEqual(res["security_violation"], "sys_path_hijack_detected")
        self.assertIn("json.py", res["detail"])


if __name__ == "__main__":
    unittest.main()
