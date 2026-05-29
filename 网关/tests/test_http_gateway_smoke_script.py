import unittest
import subprocess
import sys
from unittest.mock import Mock, patch

from scripts import http_gateway_smoke


class HttpGatewaySmokeScriptTest(unittest.TestCase):
    def test_smoke_script_can_run_as_file_path(self):
        result = subprocess.run(
            [sys.executable, "scripts/http_gateway_smoke.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Smoke test a running OneWord HTTP gateway", result.stdout)

    def test_smoke_script_checks_gateway_control_plane(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.get_method(), request.full_url, timeout, dict(request.header_items())))
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            if request.full_url.endswith("/v1/yizijue/protocol"):
                payload = {"compatibility": "agent-agnostic"}
            elif request.full_url.endswith("/v1/yizijue/resolve"):
                payload = {
                    "active_code": "查",
                    "binary_trigram": "101",
                }
            elif request.full_url.endswith("/v1/yizijue/preflight-tool"):
                body = __import__("json").loads(request.data.decode("utf-8"))
                if body["tool_name"] == "write_file":
                    payload = {
                        "allowed": False,
                        "violations": ["tool not allowed"],
                    }
                else:
                    payload = {"allowed": True, "violations": []}
            elif request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {
                    "status": "accepted",
                    "audit_log_path": ".oneword/audit.jsonl",
                }
            elif request.full_url.endswith("/v1/yizijue/build-tool"):
                body = __import__("json").loads(request.data.decode("utf-8"))
                if body["tool_name"] == "write_file":
                    payload = {
                        "status": "ok",
                        "hexagram": "111",
                        "next_hexagram": "001",
                        "evidence": {"changed_files": ["smoke_build/main.py"]},
                    }
                else:
                    payload = {"status": "blocked"}
            elif request.full_url.endswith("/v1/yizijue/run"):
                payload = {
                    "status": "completed",
                    "trace": ["查", "总"],
                    "audit_log_path": ".oneword/audit.jsonl",
                }
            else:
                self.fail(f"unexpected url: {request.full_url}")
            response.read.return_value = __import__("json").dumps(payload).encode("utf-8")
            return response

        with patch("scripts.http_gateway_smoke.urlrequest.urlopen", side_effect=fake_urlopen):
            payload = http_gateway_smoke.run_smoke("http://n100.local:8080", token="secret-token")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checks"]["protocol"], "pass")
        self.assertEqual(payload["checks"]["resolve"], "pass")
        self.assertEqual(payload["checks"]["preflight_blocks_write"], "pass")
        self.assertEqual(payload["checks"]["submit_evidence"], "pass")
        self.assertEqual(payload["checks"]["build_tool_scoped_write"], "pass")
        self.assertEqual(payload["checks"]["reference_agent_adapter"], "pass")
        self.assertEqual(payload["checks"]["run"], "pass")
        self.assertEqual(
            [call[1] for call in calls],
            [
                "http://n100.local:8080/v1/yizijue/protocol",
                "http://n100.local:8080/v1/yizijue/resolve",
                "http://n100.local:8080/v1/yizijue/preflight-tool",
                "http://n100.local:8080/v1/yizijue/submit-evidence",
                "http://n100.local:8080/v1/yizijue/build-tool",
                "http://n100.local:8080/v1/yizijue/resolve",
                "http://n100.local:8080/v1/yizijue/preflight-tool",
                "http://n100.local:8080/v1/yizijue/submit-evidence",
                "http://n100.local:8080/v1/yizijue/run",
            ],
        )
        run_request = calls[-1]
        self.assertEqual(run_request[0], "POST")
        self.assertEqual(run_request[3]["Authorization"], "Bearer secret-token")


if __name__ == "__main__":
    unittest.main()
