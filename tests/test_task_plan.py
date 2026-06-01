import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.task_plan import load_task_plan


class TaskPlanKernelTests(unittest.TestCase):
    def test_load_task_plan_returns_write_texts_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "task-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "kernel plan",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n"},
                            {"path": "tests/test_a.py", "content": "def test_a():\n    assert True\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            task, write_texts, evidence = load_task_plan(plan_path)

            self.assertEqual(task, "kernel plan")
            self.assertEqual(write_texts, ["src/a.py=A = 1\n", "tests/test_a.py=def test_a():\n    assert True\n"])
            self.assertEqual(evidence["plan_path"], str(plan_path.resolve()))
            self.assertEqual(evidence["plan_sha256"], hashlib.sha256(plan_path.read_bytes()).hexdigest())
            self.assertEqual(evidence["plan_asset_count"], 2)

    def test_load_task_plan_rejects_duplicate_paths_without_runtime_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "duplicate-plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "task": "duplicate",
                        "assets": [
                            {"path": "src/a.py", "content": "A = 1\n"},
                            {"path": "src/a.py", "content": "A = 2\n"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "invalid plan asset 2: duplicate path src/a.py"):
                load_task_plan(plan_path)

    def test_cli_does_not_redefine_task_plan_schema(self):
        tree = ast.parse(Path("src/onecode/cli.py").read_text(encoding="utf-8"))
        function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assigned_names = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        self.assertNotIn("load_task_plan", function_names)
        self.assertNotIn("PLAN_ASSET_FIELDS", assigned_names)


if __name__ == "__main__":
    unittest.main()
