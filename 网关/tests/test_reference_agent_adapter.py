import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from agent_skill_dictionary.reference_agent_adapter import ReferenceAgentAdapter


class ReferenceAgentAdapterTest(unittest.TestCase):
    def test_adapter_executes_allowed_tool_and_submits_evidence(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.get_method(), request.full_url, _request_json(request)))
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            if request.full_url.endswith("/v1/yizijue/resolve"):
                payload = {"active_code": "查", "binary_trigram": "101"}
            elif request.full_url.endswith("/v1/yizijue/preflight-tool"):
                payload = {"allowed": True, "violations": []}
            elif request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {"status": "accepted", "audit_log_path": ".oneword/audit.jsonl"}
            else:
                self.fail(f"unexpected url: {request.full_url}")
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            adapter = ReferenceAgentAdapter(
                base_url="http://127.0.0.1:8080",
                workspace=workspace,
                token="test-token",
            )

            with patch("agent_skill_dictionary.reference_agent_adapter.urlrequest.urlopen", side_effect=fake_urlopen):
                result = adapter.run("查：看看项目结构")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["active_code"], "查")
        self.assertEqual(result["tool_results"][0]["tool"], "list_directory")
        self.assertIn("README.md", result["tool_results"][0]["stdout"])
        self.assertEqual(
            [call[1] for call in calls],
            [
                "http://127.0.0.1:8080/v1/yizijue/resolve",
                "http://127.0.0.1:8080/v1/yizijue/preflight-tool",
                "http://127.0.0.1:8080/v1/yizijue/submit-evidence",
            ],
        )
        self.assertEqual(calls[1][2]["active_code"], "查")
        self.assertEqual(calls[1][2]["tool_name"], "list_directory")
        self.assertEqual(calls[2][2]["exit_code"], 0)

    def test_adapter_does_not_execute_denied_write_tool(self):
        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            if request.full_url.endswith("/v1/yizijue/resolve"):
                payload = {"active_code": "查", "binary_trigram": "101"}
            elif request.full_url.endswith("/v1/yizijue/preflight-tool"):
                payload = {
                    "allowed": False,
                    "violations": [{"tool": "write_file", "reason": "write_forbidden"}],
                }
            elif request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {"status": "accepted", "audit_log_path": ".oneword/audit.jsonl"}
            else:
                self.fail(f"unexpected url: {request.full_url}")
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            target = workspace / "README.md"
            target.write_text("# Original\n", encoding="utf-8")
            adapter = ReferenceAgentAdapter(base_url="http://127.0.0.1:8080", workspace=workspace)

            with patch("agent_skill_dictionary.reference_agent_adapter.urlrequest.urlopen", side_effect=fake_urlopen):
                result = adapter.run(
                    "查：看看项目结构",
                    planned_tools=[
                        {
                            "name": "write_file",
                            "arguments": {"path": "README.md", "content": "# Mutated\n"},
                        }
                    ],
                )

            self.assertEqual(target.read_text(encoding="utf-8"), "# Original\n")

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["tool_results"][0]["tool"], "write_file")
        self.assertEqual(result["tool_results"][0]["exit_code"], 126)
        self.assertIn("write_forbidden", result["tool_results"][0]["stderr"])

    def test_adapter_executes_default_verify_tool_for_test_state(self):
        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            if request.full_url.endswith("/v1/yizijue/resolve"):
                payload = {"active_code": "测", "binary_trigram": "011"}
            elif request.full_url.endswith("/v1/yizijue/preflight-tool"):
                payload = {"allowed": True, "violations": []}
            elif request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {"status": "accepted", "audit_log_path": ".oneword/audit.jsonl"}
            else:
                self.fail(f"unexpected url: {request.full_url}")
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_demo.py").write_text(
                "import unittest\n\n"
                "class DemoTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            adapter = ReferenceAgentAdapter(base_url="http://127.0.0.1:8080", workspace=workspace)

            with patch("agent_skill_dictionary.reference_agent_adapter.urlrequest.urlopen", side_effect=fake_urlopen):
                result = adapter.run("测试一下")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["active_code"], "测")
        self.assertEqual(result["tool_results"][0]["tool"], "run_pytest")
        self.assertEqual(result["tool_results"][0]["exit_code"], 0)
        self.assertNotIn("unsupported reference adapter tool", result["tool_results"][0]["stderr"])


def _request_json(request):
    data = request.data
    if not data:
        return {}
    return json.loads(data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
