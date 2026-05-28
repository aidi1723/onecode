import ast
from pathlib import Path
import unittest


FORBIDDEN_PARALLEL_CONTROL_NAMES = {
    "confidence_level",
    "external_policy_flag",
    "manual_priority",
    "model_mood",
    "retry_score",
}


class RuleClosureTests(unittest.TestCase):
    def test_readme_documents_rule_closure_principle(self):
        text = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("Rule Closure Principle", text)
        self.assertIn("external facts are evidence, not law", text)
        self.assertIn("6-bit status_code", text)
        self.assertIn("yin-yang", text)
        self.assertIn("five-element", text)
        self.assertIn("forbidden parallel control variables", text)
        self.assertIn("Rule Discovery Protocol", text)
        self.assertIn("Bug reports are rule-gap probes", text)
        self.assertIn("discover", text)

    def test_kernel_source_forbids_parallel_control_variables(self):
        offending_names = set()
        for source_path in Path("src/onecode/kernel").glob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id in FORBIDDEN_PARALLEL_CONTROL_NAMES:
                    offending_names.add(node.id)
                elif isinstance(node, ast.arg) and node.arg in FORBIDDEN_PARALLEL_CONTROL_NAMES:
                    offending_names.add(node.arg)
                elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_PARALLEL_CONTROL_NAMES:
                    offending_names.add(node.attr)

        self.assertEqual(offending_names, set())


if __name__ == "__main__":
    unittest.main()
