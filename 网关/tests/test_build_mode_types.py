import unittest

from agent_skill_dictionary.build_mode_types import (
    HEX_CREATE,
    HEX_HALT,
    HEX_INSPECT,
    HEX_RETURN,
    HEX_VERIFY,
    ArchiveEvidence,
    SandboxEvidence,
    SystemStateContext,
    evidence_allows_completion,
)


class BuildModeTypesTest(unittest.TestCase):
    def test_hexagram_constants_are_unique(self):
        values = {HEX_RETURN, HEX_VERIFY, HEX_INSPECT, HEX_HALT, HEX_CREATE}
        self.assertEqual(len(values), 5)
        self.assertEqual(HEX_CREATE, "111")
        self.assertEqual(HEX_VERIFY, "001")

    def test_completion_requires_exit_zero_and_manifest(self):
        sandbox = SandboxEvidence(
            exit_code=0,
            pytest_status="passed",
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            duration_ms=120,
        )
        archive = ArchiveEvidence(
            manifest_path=".yizijue/manifest.json",
            sha256_map={"app/main.py": "c" * 64},
            readonly_status="audit_only",
            lockdown=False,
        )
        self.assertTrue(evidence_allows_completion(sandbox, archive))

    def test_completion_rejects_model_only_claim(self):
        self.assertFalse(evidence_allows_completion("tests passed", None))

    def test_state_context_defaults_to_unlocked_gate(self):
        ctx = SystemStateContext(
            trace_id="trace-1",
            current_hexagram=HEX_CREATE,
            current_scope="11",
            workspace_root="/workspace/sandbox",
        )
        self.assertFalse(ctx.evidence_gate_locked)
        self.assertEqual(ctx.consecutive_failures, 0)


if __name__ == "__main__":
    unittest.main()
