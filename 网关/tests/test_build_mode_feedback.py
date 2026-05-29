import json
import unittest

from agent_skill_dictionary.build_mode_feedback import build_sse_soft_chunks, rewrite_to_soft_payload
from agent_skill_dictionary.build_mode_types import HEX_HALT, HEX_INSPECT, ViolationEvidence


class BuildModeFeedbackTest(unittest.TestCase):
    def test_violation_rewrites_to_http_200_payload(self):
        evidence = ViolationEvidence(blocked_action="rm -rf /tmp/x", reason="dangerous_command", source="path_preflight")
        payload = rewrite_to_soft_payload(evidence)
        self.assertEqual(payload["http_status"], 200)
        self.assertEqual(payload["stderr"], "")
        self.assertEqual(payload["feedback"]["source_hexagram"], HEX_HALT)
        self.assertEqual(payload["feedback"]["next_hexagram"], HEX_INSPECT)

    def test_sse_chunks_are_data_events_and_done(self):
        evidence = ViolationEvidence(blocked_action="rm -rf /tmp/x", reason="dangerous_command", source="path_preflight")
        chunks = list(build_sse_soft_chunks(evidence))
        self.assertTrue(chunks[0].startswith("data: "))
        self.assertTrue(all(chunk.endswith("\n\n") for chunk in chunks))
        self.assertEqual(chunks[-1], "data: [DONE]\n\n")
        json.loads(chunks[0][len("data: "):])


if __name__ == "__main__":
    unittest.main()
