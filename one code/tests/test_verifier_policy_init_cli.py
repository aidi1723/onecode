import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.cli import main
from onecode.kernel.verifier import load_verifier_policy


class VerifierPolicyInitCliTests(unittest.TestCase):
    def test_cli_init_verifier_policy_writes_default_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch("builtins.print") as print_mock:
                exit_code = main(["init-verifier-policy", "--workspace", tmp])
            result = json.loads(print_mock.call_args.args[0])
            policy_path = workspace / ".onecode" / "verifier-policy.json"
            policy = load_verifier_policy(policy_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["path"], ".onecode/verifier-policy.json")
            self.assertEqual(result["verifier_ids"], ["python-unittest"])
            self.assertIn("python-unittest", policy.specs)

    def test_cli_init_verifier_policy_writes_repeated_presets(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with patch("builtins.print") as print_mock:
                exit_code = main(
                    [
                        "init-verifier-policy",
                        "--workspace",
                        tmp,
                        "--preset",
                        "python-unittest",
                        "--preset",
                        "python-compileall",
                    ]
                )
            result = json.loads(print_mock.call_args.args[0])
            policy = load_verifier_policy(workspace / ".onecode" / "verifier-policy.json")

            self.assertEqual(exit_code, 0)
            self.assertEqual(result["verifier_ids"], ["python-unittest", "python-compileall"])
            self.assertEqual(sorted(policy.specs), ["python-compileall", "python-unittest"])

    def test_cli_init_verifier_policy_rejects_existing_output_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            output = workspace / ".onecode" / "verifier-policy.json"
            output.parent.mkdir(parents=True)
            output.write_text('{"sentinel": true}\n', encoding="utf-8")

            with self.assertRaises(SystemExit):
                main(["init-verifier-policy", "--workspace", tmp])

            self.assertEqual(output.read_text(encoding="utf-8"), '{"sentinel": true}\n')

    def test_cli_init_verifier_policy_force_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            output = workspace / ".onecode" / "verifier-policy.json"
            output.parent.mkdir(parents=True)
            output.write_text('{"sentinel": true}\n', encoding="utf-8")

            with patch("builtins.print") as print_mock:
                exit_code = main(["init-verifier-policy", "--workspace", tmp, "--force"])
            result = json.loads(print_mock.call_args.args[0])
            policy = load_verifier_policy(output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(result["verifier_ids"], ["python-unittest"])
            self.assertIn("python-unittest", policy.specs)
            self.assertNotIn("sentinel", output.read_text(encoding="utf-8"))

    def test_cli_init_verifier_policy_rejects_output_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with self.assertRaises(SystemExit):
                main(["init-verifier-policy", "--workspace", tmp, "--output", "../policy.json"])

            self.assertFalse((workspace.parent / "policy.json").exists())
            self.assertFalse((workspace / ".onecode" / "verifier-policy.json").exists())

    def test_cli_init_verifier_policy_rejects_unknown_preset_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            with self.assertRaises(SystemExit):
                main(["init-verifier-policy", "--workspace", tmp, "--preset", "missing"])

            self.assertFalse((workspace / ".onecode" / "verifier-policy.json").exists())


if __name__ == "__main__":
    unittest.main()
