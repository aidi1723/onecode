import os
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch
from pathlib import Path

from onecode.kernel.execution_contracts import ExecutionStep, GuardrailConfig, ToolCallSpec
from onecode.kernel.execution_guardrails import should_require_approval
from onecode.kernel.model_provider import ModelExecutionStep, ModelPlan, ModelToolCall


SERVER = textwrap.dedent(
    """
    import json
    import sys

    def read_message():
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        return json.loads(line)

    def write_message(payload):
        sys.stdout.buffer.write(json.dumps(payload).encode() + bytes([10]))
        sys.stdout.buffer.flush()

    while True:
        message = read_message()
        if message is None:
            break
        method = message.get("method")
        if method == "notifications/initialized" or "id" not in message:
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "fixture", "version": "0"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "description": "echo", "inputSchema": {"type": "object"}}]}
        elif method == "tools/call":
            text = message.get("params", {}).get("arguments", {}).get("text", "")
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        else:
            write_message({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "unknown"}})
            continue
        write_message({"jsonrpc": "2.0", "id": message["id"], "result": result})
    """
)


class McpClientTests(unittest.TestCase):
    def test_connection_failure_registers_nothing_and_reports_action_exception(self):
        from onecode.kernel.execution_tools import default_tool_registry
        from onecode.kernel.mcp_client import register_mcp_tools

        registry = default_tool_registry()
        before = registry.names()
        result = register_mcp_tools(registry, server_name="fixture", command=["/nonexistent/onecode-mcp"], remote_names=[])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["tools"], [])
        self.assertEqual(result["tools"], [])
        self.assertEqual(registry.names(), before)

    def test_listed_tool_requires_approval_and_returns_text(self):
        from onecode.kernel.approval_plans import model_plan_requires_approval
        from onecode.kernel.execution_tools import default_tool_registry
        from onecode.kernel.mcp_client import register_mcp_tools

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            script = workspace / "server.py"
            script.write_text(SERVER, encoding="utf-8")
            registry = default_tool_registry()
            with patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}, clear=False):
                with patch("subprocess.Popen") as mock_popen:
                    registered = register_mcp_tools(
                        registry,
                        server_name="fixture",
                        command=[sys.executable, str(script)],
                        remote_names=["echo"],
                    )
                    self.assertEqual(mock_popen.call_count, 0)
                tool = registry.get("mcp.fixture.echo")
                output = tool.execute({"arguments": {"text": "ping"}}, workspace)

        self.assertEqual(registered["status"], "completed")
        self.assertEqual(registered["tools"], ["mcp.fixture.echo"])
        self.assertTrue(tool.requires_approval)
        self.assertEqual(output["status"], "completed")
        self.assertEqual(output["content"], "ping")
        step = ExecutionStep(
            id="call",
            description="call echo",
            tool_calls=[ToolCallSpec(tool_name="mcp.fixture.echo", params={"arguments": {"text": "ping"}})],
        )
        plan = ModelPlan(
            task="echo",
            execution_steps=[
                ModelExecutionStep(
                    id="call",
                    description="call echo",
                    tool_calls=[ModelToolCall(tool_name="mcp.fixture.echo", params={"arguments": {"text": "ping"}})],
                )
            ],
        )
        self.assertTrue(should_require_approval(step, GuardrailConfig()))
        self.assertTrue(model_plan_requires_approval(plan))

    def test_read_only_cycle_rejects_mcp_and_open_cycle_can_call_it(self):
        from onecode.kernel.agent_cycle import run_agent_cycle

        denied = []

        def deny_after_miss(history, allowed):
            if not history:
                return [{"tool_name": "search_text", "params": {}}]
            return [{"tool_name": "mcp.fixture.echo", "params": {}}]

        def execute(name, params):
            denied.append(name)
            return {"status": "completed", "reason": "search_miss"}

        blocked = run_agent_cycle(propose=deny_after_miss, execute=execute, max_turns=4)
        allowed_calls = []

        def call_then_stop(history, allowed):
            if history:
                return []
            return [{"tool_name": "mcp.fixture.echo", "params": {"arguments": {"text": "ping"}}}]

        def run(name, params):
            allowed_calls.append((name, params))
            return {"status": "completed", "reason": None, "content": "ping"}

        completed = run_agent_cycle(
            propose=call_then_stop,
            execute=run,
            approve=lambda tool_name, params: tool_name == "mcp.fixture.echo",
            max_turns=4,
        )

        self.assertEqual(blocked["reason"], "permission_denied")
        self.assertEqual(denied, ["search_text"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(allowed_calls, [("mcp.fixture.echo", {"arguments": {"text": "ping"}})])

    def test_mcp_proxy_tool_plan_action_exposes_command_and_host_execution(self):
        from onecode.kernel.mcp_client import McpProxyTool
        from onecode.kernel.model_loop import approval_action_summaries
        from onecode.web.api import _approval_visible_text

        tool = McpProxyTool(
            name="mcp.custom.run",
            requires_approval=True,
            command=("python3", "custom_mcp.py"),
            remote_name="run",
        )
        with patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "host"}, clear=False):
            plan_action = tool.plan_action({"arguments": {"query": "test"}})
        self.assertEqual(plan_action["command"], ["python3", "custom_mcp.py"])
        self.assertTrue(plan_action["host_execution"])

        plan = ModelPlan(
            task="run mcp",
            execution_steps=[
                ModelExecutionStep(
                    id="step-1",
                    description="run mcp",
                    tool_calls=[ModelToolCall(tool_name="mcp.custom.list_tools", params={"arguments": {"query": "test"}})],
                )
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            (home / "mcp_servers.json").write_text(
                '{"mcpServers": {"custom": {"command": ["python3", "custom_mcp.py"]}}}',
                encoding="utf-8",
            )
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            planted = workspace / ".onecode"
            planted.mkdir()
            (planted / "mcp_servers.json").write_text(
                '{"mcpServers": {"custom": {"command": ["touch", "marker"]}}}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"ONECODE_HOME": str(home), "ONECODE_RUN_COMMAND_SANDBOX": "host"}, clear=False):
                actions = approval_action_summaries(plan, workspace)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["command"], ["python3", "custom_mcp.py"])
        self.assertTrue(actions[0]["host_execution"])
        visible = _approval_visible_text({"reason": "approval_required"}, actions)
        self.assertIn("MCP 外部命令（将在宿主机执行）", visible)
        self.assertNotIn("touch marker", visible)

    def test_auto_mode_does_not_launch_mcp_on_the_host(self):
        from onecode.kernel.mcp_client import McpProxyTool

        tool = McpProxyTool(
            name="mcp.custom.run",
            requires_approval=True,
            command=("python3", "custom_mcp.py"),
            remote_name="run",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ONECODE_RUN_COMMAND_SANDBOX": "auto"}, clear=False):
                with patch("onecode.kernel.execution_tools._docker_daemon_ready", return_value=False):
                    with patch("subprocess.Popen") as mock_popen:
                        output = tool.execute({"arguments": {}}, Path(tmp))
        mock_popen.assert_not_called()
        self.assertEqual(output["reason"], "sandbox_required")
        self.assertFalse(tool.plan_action({"arguments": {}})["host_execution"])


if __name__ == "__main__":
    unittest.main()
