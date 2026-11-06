from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from unittest.mock import patch

from scripts.swebench_adapter import (
    extract_git_patch,
    format_swebench_prompt,
    load_swebench_instances,
    run_swebench_instance,
    setup_swebench_workspace,
    validate_unified_diff,
    verify_predictions_dataset,
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

        inst_with_checks = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "problem_statement": "UsernameValidator allows trailing newline",
            "FAIL_TO_PASS": '["test_ascii_validator", "test_unicode_validator"]',
        }
        prompt_with_checks = format_swebench_prompt(inst_with_checks)
        self.assertIn("Expected Verification Targets:", prompt_with_checks)
        self.assertIn("- test_ascii_validator", prompt_with_checks)
        self.assertIn("- test_unicode_validator", prompt_with_checks)
        self.assertIn("tests/runtests.py", prompt_with_checks)
        self.assertIn('--settings=test_sqlite', prompt_with_checks)
        self.assertIn("--parallel=1", prompt_with_checks)
        self.assertIn('"action_type":"finish"', prompt_with_checks)
        self.assertNotIn("trailingnewline", prompt_with_checks)

    def test_prompt_omits_official_test_patch_body(self) -> None:
        leaked = "trailingnewline\\u000A"
        inst = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "problem_statement": "UsernameValidator allows trailing newline",
            "FAIL_TO_PASS": '["test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests)"]',
            "test_patch": "diff --git a/tests/auth_tests/test_validators.py\n+" + leaked + "\n",
        }
        prompt = format_swebench_prompt(inst)
        self.assertNotIn("trailingnewline", prompt)
        self.assertNotIn("test_patch", prompt)
        self.assertIn("auth_tests.test_validators.UsernameValidatorsTests.test_ascii_validator", prompt)

    def test_run_passes_fifteen_turn_budget(self) -> None:
        inst = {"instance_id": "mock__turns-1", "repo": "mock/repo", "problem_statement": "budget"}
        with (
            patch("scripts.swebench_adapter.setup_swebench_workspace", return_value=self.root),
            patch("scripts.swebench_adapter.extract_git_patch", return_value=""),
            patch("scripts.swebench_adapter.run_model_task", return_value={"status": "halted", "reason": "turn_limit_exhausted"}) as run,
        ):
            record = run_swebench_instance(
                inst,
                self.root,
                model="deepseek-v4.1-flash",
                endpoint="http://mock",
                agent_mode="terminal",
            )
        self.assertEqual(run.call_args.kwargs["max_turns"], 15)
        self.assertEqual(record["reason"], "turn_limit_exhausted")

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

    def test_validate_unified_diff(self) -> None:
        empty_res = validate_unified_diff("")
        self.assertTrue(empty_res["valid"])
        self.assertTrue(empty_res["empty"])
        self.assertEqual(empty_res["files"], [])

        valid_patch = (
            "diff --git a/pkg/mod.py b/pkg/mod.py\n"
            "index 111..222 100644\n"
            "--- a/pkg/mod.py\n"
            "+++ b/pkg/mod.py\n"
            "@@ -1,2 +1,3 @@\n"
            "-old_line\n"
            "+new_line_1\n"
            "+new_line_2\n"
        )
        res = validate_unified_diff(valid_patch)
        self.assertTrue(res["valid"])
        self.assertFalse(res["empty"])
        self.assertEqual(res["files"], ["pkg/mod.py"])
        self.assertEqual(res["additions"], 2)
        self.assertEqual(res["deletions"], 1)

        unsafe_patch = (
            "diff --git a/.git/config b/.git/config\n"
            "--- a/.git/config\n"
            "+++ b/.git/config\n"
            "@@ -1 +1 @@\n"
            "+evil=true\n"
        )
        unsafe_res = validate_unified_diff(unsafe_patch)
        self.assertFalse(unsafe_res["valid"])
        self.assertFalse(unsafe_res["is_safe"])

    def test_verify_predictions_dataset(self) -> None:
        missing = verify_predictions_dataset(self.root / "none.jsonl", self.root / "d.jsonl")
        self.assertEqual(missing["status"], "error")

        ds_path = self.root / "dataset.jsonl"
        ds_path.write_text(
            json.dumps({"instance_id": "inst-1", "repo": "repo/a", "problem_statement": "p1"}) + "\n",
            encoding="utf-8",
        )

        pred_path = self.root / "predictions.jsonl"
        pred_lines = [
            json.dumps({
                "instance_id": "inst-1",
                "model_patch": "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n+fixed\n",
                "status": "completed",
            }),
            json.dumps({
                "instance_id": "inst-2",
                "model_patch": "",
                "status": "failed",
            }),
        ]
        pred_path.write_text("\n".join(pred_lines) + "\n", encoding="utf-8")

        audit = verify_predictions_dataset(pred_path, ds_path)
        self.assertEqual(audit["status"], "verified")
        self.assertEqual(audit["dataset_total"], 1)
        self.assertEqual(audit["predictions_count"], 2)
        self.assertEqual(audit["matched_count"], 1)
        self.assertEqual(audit["valid_patch_count"], 1)
        self.assertEqual(audit["empty_patch_count"], 1)


if __name__ == "__main__":
    unittest.main()
