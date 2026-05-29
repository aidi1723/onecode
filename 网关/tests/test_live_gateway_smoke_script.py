import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from scripts import live_gateway_smoke


class LiveGatewaySmokeScriptTest(unittest.TestCase):
    def test_live_gateway_smoke_starts_gateway_runs_http_smoke_and_stops_process(self):
        process = Mock()
        process.poll.return_value = None
        process.pid = 12345
        smoke_payload = {"ok": True, "checks": {"build_tool_scoped_write": "pass"}}

        with patch.object(live_gateway_smoke.subprocess, "Popen", return_value=process) as popen, patch.object(
            live_gateway_smoke,
            "_wait_until_ready",
            return_value=None,
        ) as wait_until_ready, patch.object(
            live_gateway_smoke.http_gateway_smoke,
            "run_smoke",
            return_value=smoke_payload,
        ) as run_smoke:
            payload = live_gateway_smoke.run_live_smoke(port=8999, workspace="/tmp/oneword-live")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["gateway_pid"], 12345)
        self.assertEqual(payload["smoke"], smoke_payload)
        command = popen.call_args.args[0]
        self.assertIn("uvicorn", command)
        self.assertIn("--port", command)
        self.assertIn("8999", command)
        wait_until_ready.assert_called_once_with("http://127.0.0.1:8999", timeout_seconds=15)
        run_smoke.assert_called_once_with(
            "http://127.0.0.1:8999",
            workspace=str(Path("/tmp/oneword-live").resolve()),
            token=None,
        )
        process.terminate.assert_called_once()

    def test_live_gateway_smoke_defaults_to_temporary_workspace(self):
        process = Mock()
        process.poll.return_value = None
        process.pid = 12346
        smoke_payload = {"ok": True, "checks": {"build_tool_scoped_write": "pass"}}

        with patch.object(live_gateway_smoke.subprocess, "Popen", return_value=process) as popen, patch.object(
            live_gateway_smoke,
            "_wait_until_ready",
            return_value=None,
        ), patch.object(
            live_gateway_smoke.http_gateway_smoke,
            "run_smoke",
            return_value=smoke_payload,
        ) as run_smoke:
            payload = live_gateway_smoke.run_live_smoke(port=8998)

        workspace = run_smoke.call_args.kwargs["workspace"]
        env = popen.call_args.kwargs["env"]
        self.assertTrue(payload["ok"])
        self.assertNotEqual(workspace, ".")
        self.assertTrue(Path(workspace).is_absolute())
        self.assertEqual(env["ONEWORD_WORKSPACE_ROOT"], workspace)
        self.assertFalse(Path(workspace).exists())
        process.terminate.assert_called_once()

    def test_live_gateway_smoke_can_include_proxy_tool_call_check(self):
        process = Mock()
        process.poll.return_value = None
        process.pid = 12347
        upstream = Mock()
        upstream.poll.return_value = None
        upstream.pid = 22347
        smoke_payload = {"ok": True, "checks": {"build_tool_scoped_write": "pass"}}
        proxy_payload = {
            "ok": True,
            "response_mode": "build_mode_tool_execution",
            "file_written": True,
        }

        with patch.object(live_gateway_smoke.subprocess, "Popen", side_effect=[upstream, process]) as popen, patch.object(
            live_gateway_smoke,
            "_wait_until_ready",
            return_value=None,
        ), patch.object(
            live_gateway_smoke.http_gateway_smoke,
            "run_smoke",
            return_value=smoke_payload,
        ), patch.object(
            live_gateway_smoke,
            "_run_proxy_tool_call_smoke",
            return_value=proxy_payload,
        ) as proxy_smoke:
            payload = live_gateway_smoke.run_live_smoke(port=8997, include_proxy_tool_call=True)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["proxy_tool_call"], proxy_payload)
        self.assertEqual(popen.call_count, 2)
        proxy_smoke.assert_called_once()
        upstream.terminate.assert_called_once()
        process.terminate.assert_called_once()

    def test_proxy_tool_call_smoke_verifies_next_turn_tool_filtering(self):
        calls = []
        responses_calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if len(calls) == 1:
                workspace = Path(kwargs["json"]["metadata"]["workspace"])
                target = workspace / "proxy_build" / "main.py"
                target.parent.mkdir(parents=True)
                target.write_text("VALUE = 42\n", encoding="utf-8")
                (workspace / "test_proxy_build.py").write_text(
                    "import unittest\n\n"
                    "class ProxyBuildTest(unittest.TestCase):\n"
                    "    def test_value(self):\n"
                    "        namespace = {}\n"
                    "        with open('proxy_build/main.py', encoding='utf-8') as handle:\n"
                    "            exec(handle.read(), namespace)\n"
                    "        self.assertEqual(namespace['VALUE'], 42)\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"received_tools":["run_pytest"]}',
                            }
                        }
                    ]
                }
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [
                        {
                            "status": "completed",
                            "hexagram": "001",
                            "next_hexagram": "000",
                            "evidence": {"pytest_status": "passed", "exit_code": 0},
                        }
                    ],
                }
            }

        def fake_sse_request(method, url, **kwargs):
            responses_calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "responses_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(responses_calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                (workspace / "test_responses_build.py").write_text(
                    "import unittest\n\n"
                    "class ResponsesBuildTest(unittest.TestCase):\n"
                    "    def test_value(self):\n"
                    "        namespace = {}\n"
                    "        with open('responses_build/main.py', encoding='utf-8') as handle:\n"
                    "            exec(handle.read(), namespace)\n"
                    "        self.assertEqual(namespace['VALUE'], 42)\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(responses_calls) == 2:
                return {"output_text": '{"received_tools":["run_pytest"]}'}
            if len(responses_calls) == 3:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                    }
                }
            if len(responses_calls) == 4:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {
                                "status": "needs_fix",
                                "next_hexagram": "110",
                                "feedback": {"message": "failed"},
                            }
                        ],
                    }
                }
            if len(responses_calls) == 5:
                return {"output_text": '{"received_tools":["native_inspect_card"]}'}
            if len(responses_calls) == 6:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "111"}],
                    }
                }
            if len(responses_calls) == 7:
                return {"output_text": '{"received_tools":["write_file"]}'}
            if len(responses_calls) == 8:
                target.write_text("VALUE = 43\n", encoding="utf-8")
                test_file = workspace / "test_responses_build.py"
                test_file.write_text(test_file.read_text(encoding="utf-8").replace("42", "43"), encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            manifest = workspace / ".yizijue" / "manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            test_file = workspace / "test_responses_build.py"
            manifest.write_text(
                json.dumps(
                    {
                        "sha256_map": {
                            "responses_build/main.py": hashlib.sha256(target.read_bytes()).hexdigest(),
                            "test_responses_build.py": hashlib.sha256(test_file.read_bytes()).hexdigest(),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [
                        {
                            "status": "completed",
                            "next_hexagram": "000",
                            "archive": {"manifest_path": ".yizijue/manifest.json"},
                        }
                    ],
                }
            }

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_sse_json_request",
            side_effect=fake_sse_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            return_value={
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            },
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["file_written"])
        self.assertEqual(payload["next_hexagram"], "001")
        self.assertEqual(payload["second_turn_tools"], ["run_pytest"])
        self.assertEqual(payload["verify_next_hexagram"], "000")
        self.assertEqual(payload["verify_status"], "completed")
        self.assertEqual(payload["responses_status"], "ok")
        self.assertEqual(payload["responses_next_hexagram"], "001")
        self.assertEqual(payload["responses_file_written"], True)
        self.assertEqual(payload["responses_post_write_tools"], ["run_pytest"])
        self.assertEqual(payload["responses_verify_status"], "completed")
        self.assertEqual(payload["responses_verify_next_hexagram"], "000")
        self.assertEqual(payload["responses_failure_verify_status"], "needs_fix")
        self.assertEqual(payload["responses_failure_verify_next_hexagram"], "110")
        self.assertEqual(payload["responses_post_failure_tools"], ["native_inspect_card"])
        self.assertEqual(payload["responses_inspect_status"], "ok")
        self.assertEqual(payload["responses_inspect_next_hexagram"], "111")
        self.assertEqual(payload["responses_post_inspect_tools"], ["write_file"])
        self.assertEqual(payload["responses_repair_status"], "ok")
        self.assertEqual(payload["responses_repair_next_hexagram"], "001")
        self.assertEqual(payload["responses_repaired_file_written"], True)
        self.assertEqual(payload["responses_post_repair_verify_status"], "completed")
        self.assertEqual(payload["responses_post_repair_verify_next_hexagram"], "000")
        self.assertEqual(payload["responses_post_repair_manifest_written"], True)
        self.assertEqual(payload["responses_post_repair_manifest_has_repaired_file"], True)
        self.assertEqual(payload["responses_post_repair_manifest_sha256_matches"], True)
        self.assertEqual(payload["responses_state_written"], True)
        self.assertEqual(payload["responses_state_next_hexagram"], "000")
        self.assertEqual(payload["responses_state_consecutive_failures"], 0)
        self.assertEqual(payload["anthropic_status"], "ok")
        self.assertEqual(payload["anthropic_next_hexagram"], "001")
        self.assertEqual(payload["anthropic_file_written"], True)
        self.assertEqual(payload["anthropic_post_write_tools"], ["run_pytest"])
        self.assertEqual(payload["anthropic_verify_status"], "completed")
        self.assertEqual(payload["anthropic_verify_next_hexagram"], "000")
        self.assertEqual(payload["anthropic_failure_verify_status"], "needs_fix")
        self.assertEqual(payload["anthropic_failure_verify_next_hexagram"], "110")
        self.assertEqual(payload["anthropic_post_failure_tools"], ["native_inspect_card"])
        self.assertEqual(payload["anthropic_inspect_status"], "ok")
        self.assertEqual(payload["anthropic_inspect_next_hexagram"], "111")
        self.assertEqual(payload["anthropic_post_inspect_tools"], ["write_file"])
        self.assertEqual(payload["anthropic_repair_status"], "ok")
        self.assertEqual(payload["anthropic_repair_next_hexagram"], "001")
        self.assertEqual(payload["anthropic_repaired_file_written"], True)
        self.assertEqual(payload["anthropic_post_repair_verify_status"], "completed")
        self.assertEqual(payload["anthropic_post_repair_verify_next_hexagram"], "000")
        self.assertEqual(payload["anthropic_post_repair_manifest_written"], True)
        self.assertEqual(payload["anthropic_post_repair_manifest_has_repaired_file"], True)
        self.assertEqual(payload["anthropic_post_repair_manifest_sha256_matches"], True)
        self.assertEqual(payload["anthropic_state_written"], True)
        self.assertEqual(payload["anthropic_state_next_hexagram"], "000")
        self.assertEqual(payload["anthropic_state_consecutive_failures"], 0)
        self.assertEqual(payload["state_written"], True)
        self.assertEqual(payload["state_next_hexagram"], "000")
        self.assertEqual(payload["state_consecutive_failures"], 0)
        self.assertEqual(len(responses_calls), 9)
        self.assertEqual(responses_calls[0][1], "http://127.0.0.1:8765/v1/responses")
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][2]["json"]["session_id"], "live-smoke-proxy")
        self.assertEqual(calls[2][2]["json"]["session_id"], "live-smoke-proxy")

    def test_proxy_tool_call_smoke_requires_all_protocol_state_files(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_state_status(workspace, session_id):
            if session_id == "live-smoke-responses-proxy":
                return {"written": False, "next_hexagram": None, "consecutive_failures": None}
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_state_written"], False)
        self.assertEqual(payload["responses_state_next_hexagram"], None)

    def test_proxy_tool_call_smoke_requires_responses_post_write_tool_filtering(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_responses_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["write_file"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_responses_result()
            result["post_write_tools"] = ["run_pytest"]
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_post_write_tools"], ["write_file"])

    def test_proxy_tool_call_smoke_requires_anthropic_post_write_tool_filtering(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["post_write_tools"] = ["write_file"]
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_post_write_tools"], ["write_file"])

    def test_proxy_tool_call_smoke_requires_responses_initial_verify_success(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_responses_result():
            result = fake_protocol_result()
            result["verify_status"] = "needs_fix"
            result["verify_next_hexagram"] = "110"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_verify_status"], "needs_fix")
        self.assertEqual(payload["responses_verify_next_hexagram"], "110")

    def test_proxy_tool_call_smoke_requires_anthropic_initial_verify_success(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["verify_status"] = "needs_fix"
            result["verify_next_hexagram"] = "110"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_verify_status"], "needs_fix")
        self.assertEqual(payload["anthropic_verify_next_hexagram"], "110")

    def test_proxy_tool_call_smoke_requires_responses_post_repair_archive_evidence(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_responses_result():
            result = fake_protocol_result()
            result["post_repair_verify_next_hexagram"] = "110"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_post_repair_verify_next_hexagram"], "110")

    def test_proxy_tool_call_smoke_requires_anthropic_post_repair_archive_evidence(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["post_repair_manifest_has_repaired_file"] = False
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_post_repair_manifest_has_repaired_file"], False)

    def test_proxy_tool_call_smoke_requires_responses_failure_to_route_to_correct(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_responses_result():
            result = fake_protocol_result()
            result["failure_verify_next_hexagram"] = "000"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_failure_verify_next_hexagram"], "000")

    def test_proxy_tool_call_smoke_requires_anthropic_failure_to_route_to_correct(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["failure_verify_next_hexagram"] = "001"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_failure_verify_next_hexagram"], "001")

    def test_proxy_tool_call_smoke_requires_responses_inspect_status_ok(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_responses_result():
            result = fake_protocol_result()
            result["inspect_status"] = "needs_fix"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_inspect_status"], "needs_fix")

    def test_proxy_tool_call_smoke_requires_anthropic_inspect_status_ok(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["inspect_status"] = "needs_fix"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_inspect_status"], "needs_fix")

    def test_proxy_tool_call_smoke_requires_responses_repair_to_route_to_verify(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_responses_result():
            result = fake_protocol_result()
            result["repair_next_hexagram"] = "111"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_responses_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["responses_repair_next_hexagram"], "111")

    def test_proxy_tool_call_smoke_requires_anthropic_repair_to_route_to_verify(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                }
            }

        def fake_protocol_result():
            return {
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            }

        def fake_anthropic_result():
            result = fake_protocol_result()
            result["repair_next_hexagram"] = "111"
            return result

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_responses_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_protocol_result(),
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            side_effect=lambda base_url, workspace, token=None: fake_anthropic_result(),
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["anthropic_repair_next_hexagram"], "111")

    def test_proxy_tool_call_smoke_can_verify_failed_test_soft_feedback(self):
        calls = []
        responses_calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if len(calls) == 1:
                workspace = Path(kwargs["json"]["metadata"]["workspace"])
                target = workspace / "proxy_build" / "main.py"
                target.parent.mkdir(parents=True)
                target.write_text("VALUE = 42\n", encoding="utf-8")
                (workspace / "test_proxy_build.py").write_text(
                    "import unittest\n\n"
                    "class ProxyBuildTest(unittest.TestCase):\n"
                    "    def test_value(self):\n"
                    "        namespace = {}\n"
                    "        with open('proxy_build/main.py', encoding='utf-8') as handle:\n"
                    "            exec(handle.read(), namespace)\n"
                    "        self.assertEqual(namespace['VALUE'], 42)\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"choices": [{"message": {"content": '{"received_tools":["run_pytest"]}'}}]}
            if len(calls) == 3:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {"status": "completed", "hexagram": "001", "next_hexagram": "000"}
                        ],
                    }
                }
            if len(calls) == 4:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {
                                "status": "needs_fix",
                                "hexagram": "001",
                                "next_hexagram": "110",
                                "evidence": {"pytest_status": "failed", "exit_code": 1},
                                "feedback": {"message": "Kernel Notice: failed"},
                            }
                        ],
                    }
                }
            if len(calls) == 5:
                return {"choices": [{"message": {"content": '{"received_tools":["native_inspect_card"]}'}}]}
            if len(calls) == 6:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {
                                "status": "ok",
                                "hexagram": "101",
                                "next_hexagram": "111",
                                "repo_card_text": "[State]: 101-INSPECT",
                            }
                        ],
                    }
                }
            if len(calls) == 7:
                return {"choices": [{"message": {"content": '{"received_tools":["write_file"]}'}}]}
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "proxy_build" / "main.py"
            target.write_text("VALUE = 43\n", encoding="utf-8")
            test_file = workspace / "test_proxy_build.py"
            test_file.write_text(test_file.read_text(encoding="utf-8").replace("42", "43"), encoding="utf-8")
            if len(calls) == 9:
                manifest = workspace / ".yizijue" / "manifest.json"
                manifest.parent.mkdir(parents=True, exist_ok=True)
                main_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                test_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
                manifest.write_text(
                    json.dumps(
                        {
                            "sha256_map": {
                                "proxy_build/main.py": main_hash,
                                "test_proxy_build.py": test_hash,
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {
                                "status": "completed",
                                "hexagram": "001",
                                "next_hexagram": "000",
                                "archive": {"manifest_path": ".yizijue/manifest.json"},
                            }
                        ],
                    }
                }
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "ok", "hexagram": "111", "next_hexagram": "001"}],
                }
            }

        def fake_sse_request(method, url, **kwargs):
            responses_calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "responses_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            test_file = workspace / "test_responses_build.py"
            if len(responses_calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                test_file.write_text(
                    "import unittest\n\n"
                    "class ResponsesBuildTest(unittest.TestCase):\n"
                    "    def test_value(self):\n"
                    "        namespace = {}\n"
                    "        with open('responses_build/main.py', encoding='utf-8') as handle:\n"
                    "            exec(handle.read(), namespace)\n"
                    "        self.assertEqual(namespace['VALUE'], 42)\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(responses_calls) == 2:
                return {"output_text": '{"received_tools":["run_pytest"]}'}
            if len(responses_calls) == 3:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                    }
                }
            if len(responses_calls) == 4:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {"status": "needs_fix", "next_hexagram": "110", "feedback": {"message": "failed"}}
                        ],
                    }
                }
            if len(responses_calls) == 5:
                return {"output_text": '{"received_tools":["native_inspect_card"]}'}
            if len(responses_calls) == 6:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "111"}],
                    }
                }
            if len(responses_calls) == 7:
                return {"output_text": '{"received_tools":["write_file"]}'}
            if len(responses_calls) == 8:
                target.write_text("VALUE = 43\n", encoding="utf-8")
                test_file.write_text(test_file.read_text(encoding="utf-8").replace("42", "43"), encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            manifest = workspace / ".yizijue" / "manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {
                        "sha256_map": {
                            "responses_build/main.py": hashlib.sha256(target.read_bytes()).hexdigest(),
                            "test_responses_build.py": hashlib.sha256(test_file.read_bytes()).hexdigest(),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [
                        {
                            "status": "completed",
                            "next_hexagram": "000",
                            "archive": {"manifest_path": ".yizijue/manifest.json"},
                        }
                    ],
                }
            }

        def fake_state_status(workspace, session_id):
            return {"written": True, "next_hexagram": "000", "consecutive_failures": 0}

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ), patch.object(
            live_gateway_smoke,
            "_sse_json_request",
            side_effect=fake_sse_request,
        ), patch.object(
            live_gateway_smoke,
            "_run_anthropic_tool_call_smoke",
            return_value={
                "status": "ok",
                "next_hexagram": "001",
                "file_written": True,
                "post_write_tools": ["run_pytest"],
                "verify_status": "completed",
                "verify_next_hexagram": "000",
                "failure_verify_status": "needs_fix",
                "failure_verify_next_hexagram": "110",
                "post_failure_tools": ["native_inspect_card"],
                "inspect_status": "ok",
                "inspect_next_hexagram": "111",
                "post_inspect_tools": ["write_file"],
                "repair_status": "ok",
                "repair_next_hexagram": "001",
                "repaired_file_written": True,
                "post_repair_verify_status": "completed",
                "post_repair_verify_next_hexagram": "000",
                "post_repair_manifest_written": True,
                "post_repair_manifest_has_repaired_file": True,
                "post_repair_manifest_sha256_matches": True,
            },
        ), patch.object(
            live_gateway_smoke,
            "_state_status",
            side_effect=fake_state_status,
        ):
            payload = live_gateway_smoke._run_proxy_tool_call_smoke(
                "http://127.0.0.1:8765",
                tmpdir,
                include_failure_case=True,
            )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["failure_verify_status"], "needs_fix")
        self.assertEqual(payload["failure_verify_next_hexagram"], "110")
        self.assertEqual(payload["failure_feedback_present"], True)
        self.assertEqual(payload["post_failure_tools"], ["native_inspect_card"])
        self.assertEqual(payload["inspect_status"], "ok")
        self.assertEqual(payload["inspect_next_hexagram"], "111")
        self.assertEqual(payload["post_inspect_tools"], ["write_file"])
        self.assertEqual(payload["repair_status"], "ok")
        self.assertEqual(payload["repair_next_hexagram"], "001")
        self.assertEqual(payload["repaired_file_written"], True)
        self.assertEqual(payload["post_repair_verify_status"], "completed")
        self.assertEqual(payload["post_repair_verify_next_hexagram"], "000")
        self.assertEqual(payload["post_repair_manifest_written"], True)
        self.assertEqual(payload["post_repair_manifest_has_repaired_file"], True)
        self.assertEqual(payload["post_repair_manifest_sha256_matches"], True)
        self.assertEqual(payload["state_written"], True)
        self.assertEqual(payload["state_next_hexagram"], "000")
        self.assertEqual(payload["state_consecutive_failures"], 0)
        self.assertEqual(calls[3][2]["json"]["messages"][0]["content"], "run_verify_fail")
        self.assertEqual(calls[4][2]["json"]["messages"][0]["content"], "inspect_tools_after_failure")
        self.assertEqual(calls[5][2]["json"]["messages"][0]["content"], "run_native_inspect")
        self.assertEqual(calls[6][2]["json"]["messages"][0]["content"], "inspect_tools_after_native_inspect")
        self.assertEqual(calls[7][2]["json"]["messages"][0]["content"], "run_repair_write")
        self.assertEqual(calls[8][2]["json"]["messages"][0]["content"], "run_verify_after_repair")

    def test_anthropic_tool_call_smoke_runs_full_loop(self):
        calls = []

        def fake_json_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            workspace = Path(kwargs["json"]["metadata"]["workspace"])
            target = workspace / "anthropic_build" / "main.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            test_file = workspace / "test_anthropic_build.py"
            if len(calls) == 1:
                target.write_text("VALUE = 42\n", encoding="utf-8")
                test_file.write_text(
                    "import unittest\n\n"
                    "class AnthropicBuildTest(unittest.TestCase):\n"
                    "    def test_value(self):\n"
                    "        namespace = {}\n"
                    "        with open('anthropic_build/main.py', encoding='utf-8') as handle:\n"
                    "            exec(handle.read(), namespace)\n"
                    "        self.assertEqual(namespace['VALUE'], 42)\n",
                    encoding="utf-8",
                )
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            if len(calls) == 2:
                return {"content": [{"type": "text", "text": '{"received_tools":["run_pytest"]}'}]}
            if len(calls) == 3:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "completed", "next_hexagram": "000"}],
                    }
                }
            if len(calls) == 4:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [
                            {"status": "needs_fix", "next_hexagram": "110", "feedback": {"message": "failed"}}
                        ],
                    }
                }
            if len(calls) == 5:
                return {"content": [{"type": "text", "text": '{"received_tools":["native_inspect_card"]}'}]}
            if len(calls) == 6:
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "111"}],
                    }
                }
            if len(calls) == 7:
                return {"content": [{"type": "text", "text": '{"received_tools":["write_file"]}'}]}
            if len(calls) == 8:
                target.write_text("VALUE = 43\n", encoding="utf-8")
                test_file.write_text(test_file.read_text(encoding="utf-8").replace("42", "43"), encoding="utf-8")
                return {
                    "yizijue_gateway": {
                        "response_mode": "build_mode_tool_execution",
                        "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                    }
                }
            manifest = workspace / ".yizijue" / "manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {
                        "sha256_map": {
                            "anthropic_build/main.py": hashlib.sha256(target.read_bytes()).hexdigest(),
                            "test_anthropic_build.py": hashlib.sha256(test_file.read_bytes()).hexdigest(),
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return {
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [
                        {
                            "status": "completed",
                            "next_hexagram": "000",
                            "archive": {"manifest_path": ".yizijue/manifest.json"},
                        }
                    ],
                }
            }

        with TemporaryDirectory() as tmpdir, patch.object(
            live_gateway_smoke,
            "_json_request",
            side_effect=fake_json_request,
        ):
            payload = live_gateway_smoke._run_anthropic_tool_call_smoke("http://127.0.0.1:8765", tmpdir)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["next_hexagram"], "001")
        self.assertEqual(payload["file_written"], True)
        self.assertEqual(payload["failure_verify_status"], "needs_fix")
        self.assertEqual(payload["post_failure_tools"], ["native_inspect_card"])
        self.assertEqual(payload["inspect_next_hexagram"], "111")
        self.assertEqual(payload["post_inspect_tools"], ["write_file"])
        self.assertEqual(payload["repair_status"], "ok")
        self.assertEqual(payload["repaired_file_written"], True)
        self.assertEqual(payload["post_repair_verify_status"], "completed")
        self.assertEqual(payload["post_repair_manifest_sha256_matches"], True)
        self.assertEqual(len(calls), 9)

    def test_sse_request_extracts_completed_responses_payload(self):
        completed = {
            "type": "response.completed",
            "response": {
                "id": "resp_1",
                "object": "response",
                "output_text": "Build Mode Evidence",
                "yizijue_gateway": {
                    "response_mode": "build_mode_tool_execution",
                    "build_mode_tool_results": [{"status": "ok", "next_hexagram": "001"}],
                },
            },
        }
        data = (
            "event: response.output_text.delta\n"
            'data: {"type":"response.output_text.delta","delta":"x"}\n\n'
            "event: response.completed\n"
            f"data: {json.dumps(completed)}\n\n"
        ).encode("utf-8")

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return data

        with patch.object(live_gateway_smoke.urlrequest, "urlopen", return_value=FakeResponse()):
            payload = live_gateway_smoke._sse_json_request(
                "POST",
                "http://127.0.0.1:8765/v1/responses",
                json={"model": "mock"},
            )

        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
        self.assertEqual(payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"], "001")

    def test_mock_upstream_can_emit_responses_build_write_call(self):
        from scripts import mock_tool_call_upstream

        payload = mock_tool_call_upstream.build_mock_chat_response(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "写一个 responses build 文件",
                    }
                ]
            }
        )

        calls = payload["choices"][0]["message"]["tool_calls"]
        arguments = json.loads(calls[0]["function"]["arguments"])
        self.assertEqual(calls[0]["function"]["name"], "write_file")
        self.assertEqual(arguments["path"], "responses_build/main.py")
        self.assertEqual(arguments["content"], "VALUE = 42\n")

    def test_mock_upstream_can_emit_responses_repair_write_call(self):
        from scripts import mock_tool_call_upstream

        payload = mock_tool_call_upstream.build_mock_chat_response(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "run_responses_repair_write",
                    }
                ]
            }
        )

        calls = payload["choices"][0]["message"]["tool_calls"]
        main_args = json.loads(calls[0]["function"]["arguments"])
        test_args = json.loads(calls[1]["function"]["arguments"])
        self.assertEqual(main_args["path"], "responses_build/main.py")
        self.assertEqual(main_args["content"], "VALUE = 43\n")
        self.assertEqual(test_args["path"], "test_responses_build.py")
        self.assertIn("responses_build/main.py", test_args["content"])
        self.assertIn("43", test_args["content"])

    def test_mock_upstream_can_emit_anthropic_build_tool_use(self):
        from scripts import mock_tool_call_upstream

        payload = mock_tool_call_upstream.build_mock_anthropic_response(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "写一个 anthropic build 文件",
                    }
                ]
            }
        )

        block = payload["content"][0]
        self.assertEqual(block["type"], "tool_use")
        self.assertEqual(block["name"], "write_file")
        self.assertEqual(block["input"]["path"], "anthropic_build/main.py")
        self.assertEqual(block["input"]["content"], "VALUE = 42\n")

    def test_mock_upstream_can_emit_anthropic_repair_tool_use(self):
        from scripts import mock_tool_call_upstream

        payload = mock_tool_call_upstream.build_mock_anthropic_response(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "run_anthropic_repair_write",
                    }
                ]
            }
        )

        first = payload["content"][0]
        second = payload["content"][1]
        self.assertEqual(first["name"], "write_file")
        self.assertEqual(first["input"]["path"], "anthropic_build/main.py")
        self.assertEqual(first["input"]["content"], "VALUE = 43\n")
        self.assertEqual(second["input"]["path"], "test_anthropic_build.py")
        self.assertIn("anthropic_build/main.py", second["input"]["content"])
        self.assertIn("43", second["input"]["content"])


if __name__ == "__main__":
    unittest.main()
