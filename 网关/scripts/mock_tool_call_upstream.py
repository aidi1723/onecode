from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockToolCallHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json({"status": "ok"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path not in {"/v1/chat/completions", "/v1/messages"}:
            self.send_error(404)
            return
        length = int(self.headers.get("content-length") or "0")
        body = {}
        if length:
            raw_body = self.rfile.read(length)
            try:
                parsed = json.loads(raw_body.decode("utf-8"))
                if isinstance(parsed, dict):
                    body = parsed
            except json.JSONDecodeError:
                body = {}
        if self.path == "/v1/messages":
            self._write_json(build_mock_anthropic_response(body))
            return
        self._write_json(build_mock_chat_response(body))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(self, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _verify_tool_call_payload(arguments: dict[str, str]) -> dict[str, object]:
    return {
        "id": "chatcmpl_mock_verify_call",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_verify",
                            "type": "function",
                            "function": {
                                "name": "run_pytest",
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }


def build_mock_chat_response(body: dict[str, object]) -> dict[str, object]:
    if _is_tool_inspection_request(body):
        return {
            "id": "chatcmpl_mock_tool_inspection",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({"received_tools": _tool_names(body)}),
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    if _is_native_inspect_request(body):
        return _tool_call_response(
            "chatcmpl_mock_native_inspect_call",
            [
                {
                    "id": "call_mock_native_inspect",
                    "name": "native_inspect_card",
                    "arguments": {"target": "test_proxy_build.py"},
                }
            ],
        )
    if _is_responses_repair_write_request(body):
        return _tool_call_response(
            "chatcmpl_mock_responses_repair_write_call",
            [
                {
                    "id": "call_mock_responses_repair_write",
                    "name": "write_file",
                    "arguments": {
                        "path": "responses_build/main.py",
                        "content": "VALUE = 43\n",
                    },
                },
                {
                    "id": "call_mock_responses_repair_test",
                    "name": "write_file",
                    "arguments": {
                        "path": "test_responses_build.py",
                        "content": (
                            "import unittest\n\n"
                            "class ResponsesBuildTest(unittest.TestCase):\n"
                            "    def test_value(self):\n"
                            "        namespace = {}\n"
                            "        with open('responses_build/main.py', encoding='utf-8') as handle:\n"
                            "            exec(handle.read(), namespace)\n"
                            "        self.assertEqual(namespace['VALUE'], 43)\n"
                        ),
                    },
                },
            ],
        )
    if _is_repair_write_request(body):
        return _tool_call_response(
            "chatcmpl_mock_repair_write_call",
            [
                {
                    "id": "call_mock_repair_write",
                    "name": "write_file",
                    "arguments": {
                        "path": "proxy_build/main.py",
                        "content": "VALUE = 43\n",
                    },
                },
                {
                    "id": "call_mock_repair_test",
                    "name": "write_file",
                    "arguments": {
                        "path": "test_proxy_build.py",
                        "content": (
                            "import unittest\n\n"
                            "class ProxyBuildTest(unittest.TestCase):\n"
                            "    def test_value(self):\n"
                            "        namespace = {}\n"
                            "        with open('proxy_build/main.py', encoding='utf-8') as handle:\n"
                            "            exec(handle.read(), namespace)\n"
                            "        self.assertEqual(namespace['VALUE'], 43)\n"
                        ),
                    },
                },
            ],
        )
    if _is_verify_failure_request(body):
        return _verify_tool_call_payload({"command": "python3 -c 'raise SystemExit(1)'"})
    if _is_verify_request(body):
        return _verify_tool_call_payload({"command": "python3 -m unittest discover"})
    if _is_responses_build_request(body):
        return _tool_call_response(
            "chatcmpl_mock_responses_tool_call",
            [
                {
                    "id": "call_mock_responses_write",
                    "name": "write_file",
                    "arguments": {
                        "path": "responses_build/main.py",
                        "content": "VALUE = 42\n",
                    },
                }
            ],
        )
    return _tool_call_response(
        "chatcmpl_mock_tool_call",
        [
            {
                "id": "call_mock_write",
                "name": "write_file",
                "arguments": {
                    "path": "proxy_build/main.py",
                    "content": "VALUE = 42\n",
                },
            },
            {
                "id": "call_mock_write_test",
                "name": "write_file",
                "arguments": {
                    "path": "test_proxy_build.py",
                    "content": (
                        "import unittest\n\n"
                        "class ProxyBuildTest(unittest.TestCase):\n"
                        "    def test_value(self):\n"
                        "        namespace = {}\n"
                        "        with open('proxy_build/main.py', encoding='utf-8') as handle:\n"
                        "            exec(handle.read(), namespace)\n"
                        "        self.assertEqual(namespace['VALUE'], 42)\n"
                    ),
                },
            },
        ],
    )


def build_mock_anthropic_response(body: dict[str, object]) -> dict[str, object]:
    if _is_tool_inspection_request(body):
        return _anthropic_text_response(json.dumps({"received_tools": _anthropic_tool_names(body)}))
    if _is_native_inspect_request(body):
        return _anthropic_tool_use_response(
            "msg_mock_anthropic_native_inspect",
            [
                {
                    "id": "toolu_mock_anthropic_native_inspect",
                    "name": "native_inspect_card",
                    "input": {"target": "test_anthropic_build.py"},
                }
            ],
        )
    if _is_anthropic_repair_write_request(body):
        return _anthropic_tool_use_response(
            "msg_mock_anthropic_repair",
            [
                {
                    "id": "toolu_mock_anthropic_repair_write",
                    "name": "write_file",
                    "input": {
                        "path": "anthropic_build/main.py",
                        "content": "VALUE = 43\n",
                    },
                },
                {
                    "id": "toolu_mock_anthropic_repair_test",
                    "name": "write_file",
                    "input": {
                        "path": "test_anthropic_build.py",
                        "content": (
                            "import unittest\n\n"
                            "class AnthropicBuildTest(unittest.TestCase):\n"
                            "    def test_value(self):\n"
                            "        namespace = {}\n"
                            "        with open('anthropic_build/main.py', encoding='utf-8') as handle:\n"
                            "            exec(handle.read(), namespace)\n"
                            "        self.assertEqual(namespace['VALUE'], 43)\n"
                        ),
                    },
                },
            ],
        )
    if _is_verify_failure_request(body):
        return _anthropic_tool_use_response(
            "msg_mock_anthropic_verify_fail",
            [
                {
                    "id": "toolu_mock_anthropic_verify_fail",
                    "name": "run_pytest",
                    "input": {"command": "python3 -c 'raise SystemExit(1)'"},
                }
            ],
        )
    if _is_verify_request(body):
        return _anthropic_tool_use_response(
            "msg_mock_anthropic_verify",
            [
                {
                    "id": "toolu_mock_anthropic_verify",
                    "name": "run_pytest",
                    "input": {"command": "python3 -m unittest discover"},
                }
            ],
        )
    if _is_anthropic_build_request(body):
        return _anthropic_tool_use_response(
            "msg_mock_anthropic_build",
            [
                {
                    "id": "toolu_mock_anthropic_write",
                    "name": "write_file",
                    "input": {
                        "path": "anthropic_build/main.py",
                        "content": "VALUE = 42\n",
                    },
                },
                {
                    "id": "toolu_mock_anthropic_test",
                    "name": "write_file",
                    "input": {
                        "path": "test_anthropic_build.py",
                        "content": (
                            "import unittest\n\n"
                            "class AnthropicBuildTest(unittest.TestCase):\n"
                            "    def test_value(self):\n"
                            "        namespace = {}\n"
                            "        with open('anthropic_build/main.py', encoding='utf-8') as handle:\n"
                            "            exec(handle.read(), namespace)\n"
                            "        self.assertEqual(namespace['VALUE'], 42)\n"
                        ),
                    },
                },
            ],
        )
    return _anthropic_text_response("ok")


def _anthropic_text_response(text: str) -> dict[str, object]:
    return {
        "id": "msg_mock_text",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
    }


def _anthropic_tool_use_response(response_id: str, blocks: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": response_id,
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": str(block.get("id") or ""),
                "name": str(block.get("name") or ""),
                "input": block.get("input") or {},
            }
            for block in blocks
        ],
        "stop_reason": "tool_use",
    }


def _tool_call_response(response_id: str, calls: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": response_id,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": str(call.get("id") or ""),
                            "type": "function",
                            "function": {
                                "name": str(call.get("name") or ""),
                                "arguments": json.dumps(call.get("arguments") or {}),
                            },
                        }
                        for call in calls
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }


def _is_tool_inspection_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "inspect_tools" in content:
            return True
    return False


def _is_verify_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "run_verify" in content:
            return True
    return False


def _is_native_inspect_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "run_native_inspect" in content:
            return True
    return False


def _is_repair_write_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "run_repair_write" in content:
            return True
    return False


def _is_responses_repair_write_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "run_responses_repair_write" in content:
            return True
    return False


def _is_anthropic_repair_write_request(body: dict[str, object]) -> bool:
    return _message_contains(body, "run_anthropic_repair_write")


def _is_verify_failure_request(body: dict[str, object]) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and "run_verify_fail" in content:
            return True
    return False


def _is_responses_build_request(body: dict[str, object]) -> bool:
    return _message_contains(body, "responses build")


def _is_anthropic_build_request(body: dict[str, object]) -> bool:
    return _message_contains(body, "anthropic build")


def _message_contains(body: dict[str, object], marker: str) -> bool:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and marker in content:
            return True
    return False


def _tool_names(body: dict[str, object]) -> list[str]:
    tools = body.get("tools")
    if not isinstance(tools, list):
        return []
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _anthropic_tool_names(body: dict[str, object]) -> list[str]:
    tools = body.get("tools")
    if not isinstance(tools, list):
        return []
    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock upstream that returns a Build Mode write_file tool call.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockToolCallHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
