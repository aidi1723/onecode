"""MCP server protocol for ledger, sandbox, and verifier tools."""
from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from onecode.kernel.mcp_server import handle_mcp_message, serve_stdio


class McpServerTests(unittest.TestCase):
    def test_initialize_and_tools_list(self) -> None:
        initialized = handle_mcp_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        })
        self.assertEqual(initialized["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "onecode")
        listed = handle_mcp_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = [item["name"] for item in listed["result"]["tools"]]
        self.assertEqual(names, ["onecode_ledger", "onecode_sandbox", "onecode_verify"])
        self.assertIsNone(handle_mcp_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_ledger_sandbox_and_verify_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ledger = handle_mcp_message({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "onecode_ledger", "arguments": {"workspace": str(workspace)}},
            })
            ledger_body = json.loads(ledger["result"]["content"][0]["text"])
            self.assertEqual(ledger_body["runs"], [])

            with patch("onecode.kernel.sandbox.run_sandbox_smoke", return_value={"status": "blocked", "reason": "docker_not_found"}):
                sandbox = handle_mcp_message({
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "onecode_sandbox", "arguments": {"workspace": str(workspace)}},
                })
            sandbox_body = json.loads(sandbox["result"]["content"][0]["text"])
            self.assertEqual(sandbox_body["reason"], "docker_not_found")

            verify = handle_mcp_message({
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "onecode_verify", "arguments": {"workspace": str(workspace)}},
            })
            verify_body = json.loads(verify["result"]["content"][0]["text"])
            self.assertEqual(verify_body["reason"], "tests_absent")

    def test_stdio_round_trip_ignores_notifications(self) -> None:
        incoming = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": {}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        )
        outgoing = io.StringIO()
        serve_stdio(incoming, outgoing)
        lines = [line for line in outgoing.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], 7)


if __name__ == "__main__":
    unittest.main()
