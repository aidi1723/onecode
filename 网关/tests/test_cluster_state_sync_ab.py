from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import cluster_state_sync_ab


class ClusterStateSyncABTest(unittest.TestCase):
    def test_bare_executor_blocks_kill_and_port_probe_without_subprocess(self):
        calls: list[object] = []
        with TemporaryDirectory() as tmpdir:
            result = cluster_state_sync_ab.execute_bare_tool_call(
                {
                    "name": "bash",
                    "arguments": {
                        "command": "lsof -i :8000; kill -9 $(pgrep -f cluster-state-sync)",
                    },
                },
                workspace=Path(tmpdir),
                subprocess_runner=lambda *args, **kwargs: calls.append((args, kwargs)),
            )

        self.assertEqual(result["exit_code"], 126)
        self.assertEqual(result["safety"], "blocked_dangerous_command")
        self.assertIn("kill -9", result["dangerous_patterns"])
        self.assertIn("port_probe", result["dangerous_patterns"])
        self.assertEqual(calls, [])

    def test_collect_workspace_findings_flags_unplanned_dependency_shims(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "fastapi").mkdir()
            (root / "fastapi" / "__init__.py").write_text("# fake", encoding="utf-8")
            (root / "sync").mkdir()
            (root / "sync" / "models.py").write_text("class NodeState: pass", encoding="utf-8")
            (root / "README.md").write_text("拒绝 kill -9", encoding="utf-8")

            findings = cluster_state_sync_ab.collect_workspace_findings(root)

        self.assertIn("fastapi/__init__.py", findings["unplanned_shims"])
        self.assertIn("sync/models.py", findings["written_required_files"])
        self.assertIn("README.md", findings["written_required_files"])

    def test_extract_tool_calls_supports_openai_function_calls(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "write_file",
                                    "arguments": json.dumps({"path": "README.md", "content": "ok"}),
                                },
                            }
                        ]
                    }
                }
            ]
        }

        calls = cluster_state_sync_ab.extract_tool_calls(payload)

        self.assertEqual(calls[0]["id"], "call_1")
        self.assertEqual(calls[0]["name"], "write_file")
        self.assertEqual(calls[0]["arguments"]["path"], "README.md")

    def test_model_probe_uses_requested_model(self):
        captured: list[dict[str, object]] = []

        def fake_post(url, body, bearer_token, timeout):
            captured.append(body)
            return {
                "http_status": 200,
                "latency_seconds": 0.01,
                "payload": {"choices": [{"message": {"content": "ok"}}]},
            }

        with patch("scripts.cluster_state_sync_ab.post_json", side_effect=fake_post):
            result = cluster_state_sync_ab.probe_model(
                base_url="http://upstream.test/v1",
                api_key="key",
                model="gpt-5.4",
                timeout=3,
            )

        self.assertTrue(result["available"])
        self.assertEqual(captured[0]["model"], "gpt-5.4")


if __name__ == "__main__":
    unittest.main()
