import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipIf(TestClient is None, "fastapi test client is not installed")
class GatewayServerRoutesTest(unittest.TestCase):
    def test_build_mode_tool_route_executes_scoped_write(self):
        import tempfile
        from pathlib import Path

        import agent_skill_dictionary.gateway_server as gateway_server

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONEWORD_GATEWAY_TOKEN": "test-token"},
            clear=False,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/yizijue/build-tool",
                headers={"authorization": "Bearer test-token"},
                json={
                    "workspace": tmp,
                    "tool_name": "write_file",
                    "arguments": {"path": "app/main.py", "content": "VALUE = 1\n"},
                },
            )

            payload = response.json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["next_hexagram"], "001")
            self.assertTrue((Path(tmp) / "app" / "main.py").exists())

    def test_build_mode_tool_route_requires_gateway_auth(self):
        import tempfile

        import agent_skill_dictionary.gateway_server as gateway_server

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONEWORD_GATEWAY_TOKEN": "test-token"},
            clear=False,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/yizijue/build-tool",
                json={"workspace": tmp, "tool_name": "write_file", "arguments": {"path": "x.py"}},
            )

            self.assertEqual(response.status_code, 401)

    def test_resolve_route_requires_gateway_auth(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_GATEWAY_TOKEN": "test-token"},
            clear=False,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post("/v1/yizijue/resolve", json={"input": "查：看看项目结构"})

        self.assertEqual(response.status_code, 401)

    def test_preflight_tool_route_requires_gateway_auth_by_default(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_GATEWAY_TOKEN": "test-token"},
            clear=False,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/yizijue/preflight-tool",
                json={"active_code": "修", "tool_name": "edit_scoped_file", "arguments": {}},
            )

        self.assertEqual(response.status_code, 401)

    def test_invalid_json_body_returns_stable_400(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_GATEWAY_TOKEN": "test-token"},
            clear=False,
        ):
            client = TestClient(gateway_server.create_app(), raise_server_exceptions=False)
            response = client.post(
                "/v1/yizijue/resolve",
                headers={"authorization": "Bearer test-token", "content-type": "application/json"},
                content="{",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["type"], "invalid_json")

    def test_chat_completions_route_executes_upstream_build_mode_tool_call(self):
        import tempfile
        from pathlib import Path

        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "chatcmpl_build_tool",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "write_file",
                                            "arguments": '{"path":"app/main.py","content":"VALUE = 9\\n"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            gateway_server,
            "UPSTREAM_API_KEY",
            "upstream-key",
        ), patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_BUILD_MODE": "1",
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
            },
            clear=False,
        ), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "写一个 demo 文件"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
            )

            payload = response.json()
            written = Path(tmpdir) / "app" / "main.py"
            written_text = written.read_text(encoding="utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
        self.assertEqual(payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"], "001")
        self.assertEqual(written_text, "VALUE = 9\n")

    def test_openai_responses_route_executes_upstream_build_mode_function_call(self):
        import json
        import tempfile
        from pathlib import Path

        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "chatcmpl_responses_build_tool",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "write_file",
                                            "arguments": '{"path":"app/main.py","content":"VALUE = 13\\n"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            gateway_server,
            "UPSTREAM_API_KEY",
            "upstream-key",
        ), patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_BUILD_MODE": "1",
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
            },
            clear=False,
        ), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/responses",
                json={
                    "model": "gpt-test",
                    "input": "写一个 responses demo 文件",
                    "tools": [
                        {"type": "function", "name": "write_file", "parameters": {"type": "object"}},
                        {"type": "function", "name": "run_pytest", "parameters": {"type": "object"}},
                    ],
                },
            )

            written = Path(tmpdir) / "app" / "main.py"
            written_text = written.read_text(encoding="utf-8")

        completed_payload = None
        for block in response.text.split("\n\n"):
            if "event: response.completed" not in block:
                continue
            for line in block.splitlines():
                if line.startswith("data:"):
                    completed_payload = json.loads(line.split(":", 1)[1].strip())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(written_text, "VALUE = 13\n")
        self.assertIsNotNone(completed_payload)
        response_payload = completed_payload["response"]
        self.assertEqual(response_payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
        self.assertEqual(
            response_payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"],
            "001",
        )
        self.assertIn("Build Mode Evidence", response_payload["output_text"])

    def test_anthropic_messages_route_executes_upstream_build_mode_tool_use(self):
        import tempfile
        from pathlib import Path

        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "msg_build_tool",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "write_file",
                            "input": {"path": "app/main.py", "content": "VALUE = 11\n"},
                        }
                    ],
                    "stop_reason": "tool_use",
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            gateway_server,
            "ANTHROPIC_API_KEY",
            "anthropic-key",
        ), patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_BUILD_MODE": "1",
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
            },
            clear=False,
        ), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "messages": [{"role": "user", "content": "写一个 anthropic demo 文件"}],
                    "tools": [
                        {"name": "write_file", "input_schema": {"type": "object"}},
                        {"name": "run_pytest", "input_schema": {"type": "object"}},
                    ],
                },
            )

            payload = response.json()
            written = Path(tmpdir) / "app" / "main.py"
            written_text = written.read_text(encoding="utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
        self.assertEqual(payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"], "001")
        self.assertEqual(payload["stop_reason"], "end_turn")
        self.assertEqual(payload["content"][0]["type"], "text")
        self.assertEqual(written_text, "VALUE = 11\n")

    def test_anthropic_messages_route_blocks_forbidden_tool_use_response(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "write_file",
                            "input": {"path": "app.py"},
                        }
                    ],
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch.object(gateway_server, "ANTHROPIC_API_KEY", "anthropic-key"), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "messages": [{"role": "user", "content": "查：看看项目结构"}],
                    "tools": [
                        {"name": "read_file", "input_schema": {"type": "object"}},
                        {"name": "write_file", "input_schema": {"type": "object"}},
                    ],
                },
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertEqual(payload["yizijue_gateway"]["active_code"], "查")
        self.assertEqual(payload["content"][0]["type"], "text")
        self.assertIn("Kernel Notice", payload["content"][0]["text"])

    def test_anthropic_messages_route_shadow_rewrites_inspect_read_tool_use(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "Read",
                            "input": {"file_path": "README.md"},
                        }
                    ],
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch.object(gateway_server, "ANTHROPIC_API_KEY", "anthropic-key"), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "messages": [{"role": "user", "content": "查：看看项目结构"}],
                    "tools": [
                        {"name": "Read", "input_schema": {"type": "object"}},
                        {"name": "Write", "input_schema": {"type": "object"}},
                    ],
                },
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "shadow_native_inspect")
        self.assertEqual(payload["content"][0]["type"], "text")
        self.assertIn("[State]: 101-INSPECT", payload["content"][0]["text"])
        self.assertNotIn("tool_use", str(payload["content"]))

    def test_anthropic_messages_route_injects_native_tool_before_upstream(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        captured = {}

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "ok"}],
                }

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                captured["json"] = kwargs.get("json")
                return FakeResponse()

        with patch.object(gateway_server, "ANTHROPIC_API_KEY", "anthropic-key"), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "messages": [{"role": "user", "content": "查：看看项目结构"}],
                    "tools": [
                        {
                            "name": "Read",
                            "description": "read docs " * 500,
                            "input_schema": {"type": "object"},
                        },
                        {
                            "name": "Bash",
                            "description": "bash docs " * 500,
                            "input_schema": {"type": "object"},
                        },
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        tools = captured["json"]["tools"]
        self.assertEqual(tools, [])
        self.assertIn("Native Inspect Context", captured["json"]["system"])
        self.assertIn("[State]: 101-INSPECT", captured["json"]["system"])

    def test_anthropic_messages_route_blocks_streaming_tool_use_chunk(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "text/event-stream"}

            async def aiter_bytes(self):
                yield b'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"text":"ok"}}\n\n'
                yield b'event: content_block_start\ndata: {"type":"tool_use","name":"write_file"}\n\n'

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch.object(gateway_server, "ANTHROPIC_API_KEY", "anthropic-key"), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "stream": True,
                    "messages": [{"role": "user", "content": "查：看看项目结构"}],
                    "tools": [
                        {"name": "read_file", "input_schema": {"type": "object"}},
                        {"name": "write_file", "input_schema": {"type": "object"}},
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/event-stream")
        self.assertIn(b"Kernel Notice", response.content)

    def test_anthropic_messages_route_forwards_clean_streaming_chunks(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        clean_chunk = b'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"text":"ok"}}\n\n'

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "text/event-stream"}

            async def aiter_bytes(self):
                yield clean_chunk

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch.object(gateway_server, "ANTHROPIC_API_KEY", "anthropic-key"), patch(
            "httpx.AsyncClient",
            FakeAsyncClient,
        ):
            client = TestClient(gateway_server.create_app())
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-test",
                    "max_tokens": 128,
                    "stream": True,
                    "messages": [{"role": "user", "content": "查：看看项目结构"}],
                    "tools": [{"name": "read_file", "input_schema": {"type": "object"}}],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/event-stream")
        self.assertEqual(response.content, clean_chunk)


if __name__ == "__main__":
    unittest.main()
