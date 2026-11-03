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


if __name__ == "__main__":
    unittest.main()
