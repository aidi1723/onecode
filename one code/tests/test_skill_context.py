import json
import tempfile
import unittest
from pathlib import Path

from onecode.kernel.hexagram import IchingKernel


class SkillContextTests(unittest.TestCase):
    def test_discovers_valid_project_skill_manifest_without_raw_body(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "code-test-regression.json").write_text(
                json.dumps(
                    {
                        "name": "code-test-regression",
                        "version": "1",
                        "description": "Guides regression test creation.",
                        "capabilities": ["test", "verification", "test"],
                        "risk": "low",
                        "mode": "method_only",
                        "allowed_tools": ["pytest"],
                        "verifier_expectations": ["focused_test"],
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["skill_count"], 1)
        self.assertEqual(payload["summary"]["element"], "water")
        self.assertEqual(payload["skills"][0]["name"], "code-test-regression")
        self.assertEqual(payload["skills"][0]["source"], "project")
        self.assertEqual(payload["skills"][0]["risk"], "low")
        self.assertEqual(payload["skills"][0]["mode"], "method_only")
        self.assertEqual(payload["skills"][0]["capability_count"], 2)
        self.assertEqual(payload["skills"][0]["capabilities"], ["test", "verification"])
        self.assertIn("content_sha256", payload["skills"][0])
        self.assertNotIn("description", payload["skills"][0])
        self.assertNotIn("allowed_tools", payload["skills"][0])
        self.assertNotIn("verifier_expectations", payload["skills"][0])
        serialized = json.dumps(payload)
        self.assertNotIn("description", serialized)
        self.assertNotIn("allowed_tools", serialized)
        self.assertNotIn("verifier_expectations", serialized)
        self.assertNotIn("Guides regression test creation.", serialized)
        self.assertNotIn("pytest", serialized)
        self.assertNotIn("focused_test", serialized)

    def test_invalid_skill_manifest_is_reported_without_loading(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "bad.json").write_text("{not json", encoding="utf-8")

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_json")

    def test_unsafe_skill_name_is_invalid(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "unsafe.json").write_text(
                json.dumps(
                    {
                        "name": "../escape",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_name")

    def test_symlinked_skill_manifest_outside_workspace_is_invalid(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            workspace.mkdir()
            outside = base / "outside.json"
            outside.write_text(
                json.dumps(
                    {
                        "name": "outside-skill",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "outside.json").symlink_to(outside)

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "outside_project")
        self.assertEqual(payload["iching_status_code"], IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(payload["iching_transition_action"], "halt")
        self.assertEqual(payload["dispatch_decision"], "stop")

    def test_symlinked_skill_directory_outside_workspace_is_invalid_before_listing(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            workspace.mkdir()
            outside_dir = base / "outside-skills"
            outside_dir.mkdir()
            (outside_dir / "outside.json").write_text(
                json.dumps(
                    {
                        "name": "outside-skill",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )
            onecode_dir = workspace / ".onecode"
            onecode_dir.mkdir()
            (onecode_dir / "skills").symlink_to(outside_dir, target_is_directory=True)

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0], {"path": ".onecode/skills", "reason": "outside_project"})
        self.assertEqual(payload["iching_status_code"], IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(payload["iching_transition_action"], "halt")
        self.assertEqual(payload["dispatch_decision"], "stop")

    def test_symlinked_onecode_directory_outside_workspace_is_invalid_before_listing(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            workspace.mkdir()
            outside_onecode = base / "outside-onecode"
            outside_skills = outside_onecode / "skills"
            outside_skills.mkdir(parents=True)
            (outside_skills / "outside.json").write_text(
                json.dumps(
                    {
                        "name": "outside-skill",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )
            (workspace / ".onecode").symlink_to(outside_onecode, target_is_directory=True)

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0], {"path": ".onecode", "reason": "outside_project"})
        self.assertEqual(payload["iching_status_code"], IchingKernel.compute_status(IchingKernel.LI, IchingKernel.KUN))
        self.assertEqual(payload["iching_transition_action"], "halt")
        self.assertEqual(payload["dispatch_decision"], "stop")

    def test_oversized_skill_manifest_is_rejected_before_json_loading(self):
        from onecode.kernel.skill_context import MAX_SKILL_MANIFEST_BYTES, discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "large.json").write_text(" " * (MAX_SKILL_MANIFEST_BYTES + 1), encoding="utf-8")

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "manifest_too_large")

    def test_skill_manifest_rejects_excessive_capability_count(self):
        from onecode.kernel.skill_context import MAX_SKILL_CAPABILITIES, discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "too-many.json").write_text(
                json.dumps(
                    {
                        "name": "too-many",
                        "version": "1",
                        "capabilities": [f"cap-{index}" for index in range(MAX_SKILL_CAPABILITIES + 1)],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_capabilities")

    def test_skill_manifest_rejects_overlong_capability_text(self):
        from onecode.kernel.skill_context import MAX_SKILL_FIELD_CHARS, discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "long-capability.json").write_text(
                json.dumps(
                    {
                        "name": "long-capability",
                        "version": "1",
                        "capabilities": ["x" * (MAX_SKILL_FIELD_CHARS + 1)],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "invalid_capabilities")

    def test_public_skill_context_exposes_summary_without_manifest_lists(self):
        from onecode.kernel.skill_context import discover_skill_context, public_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "code-test-regression.json").write_text(
                json.dumps(
                    {
                        "name": "code-test-regression",
                        "version": "1",
                        "description": "private skill body",
                        "capabilities": ["test", "verification"],
                        "risk": "low",
                        "mode": "method_only",
                        "allowed_tools": ["pytest"],
                        "verifier_expectations": ["focused_test"],
                    }
                ),
                encoding="utf-8",
            )

            payload = public_skill_context(discover_skill_context(workspace))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["skill_count"], 1)
        self.assertEqual(payload["summary"]["element"], "water")
        self.assertNotIn("skills", payload)
        self.assertNotIn("invalid_skills", payload)
        serialized = json.dumps(payload)
        self.assertNotIn("private skill body", serialized)
        self.assertNotIn("allowed_tools", serialized)
        self.assertNotIn("pytest", serialized)

    def test_select_skill_evidence_prefers_method_only_matches_without_raw_fields(self):
        from onecode.kernel.skill_context import select_skill_evidence

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            shared = {
                "version": "1",
                "description": "private skill body",
                "capabilities": ["test", "verification"],
                "risk": "low",
                "allowed_tools": ["pytest"],
                "verifier_expectations": ["focused_test"],
            }
            (skill_dir / "reference.json").write_text(
                json.dumps({"name": "reference-skill", "mode": "reference_only", **shared}),
                encoding="utf-8",
            )
            (skill_dir / "method.json").write_text(
                json.dumps({"name": "method-skill", "mode": "method_only", **shared}),
                encoding="utf-8",
            )

            evidence = select_skill_evidence(workspace, "please run test verification")

        self.assertEqual(evidence["status"], "ok")
        self.assertEqual(evidence["selection_reason"], "capability_match")
        self.assertEqual(evidence["selected_count"], 2)
        self.assertEqual([item["name"] for item in evidence["selected_skills"]], ["method-skill", "reference-skill"])
        self.assertEqual(evidence["selected_skills"][0]["matched_capabilities"], ["test", "verification"])
        self.assertIn("selection_sha256", evidence)
        serialized = json.dumps(evidence)
        self.assertNotIn("private skill body", serialized)
        self.assertNotIn("allowed_tools", serialized)
        self.assertNotIn("pytest", serialized)
        self.assertNotIn("focused_test", serialized)
        self.assertNotIn("skill_score", serialized)
        self.assertNotIn("skill_priority", serialized)
        self.assertNotIn("skill_confidence", serialized)

    def test_select_skill_evidence_records_no_match_without_loading_raw_fields(self):
        from onecode.kernel.skill_context import select_skill_evidence

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "docs.json").write_text(
                json.dumps(
                    {
                        "name": "docs-skill",
                        "version": "1",
                        "description": "private docs body",
                        "capabilities": ["documentation"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            evidence = select_skill_evidence(workspace, "run regression tests")

        self.assertEqual(evidence["status"], "ok")
        self.assertEqual(evidence["selection_reason"], "no_matching_capability")
        self.assertEqual(evidence["selected_count"], 0)
        self.assertEqual(evidence["selected_skills"], [])
        self.assertNotIn("private docs body", json.dumps(evidence))

    def test_select_skill_evidence_matches_plural_and_punctuated_task_tokens(self):
        from onecode.kernel.skill_context import select_skill_evidence

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "tests.json").write_text(
                json.dumps(
                    {
                        "name": "test-skill",
                        "version": "1",
                        "capabilities": ["test"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            evidence = select_skill_evidence(workspace, "run-tests, please")

        self.assertEqual(evidence["selection_reason"], "capability_match")
        self.assertEqual(evidence["selected_skills"][0]["matched_capabilities"], ["test"])

    def test_select_skill_evidence_matches_phrase_capabilities_by_component_tokens(self):
        from onecode.kernel.skill_context import select_skill_evidence

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "review.json").write_text(
                json.dumps(
                    {
                        "name": "review-skill",
                        "version": "1",
                        "capabilities": ["code review", "security-audit"],
                        "risk": "low",
                        "mode": "method_only",
                    }
                ),
                encoding="utf-8",
            )

            evidence = select_skill_evidence(workspace, "please do a code review and security audit")

        self.assertEqual(evidence["selection_reason"], "capability_match")
        self.assertEqual(evidence["selected_skills"][0]["matched_capabilities"], ["code_review", "security_audit"])

    def test_duplicate_skill_names_are_reported_once(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            skill_dir = workspace / ".onecode" / "skills"
            skill_dir.mkdir(parents=True)
            manifest = {
                "name": "code-test-regression",
                "version": "1",
                "capabilities": ["test"],
                "risk": "low",
                "mode": "method_only",
            }
            (skill_dir / "a.json").write_text(json.dumps(manifest), encoding="utf-8")
            (skill_dir / "b.json").write_text(json.dumps(manifest), encoding="utf-8")

            payload = discover_skill_context(workspace)

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["summary"]["skill_count"], 1)
        self.assertEqual(payload["summary"]["invalid_count"], 1)
        self.assertEqual(payload["invalid_skills"][0]["reason"], "duplicate_name")

    def test_missing_skill_directory_is_ok_without_loaded_skills(self):
        from onecode.kernel.skill_context import discover_skill_context

        with tempfile.TemporaryDirectory() as tmp:
            payload = discover_skill_context(Path(tmp))

        self.assertEqual(payload["status"], "missing")
        self.assertEqual(payload["summary"]["skill_count"], 0)
        self.assertEqual(payload["summary"]["invalid_count"], 0)
