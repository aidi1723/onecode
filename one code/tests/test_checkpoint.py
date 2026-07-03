import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from onecode.kernel.checkpoint import file_lock, sha256_file, skill_selection_sha256, write_checkpoint, write_ledger
from onecode.kernel.context import create_context
from onecode.kernel.hexagram import COMPLETE


class CheckpointTests(unittest.TestCase):
    def test_file_lock_uses_os_level_flock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "evidence.lock"

            with patch("onecode.kernel.checkpoint.fcntl.flock") as flock:
                with file_lock(lock_path):
                    pass

            self.assertEqual(flock.call_count, 2)

    def test_write_checkpoint_updates_manifest_with_matching_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="checkpoint-test")
            checkpoint_path = write_checkpoint(
                context=context,
                payload={"task": "smoke", "status": "completed"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))

            self.assertEqual(checkpoint["next_state"], "000000")
            self.assertIn("duration_ms", checkpoint)
            self.assertGreaterEqual(checkpoint["duration_ms"], 0)
            self.assertEqual(manifest["run_id"], "checkpoint-test")
            self.assertEqual(manifest["current_state"], "000000")
            self.assertEqual(manifest["status"], "completed")
            self.assertFalse(manifest["partial"])
            self.assertEqual(manifest["checkpoints"][0]["sha256"], sha256_file(checkpoint_path))
            self.assertIn("duration_ms", manifest["checkpoints"][0])

    def test_write_ledger_creates_user_facing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-test")
            ledger_path = write_ledger(
                context,
                {
                    "run_id": "ledger-test",
                    "status": "completed",
                    "state": "000000",
                    "partial": False,
                    "reason": None,
                },
            )

            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["run_id"], "ledger-test")
            self.assertEqual(ledger["status"], "completed")

    def test_write_ledger_keeps_append_only_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-history-test")

            write_ledger(context, {"run_id": "ledger-history-test", "status": "halted"})
            ledger_path = write_ledger(context, {"run_id": "ledger-history-test", "status": "completed"})

            latest = json.loads(ledger_path.read_text(encoding="utf-8"))
            history_path = ledger_path.with_suffix(".jsonl")
            history = [
                json.loads(line)
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            self.assertEqual(latest["status"], "completed")
            self.assertEqual([entry["status"] for entry in history], ["halted", "completed"])

    def test_write_ledger_appends_tamper_evident_chain_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-chain-test")

            write_ledger(context, {"run_id": "ledger-chain-test", "status": "halted"})
            write_ledger(context, {"run_id": "ledger-chain-test", "status": "completed"})

            chain_path = context.evidence_root / "evidence-chain.jsonl"
            records = [
                json.loads(line)
                for line in chain_path.read_text(encoding="utf-8").splitlines()
                if line
            ]

            self.assertEqual([record["sequence"] for record in records], [1, 2])
            self.assertEqual([record["artifact_type"] for record in records], ["ledger", "ledger"])
            self.assertEqual(records[0]["previous_chain_hash"], "0" * 64)
            self.assertEqual(records[1]["previous_chain_hash"], records[0]["chain_hash"])
            self.assertRegex(records[0]["artifact_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(records[0]["chain_hash"], r"^[0-9a-f]{64}$")

    def test_write_ledger_rejects_invalid_skill_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="ledger-skill-selection-invalid")

            with self.assertRaisesRegex(ValueError, "skill_selection_forbidden_field:allowed_tools"):
                write_ledger(
                    context,
                    {
                        "run_id": "ledger-skill-selection-invalid",
                        "status": "completed",
                        "partial": False,
                        "reason": None,
                        "skill_selection": {
                            "status": "ok",
                            "selection_reason": "capability_match",
                            "selected_count": 1,
                            "selected_skills": [
                                {
                                    "name": "code-test-regression",
                                    "mode": "method_only",
                                    "risk": "low",
                                    "matched_capabilities": ["test"],
                                    "content_sha256": "a" * 64,
                                    "allowed_tools": ["pytest"],
                                }
                            ],
                            "selection_sha256": "b" * 64,
                        },
                    },
                )


class AppendOnlyManifestTests(unittest.TestCase):
    def test_write_checkpoint_preserves_prior_checkpoint_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="append-test")

            first = write_checkpoint(
                context=context,
                payload={"task": "one"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="noop",
                decision="allowed",
            )
            second = write_checkpoint(
                context=context,
                payload={"task": "two"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="write_text",
                decision="allowed",
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["checkpoints"]), 2)
            self.assertEqual(manifest["checkpoints"][0]["path"], str(first))
            self.assertEqual(manifest["checkpoints"][0]["intent_type"], "noop")
            self.assertEqual(manifest["checkpoints"][1]["path"], str(second))
            self.assertEqual(manifest["checkpoints"][1]["intent_type"], "write_text")

    def test_patch_checkpoint_manifest_record_indexes_patch_hash_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="patch-manifest-index")
            payload = {
                "path": "src/a.py",
                "sha256": "post",
                "pre_sha256": "pre",
                "post_sha256": "post",
                "search_block_sha256": "search",
                "replace_block_sha256": "replace",
            }

            write_checkpoint(
                context=context,
                payload=payload,
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                intent_type="patch_text",
                decision="allowed",
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            record = manifest["checkpoints"][0]

            self.assertEqual(record["patch_evidence"], {
                "pre_sha256": "pre",
                "post_sha256": "post",
                "search_block_sha256": "search",
                "replace_block_sha256": "replace",
            })


class ManifestBoundaryTests(unittest.TestCase):
    def test_write_checkpoint_persists_bounded_skill_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-valid")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [
                    {
                        "name": "code-test-regression",
                        "mode": "method_only",
                        "risk": "low",
                        "matched_capabilities": ["test", "verification"],
                        "content_sha256": "a" * 64,
                    }
                ],
                "selected_count": 1,
                "skill_context_summary": {"skill_count": 1, "invalid_count": 0, "element": "water"},
                "iching_status_code": 17,
                "iching_transition_action": "checkpoint",
                "iching_transition_reason": "network_water_preserves_resume_seed",
                "dispatch_decision": "stop",
                "selection_sha256": "b" * 64,
            }
            skill_selection["selection_sha256"] = skill_selection_sha256(skill_selection)

            checkpoint_path = write_checkpoint(
                context=context,
                payload={"task": "skill evidence"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                skill_selection=skill_selection,
            )

            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["skill_selection"], skill_selection)
            self.assertEqual(manifest["skill_selection"], skill_selection)
            self.assertEqual(manifest["checkpoints"][0]["skill_selection"], skill_selection)

    def test_write_checkpoint_rejects_skill_selection_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-hash-mismatch")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [
                    {
                        "name": "code-test-regression",
                        "mode": "method_only",
                        "risk": "low",
                        "matched_capabilities": ["test"],
                        "content_sha256": "a" * 64,
                    }
                ],
                "selected_count": 1,
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_hash_mismatch"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_invalid_skill_selection_rule_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-rule-metadata")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [],
                "selected_count": 0,
                "iching_status_code": "17",
            }
            skill_selection["selection_sha256"] = skill_selection_sha256(skill_selection)

            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_field:iching_status_code"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [],
                "selected_count": 0,
                "iching_transition_action": "raw body text",
            }
            skill_selection["selection_sha256"] = skill_selection_sha256(skill_selection)

            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_field:iching_transition_action"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_skill_selection_forbidden_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-forbidden")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [
                    {
                        "name": "code-test-regression",
                        "mode": "method_only",
                        "risk": "low",
                        "matched_capabilities": ["test"],
                        "content_sha256": "a" * 64,
                        "allowed_tools": ["pytest"],
                    }
                ],
                "selected_count": 1,
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_forbidden_field:allowed_tools"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_raw_fields_inside_skill_context_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-summary-forbidden")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [],
                "selected_count": 0,
                "skill_context_summary": {
                    "skill_count": 1,
                    "invalid_count": 0,
                    "element": "water",
                    "allowed_tools": ["pytest"],
                },
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_summary_forbidden_field:allowed_tools"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_invalid_skill_selection_status_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-status-reason")
            skill_selection = {
                "status": "ok",
                "selection_reason": "private body text",
                "selected_skills": [],
                "selected_count": 0,
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_field:selection_reason"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

            skill_selection["selection_reason"] = "capability_match"
            skill_selection["status"] = "trusted"
            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_field:status"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_invalid_selected_skill_mode_and_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-mode-risk")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [
                    {
                        "name": "code-test-regression",
                        "mode": "execute",
                        "risk": "low",
                        "matched_capabilities": ["test"],
                        "content_sha256": "a" * 64,
                    }
                ],
                "selected_count": 1,
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_selected_field:mode"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

            skill_selection["selected_skills"][0]["mode"] = "method_only"
            skill_selection["selected_skills"][0]["risk"] = "critical"
            with self.assertRaisesRegex(ValueError, "skill_selection_invalid_selected_field:risk"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_skill_selection_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-count")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [],
                "selected_count": 1,
                "selection_sha256": "b" * 64,
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_count_mismatch"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_boolean_skill_selection_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-bool-count")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [
                    {
                        "name": "code-test-regression",
                        "mode": "method_only",
                        "risk": "low",
                        "matched_capabilities": ["test"],
                        "content_sha256": "a" * 64,
                    }
                ],
                "selected_count": True,
            }
            skill_selection["selection_sha256"] = skill_selection_sha256(skill_selection)

            with self.assertRaisesRegex(ValueError, "skill_selection_count_mismatch"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_rejects_oversized_skill_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="skill-selection-oversized")
            skill_selection = {
                "status": "ok",
                "selection_reason": "capability_match",
                "selected_skills": [],
                "selected_count": 0,
                "selection_sha256": "b" * 64,
                "skill_context_summary": {"padding": "x" * 8000},
            }

            with self.assertRaisesRegex(ValueError, "skill_selection_too_large"):
                write_checkpoint(
                    context=context,
                    payload={"task": "skill evidence"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    skill_selection=skill_selection,
                )

    def test_write_checkpoint_persists_bounded_domain_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["trace:span-123", "wal:global-ledger:456"],
            }

            write_checkpoint(
                context=context,
                payload={"task": "domain transition"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
                domain_projection=projection,
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["manifest_schema_version"], 1)
            self.assertEqual(manifest["domain_projection"], projection)
            self.assertEqual(manifest["manifest_metrics"]["domain_projection_count"], 1)
            self.assertGreater(manifest["manifest_metrics"]["section_sizes"]["checkpoints"], 0)

    def test_write_checkpoint_rejects_business_workflow_graph_in_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-reject")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["trace:span-123"],
                "transitions": [{"from": "a", "to": "b"}],
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_forbidden_field"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_unknown_domain_projection_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-unknown-field")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["trace:span-123"],
                "approval_timeout_seconds": 30,
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_unknown_field"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_oversized_domain_projection_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-oversized-field")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-" + "x" * 300,
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["trace:span-123"],
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_field_too_large:decision_id"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_too_many_domain_projection_evidence_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-too-many-refs")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": [f"trace:span-{index}" for index in range(40)],
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_too_many_evidence_refs"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_malformed_domain_projection_evidence_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-bad-ref")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["workflow-engine-hidden-config"],
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_invalid_evidence_ref"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_domain_projection_control_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="domain-projection-control-char")
            projection = {
                "schema_id": "order-workflow/v3",
                "entity_id_hash": "sha256:" + "a" * 64,
                "from_state": "payment_authorized\nhidden_state",
                "to_state": "fulfillment_requested",
                "decision_id": "workflow-decision-018",
                "decision_hash": "sha256:" + "b" * 64,
                "evidence_refs": ["trace:span-123"],
            }

            with self.assertRaisesRegex(ValueError, "domain_projection_invalid_charset:from_state"):
                write_checkpoint(
                    context=context,
                    payload={"task": "domain transition"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                    domain_projection=projection,
                )

    def test_write_checkpoint_rejects_manifest_metrics_threshold_breach(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="manifest-threshold")
            context.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            context.manifest_path.write_text(
                json.dumps(
                    {
                        "manifest_schema_version": 1,
                        "run_id": "manifest-threshold",
                        "created_at": "2026-06-02T00:00:00+00:00",
                        "checkpoints": [{"path": "x" * 260_000, "sha256": "a" * 64}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "manifest_metrics_total_bytes_exceeded"):
                write_checkpoint(
                    context=context,
                    payload={"task": "small"},
                    next_state=COMPLETE,
                    status="completed",
                    partial=False,
                    reason=None,
                )

    def test_manifest_metrics_count_embedded_and_referenced_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            context = create_context(Path(tmp), run_id="manifest-metrics")

            write_checkpoint(
                context=context,
                payload={"task": "metric"},
                next_state=COMPLETE,
                status="completed",
                partial=False,
                reason=None,
            )

            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
            metrics = manifest["manifest_metrics"]
            self.assertGreater(metrics["total_bytes"], 0)
            self.assertGreater(metrics["largest_field_bytes"], 0)
            self.assertIn("embedded_to_referenced_bytes_ratio", metrics)


class ResumedCheckpointMetadataTests(unittest.TestCase):
    def test_write_checkpoint_persists_resume_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            asset = workspace / "src" / "ready.py"
            asset.parent.mkdir(parents=True)
            asset.write_text("ready = True\n", encoding="utf-8")
            asset_hash = sha256_file(asset)

            old_run = workspace / ".onecode" / "runs" / "old-run"
            old_checkpoint = old_run / "checkpoints" / "0001.json"
            old_checkpoint.parent.mkdir(parents=True)
            old_checkpoint.write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "intent_type": "write_text",
                        "decision": "allowed",
                        "turn_index": 1,
                        "payload": {"path": str(asset), "sha256": asset_hash},
                    }
                ),
                encoding="utf-8",
            )
            (old_run / "manifest.json").write_text(
                json.dumps({"run_id": "old-run", "checkpoints": [{"path": str(old_checkpoint)}]}),
                encoding="utf-8",
            )

            context = create_context(workspace, run_id="retry-run", resume_from_run_id="old-run")
            checkpoint_path = write_checkpoint(
                context=context,
                payload={"path": "src/ready.py", "sha256": asset_hash},
                next_state=COMPLETE,
                status="skipped",
                partial=False,
                reason="resumed_asset_ready",
                intent_type="write_text",
                decision="allowed",
            )

            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(checkpoint["resumed_from"], "old-run")
            self.assertEqual(checkpoint["ready_assets"]["src/ready.py"]["sha256"], asset_hash)
            self.assertEqual(checkpoint["resume_audit_events"][0]["path"], "src/ready.py")
            self.assertEqual(checkpoint["resume_audit_events"][0]["status"], "ready")
            self.assertEqual(manifest["resumed_from"], "old-run")
            self.assertEqual(manifest["ready_assets"]["src/ready.py"]["source_run_id"], "old-run")
            self.assertEqual(manifest["resume_audit_events"][0]["path"], "src/ready.py")


if __name__ == "__main__":
    unittest.main()
