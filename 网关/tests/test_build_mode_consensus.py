import tempfile
import unittest
from pathlib import Path

from agent_skill_dictionary.build_mode_consensus import (
    append_node_event,
    sign_evidence_envelope,
    verify_evidence_envelope,
)


class BuildModeConsensusTest(unittest.TestCase):
    def test_signed_envelope_verifies_with_same_secret(self):
        envelope = sign_evidence_envelope(
            node_id="n100",
            hexagram="111",
            evidence={"changed_files": ["core/crypto.py"]},
            secret=b"test-secret",
            timestamp_ms=123,
        )

        self.assertTrue(verify_evidence_envelope(envelope, b"test-secret"))
        self.assertFalse(verify_evidence_envelope(envelope, b"wrong-secret"))

    def test_append_node_event_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "node-state.jsonl"
            envelope = sign_evidence_envelope("n100", "001", {"exit_code": 1}, b"s", timestamp_ms=1)
            append_node_event(path, envelope)

            text = path.read_text(encoding="utf-8")
            self.assertIn('"node_id": "n100"', text)
            self.assertIn('"hexagram": "001"', text)


if __name__ == "__main__":
    unittest.main()
