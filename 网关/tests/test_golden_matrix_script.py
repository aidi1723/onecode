import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from scripts import golden_matrix


class GoldenMatrixScriptTest(unittest.TestCase):
    def test_script_can_run_as_file_path(self):
        result = subprocess.run(
            [sys.executable, "scripts/golden_matrix.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Build a OneWord golden model comparison matrix", result.stdout)
        self.assertIn("local,run,chat,anthropic", result.stdout)

    def test_local_matrix_writes_json_and_markdown_for_each_model(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "golden-matrix.json"
            output_md = Path(tmpdir) / "golden-matrix.md"

            report = golden_matrix.run_matrix(
                cases_path=Path("tests/golden_cases/eight_word_core.json"),
                models=["gpt-5-mini", "gpt-5.2"],
                modes=["local"],
                output_json=output_json,
                output_md=output_md,
                workspace_parent=Path(tmpdir) / "workspaces",
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["case_count"], 10)
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())

            written = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(written["case_count"], 10)
            self.assertEqual({row["model"] for row in written["results"]}, {"gpt-5-mini", "gpt-5.2"})
            self.assertEqual({row["gateway_mode"] for row in written["results"]}, {"local"})
            self.assertTrue(all(row["session_id"] for row in written["results"]))
            for row in written["results"]:
                self.assertIn("retry_count_to_success", row)
                self.assertIn("summary_information_density", row)
                self.assertIn("tool_mask_match", row)
            self.assertIn("| task_id | model | gateway_mode |", output_md.read_text(encoding="utf-8"))

    def test_http_run_matrix_records_gateway_rows_and_isolates_sessions(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = json.dumps(
                {
                    "status": "completed",
                    "trace": ["查", "总"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [],
                }
            ).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini"],
                    modes=["run"],
                    base_url="http://127.0.0.1:8080",
                    token="secret-token",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    concurrency=4,
                )

        self.assertEqual(report["case_count"], 5)
        self.assertEqual(len(calls), 4)
        for row in report["results"]:
            self.assertEqual(row["model"], "gpt-5-mini")
            self.assertEqual(row["gateway_mode"], "run")
            self.assertTrue(row["session_id"].startswith("gpt-5-mini-run-"))
            self.assertTrue(Path(row["workspace"]).name.startswith(row["session_id"]))
        self.assertEqual({call[0] for call in calls}, {"http://127.0.0.1:8080/v1/yizijue/run"})
        self.assertEqual({call[1]["model"] for call in calls}, {"gpt-5-mini"})
        self.assertEqual(len({call[1]["session_id"] for call in calls}), 4)

    def test_http_run_matrix_uses_configured_concurrency(self):
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_urlopen(request, timeout):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = json.dumps(
                {
                    "status": "completed",
                    "trace": ["查", "总"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [],
                }
            ).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini", "gpt-5.2"],
                    modes=["run"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    concurrency=4,
                )

        self.assertGreater(max_active, 1)

    def test_http_run_matrix_skips_local_only_mock_cases(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(request.full_url)
            body = json.loads(request.data.decode("utf-8"))
            text = body.get("input", "")
            if "rm -rf" in text:
                payload = {
                    "status": "halted",
                    "trace": ["卫", "停"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [],
                }
            elif "运行测试" in text:
                payload = {
                    "status": "halted",
                    "trace": ["测", "修", "修", "停"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [{"result": {"exit_code": 1}}],
                }
            elif "总结" in text:
                payload = {
                    "status": "completed",
                    "trace": ["总"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [],
                }
            else:
                payload = {
                    "status": "completed",
                    "trace": ["查", "总"],
                    "audit_log_path": ".oneword/audit.jsonl",
                    "history": [],
                }
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini"],
                    modes=["run"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                )

        skipped = [row for row in report["results"] if row.get("skipped")]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["task_id"], "TASK_005_GUARD_SCANNER_REQUIRED")
        self.assertEqual(skipped[0]["skip_reason"], "local_only_mock_case")
        self.assertEqual(len(calls), 4)
        self.assertTrue(report["ok"], report)

    def test_chat_matrix_records_blocked_http_error_payload(self):
        def fake_urlopen(request, timeout):
            raise golden_matrix.urlerror.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=_BytesResponse(
                    {
                        "error": {"type": "yizijue_stream_tool_block"},
                        "yizijue_gateway": {
                            "blocked": True,
                            "active_code": "查",
                            "stream_guard": {"allowed": False},
                        },
                    }
                ),
            )

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini"],
                    modes=["chat"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    chat_stream=True,
                    concurrency=2,
                )

        self.assertEqual(report["case_count"], 5)
        probed = [row for row in report["results"] if not row.get("skipped")]
        self.assertTrue(all(row["gateway_mode"] == "chat" for row in report["results"]))
        self.assertTrue(all(row["blocked"] for row in probed))
        self.assertEqual({row["http_status"] for row in probed}, {403})
        self.assertEqual({row["error_type"] for row in probed}, {"yizijue_stream_tool_block"})

    def test_anthropic_matrix_posts_messages_and_records_blocked_tool_use(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            raise golden_matrix.urlerror.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=_BytesResponse(
                    {
                        "error": {"type": "yizijue_tool_guard_block"},
                        "yizijue_gateway": {
                            "blocked": True,
                            "active_code": "查",
                            "tool_guard": {"allowed": False},
                        },
                    }
                ),
            )

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["claude-test"],
                    modes=["anthropic"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                )

        self.assertEqual(report["case_count"], 5)
        probed = [row for row in report["results"] if not row.get("skipped")]
        self.assertEqual({call[0] for call in calls}, {"http://127.0.0.1:8080/v1/messages"})
        self.assertEqual({call[1]["model"] for call in calls}, {"claude-test"})
        self.assertTrue(all("tools" in call[1] for call in calls))
        self.assertTrue(all(row["gateway_mode"] == "anthropic" for row in report["results"]))
        self.assertTrue(all(row["blocked"] for row in probed))
        self.assertEqual({row["http_status"] for row in probed}, {403})
        self.assertEqual({row["error_type"] for row in probed}, {"yizijue_tool_guard_block"})

    def test_anthropic_matrix_can_probe_streaming_tool_block(self):
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            raise golden_matrix.urlerror.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=_BytesResponse(
                    {
                        "error": {"type": "yizijue_stream_tool_block"},
                        "yizijue_gateway": {
                            "blocked": True,
                            "active_code": "查",
                            "stream_guard": {"allowed": False},
                        },
                    }
                ),
            )

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["claude-test"],
                    modes=["anthropic"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    chat_stream=True,
                )

        probed = [row for row in report["results"] if not row.get("skipped")]
        self.assertTrue(all(call[1]["stream"] is True for call in calls))
        self.assertTrue(all(row["gateway_mode"] == "anthropic" for row in report["results"]))
        self.assertTrue(all(row["blocked"] for row in probed))
        self.assertEqual({row["error_type"] for row in probed}, {"yizijue_stream_tool_block"})

    def test_chat_matrix_fails_when_blocked_request_routes_to_wrong_state(self):
        def fake_urlopen(request, timeout):
            raise golden_matrix.urlerror.HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs={},
                fp=_BytesResponse(
                    {
                        "error": {"type": "yizijue_stream_tool_block"},
                        "yizijue_gateway": {
                            "blocked": True,
                            "active_code": "设",
                            "stream_guard": {"allowed": False},
                        },
                    }
                ),
            )

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini"],
                    modes=["chat"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    chat_stream=True,
                )

        compact_rows = [row for row in report["results"] if row["task_id"] == "TASK_004_COMPACT"]
        self.assertEqual(len(compact_rows), 1)
        self.assertFalse(compact_rows[0]["trace_match"])
        self.assertFalse(compact_rows[0]["ok"])
        self.assertFalse(report["ok"])

    def test_chat_matrix_validates_summary_contract_payload(self):
        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "implemented_patch_sha256": "a" * 64,
                                        "remaining_risk": "low",
                                    }
                                )
                            }
                        }
                    ],
                    "yizijue_gateway": {
                        "active_code": "总",
                        "tool_guard": {"allowed": True},
                    },
                }
            ).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.golden_matrix.urlrequest.urlopen", side_effect=fake_urlopen):
                report = golden_matrix.run_matrix(
                    cases_path=Path("tests/golden_cases/eight_word_core.json"),
                    models=["gpt-5-mini"],
                    modes=["chat"],
                    base_url="http://127.0.0.1:8080",
                    output_json=Path(tmpdir) / "matrix.json",
                    output_md=Path(tmpdir) / "matrix.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                )

        compact = [row for row in report["results"] if row["task_id"] == "TASK_004_COMPACT"][0]
        self.assertTrue(compact["summary_contract_validated"], compact)
        self.assertGreater(compact["summary_information_density"], 0.0)


class _BytesResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def close(self):
        pass


if __name__ == "__main__":
    unittest.main()
