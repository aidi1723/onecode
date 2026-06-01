import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.runner import run_task
from onecode.kernel.task_resume import PlannedAsset, classify_task_resume
from onecode.kernel.verifier import VerifierSpec


class TaskResumeClassificationTests(unittest.TestCase):
    def test_missing_source_manifest_classifies_assets_as_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="missing-source",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 1\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "apply")
            self.assertEqual(summary.decisions[0].target_type, "asset")
            self.assertEqual(summary.decisions[0].target_id, "src/a.py")
            self.assertEqual(summary.decisions[0].reason, "missing_source_manifest")

    def test_matching_completed_asset_classifies_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
            )

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "ready")
            self.assertEqual(summary.decisions[0].reason, None)

    def test_matching_wal_only_completed_asset_classifies_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "ready")
            self.assertEqual(summary.decisions[0].reason, None)

    def test_modified_wal_only_completed_asset_classifies_as_halt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )
            (workspace / "src" / "a.py").write_text("A = 99\n", encoding="utf-8")

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "halt")
            self.assertEqual(summary.decisions[0].reason, "asset_hash_conflict")

    def test_tampered_wal_only_source_classifies_task_as_halt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )
            wal_path = workspace / ".onecode" / "global-ledger.jsonl"
            entry = json.loads(wal_path.read_text(encoding="utf-8").splitlines()[0])
            entry["st"] = "completed-but-tampered"
            wal_path.write_text(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "halt")
            self.assertEqual(summary.decisions[0].target_type, "task")
            self.assertEqual(summary.decisions[0].reason, "source_evidence_corrupt")

    def test_modified_completed_asset_classifies_as_halt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
            )
            (workspace / "src" / "a.py").write_text("A = 99\n", encoding="utf-8")

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[],
            )

            self.assertEqual(summary.decisions[0].kind, "halt")
            self.assertEqual(summary.decisions[0].reason, "asset_hash_conflict")

    def test_ready_asset_without_selected_verifier_evidence_classifies_verify_and_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
            )
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "unittest"],
                cwd=".",
                timeout_ms=1000,
            )

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[spec],
            )

            decisions = {(decision.target_type, decision.target_id): decision for decision in summary.decisions}
            self.assertEqual(decisions[("asset", "src/a.py")].kind, "verify")
            self.assertEqual(decisions[("asset", "src/a.py")].reason, "missing_verifier_evidence")
            self.assertEqual(decisions[("verifier", "python-unittest")].kind, "apply")

    def test_matching_passed_verifier_classifies_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
            )
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "unittest"],
                cwd=".",
                timeout_ms=1000,
            )
            ledger_path = Path(result["ledger_path"])
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["verifier_results"] = [
                {
                    "id": "python-unittest",
                    "status": "passed",
                    "reason": None,
                    "exit_code": 0,
                    "duration_ms": 1,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "stdout_sha256": "0" * 64,
                    "stderr_sha256": "0" * 64,
                    "cwd": ".",
                    "command": ["python3", "-m", "unittest"],
                    "timeout_ms": 1000,
                }
            ]
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[spec],
            )

            decisions = {(decision.target_type, decision.target_id): decision for decision in summary.decisions}
            self.assertEqual(decisions[("asset", "src/a.py")].kind, "ready")
            self.assertEqual(decisions[("verifier", "python-unittest")].kind, "ready")

    def test_changed_verifier_policy_classifies_as_halt(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = run_task(
                "source",
                workspace=workspace,
                run_id="source-run",
                write_path="src/a.py",
                write_content="A = 1\n",
            )
            ledger_path = Path(result["ledger_path"])
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["verifier_results"] = [
                {
                    "id": "python-unittest",
                    "status": "passed",
                    "reason": None,
                    "exit_code": 0,
                    "duration_ms": 1,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "stdout_sha256": "0" * 64,
                    "stderr_sha256": "0" * 64,
                    "cwd": ".",
                    "command": ["python3", "-m", "unittest"],
                    "timeout_ms": 1000,
                }
            ]
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            spec = VerifierSpec(
                id="python-unittest",
                command=["python3", "-m", "compileall"],
                cwd=".",
                timeout_ms=1000,
            )

            summary = classify_task_resume(
                workspace=workspace,
                source_run_id="source-run",
                planned_assets=[PlannedAsset(path="src/a.py", content="A = 2\n")],
                verifier_specs=[spec],
            )

            decisions = {(decision.target_type, decision.target_id): decision for decision in summary.decisions}
            self.assertEqual(decisions[("verifier", "python-unittest")].kind, "halt")
            self.assertEqual(decisions[("verifier", "python-unittest")].reason, "verifier_policy_changed")
