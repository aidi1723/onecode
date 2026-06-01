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
    def test_readme_documents_public_control_boundary(self):
        text = Path("README.md").read_text(encoding="utf-8")

        for snippet in [
            "model outputs into\ncandidates",
            "deterministic state",
            "path and intent gate",
            "6-bit state profile",
            "Append-only WAL evidence",
            "hash-chain validation",
            "Stateful resume logic",
            "model output as a candidate, not an authority",
        ]:
            self.assertIn(snippet, text)

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
