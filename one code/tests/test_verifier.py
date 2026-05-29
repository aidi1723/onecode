import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.verifier import VerifierSpec, load_verifier_policy, run_verifier


class VerifierPolicyTests(unittest.TestCase):
    def test_load_verifier_policy_accepts_allowlisted_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {
                                "id": "python-unittest",
                                "command": ["python3", "-m", "unittest"],
                                "cwd": ".",
                                "timeout_ms": 1000,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            policy = load_verifier_policy(path)

            spec = policy.require("python-unittest")
            self.assertEqual(spec.id, "python-unittest")
            self.assertEqual(spec.command, ["python3", "-m", "unittest"])
            self.assertEqual(spec.cwd, ".")
            self.assertEqual(spec.timeout_ms, 1000)

    def test_load_verifier_policy_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {"id": "unit", "command": ["python3"], "cwd": ".", "timeout_ms": 1000},
                            {"id": "unit", "command": ["python3"], "cwd": ".", "timeout_ms": 1000},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate verifier id"):
                load_verifier_policy(path)

    def test_policy_require_rejects_unknown_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verifiers.json"
            path.write_text(
                json.dumps(
                    {
                        "verifiers": [
                            {"id": "unit", "command": ["python3"], "cwd": ".", "timeout_ms": 1000}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            policy = load_verifier_policy(path)

            with self.assertRaisesRegex(ValueError, "unknown verifier id"):
                policy.require("missing")


class VerifierExecutionTests(unittest.TestCase):
    def test_run_verifier_records_success_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="ok",
                command=["python3", "-c", "print('ok')"],
                cwd=".",
                timeout_ms=5000,
            )

            result = run_verifier(workspace, spec)

            self.assertEqual(result.status, "passed")
            self.assertIsNone(result.reason)
            self.assertEqual(result.exit_code, 0)
            self.assertIn("ok", result.stdout_tail)
            self.assertEqual(result.stderr_tail, "")
            self.assertRegex(result.stdout_sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(result.stderr_sha256, r"^[0-9a-f]{64}$")

    def test_run_verifier_records_failure_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="fail",
                command=["python3", "-c", "import sys; print('bad'); sys.exit(7)"],
                cwd=".",
                timeout_ms=5000,
            )

            result = run_verifier(workspace, spec)

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "verifier_failed")
            self.assertEqual(result.exit_code, 7)
            self.assertIn("bad", result.stdout_tail)

    def test_run_verifier_records_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = VerifierSpec(
                id="slow",
                command=["python3", "-c", "import time; time.sleep(1)"],
                cwd=".",
                timeout_ms=10,
            )

            result = run_verifier(workspace, spec)

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.reason, "verifier_timeout")
            self.assertIsNone(result.exit_code)

    def test_run_verifier_rejects_cwd_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            spec = VerifierSpec(id="outside", command=["python3", "-V"], cwd="..", timeout_ms=1000)

            with self.assertRaisesRegex(ValueError, "verifier cwd outside workspace"):
                run_verifier(workspace, spec)
