from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.swebench_adapter import (
    extract_git_patch,
    format_swebench_prompt,
    load_swebench_instances,
    run_swebench_instance,
    setup_swebench_workspace,
)


class TestSWEBenchAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_load_swebench_instances(self) -> None:
        dataset_file = self.root / "dataset.jsonl"
        lines = [
            {"instance_id": "inst-1", "repo": "repo/a", "problem_statement": "fix a bug"},
            {"instance_id": "inst-2", "repo": "repo/b", "problem_statement": "fix another bug"},
        ]
        dataset_file.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")

        all_insts = load_swebench_instances(dataset_file)
        self.assertEqual(len(all_insts), 2)
        self.assertEqual(all_insts[0]["instance_id"], "inst-1")

        filtered = load_swebench_instances(dataset_file, instance_filter={"inst-2"})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["instance_id"], "inst-2")

    def test_setup_swebench_workspace_and_git_patch(self) -> None:
        ws = self.root / "workspace"
        inst = {"instance_id": "test-1", "repo": "my/repo"}
        setup_swebench_workspace(inst, ws)

        self.assertTrue((ws / ".git").is_dir())
        self.assertTrue((ws / ".gitignore").is_file())

        # Modify a file and check diff
        test_file = ws / "module.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "module.py"], cwd=ws, capture_output=True, check=False)
        subprocess.run(["git", "commit", "-m", "add module"], cwd=ws, capture_output=True, check=False)

        # Make a change
        test_file.write_text("x = 2\n", encoding="utf-8")
        patch = extract_git_patch(ws)
        self.assertIn("diff --git a/module.py b/module.py", patch)
        self.assertIn("+x = 2", patch)

    def test_format_swebench_prompt(self) -> None:
        inst = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "problem_statement": "UsernameValidator allows trailing newline",
            "hints_text": "Check contrib.auth.validators",
        }
        prompt = format_swebench_prompt(inst)
        self.assertIn("django__django-11099", prompt)
        self.assertIn("UsernameValidator allows trailing newline", prompt)
        self.assertIn("Check contrib.auth.validators", prompt)

    def test_run_swebench_instance_dry_run(self) -> None:
        inst = {
            "instance_id": "mock__repo-100",
            "repo": "mock/repo",
            "problem_statement": "dry run problem",
        }
        res = run_swebench_instance(
            inst,
            self.root,
            model="deepseek-v4.1-flash",
            endpoint="http://mock",
            agent_mode="terminal",
            dry_run=True,
        )
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["instance_id"], "mock__repo-100")
        self.assertEqual(res["agent_mode"], "terminal")
        self.assertTrue(Path(res["workspace"]).is_dir())


if __name__ == "__main__":
    unittest.main()
