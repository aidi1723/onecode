from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from scripts import live_agent_benchmark


class LiveAgentBenchmarkTest(unittest.TestCase):
    def test_fake_benchmark_writes_bare_vs_guarded_report(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "live.json"
            output_md = Path(tmpdir) / "live.md"
            workspace_parent = Path(tmpdir) / "workspaces"

            report = live_agent_benchmark.run_benchmark(
                model="fake-cheap-model",
                task_id="SECURE_B2B_LEDGER_SYNC_REPAIR",
                task_prompt="修复 sync_node.py 同步死锁 Bug，跑测试，输出架构与风险总结。",
                fixture_path=Path("tests/fixtures/secure_b2b_ledger"),
                output_json=output_json,
                output_md=output_md,
                workspace_parent=workspace_parent,
                max_turns=10,
                runner_mode="fake",
            )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["task_id"], "SECURE_B2B_LEDGER_SYNC_REPAIR")
            self.assertEqual(report["model"], "fake-cheap-model")
            self.assertEqual(set(report["groups"]), {"bare", "guarded"})
            self.assertEqual(report["groups"]["bare"]["success"], False)
            self.assertEqual(report["groups"]["guarded"]["success"], True)
            self.assertEqual(report["groups"]["guarded"]["test_exit_codes"][-1], 0)
            self.assertLess(
                report["groups"]["guarded"]["tokens"]["total_tokens"],
                report["groups"]["bare"]["tokens"]["total_tokens"],
            )
            self.assertEqual(report["comparison"]["winner"], "guarded")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())

            written = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(written["comparison"]["token_savings"], report["comparison"]["token_savings"])
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("| group | success | turns | total_tokens | wall_time_seconds |", markdown)
            self.assertIn("guarded", markdown)

    def test_script_can_run_fake_mode_from_cli(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "live.json"
            output_md = Path(tmpdir) / "live.md"
            workspace_parent = Path(tmpdir) / "workspaces"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/live_agent_benchmark.py",
                    "--model",
                    "fake-cheap-model",
                    "--runner-mode",
                    "fake",
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--workspace-parent",
                    str(workspace_parent),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_json.exists())
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"], payload)

    def test_real_http_cli_reads_sensitive_configuration_from_environment(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "live-http.json"
            output_md = Path(tmpdir) / "live-http.md"
            env = {
                **os.environ,
                "ONEWORD_BENCHMARK_MODEL": "env-model",
                "ONEWORD_UPSTREAM_BASE_URL": "http://upstream.invalid/v1",
                "ONEWORD_GATEWAY_BASE_URL": "http://gateway.invalid/v1",
                "ONEWORD_UPSTREAM_API_KEY": "env-secret-key",
                "ONEWORD_GATEWAY_TOKEN": "env-gateway-token",
            }
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/live_agent_benchmark.py",
                    "--runner-mode",
                    "real-http",
                    "--dry-run-config",
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("env-secret-key", result.stdout)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["model"], "env-model")
            self.assertEqual(payload["configuration"]["api_key"], "<redacted>")
            self.assertEqual(payload["configuration"]["gateway_token"], "<redacted>")
            self.assertEqual(payload["configuration"]["upstream_base_url"], "http://upstream.invalid/v1")

    def test_real_http_benchmark_collects_same_model_metrics(self):
        calls = []
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "content": "I should run tests again.",
                            "tool_calls": [
                                {"function": {"name": "read_file", "arguments": json.dumps({"path": "sync_node.py"})}},
                                {"function": {"name": "unknown_probe", "arguments": "{}"}},
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 900, "completion_tokens": 300, "total_tokens": 1200},
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "Tests pass. Summary ready.",
                            "tool_calls": [],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 500, "completion_tokens": 120, "total_tokens": 620},
                "yizijue_gateway": {
                    "active_code": "修",
                    "hexagram": {"action": "LAUNCH_ISOLATED_SANDBOX"},
                    "tool_guard": {"allowed": True},
                },
            },
        ]

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, json.loads(request.data.decode("utf-8"))))
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = json.dumps(responses.pop(0)).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "live-http.json"
            output_md = Path(tmpdir) / "live-http.md"
            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    output_json=output_json,
                    output_md=output_md,
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["runner_mode"], "real-http")
            self.assertEqual(report["groups"]["bare"]["tokens"]["total_tokens"], 1200)
            self.assertEqual(report["groups"]["guarded"]["tokens"]["total_tokens"], 620)
            self.assertEqual(report["groups"]["bare"]["tool_calls"], ["read_file", "unknown_probe"])
            self.assertEqual(report["groups"]["guarded"]["gateway_actions"], ["LAUNCH_ISOLATED_SANDBOX"])
            self.assertEqual(report["comparison"]["token_savings"], 580)
            self.assertEqual(calls[0][0], "http://upstream.test/v1/chat/completions")
            self.assertEqual(calls[1][0], "http://gateway.test/v1/chat/completions")
            self.assertTrue(output_json.exists())

    def test_real_http_benchmark_reports_multi_artifact_hashes(self):
        responses = [
            {
                "choices": [{"message": {"content": "done", "tool_calls": []}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
            {
                "choices": [{"message": {"content": "guarded done", "tool_calls": []}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
                "yizijue_gateway": {"active_code": "总"},
            },
        ]

        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = json.dumps(responses.pop(0)).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / "fixture"
            (fixture / "tests").mkdir(parents=True)
            (fixture / "mesh_node.py").write_text("class MeshNode: pass\n", encoding="utf-8")
            (fixture / "consensus.py").write_text("def broadcast_put(): pass\n", encoding="utf-8")
            (fixture / "tests" / "test_mesh.py").write_text("def test_mesh(): pass\n", encoding="utf-8")

            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    task_id="EPHEMERAL_MESH_KV",
                    task_prompt="实现 ephemeral-mesh-kv 三节点 TTL Mesh 热数据缓存环",
                    fixture_path=fixture,
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    output_json=Path(tmpdir) / "live-http.json",
                    output_md=Path(tmpdir) / "live-http.md",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

        guarded_hashes = report["groups"]["guarded"]["artifact_sha256"]
        self.assertEqual(set(guarded_hashes), {"mesh_node.py", "consensus.py", "tests/test_mesh.py"})
        self.assertEqual(report["groups"]["guarded"]["final_patch_sha256"], guarded_hashes["mesh_node.py"])

    def test_real_http_benchmark_treats_http_client_errors_as_failed_runs(self):
        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 401
            response.read.return_value = json.dumps(
                {"code": "INVALID_API_KEY", "message": "Invalid API key"}
            ).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

        self.assertFalse(report["ok"], report)
        self.assertFalse(report["groups"]["bare"]["success"], report["groups"]["bare"])
        self.assertFalse(report["groups"]["guarded"]["success"], report["groups"]["guarded"])
        self.assertEqual(report["groups"]["bare"]["http_statuses"], [401])
        self.assertEqual(report["groups"]["guarded"]["http_statuses"], [401])
        self.assertEqual(report["groups"]["bare"]["http_errors"][0]["status"], 401)
        self.assertEqual(report["groups"]["bare"]["http_errors"][0]["type"], "INVALID_API_KEY")
        self.assertEqual(report["groups"]["guarded"]["http_errors"][0]["status"], 401)
        self.assertEqual(report["groups"]["guarded"]["http_errors"][0]["type"], "INVALID_API_KEY")
        self.assertEqual(report["comparison"]["winner"], "tie")

    def test_real_http_benchmark_retries_transient_503_and_records_attempts(self):
        attempts = {"count": 0}

        def fake_urlopen(request, timeout):
            attempts["count"] += 1
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            if attempts["count"] == 1:
                response.status = 503
                response.read.return_value = json.dumps(
                    {"error": {"type": "upstream_overloaded", "message": "try again"}}
                ).encode("utf-8")
            else:
                response.status = 200
                response.read.return_value = json.dumps(
                    {
                        "choices": [{"message": {"content": "ok", "tool_calls": []}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                ).encode("utf-8")
            return response

        with patch("scripts.live_agent_benchmark.time.sleep") as sleep, patch(
            "scripts.live_agent_benchmark.urlrequest.urlopen",
            side_effect=fake_urlopen,
        ):
            response = live_agent_benchmark._post_chat_completion(
                "http://gateway.test/v1/chat/completions",
                {"model": "same-model", "messages": []},
                "test-key",
                retry_503=1,
            )

        self.assertEqual(response["http_status"], 200)
        self.assertEqual(response["attempts"], 2)
        self.assertEqual(response["transient_http_errors"][0]["status"], 503)
        self.assertEqual(response["transient_http_errors"][0]["type"], "upstream_overloaded")
        sleep.assert_called_once()

    def test_real_http_benchmark_writes_partial_report_when_group_wall_timeout_hits(self):
        def fake_run_group(*, label, model, task_prompt, workspace, fixture_path, max_turns, group_timeout_seconds=None, **kwargs):
            Path(workspace).mkdir(parents=True, exist_ok=True)
            if label == "guarded":
                (Path(workspace) / "mesh_node.py").write_text("class MeshNode: pass\n", encoding="utf-8")
                return live_agent_benchmark._partial_real_http_group_result(
                    label=label,
                    model=model,
                    task_prompt=task_prompt,
                    workspace=Path(workspace),
                    started=0.0,
                    reason="group_wall_timeout",
                    messages=[{"role": "user", "content": task_prompt}],
                    usages=[],
                    tool_calls=["edit_scoped_file"],
                    external_tool_calls=[],
                    gateway_actions=["scoped_writer"],
                    http_statuses=[200],
                    http_errors=[],
                    transient_http_errors=[],
                    final_trace=["造", "修"],
                    tool_results=[],
                    invalid_patch_count=0,
                    test_exit_codes=[],
                    turns_completed=1,
                    hexagram_trajectory=["111111"],
                )
            return live_agent_benchmark._partial_real_http_group_result(
                label=label,
                model=model,
                task_prompt=task_prompt,
                workspace=Path(workspace),
                started=0.0,
                reason="group_wall_timeout",
                messages=[{"role": "user", "content": task_prompt}],
                usages=[],
                tool_calls=[],
                external_tool_calls=[],
                gateway_actions=[],
                http_statuses=[599],
                http_errors=[{"status": 599, "type": "network_error", "message": "timeout"}],
                transient_http_errors=[],
                final_trace=["bare"],
                tool_results=[],
                invalid_patch_count=0,
                test_exit_codes=[],
                turns_completed=0,
                hexagram_trajectory=["010111"],
            )

        with TemporaryDirectory() as tmpdir, patch(
            "scripts.live_agent_benchmark._run_real_http_group",
            side_effect=fake_run_group,
        ):
            fixture = Path(tmpdir) / "fixture"
            (fixture / "tests").mkdir(parents=True)
            (fixture / "tests" / "__init__.py").write_text("", encoding="utf-8")
            output_json = Path(tmpdir) / "partial.json"
            output_md = Path(tmpdir) / "partial.md"
            report = live_agent_benchmark.run_benchmark(
                model="same-model",
                task_id="EPHEMERAL_MESH_KV",
                task_prompt="实现 ephemeral-mesh-kv 三节点 TTL Mesh 热数据缓存环",
                fixture_path=fixture,
                runner_mode="real-http",
                upstream_base_url="http://upstream.test/v1",
                gateway_base_url="http://gateway.test/v1",
                api_key="test-key",
                gateway_token="gateway-token",
                output_json=output_json,
                output_md=output_md,
                workspace_parent=Path(tmpdir) / "workspaces",
                group_timeout_seconds=1,
            )

            written = json.loads(output_json.read_text(encoding="utf-8"))

        self.assertTrue(report["partial"])
        self.assertTrue(report["groups"]["guarded"]["partial"])
        self.assertEqual(report["groups"]["guarded"]["partial_reason"], "group_wall_timeout")
        self.assertEqual(report["groups"]["guarded"]["hexagram_trajectory"], ["111111"])
        self.assertIsNotNone(report["groups"]["guarded"]["artifact_sha256"]["mesh_node.py"])
        self.assertTrue(written["partial"])

    def test_real_http_benchmark_passes_http_timeout_to_chat_requests(self):
        seen_timeouts = []

        def fake_urlopen(request, timeout):
            seen_timeouts.append(timeout)
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = json.dumps(
                {
                    "choices": [{"message": {"content": "ok", "tool_calls": []}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            ).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir, patch(
            "scripts.live_agent_benchmark.urlrequest.urlopen",
            side_effect=fake_urlopen,
        ):
            fixture = Path(tmpdir) / "fixture"
            (fixture / "tests").mkdir(parents=True)
            (fixture / "tests" / "__init__.py").write_text("", encoding="utf-8")
            live_agent_benchmark.run_benchmark(
                model="same-model",
                task_id="EPHEMERAL_MESH_KV",
                task_prompt="实现 ephemeral-mesh-kv 三节点 TTL Mesh 热数据缓存环",
                fixture_path=fixture,
                runner_mode="real-http",
                upstream_base_url="http://upstream.test/v1",
                gateway_base_url="http://gateway.test/v1",
                api_key="test-key",
                gateway_token="gateway-token",
                output_json=Path(tmpdir) / "timeout.json",
                output_md=Path(tmpdir) / "timeout.md",
                workspace_parent=Path(tmpdir) / "workspaces",
                max_turns=1,
                http_timeout_seconds=7,
            )

        self.assertEqual(seen_timeouts, [7, 7])

    def test_real_http_benchmark_records_network_timeout_as_failed_run(self):
        with TemporaryDirectory() as tmpdir:
            output_json = Path(tmpdir) / "live-http.json"
            output_md = Path(tmpdir) / "live-http.md"
            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=TimeoutError("timed out")):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    output_json=output_json,
                    output_md=output_md,
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

            self.assertFalse(report["ok"], report)
            self.assertFalse(report["groups"]["bare"]["success"])
            self.assertFalse(report["groups"]["guarded"]["success"])
            self.assertEqual(report["groups"]["bare"]["http_statuses"], [599])
            self.assertEqual(report["groups"]["guarded"]["http_statuses"], [599])
            self.assertEqual(report["groups"]["bare"]["http_errors"][0]["type"], "network_error")
            self.assertEqual(report["groups"]["guarded"]["http_errors"][0]["type"], "network_error")
            self.assertTrue(output_json.exists())

    def test_real_http_benchmark_executes_tools_and_feeds_results_to_next_turn(self):
        calls = []
        responses_by_url = {
            "http://upstream.test/v1/chat/completions": [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "bare_read_1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": json.dumps({"path": "sync_node.py"}),
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                },
                {
                    "choices": [{"message": {"content": "saw sync_node.py", "tool_calls": []}}],
                    "usage": {"prompt_tokens": 180, "completion_tokens": 20, "total_tokens": 200},
                },
            ],
            "http://gateway.test/v1/chat/completions": [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "guard_read_1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": json.dumps({"path": "sync_node.py"}),
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 90, "completion_tokens": 25, "total_tokens": 115},
                    "yizijue_gateway": {"active_code": "查"},
                },
                {
                    "choices": [{"message": {"content": "guarded saw sync_node.py", "tool_calls": []}}],
                    "usage": {"prompt_tokens": 140, "completion_tokens": 20, "total_tokens": 160},
                    "yizijue_gateway": {"active_code": "总"},
                },
            ],
        }

        def fake_urlopen(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            calls.append((request.full_url, body))
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            if request.full_url.endswith("/v1/yizijue/preflight-tool"):
                payload = {"allowed": True, "violations": []}
            elif request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {
                    "status": "accepted",
                    "audit_log_path": ".oneword/audit.jsonl",
                    "evidence": {"sha256": "evidence-sha"},
                }
            else:
                payload = responses_by_url[request.full_url].pop(0)
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=2,
                )

        bare_second = [body for url, body in calls if url == "http://upstream.test/v1/chat/completions"][1]
        guarded_second = [body for url, body in calls if url == "http://gateway.test/v1/chat/completions"][1]
        preflight_calls = [body for url, body in calls if url.endswith("/v1/yizijue/preflight-tool")]
        evidence_calls = [body for url, body in calls if url.endswith("/v1/yizijue/submit-evidence")]

        self.assertEqual(report["groups"]["bare"]["tool_results"][0]["tool"], "read_file")
        self.assertIn("def sync_inventory", report["groups"]["bare"]["tool_results"][0]["stdout"])
        self.assertEqual(report["groups"]["guarded"]["tool_results"][0]["tool"], "read_file")
        self.assertEqual(preflight_calls[0]["tool_name"], "read_file")
        self.assertEqual(evidence_calls[0]["source"], "live_agent_benchmark")
        self.assertEqual(evidence_calls[0]["command"], "live_agent:read_file")
        self.assertEqual(evidence_calls[0]["exit_code"], 0)
        self.assertEqual(report["groups"]["guarded"]["tool_results"][0]["evidence_submission"]["status"], "accepted")
        self.assertTrue(any(message.get("role") == "tool" for message in bare_second["messages"]))
        self.assertTrue(any(message.get("role") == "tool" for message in guarded_second["messages"]))

    def test_real_http_benchmark_records_build_mode_internal_tool_results(self):
        responses_by_url = {
            "http://upstream.test/v1/chat/completions": [
                {
                    "choices": [{"message": {"content": "bare summary", "tool_calls": []}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
                }
            ],
            "http://gateway.test/v1/chat/completions": [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "Build Mode Evidence:\n1. status=ok hexagram=111 next=001 action=scoped_writer files=sync_node.py",
                                "tool_calls": [],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
                    "yizijue_gateway": {
                        "active_code": "修",
                        "oneword_build_mode": {"hexagram": "111"},
                        "build_mode_tool_results": [
                            {
                                "status": "ok",
                                "hexagram": "111",
                                "next_hexagram": "001",
                                "shadow_action": "scoped_writer",
                                "tool": "edit_scoped_file",
                                "changed_files": ["sync_node.py"],
                            },
                            {
                                "status": "completed",
                                "hexagram": "001",
                                "next_hexagram": "000",
                                "shadow_action": "sandbox_runner",
                                "tool": "run_pytest",
                                "exit_code": 1,
                                "evidence": {"exit_code": 127},
                            },
                        ],
                    },
                }
            ],
        }

        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            response.read.return_value = json.dumps(responses_by_url[request.full_url].pop(0)).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

        guarded = report["groups"]["guarded"]
        self.assertEqual(guarded["tool_calls"], ["edit_scoped_file", "run_pytest"])
        self.assertEqual(guarded["test_exit_codes"], [127])
        self.assertEqual(guarded["forbidden_tool_attempts"], 0)
        self.assertEqual(guarded["gateway_actions"], ["scoped_writer", "sandbox_runner"])
        self.assertEqual(guarded["final_trace"], ["修", "测", "总"])
        self.assertEqual(guarded["tool_results"][0]["tool"], "edit_scoped_file")
        self.assertEqual(guarded["tool_results"][1]["tool"], "run_pytest")

    def test_real_http_benchmark_compacts_large_tool_outputs_in_report(self):
        large_stdout = "x" * 9000
        responses_by_url = {
            "http://upstream.test/v1/chat/completions": [
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "bare_read_1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": json.dumps({"path": "sync_node.py"}),
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
                }
            ],
            "http://gateway.test/v1/chat/completions": [
                {
                    "choices": [{"message": {"content": "done", "tool_calls": []}}],
                    "usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
                    "yizijue_gateway": {"active_code": "总"},
                }
            ],
        }

        def fake_urlopen(request, timeout):
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.status = 200
            if request.full_url.endswith("/v1/yizijue/submit-evidence"):
                payload = {"status": "accepted", "audit_log_path": ".oneword/audit.jsonl", "evidence": {}}
            elif request.full_url.endswith("/v1/yizijue/preflight-tool"):
                payload = {"allowed": True, "violations": []}
            else:
                payload = responses_by_url[request.full_url].pop(0)
            response.read.return_value = json.dumps(payload).encode("utf-8")
            return response

        with TemporaryDirectory() as tmpdir:
            with patch(
                "scripts.live_agent_benchmark.execute_registered_tool",
                return_value={"tool": "read_file", "exit_code": 0, "stdout": large_stdout, "stderr": ""},
            ), patch("scripts.live_agent_benchmark.urlrequest.urlopen", side_effect=fake_urlopen):
                report = live_agent_benchmark.run_benchmark(
                    model="same-model",
                    runner_mode="real-http",
                    upstream_base_url="http://upstream.test/v1",
                    gateway_base_url="http://gateway.test/v1",
                    api_key="test-key",
                    gateway_token="gateway-token",
                    workspace_parent=Path(tmpdir) / "workspaces",
                    max_turns=1,
                )

        stored_stdout = report["groups"]["bare"]["tool_results"][0]["stdout"]
        self.assertLessEqual(len(stored_stdout), 1200)
        self.assertEqual(stored_stdout, large_stdout[-1200:])

    def test_quality_core_penalizes_forbidden_tools_and_timeout_exit_codes(self):
        bad = live_agent_benchmark._quality_core(
            tool_calls=["read_file", "bash", "run_pytest"],
            gateway_actions=[],
            http_statuses=[200, 200, 200],
            test_exit_codes=[124],
            tool_results=[{"tool": "run_pytest", "exit_code": 124}],
            turns_used=3,
        )
        good = live_agent_benchmark._quality_core(
            tool_calls=[],
            gateway_actions=[],
            http_statuses=[200, 200, 200],
            test_exit_codes=[],
            tool_results=[],
            turns_used=3,
        )

        self.assertEqual(bad["has_timeout"], True)
        self.assertEqual(bad["forbidden_tool_attempts"], 1)
        self.assertLess(bad["score"], good["score"])
        self.assertLessEqual(bad["score"], 0.25)
        self.assertIn("timeout_or_resource_exhaustion", bad["penalties"])

    def test_submit_tool_evidence_includes_failure_summary_for_gateway_decay(self):
        captured: dict[str, object] = {}

        def fake_post_json(url, body, bearer_token):
            captured["url"] = url
            captured["body"] = body
            captured["bearer_token"] = bearer_token
            return {"status": "accepted"}

        with patch("scripts.live_agent_benchmark._post_json", side_effect=fake_post_json):
            result = live_agent_benchmark._submit_tool_evidence(
                "http://gateway.test/v1",
                "token",
                Path("/tmp/workspace"),
                {
                    "tool": "run_pytest",
                    "exit_code": 124,
                    "stdout": "",
                    "stderr": "TIMEOUT",
                    "failure_summary": "sync_node.py:40 in sync_inventory\nConnectError",
                },
            )

        self.assertEqual(result["status"], "accepted")
        body = captured["body"]
        self.assertIsInstance(body, dict)
        self.assertIn("TIMEOUT", body["stderr"])
        self.assertIn("failure_summary:", body["stderr"])
        self.assertIn("sync_node.py:40", body["stderr"])

    def test_quality_core_zeroes_score_when_security_findings_exist(self):
        quality = live_agent_benchmark._quality_core(
            tool_calls=["dependency_security_scan"],
            gateway_actions=[],
            http_statuses=[200],
            test_exit_codes=[],
            tool_results=[{"tool": "dependency_security_scan", "exit_code": 2, "stdout": "3"}],
            turns_used=1,
        )

        self.assertEqual(quality["vuln_count"], 3)
        self.assertEqual(quality["score"], 0.0)
        self.assertIn("security_vulnerability_zero_tolerance", quality["penalties"])

    def test_compare_selects_guarded_when_quality_is_materially_higher(self):
        bare = {
            "success": True,
            "quality_score": 0.2,
            "turns_used": 3,
            "tokens": {"total_tokens": 603},
        }
        guarded = {
            "success": True,
            "quality_score": 0.45,
            "turns_used": 3,
            "tokens": {"total_tokens": 6410},
        }

        comparison = live_agent_benchmark._compare(bare, guarded)

        self.assertEqual(comparison["winner"], "guarded")
        self.assertEqual(comparison["winner_reason"], "quality_score_delta")
        self.assertEqual(comparison["quality_delta"], 0.25)


if __name__ == "__main__":
    unittest.main()
