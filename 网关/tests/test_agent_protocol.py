import unittest

from agent_skill_dictionary.agent_protocol import build_agent_protocol_manifest
from agent_skill_dictionary.gateway_server import protocol_payload


class AgentProtocolTest(unittest.TestCase):
    def test_protocol_manifest_describes_agent_agnostic_contract(self):
        manifest = build_agent_protocol_manifest()

        self.assertEqual(manifest["name"], "oneword-agent-control-protocol")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["compatibility"], "agent-agnostic")
        self.assertEqual(
            [endpoint["path"] for endpoint in manifest["endpoints"]],
            [
                "/v1/yizijue/protocol",
                "/v1/yizijue/resolve",
                "/v1/yizijue/preflight-tool",
                "/v1/yizijue/submit-evidence",
                "/v1/yizijue/run",
                "/v1/chat/completions",
            ],
        )

    def test_protocol_manifest_exposes_final_root_tool_contracts(self):
        manifest = build_agent_protocol_manifest()
        roots = manifest["root_opcodes"]

        self.assertEqual(roots["查"]["binary_trigram"], "101")
        self.assertEqual(
            roots["查"]["allowed_tools"],
            ["native_inspect_card", "read_file", "list_directory", "grep_code", "git_diff"],
        )
        self.assertEqual(roots["总"]["allowed_tools"], ["compress_tokens"])
        self.assertEqual(roots["卫"]["physical_control_flows"]["source_write"], "forbidden")
        self.assertEqual(roots["修"]["physical_control_flows"]["source_write"], "scoped")
        self.assertEqual(roots["停"]["halt_model_forwarding"], True)

    def test_protocol_manifest_declares_evidence_and_audit_contract(self):
        manifest = build_agent_protocol_manifest()

        self.assertEqual(
            manifest["evidence_contract"]["audit_fields"],
            ["timestamp", "command", "exit_code", "stdout_digest", "stderr_digest", "sha256", "previous_sha256"],
        )
        self.assertEqual(manifest["evidence_contract"]["audit_log_write_access"], "system_only")
        self.assertEqual(manifest["required_agent_loop"][0], "resolve")
        self.assertIn("preflight_tool", manifest["required_agent_loop"])
        self.assertIn("submit_evidence", manifest["required_agent_loop"])
        self.assertEqual(
            manifest["reference_adapter"]["module"],
            "agent_skill_dictionary.reference_agent_adapter",
        )
        self.assertIn("submit-evidence", manifest["reference_adapter"]["purpose"])

    def test_gateway_protocol_payload_is_available_without_fastapi(self):
        payload = protocol_payload()

        self.assertEqual(payload["compatibility"], "agent-agnostic")
        self.assertIn("root_opcodes", payload)


if __name__ == "__main__":
    unittest.main()
