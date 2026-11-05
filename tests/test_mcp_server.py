"""MCP server protocol for ledger, sandbox, verifier, diagnostics, and symbol locator tools."""
from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from onecode.kernel.mcp_server import (
    generate_mcp_client_config,
    handle_mcp_message,
    serve_stdio,
)


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
        expected = [
            "onecode_ledger",
            "onecode_sandbox",
            "onecode_verify",
            "onecode_doctor",
            "onecode_locate",
            "onecode_audit",
        ]
        self.assertEqual(names, expected)
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

    def test_doctor_locate_and_audit_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            doc_msg = handle_mcp_message({
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "onecode_doctor", "arguments": {}},
            })
            doc_body = json.loads(doc_msg["result"]["content"][0]["text"])
            self.assertIn("checks", doc_body)

            # Create sample python file for locator
            src_dir = workspace / "src"
            src_dir.mkdir()
            (src_dir / "calculator.py").write_text(
                "def add(a: int, b: int) -> int:\n    return a + b\n",
                encoding="utf-8",
            )
            tb = 'Traceback (most recent call last):\n  File "src/calculator.py", line 2, in add\n    return a + b\n'
            loc_msg = handle_mcp_message({
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "onecode_locate",
                    "arguments": {"workspace": str(workspace), "traceback": tb},
                },
            })
            loc_body = json.loads(loc_msg["result"]["content"][0]["text"])
            self.assertEqual(loc_body["status"], "completed")

            audit_msg = handle_mcp_message({
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "onecode_audit", "arguments": {"workspace": str(workspace)}},
            })
            audit_body = json.loads(audit_msg["result"]["content"][0]["text"])
            self.assertEqual(audit_body["status"], "completed")
            self.assertFalse(audit_body["tamper_detected"])

    def test_generate_mcp_client_config(self) -> None:
        claude_cfg = generate_mcp_client_config("claude")
        self.assertIn("onecode", claude_cfg["mcpServers"])
        self.assertEqual(claude_cfg["mcpServers"]["onecode"]["args"], ["-m", "onecode.kernel.mcp_server"])

        cursor_cfg = generate_mcp_client_config("cursor")
        self.assertIn("onecode", cursor_cfg["mcpServers"])

        goose_cfg = generate_mcp_client_config("goose")
        self.assertIn("onecode", goose_cfg["extensions"])
        self.assertEqual(goose_cfg["extensions"]["onecode"]["type"], "stdio")

    def test_cli_mcp_config_output(self) -> None:
        from contextlib import redirect_stdout
        from onecode.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["mcp", "--config", "--target", "cursor"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("mcpServers", data)
        self.assertIn("onecode", data["mcpServers"])

    def test_stdio_round_trip_ignores_notifications(self) -> None:
        incoming = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        )
        outgoing = io.StringIO()
        serve_stdio(incoming, outgoing)
        lines = [line for line in outgoing.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], 9)


if __name__ == "__main__":
    unittest.main()
