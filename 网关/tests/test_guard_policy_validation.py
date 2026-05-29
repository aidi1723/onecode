import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_skill_dictionary.guard_executor import validate_guard_policy_file


class GuardPolicyValidationTest(unittest.TestCase):
    def test_default_guard_policy_validates_without_errors(self):
        errors = validate_guard_policy_file("agent_skill_dictionary/guard_policy.json")

        self.assertEqual(errors, [])

    def test_guard_policy_reports_schema_errors(self):
        invalid_policy = {
            "ignore_paths": ["tmp/**"],
            "text_suffixes": ["txt"],
            "rules": [
                {
                    "id": "bad-rule",
                    "name": "bad rule",
                    "pattern": "[",
                    "severity": "critical",
                    "block": "yes",
                }
            ],
        }

        errors = validate_guard_policy_file_dict(invalid_policy)

        self.assertIn("text_suffixes[0] must start with '.'", errors)
        self.assertIn("rules[0].severity must be one of ['high', 'low', 'medium']", errors)
        self.assertIn("rules[0].block must be boolean", errors)
        self.assertTrue(any("rules[0].pattern is invalid regex" in error for error in errors))


def validate_guard_policy_file_dict(data):
    with TemporaryDirectory() as tmpdir:
        policy_path = Path(tmpdir) / "guard_policy.json"
        policy_path.write_text(json.dumps(data), encoding="utf-8")
        return validate_guard_policy_file(policy_path)


if __name__ == "__main__":
    unittest.main()
