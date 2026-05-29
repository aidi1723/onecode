import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class GatewayServerImportTest(unittest.TestCase):
    def test_gateway_server_import_error_is_actionable_without_fastapi(self):
        try:
            import agent_skill_dictionary.gateway_server as gateway_server
        except RuntimeError as exc:
            self.assertIn("requirements-gateway.txt", str(exc))
        else:
            self.assertTrue(hasattr(gateway_server, "app"))

    def test_run_endpoint_handler_returns_oneword_result_without_fastapi(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            result = gateway_server.run_task_payload(
                {"input": "帮我看看项目结构", "workspace": str(workspace)}
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trace"], ["查", "总"])
            self.assertTrue(Path(result["audit_log_path"]).exists())

    def test_run_endpoint_rejects_workspace_outside_allowed_root(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as allowed_dir, TemporaryDirectory() as outside_dir:
            with patch.dict(
                gateway_server.os.environ,
                {"ONEWORD_WORKSPACE_ROOT": allowed_dir},
                clear=False,
            ):
                result = gateway_server.run_task_payload(
                    {"input": "帮我看看项目结构", "workspace": outside_dir}
                )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"]["type"], "workspace_not_allowed")

    def test_submit_evidence_payload_writes_audit_record_inside_workspace(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.submit_evidence_payload(
                {
                    "workspace": str(workspace),
                    "command": "external_agent_review",
                    "exit_code": 0,
                    "stdout": "review-ok",
                    "stderr": "",
                }
            )

            self.assertEqual(result["status"], "accepted")
            self.assertEqual(result["evidence"]["exit_code"], 0)
            self.assertEqual(result["evidence"]["source"], "external_agent")
            self.assertEqual(result["evidence"]["session_id"], "default")
            self.assertTrue((workspace / ".oneword" / "audit.jsonl").exists())

    def test_submit_evidence_payload_rejects_oversized_output(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            result = gateway_server.submit_evidence_payload(
                {
                    "workspace": tmpdir,
                    "command": "external_agent_review",
                    "exit_code": 0,
                    "stdout": "x" * (gateway_server.MAX_EVIDENCE_FIELD_CHARS + 1),
                    "stderr": "",
                }
            )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"]["type"], "evidence_payload_too_large")

    def test_submit_evidence_payload_records_source_and_session(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            result = gateway_server.submit_evidence_payload(
                {
                    "workspace": tmpdir,
                    "source": "reference_agent",
                    "session_id": "session-123",
                    "command": "reference_agent:list_directory",
                    "exit_code": 0,
                    "stdout": "ok",
                    "stderr": "",
                }
            )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["evidence"]["source"], "reference_agent")
        self.assertEqual(result["evidence"]["session_id"], "session-123")

    def test_build_tool_payload_executes_scoped_write_without_fastapi(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "write_file",
                    "arguments": {"path": "app/main.py", "content": "VALUE = 1\n"},
                }
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["next_hexagram"], "001")
            self.assertTrue((workspace / "app" / "main.py").exists())


    def test_expert_handoff_payload_applies_authorized_seed(self):
        import json
        import sys
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
            clear=False,
        ):
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps({"consecutive_failures": 2}),
                encoding="utf-8",
            )
            result = gateway_server.expert_handoff_payload(
                {
                    "workspace": str(workspace),
                    "request_text": "实现 cluster-state-sync",
                    "token": "secret",
                    "changes": {"sync/models.py": "VALUE = 1\n"},
                    "verify_command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('sync/models.py').exists()",
                    ],
                }
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hexagram"], "000")
            self.assertTrue((workspace / "sync" / "models.py").exists())
            state = json.loads((state_dir / "build-mode-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["consecutive_failures"], 0)
            self.assertEqual(state["results"][-1]["source"], "expert_handoff")
            self.assertEqual(state["results"][-1]["next_hexagram"], "000")

    def test_expert_handoff_payload_uses_session_scoped_state(self):
        import json
        import sys
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_EXPERT_HANDOFF_TOKEN": "secret"},
            clear=False,
        ):
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            default_state = state_dir / "build-mode-state.json"
            session_state = state_dir / "build-mode-state-session-a.json"
            default_state.write_text(json.dumps({"consecutive_failures": 0}), encoding="utf-8")
            session_state.write_text(json.dumps({"consecutive_failures": 2}), encoding="utf-8")

            result = gateway_server.expert_handoff_payload(
                {
                    "workspace": str(workspace),
                    "session_id": "session-a",
                    "request_text": "实现 cluster-state-sync",
                    "token": "secret",
                    "changes": {"sync/models.py": "VALUE = 1\n"},
                    "verify_command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('sync/models.py').exists()",
                    ],
                }
            )

            self.assertEqual(result["status"], "completed")
            default_after = json.loads(default_state.read_text(encoding="utf-8"))
            session_after = json.loads(session_state.read_text(encoding="utf-8"))
            self.assertEqual(default_after["consecutive_failures"], 0)
            self.assertEqual(session_after["consecutive_failures"], 0)
            self.assertEqual(session_after["results"][-1]["source"], "expert_handoff")

    def test_expert_handoff_payload_rejects_workspace_outside_allowed_root(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as allowed_dir, TemporaryDirectory() as outside_dir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_WORKSPACE_ROOT": allowed_dir},
            clear=False,
        ):
            result = gateway_server.expert_handoff_payload(
                {
                    "workspace": outside_dir,
                    "request_text": "实现 cluster-state-sync",
                    "token": "secret",
                    "changes": {"sync/models.py": "VALUE = 1\n"},
                    "verify_command": ["python3", "-c", "raise SystemExit(0)"],
                }
            )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"]["type"], "workspace_not_allowed")

    def test_expert_handoff_payload_rejects_unknown_plan_and_invalid_payload(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            unknown = gateway_server.expert_handoff_payload(
                {
                    "workspace": tmpdir,
                    "request_text": "实现 unknown-project",
                    "token": "secret",
                    "changes": {"sync/models.py": "VALUE = 1\n"},
                    "verify_command": ["python3", "-c", "raise SystemExit(0)"],
                }
            )
            invalid = gateway_server.expert_handoff_payload(
                {
                    "workspace": tmpdir,
                    "request_text": "实现 cluster-state-sync",
                    "token": "secret",
                    "changes": ["bad"],
                    "verify_command": "python3 -m pytest",
                }
            )

        self.assertEqual(unknown["status"], "blocked")
        self.assertEqual(unknown["reason"], "unknown_artifact_plan")
        self.assertEqual(invalid["status"], "blocked")
        self.assertEqual(invalid["reason"], "invalid_changes")


    def test_build_tool_payload_blocks_unplanned_shim_when_request_plan_is_bound(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "write_file",
                    "arguments": {"path": "fastapi/__init__.py", "content": "fake\n"},
                    "request_text": "实现 cluster-state-sync",
                }
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["evidence"]["reason"], "unplanned_artifact_path")
            self.assertFalse((workspace / "fastapi" / "__init__.py").exists())


    def test_build_tool_payload_run_pytest_quarantines_unplanned_side_effect_when_plan_bound(self):
        import sys
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {
                        "command": (
                            f"{sys.executable} -c \"from pathlib import Path; "
                            "Path('sqlmodel').mkdir(); "
                            "Path('sqlmodel/__init__.py').write_text('fake')\""
                        )
                    },
                    "request_text": "实现 cluster-state-sync",
                }
            )

            self.assertEqual(result["status"], "needs_fix")
            self.assertEqual(result["runtime_guard"]["reason"], "post_run_unplanned_artifacts")
            self.assertFalse((workspace / "sqlmodel" / "__init__.py").exists())
            self.assertTrue((workspace / ".yizijue" / "quarantine" / "sqlmodel" / "__init__.py").exists())


    def test_build_tool_payload_persists_failed_verification_state(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {"command": "python3 -c \"raise SystemExit(1)\""},
                    "timeout_seconds": 5,
                }
            )

            self.assertEqual(result["status"], "needs_fix")
            state_path = workspace / ".yizijue" / "build-mode-state.json"
            self.assertTrue(state_path.exists())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["consecutive_failures"], 1)
            self.assertEqual(state["last_exit_code"], 1)
            self.assertEqual(state["results"][0]["status"], "needs_fix")
            self.assertEqual(state["results"][0]["hexagram"], "001")
            self.assertEqual(state["results"][0]["next_hexagram"], "101")
            self.assertIn("repair_card", state)
            self.assertIn("Build Mode Repair Card", state["repair_card"])
            self.assertIn("failure_summary", state["results"][0])
            self.assertEqual(state["gateway_rule"]["aggregation_decision"], "accept_entropy_balanced")
            self.assertIn("gateway_status_code", state["gateway_rule"])
            self.assertEqual(state["gateway_rule"]["source"], "build_mode_state")
            self.assertIn("compressed_summary", state)
            self.assertEqual(state["compression_rule"]["mode"], "internal_caveman")
            self.assertIn("Build Mode Repair Card", state["repair_card"])
            self.assertLessEqual(
                state["compression_rule"]["compressed_chars"],
                state["compression_rule"]["raw_chars"],
            )

    def test_build_tool_payload_timeout_triggers_secure_b2b_expert_handoff(self):
        import json
        import shutil
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            shutil.copytree(Path("tests/fixtures/secure_b2b_ledger"), workspace, dirs_exist_ok=True)

            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {},
                    "request_text": "修复 sync_node.py 同步死锁 Bug，跑测试，输出架构与风险总结。",
                    "timeout_seconds": 1,
                }
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["hexagram"], "100")
            self.assertEqual(result["next_hexagram"], "000")
            self.assertEqual(result["source"], "timeout_flash_expert_handoff")
            self.assertEqual(result["verify"]["exit_code"], 0)
            state_path = workspace / ".yizijue" / "build-mode-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["last_exit_code"], 0)
            self.assertEqual(state["consecutive_failures"], 0)
            self.assertEqual(state["results"][-1]["source"], "expert_handoff")
            self.assertEqual(state["gateway_rule"]["gateway_status_code"], 63)
            self.assertEqual(state["gateway_rule"]["source"], "expert_handoff_state")

    def test_chat_tool_timeout_uses_request_text_for_flash_handoff_plan(self):
        import shutil
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            shutil.copytree(Path("tests/fixtures/secure_b2b_ledger"), workspace, dirs_exist_ok=True)
            response_payload = {
                "id": "chatcmpl_timeout_flash",
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
                                        "name": "run_pytest",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

            payload, status_code = gateway_server.chat_completion_response_payload(
                response_payload,
                {
                    "active_code": "测",
                    "root_opcode": "测",
                    "workspace": str(workspace),
                    "request_text": "修复 sync_node.py 同步死锁 Bug，跑测试，输出架构与风险总结。",
                    "oneword_build_mode": {"hexagram": "001"},
                },
                dictionary,
            )

            self.assertEqual(status_code, 200)
            results = payload["yizijue_gateway"]["build_mode_tool_results"]
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[0]["source"], "timeout_flash_expert_handoff")
            self.assertEqual(results[0]["next_hexagram"], "000")

    def test_build_mode_state_persists_audit_and_decay_metadata(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            gateway_server._persist_build_mode_state(
                str(workspace),
                [
                    {
                        "status": "needs_fix",
                        "hexagram": "001",
                        "next_hexagram": "101",
                        "audit": {"suspicious": True, "recommended_hexagram": "100"},
                        "decay": {"dynamic_threshold": 1, "deadlock_suspected": True},
                    }
                ],
                {},
            )

            state = json.loads((workspace / ".yizijue" / "build-mode-state.json").read_text(encoding="utf-8"))

        self.assertEqual(state["results"][0]["audit"]["recommended_hexagram"], "100")
        self.assertEqual(state["results"][0]["decay"]["dynamic_threshold"], 1)

    def test_build_tool_payload_adds_decay_metadata_for_repeated_verification_failure(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        command = (
            "python3 -c \"print('FAILED tests/test_mesh.py::test_duplicate - "
            "TypeError: bad arg'); raise SystemExit(1)\""
        )
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            first = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {"command": command},
                    "timeout_seconds": 5,
                }
            )
            second = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {"command": command},
                    "timeout_seconds": 5,
                }
            )
            state = json.loads((workspace / ".yizijue" / "build-mode-state.json").read_text(encoding="utf-8"))

        self.assertNotIn("decay", first)
        self.assertEqual(second["decay"]["dynamic_threshold"], 1)
        self.assertTrue(state["results"][0]["decay"]["deadlock_suspected"])

    def test_build_mode_deadlock_decay_triggers_expert_handoff_gate(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_BUILD_MODE": "1"},
            clear=False,
        ):
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "consecutive_failures": 1,
                        "results": [
                            {
                                "status": "needs_fix",
                                "hexagram": "001",
                                "next_hexagram": "110",
                                "decay": {"dynamic_threshold": 1, "deadlock_suspected": True},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            payload, metadata = gateway_server._apply_build_mode_failure_gate(
                {"messages": [{"role": "user", "content": "修复 sync_node.py"}], "tools": [{"type": "function", "function": {"name": "write_file"}}]},
                {"workspace": str(workspace)},
            )

        self.assertEqual(payload["tools"], [])
        self.assertEqual(metadata["oneword_build_mode"]["hexagram"], "100")
        self.assertTrue(metadata["oneword_build_mode"]["failure_gate_locked"])
        self.assertEqual(metadata["build_mode_equilibrium"]["source"], "v3_deadlock_decay_gate")
        self.assertEqual(metadata["build_mode_expert_handoff"]["source"], "v3_deadlock_decay_gate")

    def test_build_tool_payload_persists_behavior_audit_block(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "write_file",
                    "arguments": {"path": "README.md", "content": "safe\n"},
                    "assistant_text": "Before testing, remove ~/SENTINEL.txt with rm -rf.",
                }
            )
            state = json.loads((workspace / ".yizijue" / "build-mode-state.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["audit"]["suspicious"])
        self.assertEqual(state["results"][0]["audit"]["recommended_hexagram"], "100")
        self.assertFalse((workspace / "README.md").exists())

    def test_build_tool_payload_rejects_workspace_outside_allowed_root(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as allowed_dir, TemporaryDirectory() as outside_dir:
            with patch.dict(
                gateway_server.os.environ,
                {"ONEWORD_WORKSPACE_ROOT": allowed_dir},
                clear=False,
            ):
                result = gateway_server.build_tool_payload(
                    {
                        "workspace": outside_dir,
                        "tool_name": "write_file",
                        "arguments": {"path": "app.py", "content": ""},
                    }
                )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"]["type"], "workspace_not_allowed")

    def test_chat_response_executes_build_mode_write_tool_call(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            response_payload = {
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
                                        "arguments": '{"path":"app/main.py","content":"VALUE = 1\\n"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

            payload, status_code = gateway_server.chat_completion_response_payload(
                response_payload,
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
            self.assertNotIn("tool_calls", payload["choices"][0]["message"])
            self.assertIn("Build Mode Evidence", payload["choices"][0]["message"]["content"])
            results = payload["yizijue_gateway"]["build_mode_tool_results"]
            self.assertEqual(results[0]["status"], "ok")
            self.assertEqual(results[0]["next_hexagram"], "001")
            self.assertEqual(
                results[0]["evidence"]["changed_files"],
                ["app/main.py"],
            )
            state_path = workspace / ".yizijue" / "build-mode-state.json"
            self.assertTrue(state_path.exists())
            self.assertIn("app/main.py", state_path.read_text(encoding="utf-8"))

    def test_chat_completions_payload_injects_previous_build_mode_context(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.chat_completion_response_payload(
                {
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
                                            "arguments": '{"path":"app/main.py","content":"VALUE = 1\\n"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续修复并测试"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertIn("Build Mode Context", system_text)
        self.assertIn("app/main.py", system_text)
        self.assertIn("[State]: 101-INSPECT", system_text)

    def test_chat_completions_payload_uses_previous_next_hexagram_for_tools(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.chat_completion_response_payload(
                {
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
                                            "arguments": '{"path":"app/main.py","content":"VALUE = 1\\n"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        tool_names = [tool["function"]["name"] for tool in result["payload"]["tools"]]
        self.assertEqual(tool_names, ["run_pytest"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")
        self.assertEqual(result["metadata"]["build_mode_state_injection"]["next_hexagram"], "001")
        self.assertIn("gateway_rule", result["metadata"])
        self.assertIn("gateway_status_code", result["metadata"]["gateway_rule"])
        self.assertEqual(result["metadata"]["gateway_rule"]["outer_plane"], "environment")

    def test_compact_build_mode_results_adds_gateway_rule(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        compacted = gateway_server._compact_build_mode_results(
            [
                {
                    "status": "completed",
                    "hexagram": "111",
                    "next_hexagram": "000",
                    "evidence": {"changed_files": ["mesh.py"], "exit_code": 0},
                }
            ]
        )

        self.assertEqual(compacted[0]["gateway_rule"]["gateway_status_code"], 63)
        self.assertEqual(compacted[0]["gateway_rule"]["dispatch_decision"], "continue")

    def test_preflight_tool_payload_adds_gateway_rule_for_policy_breach(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        payload = gateway_server.preflight_tool_payload(
            {
                "active_code": "查",
                "tool_name": "write_file",
                "arguments": {"path": "app.py", "content": "print(1)\n"},
            },
            dictionary,
        )

        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["gateway_rule"]["gateway_status_code"], 48)
        self.assertEqual(payload["gateway_rule"]["transition_action"], "halt")
        self.assertEqual(payload["gateway_rule"]["dispatch_decision"], "stop")

    def test_chat_completions_payload_uses_write_file_fallback_after_empty_patch_retry(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.chat_completion_response_payload(
                {
                    "id": "chatcmpl_empty_patch",
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
                                            "name": "apply_patch",
                                            "arguments": '{"patch":""}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续写文件"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "apply_patch", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        tools = result["payload"]["tools"]
        self.assertEqual([tool["function"]["name"] for tool in tools], ["write_file"])
        self.assertEqual(tools[0]["function"]["parameters"]["required"], ["path", "content"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["fallback_tools"], ["write_file"])

    def test_chat_completions_payload_injects_next_artifact_instruction_for_secure_rpc_mesh(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )
            support_files_exist = (
                (Path(tmpdir) / "api" / "__init__.py").exists(),
                (Path(tmpdir) / "core" / "__init__.py").exists(),
                (Path(tmpdir) / "tests" / "__init__.py").exists(),
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertIn("Build Mode Artifact Plan", system_text)
        self.assertIn("目标文件: core/crypto.py", system_text)
        self.assertIn("本轮只写一个文件", system_text)
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "core/crypto.py")
        self.assertEqual(support_files_exist, (True, True, True))
        self.assertEqual(
            result["metadata"]["build_mode_artifact_plan"]["support_files"],
            ["api/__init__.py", "core/__init__.py", "tests/__init__.py"],
        )

    def test_chat_completions_payload_halts_cluster_state_sync_when_real_deps_required(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
                "ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS": "1",
                "ONEWORD_BUILD_MODE_PYTHON": str(Path(tmpdir) / "missing-python"),
            },
            clear=False,
        ):
            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "实现 cluster-state-sync"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertEqual(result["payload"]["tools"], [])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(
            result["metadata"]["oneword_build_mode"]["source"],
            "sovereignty_environment_gate",
        )
        self.assertIn("sqlmodel", result["metadata"]["build_mode_sovereignty"]["environment_gate"]["missing_packages"])
        self.assertIn("Missing Environment Gate", system_text)
        self.assertIn("不要自造 fastapi/sqlmodel/pytest shim", system_text)

    def test_chat_completions_payload_halts_cluster_state_sync_unplanned_shim(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            (workspace / "fastapi").mkdir()
            (workspace / "fastapi" / "__init__.py").write_text("fake\n", encoding="utf-8")

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 cluster-state-sync"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertEqual(result["payload"]["tools"], [])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(
            result["metadata"]["oneword_build_mode"]["source"],
            "sovereignty_workspace_gate",
        )
        self.assertIn(
            "fastapi/__init__.py",
            result["metadata"]["build_mode_sovereignty"]["workspace_gate"]["unplanned_paths"],
        )
        self.assertIn("Workspace Sovereignty Gate", system_text)
        self.assertIn("未授权本地造物", system_text)

    def test_chat_completions_payload_continues_artifact_plan_before_verify_state(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            (workspace / "core").mkdir()
            (workspace / "core" / "crypto.py").write_text("VALUE = 1\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 0,
                        "results": [{"status": "ok", "hexagram": "111", "next_hexagram": "001"}],
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "write_file")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_continuation_gate")
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "api/server.py")
        self.assertIn("目标文件: api/server.py", system_text)

    def test_chat_completions_payload_build_mode_artifact_plan_overrides_hexagram_halt(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        prompt = (
            "实现 ephemeral-mesh-kv：基于 Python asyncio 的三节点局部网格 Mesh 热数据缓存环。"
            "必须且只能对齐 mesh_node.py、consensus.py、tests/test_mesh.py 三个资产；"
            "跑测试并输出架构与风险总结。"
        )
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "read_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "edit_scoped_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "bash", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["metadata"]["hexagram_route"]["action"], "FORCE_HALT_TO_HUMAN")
        self.assertFalse(result["metadata"]["kernel_policy"]["halt_model_forwarding"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "mesh_node.py")
        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["write_file"])


    def test_chat_completions_payload_enters_verify_gate_when_secure_rpc_mesh_artifacts_complete(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")
        self.assertTrue(result["metadata"]["build_mode_verify_gate"]["complete"])
        self.assertIn("Build Mode Verify Gate", system_text)
        self.assertIn("python3 -m unittest discover -s tests -v", system_text)

    def test_chat_completions_payload_enters_verify_gate_when_complete_after_state_override(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 0,
                        "results": [{"status": "ok", "hexagram": "111", "next_hexagram": "001"}],
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "run_pytest")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_verify_gate")

    def test_build_mode_create_forces_full_file_write_for_planned_sync_node_repair(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [
                        {
                            "role": "user",
                            "content": "修复 sync_node.py 同步死锁 Bug，跑测试，输出架构与风险总结。",
                        }
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "read_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "edit_scoped_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["metadata"]["codes"], ["修", "测", "总"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "write_file")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_continuation_gate")
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "sync_node.py")

    def test_chat_completions_payload_verifies_after_successful_repair_write(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 1,
                        "last_exit_code": 1,
                        "results": [
                            {
                                "status": "ok",
                                "hexagram": "111",
                                "next_hexagram": "001",
                                "changed_files": ["core/crypto.py"],
                            }
                        ],
                        "repair_card": "Build Mode Repair Card\nFAILED tests/test_mesh.py::test_encrypt",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "run_pytest")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_verify_gate")


    def test_chat_completions_verify_gate_injects_run_pytest_when_client_omits_it(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "apply_patch", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "run_pytest")
        self.assertEqual(result["payload"]["tools"][0]["function"]["parameters"]["required"], ["command"])

    def test_chat_completions_payload_injects_repair_card_after_failed_verification(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            (workspace / "api").mkdir()
            (workspace / "api" / "server.py").write_text(
                "class SecureMeshServer:\n"
                "    def __init__(self, private_key):\n"
                "        pass\n",
                encoding="utf-8",
            )
            gateway_server.build_tool_payload(
                {
                    "workspace": str(workspace),
                    "tool_name": "run_pytest",
                    "arguments": {
                        "command": (
                            "python3 -c \"print('FAILED tests/test_mesh.py::test_duplicate - "
                            "TypeError: SecureMeshServer.__init__() got bad arg'); "
                            "raise SystemExit(1)\""
                        )
                    },
                    "timeout_seconds": 5,
                }
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续修复"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        }
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertIn("Repair Card:", system_text)
        self.assertIn("test_duplicate", system_text)
        self.assertIn("SecureMeshServer.__init__", system_text)

    def test_chat_completions_payload_allows_repair_writer_after_failed_complete_plan(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 1,
                        "last_exit_code": 1,
                        "results": [
                            {
                                "status": "needs_fix",
                                "hexagram": "001",
                                "next_hexagram": "101",
                                "exit_code": 1,
                                "failure_summary": "FAILED tests/test_mesh.py::test_encrypt",
                            }
                        ],
                        "repair_card": "Build Mode Repair Card\nFAILED tests/test_mesh.py::test_encrypt",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续实现 secure-rpc-mesh"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        system_text = "\n".join(
            str(message.get("content") or "")
            for message in result["payload"]["messages"]
            if message.get("role") == "system"
        )
        self.assertEqual([tool["function"]["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tool_choice"]["function"]["name"], "write_file")
        self.assertEqual(
            result["payload"]["tools"][0]["function"]["parameters"]["properties"]["path"]["enum"],
            ["core/crypto.py"],
        )
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_repair_gate")
        self.assertEqual(result["metadata"]["build_mode_repair_gate"]["target_path"], "core/crypto.py")
        self.assertIn("Build Mode Repair Gate", system_text)
        self.assertIn("目标修复文件: core/crypto.py", system_text)
        self.assertIn("Repair Card:", system_text)

    def test_build_mode_state_is_isolated_by_session_id(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.chat_completion_response_payload(
                {
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
                                            "arguments": '{"path":"app/main.py","content":"VALUE = 1\\n"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "session_id": "session-a",
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            same_session = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "session_id": "session-a",
                    "messages": [{"role": "user", "content": "继续"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )
            other_session = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "session_id": "session-b",
                    "messages": [{"role": "user", "content": "做一个新模块"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        same_tool_names = [tool["function"]["name"] for tool in same_session["payload"]["tools"]]
        other_tool_names = [tool["function"]["name"] for tool in other_session["payload"]["tools"]]
        self.assertEqual(same_tool_names, ["run_pytest"])
        self.assertNotEqual(other_tool_names, ["run_pytest"])
        self.assertNotEqual(other_session["metadata"]["oneword_build_mode"].get("source"), "state_next_hexagram")
        self.assertIn("build-mode-state-session-a.json", same_session["metadata"]["build_mode_state_injection"]["state_path"])
        self.assertNotIn("build_mode_state_injection", other_session["metadata"])

    def test_build_mode_state_persistence_uses_atomic_replace(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir, patch.object(gateway_server.os, "replace") as replace:
            workspace = Path(tmpdir)
            gateway_server._persist_build_mode_state(
                str(workspace),
                [
                    {
                        "status": "updated",
                        "hexagram": "111",
                        "next_hexagram": "001",
                        "evidence": {"changed_files": ["app/main.py"]},
                    }
                ],
                {"session_id": "atomic-session"},
            )

            replace.assert_called_once()
            tmp_path = Path(replace.call_args.args[0])
            final_path = Path(replace.call_args.args[1])

        self.assertEqual(final_path.name, "build-mode-state-atomic-session.json")
        self.assertEqual(tmp_path.name, "build-mode-state-atomic-session.json.tmp")

    def test_build_mode_state_persistence_locks_state_file(self):
        from contextlib import contextmanager
        import agent_skill_dictionary.gateway_server as gateway_server

        locked_paths = []

        @contextmanager
        def fake_lock(path):
            locked_paths.append(Path(path))
            yield

        with TemporaryDirectory() as tmpdir, patch.object(
            gateway_server,
            "_build_mode_state_file_lock",
            side_effect=fake_lock,
        ):
            workspace = Path(tmpdir)
            gateway_server._persist_build_mode_state(
                str(workspace),
                [
                    {
                        "status": "updated",
                        "hexagram": "111",
                        "next_hexagram": "001",
                        "evidence": {"changed_files": ["app/main.py"]},
                    }
                ],
                {"session_id": "locked-session"},
            )

        self.assertEqual(len(locked_paths), 1)
        self.assertEqual(locked_paths[0].name, "build-mode-state-locked-session.json")

    def test_build_mode_state_persistence_leaves_lock_file_not_tmp_file(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            gateway_server._persist_build_mode_state(
                str(workspace),
                [
                    {
                        "status": "updated",
                        "hexagram": "111",
                        "next_hexagram": "001",
                        "evidence": {"changed_files": ["app/main.py"]},
                    }
                ],
                {"session_id": "lock-file-session"},
            )
            state_path = workspace / ".yizijue" / "build-mode-state-lock-file-session.json"

            self.assertTrue(state_path.exists())
            self.assertTrue((workspace / ".yizijue" / "build-mode-state-lock-file-session.json.lock").exists())
            self.assertFalse((workspace / ".yizijue" / "build-mode-state-lock-file-session.json.tmp").exists())

    def test_chat_response_build_mode_dangerous_tool_call_returns_soft_feedback(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            response_payload = {
                "id": "chatcmpl_build_tool_block",
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
                                        "name": "bash",
                                        "arguments": '{"command":"rm -rf /"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

            payload, status_code = gateway_server.chat_completion_response_payload(
                response_payload,
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": tmpdir,
                    "oneword_build_mode": {"hexagram": "111"},
                },
                dictionary,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
            self.assertNotIn("tool_calls", payload["choices"][0]["message"])
            results = payload["yizijue_gateway"]["build_mode_tool_results"]
            self.assertEqual(results[0]["status"], "blocked")
            self.assertEqual(results[0]["hexagram"], "100")
            self.assertEqual(results[0]["next_hexagram"], "110")
            self.assertEqual(results[0]["evidence"]["exit_code"], 126)
            self.assertEqual(results[0]["feedback"]["feedback"]["next_hexagram"], "101")

    def test_build_mode_state_counts_verify_failures_and_resets_on_success(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            fail_payload = {
                "id": "chatcmpl_verify_fail",
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
                                        "name": "run_pytest",
                                        "arguments": '{"command":"python3 -c \\"import sys; sys.exit(1)\\""}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
            success_payload = {
                "id": "chatcmpl_verify_success",
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
                                        "name": "run_pytest",
                                        "arguments": '{"command":"python3 -c \\"print(1)\\""}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

            gateway_server.chat_completion_response_payload(
                fail_payload,
                {
                    "active_code": "测",
                    "root_opcode": "测",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "001"},
                },
                dictionary,
            )
            gateway_server.chat_completion_response_payload(
                fail_payload,
                {
                    "active_code": "测",
                    "root_opcode": "测",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "001"},
                },
                dictionary,
            )

            state_path = workspace / ".yizijue" / "build-mode-state.json"
            failed_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(failed_state["consecutive_failures"], 2)
            self.assertEqual(failed_state["last_exit_code"], 1)
            self.assertEqual(failed_state["results"][0]["next_hexagram"], "101")
            self.assertEqual(
                gateway_server._build_mode_state_next_hexagram_for_metadata({"workspace": str(workspace)}),
                "101",
            )

            gateway_server.chat_completion_response_payload(
                success_payload,
                {
                    "active_code": "测",
                    "root_opcode": "测",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "001"},
                },
                dictionary,
            )

            passed_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(passed_state["consecutive_failures"], 0)
            self.assertEqual(passed_state["last_exit_code"], 0)

    def test_chat_completions_payload_halts_after_two_build_mode_failures(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            state_dir = workspace / ".yizijue"
            state_dir.mkdir(parents=True)
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 2,
                        "last_exit_code": 1,
                        "results": [{"status": "needs_fix", "next_hexagram": "110"}],
                        "repo_card": "[State]: 101-INSPECT | [Target]: *",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "继续"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "write_file", "parameters": {"type": "object"}},
                        },
                        {
                            "type": "function",
                            "function": {"name": "run_pytest", "parameters": {"type": "object"}},
                        },
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["payload"]["tools"], [])
        self.assertTrue(result["metadata"]["oneword_build_mode"]["failure_gate_locked"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(result["metadata"]["build_mode_equilibrium"]["shadow_action"], "expert_handoff")
        self.assertIn("repo_card", result["metadata"]["build_mode_expert_handoff"])
        self.assertIn("Failure Gate", result["payload"]["messages"][0]["content"])

    def test_readiness_payload_reports_safe_configuration_status(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as workspace_root:
            payload = gateway_server.readiness_payload(
                dictionary={"entries": [{"code": "查"}]},
                workspace_root=workspace_root,
                gateway_token="gateway-token",
                upstream_api_key="upstream-key",
            )

        self.assertTrue(payload["ready"])
        self.assertTrue(payload["checks"]["dictionary_loaded"])
        self.assertTrue(payload["checks"]["workspace_root_configured"])
        self.assertTrue(payload["checks"]["gateway_token_configured"])
        self.assertTrue(payload["checks"]["upstream_api_key_configured"])
        self.assertNotIn("gateway-token", str(payload))
        self.assertNotIn("upstream-key", str(payload))

    def test_readiness_payload_allows_control_plane_without_upstream_key(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as workspace_root:
            payload = gateway_server.readiness_payload(
                dictionary={"entries": [{"code": "查"}]},
                workspace_root=workspace_root,
                gateway_token="gateway-token",
                upstream_api_key="",
            )

        self.assertTrue(payload["ready"])
        self.assertTrue(payload["control_plane_ready"])
        self.assertFalse(payload["chat_proxy_ready"])
        self.assertFalse(payload["checks"]["upstream_api_key_configured"])

    def test_readiness_payload_reports_anthropic_proxy_state(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as workspace_root:
            payload = gateway_server.readiness_payload(
                dictionary={"entries": [{"code": "查"}]},
                workspace_root=workspace_root,
                gateway_token="gateway-token",
                upstream_api_key="openai-key",
                anthropic_api_key="anthropic-key",
            )

        self.assertTrue(payload["anthropic_proxy_ready"])
        self.assertTrue(payload["checks"]["anthropic_api_key_configured"])
        self.assertNotIn("anthropic-key", str(payload))

    def test_readiness_payload_reports_docker_verification_policy(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as workspace_root, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_REQUIRE_DOCKER_FOR_VERIFY": "1"},
            clear=False,
        ), patch("agent_skill_dictionary.gateway_server.shutil.which", return_value=None):
            payload = gateway_server.readiness_payload(
                dictionary={"entries": [{"code": "查"}]},
                workspace_root=workspace_root,
                gateway_token="gateway-token",
                upstream_api_key="",
            )

        self.assertTrue(payload["checks"]["docker_required_for_verify"])
        self.assertFalse(payload["checks"]["docker_available"])
        self.assertFalse(payload["verify_sandbox_ready"])

    def test_readiness_payload_reports_guard_scanner_policy(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as workspace_root, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_REQUIRE_GUARD_SCANNER": "1",
                "ONEWORD_GUARD_SCANNER_TYPE": "semgrep,osv-scanner",
            },
            clear=False,
        ), patch(
            "agent_skill_dictionary.gateway_server.shutil.which",
            side_effect=lambda name: "/usr/bin/semgrep" if name == "semgrep" else None,
        ):
            payload = gateway_server.readiness_payload(
                dictionary={"entries": [{"code": "查"}]},
                workspace_root=workspace_root,
                gateway_token="gateway-token",
                upstream_api_key="",
            )

        self.assertTrue(payload["checks"]["guard_scanner_required"])
        self.assertTrue(payload["checks"]["semgrep_available"])
        self.assertFalse(payload["checks"]["osv_scanner_available"])
        self.assertFalse(payload["guard_sandbox_ready"])

    def test_streaming_chunk_inspector_soft_rewrites_tool_call_chunk(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
            {"active_code": "查", "root_opcode": "查"},
            [
                b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n',
                b'data: {"choices":[{"delta":{"tool_calls":[{"function":{"name":"write_file"}}]}}]}\n\n',
            ],
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertIn("Kernel Notice", payload["choices"][0]["delta"]["content"])

    def test_streaming_chunk_inspector_allows_clean_chunks(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
            {"active_code": "查", "root_opcode": "查"},
            [b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'],
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["stream_guard"]["allowed"], True)

    def test_streaming_chunk_inspector_bypasses_zero_tool_fast_path(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
            {"active_code": "解", "root_opcode": "查", "zero_tool_fast_path": True},
            [b'data: {"choices":[{"delta":{"tool_calls":[{"function":{"name":"write_file"}}]}}]}\n\n'],
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["stream_guard"]["allowed"], True)
        self.assertEqual(payload["stream_guard"]["inspected_chunks"], 0)
        self.assertEqual(payload["stream_guard"]["mode"], "bypassed_zero_tool")

    def test_streaming_chunk_inspector_executes_build_mode_tool_call_chunk(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                [
                    b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_1","type":"function","function":{"name":"write_file","arguments":"{\\"path\\":\\"app/main.py\\",\\"content\\":\\"VALUE = 4\\\\n\\"}"}}]}}]}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
            self.assertIn("Build Mode Evidence", payload["choices"][0]["delta"]["content"])
            self.assertEqual(
                payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"],
                "001",
            )

    def test_stream_build_mode_execution_payload_is_sse_rewrite(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        payload = {
            "choices": [{"delta": {"content": "Build Mode Evidence:"}}],
            "yizijue_gateway": {"response_mode": "build_mode_tool_execution"},
        }

        self.assertTrue(gateway_server._is_stream_gateway_rewrite(payload))
        self.assertIn(
            "Build Mode Evidence",
            gateway_server._openai_stream_notice_chunk(payload).decode("utf-8"),
        )
        self.assertIn(
            "Build Mode Evidence",
            gateway_server._anthropic_stream_notice_chunk(payload).decode("utf-8"),
        )
        self.assertTrue(
            gateway_server._is_stream_gateway_rewrite(
                {
                    "choices": [{"delta": {"content": "Kernel Notice"}}],
                    "yizijue_gateway": {"blocked": True, "response_mode": "soft_rewrite"},
                }
            )
        )

    def test_streaming_build_mode_tool_call_without_workspace_soft_rewrites(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
            {
                "active_code": "造",
                "root_opcode": "造",
                "oneword_build_mode": {"hexagram": "111"},
            },
            [
                b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_1","type":"function","function":{"name":"write_file","arguments":"{\\"path\\":\\"app/main.py\\",\\"content\\":\\"VALUE = 4\\\\n\\"}"}}]}}]}\n\n',
            ],
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertIn("workspace", payload["choices"][0]["delta"]["content"])

    def test_streaming_chunk_inspector_executes_split_openai_tool_call_arguments(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                [
                    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"write_file","arguments":"{\\"path\\":"}}]}}]}\n\n',
                    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"app/main.py\\",\\"content\\":"}}]}}]}\n\n',
                    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"VALUE = 6\\\\n\\"}"}}]}}]}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual((workspace / "app" / "main.py").read_text(encoding="utf-8"), "VALUE = 6\n")
            self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
            self.assertEqual(
                payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"],
                "001",
            )

    def test_streaming_chunk_inspector_does_not_execute_incomplete_openai_tool_arguments(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                },
                [
                    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"write_file","arguments":"{\\"path\\":"}}]}}]}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["stream_guard"]["allowed"], True)
            self.assertFalse((workspace / "app" / "main.py").exists())
            self.assertFalse((workspace / ".yizijue" / "build-mode-state.json").exists())

    def test_streaming_chunk_inspector_executes_build_mode_anthropic_tool_use_chunk(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                [
                    b'event: content_block_start\ndata: {"type":"content_block_start","content_block":{"type":"tool_use","id":"toolu_1","name":"write_file","input":{"path":"app/main.py","content":"VALUE = 5\\n"}}}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
            self.assertIn("Build Mode Evidence", payload["choices"][0]["delta"]["content"])
            self.assertEqual(
                payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"],
                "001",
            )

    def test_streaming_chunk_inspector_executes_split_anthropic_tool_input_json(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                [
                    b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"toolu_1","name":"write_file","input":{}}}\n\n',
                    b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"path\\":"}}\n\n',
                    b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"\\"app/main.py\\",\\"content\\":"}}\n\n',
                    b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"\\"VALUE = 7\\\\n\\"}"}}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual((workspace / "app" / "main.py").read_text(encoding="utf-8"), "VALUE = 7\n")
            self.assertEqual(payload["yizijue_gateway"]["response_mode"], "build_mode_tool_execution")
            self.assertEqual(
                payload["yizijue_gateway"]["build_mode_tool_results"][0]["next_hexagram"],
                "001",
            )

    def test_streaming_chunk_inspector_does_not_execute_incomplete_anthropic_tool_input_json(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.inspect_stream_chunk_for_policy(
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                [
                    b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"toolu_1","name":"write_file","input":{}}}\n\n',
                    b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"path\\":"}}\n\n',
                ],
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["stream_guard"]["allowed"], True)
            self.assertFalse((workspace / "app" / "main.py").exists())
            self.assertFalse((workspace / ".yizijue" / "build-mode-state.json").exists())

    def test_anthropic_messages_payload_rewrites_tools_for_policy(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        result = gateway_server.anthropic_messages_payload(
            {
                "model": "claude-test",
                "messages": [{"role": "user", "content": "查：看看项目结构"}],
                "tools": [
                    {"name": "read_file", "input_schema": {"type": "object"}},
                    {"name": "write_file", "input_schema": {"type": "object"}},
                ],
            },
            dictionary=gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH),
        )

        self.assertEqual(result["metadata"]["root_opcode"], "查")
        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["read_file"])
        self.assertIn("一字诀网关已接管本次请求。", result["payload"]["system"])

    def test_anthropic_messages_response_payload_soft_rewrites_forbidden_tool_use(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        rewritten = gateway_server.anthropic_messages_payload(
            {
                "model": "claude-test",
                "messages": [{"role": "user", "content": "查：看看项目结构"}],
            },
            dictionary=dictionary,
        )

        payload, status_code = gateway_server.anthropic_messages_response_payload(
            {
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
            },
            rewritten["metadata"],
            dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["yizijue_gateway"]["blocked"])
        self.assertEqual(payload["yizijue_gateway"]["response_mode"], "soft_rewrite")
        self.assertEqual(payload["content"][0]["type"], "text")
        self.assertIn("Kernel Notice", payload["content"][0]["text"])
        self.assertNotIn("tool_use", str(payload["content"]))

    def test_anthropic_messages_response_payload_executes_build_mode_tool_use(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.anthropic_messages_response_payload(
                {
                    "id": "msg_build_tool",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "write_file",
                            "input": {"path": "app/main.py", "content": "VALUE = 3\n"},
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                dictionary,
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual(payload["stop_reason"], "end_turn")
            self.assertEqual(payload["content"][0]["type"], "text")
            self.assertIn("Build Mode Evidence", payload["content"][0]["text"])
            self.assertNotIn("tool_use", str(payload["content"]))
            results = payload["yizijue_gateway"]["build_mode_tool_results"]
            self.assertEqual(results[0]["status"], "ok")
            self.assertEqual(results[0]["next_hexagram"], "001")

    def test_anthropic_messages_payload_applies_build_mode_request_policy(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.anthropic_messages_payload(
                {
                    "model": "claude-test",
                    "messages": [{"role": "user", "content": "写一个 anthropic build 文件"}],
                    "tools": [
                        {"name": "write_file", "input_schema": {"type": "object"}},
                        {"name": "run_pytest", "input_schema": {"type": "object"}},
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["write_file"])

    def test_openai_responses_payload_rewrites_input_for_codex_fast_path(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        result = gateway_server.openai_responses_payload(
            {
                "model": "gpt-5.5",
                "input": "问：只回复 ok，用于测试 Codex Responses API。",
                "tools": [{"type": "function", "name": "shell"}],
                "max_output_tokens": 512,
            },
            dictionary=dictionary,
        )

        payload = result["payload"]
        metadata = result["metadata"]
        self.assertEqual(metadata["protocol"], "openai_responses")
        self.assertEqual(metadata["root_opcode"], "问")
        self.assertTrue(metadata["zero_tool_fast_path"])
        self.assertEqual(payload["tools"], [])
        self.assertEqual(payload["max_output_tokens"], gateway_server.ZERO_TOOL_MAX_TOKENS)
        self.assertIn("一字诀网关已接管本次请求。", payload["instructions"])

    def test_openai_responses_payload_injects_previous_build_mode_context(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.openai_responses_response_payload(
                {
                    "id": "resp_build_tool",
                    "object": "response",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "write_file",
                            "arguments": '{"path":"app/main.py","content":"VALUE = 2\\n"}',
                        }
                    ],
                    "output_text": "",
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "openai_responses",
                },
                dictionary,
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续修复",
                    "tools": [{"type": "function", "name": "write_file"}],
                },
                dictionary,
            )

        self.assertIn("Build Mode Context", result["payload"]["instructions"])
        self.assertIn("app/main.py", result["payload"]["instructions"])

    def test_openai_responses_payload_uses_previous_next_hexagram_for_tools(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.openai_responses_response_payload(
                {
                    "id": "resp_build_tool",
                    "object": "response",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "write_file",
                            "arguments": '{"path":"app/main.py","content":"VALUE = 2\\n"}',
                        }
                    ],
                    "output_text": "",
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "openai_responses",
                },
                dictionary,
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")

    def test_openai_responses_payload_uses_write_file_fallback_after_empty_patch_retry(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.openai_responses_response_payload(
                {
                    "id": "resp_empty_patch",
                    "object": "response",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "apply_patch",
                            "arguments": '{"patch":""}',
                        }
                    ],
                    "output_text": "",
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "openai_responses",
                },
                dictionary,
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续写文件",
                    "tools": [
                        {"type": "function", "name": "apply_patch", "parameters": {"type": "object"}},
                        {"type": "function", "name": "write_file", "parameters": {"type": "object"}},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tools"][0]["parameters"]["required"], ["path", "content"])
        self.assertEqual(
            [tool["function"]["name"] for tool in result["chat_payload"]["tools"]],
            ["write_file"],
        )
        self.assertEqual(result["metadata"]["oneword_build_mode"]["fallback_tools"], ["write_file"])

    def test_openai_responses_payload_injects_next_artifact_instruction_for_secure_rpc_mesh(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "实现 secure-rpc-mesh",
                    "tools": [{"type": "function", "name": "write_file", "parameters": {"type": "object"}}],
                },
                dictionary,
            )
            support_files_exist = (
                (Path(tmpdir) / "api" / "__init__.py").exists(),
                (Path(tmpdir) / "core" / "__init__.py").exists(),
                (Path(tmpdir) / "tests" / "__init__.py").exists(),
            )

        self.assertIn("Build Mode Artifact Plan", result["payload"]["instructions"])
        self.assertIn("目标文件: core/crypto.py", result["payload"]["instructions"])
        self.assertIn("本轮只写一个文件", result["payload"]["instructions"])
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "core/crypto.py")
        self.assertEqual(support_files_exist, (True, True, True))
        self.assertEqual(
            result["metadata"]["build_mode_artifact_plan"]["support_files"],
            ["api/__init__.py", "core/__init__.py", "tests/__init__.py"],
        )

    def test_openai_responses_payload_halts_cluster_state_sync_when_real_deps_required(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
                "ONEWORD_BUILD_MODE_REQUIRE_REAL_DEPS": "1",
                "ONEWORD_BUILD_MODE_PYTHON": str(Path(tmpdir) / "missing-python"),
            },
            clear=False,
        ):
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "实现 cluster-state-sync",
                    "tools": [{"type": "function", "name": "write_file", "parameters": {"type": "object"}}],
                },
                dictionary,
            )

        self.assertEqual(result["payload"]["tools"], [])
        self.assertEqual(result["chat_payload"]["tools"], [])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(
            result["metadata"]["oneword_build_mode"]["source"],
            "sovereignty_environment_gate",
        )
        self.assertIn("Missing Environment Gate", result["payload"]["instructions"])
        self.assertIn("sqlmodel", result["metadata"]["build_mode_sovereignty"]["environment_gate"]["missing_packages"])

    def test_openai_responses_payload_halts_cluster_state_sync_unplanned_shim(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            (workspace / "sqlmodel").mkdir()
            (workspace / "sqlmodel" / "__init__.py").write_text("fake\n", encoding="utf-8")

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 cluster-state-sync",
                    "tools": [{"type": "function", "name": "write_file", "parameters": {"type": "object"}}],
                },
                dictionary,
            )

        self.assertEqual(result["payload"]["tools"], [])
        self.assertEqual(result["chat_payload"]["tools"], [])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(
            result["metadata"]["oneword_build_mode"]["source"],
            "sovereignty_workspace_gate",
        )
        self.assertIn(
            "sqlmodel/__init__.py",
            result["metadata"]["build_mode_sovereignty"]["workspace_gate"]["unplanned_paths"],
        )
        self.assertIn("Workspace Sovereignty Gate", result["payload"]["instructions"])

    def test_openai_responses_payload_continues_artifact_plan_before_verify_state(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            (workspace / "core").mkdir()
            (workspace / "core" / "crypto.py").write_text("VALUE = 1\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 0,
                        "results": [{"status": "ok", "hexagram": "111", "next_hexagram": "001"}],
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual([tool["function"]["name"] for tool in result["chat_payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tool_choice"]["name"], "write_file")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_continuation_gate")
        self.assertEqual(result["metadata"]["build_mode_artifact_plan"]["next_path"], "api/server.py")
        self.assertIn("目标文件: api/server.py", result["payload"]["instructions"])


    def test_openai_responses_payload_enters_verify_gate_when_secure_rpc_mesh_artifacts_complete(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")
        self.assertTrue(result["metadata"]["build_mode_verify_gate"]["complete"])
        self.assertIn("Build Mode Verify Gate", result["payload"]["instructions"])
        self.assertIn("python3 -m unittest discover -s tests -v", result["payload"]["instructions"])

    def test_openai_responses_payload_enters_verify_gate_when_complete_after_state_override(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 0,
                        "results": [{"status": "ok", "hexagram": "111", "next_hexagram": "001"}],
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [{"type": "function", "name": "write_file"}],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual([tool["function"]["name"] for tool in result["chat_payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["name"], "run_pytest")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_verify_gate")

    def test_openai_responses_payload_verifies_after_successful_repair_write(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 1,
                        "last_exit_code": 1,
                        "results": [
                            {
                                "status": "ok",
                                "hexagram": "111",
                                "next_hexagram": "001",
                                "changed_files": ["core/crypto.py"],
                            }
                        ],
                        "repair_card": "Build Mode Repair Card\nFAILED tests/test_mesh.py::test_encrypt",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["name"], "run_pytest")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_verify_gate")

    def test_openai_responses_payload_allows_repair_writer_after_failed_complete_plan(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            state_dir = workspace / ".yizijue"
            state_dir.mkdir()
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 1,
                        "last_exit_code": 1,
                        "results": [
                            {
                                "status": "needs_fix",
                                "hexagram": "001",
                                "next_hexagram": "101",
                                "exit_code": 1,
                                "failure_summary": "FAILED tests/test_mesh.py::test_encrypt",
                            }
                        ],
                        "repair_card": "Build Mode Repair Card\nFAILED tests/test_mesh.py::test_encrypt",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual([tool["function"]["name"] for tool in result["chat_payload"]["tools"]], ["write_file"])
        self.assertEqual(result["payload"]["tool_choice"]["name"], "write_file")
        self.assertEqual(
            result["payload"]["tools"][0]["parameters"]["properties"]["path"]["enum"],
            ["core/crypto.py"],
        )
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual(result["metadata"]["oneword_build_mode"]["source"], "artifact_repair_gate")
        self.assertEqual(result["metadata"]["build_mode_repair_gate"]["target_path"], "core/crypto.py")
        self.assertIn("Build Mode Repair Gate", result["payload"]["instructions"])
        self.assertIn("目标修复文件: core/crypto.py", result["payload"]["instructions"])


    def test_openai_responses_verify_gate_injects_run_pytest_when_client_omits_it(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            for relative in ("core/crypto.py", "api/server.py", "tests/test_mesh.py", "README.md"):
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续实现 secure-rpc-mesh",
                    "tools": [{"type": "function", "name": "apply_patch"}],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["payload"]["tool_choice"]["name"], "run_pytest")
        self.assertEqual(result["payload"]["tools"][0]["parameters"]["required"], ["command"])

    def test_openai_responses_payload_halts_after_two_build_mode_failures(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            state_dir = Path(tmpdir) / ".yizijue"
            state_dir.mkdir(parents=True)
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 2,
                        "last_exit_code": 1,
                        "results": [{"status": "needs_fix", "next_hexagram": "110"}],
                        "repo_card": "[State]: 101-INSPECT | [Target]: *",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "继续",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["payload"]["tools"], [])
        self.assertTrue(result["metadata"]["oneword_build_mode"]["failure_gate_locked"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(result["metadata"]["build_mode_equilibrium"]["shadow_action"], "expert_handoff")
        self.assertIn("repo_card", result["metadata"]["build_mode_expert_handoff"])
        self.assertIn("Failure Gate", result["payload"]["instructions"])

    def test_anthropic_messages_payload_injects_previous_build_mode_context(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.anthropic_messages_response_payload(
                {
                    "id": "msg_build_tool",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "write_file",
                            "input": {"path": "app/main.py", "content": "VALUE = 3\n"},
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                dictionary,
            )

            result = gateway_server.anthropic_messages_payload(
                {
                    "model": "claude-test",
                    "messages": [{"role": "user", "content": "继续修复"}],
                    "tools": [{"name": "write_file", "input_schema": {"type": "object"}}],
                },
                dictionary,
            )

        self.assertIn("Build Mode Context", str(result["payload"]["system"]))
        self.assertIn("app/main.py", str(result["payload"]["system"]))

    def test_anthropic_messages_payload_uses_previous_next_hexagram_for_tools(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            workspace = Path(tmpdir)
            gateway_server.anthropic_messages_response_payload(
                {
                    "id": "msg_build_tool",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "write_file",
                            "input": {"path": "app/main.py", "content": "VALUE = 3\n"},
                        }
                    ],
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "anthropic_messages",
                },
                dictionary,
            )

            result = gateway_server.anthropic_messages_payload(
                {
                    "model": "claude-test",
                    "messages": [{"role": "user", "content": "继续"}],
                    "tools": [
                        {"name": "write_file", "input_schema": {"type": "object"}},
                        {"name": "run_pytest", "input_schema": {"type": "object"}},
                    ],
                },
                dictionary,
            )

        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["run_pytest"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "001")

    def test_anthropic_messages_payload_halts_after_two_build_mode_failures(self):
        import json
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            state_dir = Path(tmpdir) / ".yizijue"
            state_dir.mkdir(parents=True)
            (state_dir / "build-mode-state.json").write_text(
                json.dumps(
                    {
                        "status": "updated",
                        "consecutive_failures": 2,
                        "last_exit_code": 1,
                        "results": [{"status": "needs_fix", "next_hexagram": "110"}],
                        "repo_card": "[State]: 101-INSPECT | [Target]: *",
                    }
                ),
                encoding="utf-8",
            )

            result = gateway_server.anthropic_messages_payload(
                {
                    "model": "claude-test",
                    "messages": [{"role": "user", "content": "继续"}],
                    "tools": [
                        {"name": "write_file", "input_schema": {"type": "object"}},
                        {"name": "run_pytest", "input_schema": {"type": "object"}},
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["payload"]["tools"], [])
        self.assertTrue(result["metadata"]["oneword_build_mode"]["failure_gate_locked"])
        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "100")
        self.assertEqual(result["metadata"]["build_mode_equilibrium"]["shadow_action"], "expert_handoff")
        self.assertIn("repo_card", result["metadata"]["build_mode_expert_handoff"])
        self.assertIn("Failure Gate", str(result["payload"]["system"]))

    def test_chat_completions_payload_records_workspace_root_for_build_mode_execution(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_WORKSPACE_ROOT": tmpdir},
            clear=False,
        ):
            result = gateway_server.chat_completions_payload(
                {
                    "model": "gpt-test",
                    "messages": [{"role": "user", "content": "造：写一个 demo 项目"}],
                },
                dictionary,
            )

        self.assertEqual(result["metadata"]["workspace"], str(Path(tmpdir).resolve()))

    def test_openai_responses_payload_injects_native_context_for_inspect(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {"ONEWORD_WORKSPACE_ROOT": tmpdir},
            clear=False,
        ):
            Path(tmpdir, "README.md").write_text("# Demo\n", encoding="utf-8")
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-5.5",
                    "input": "查：请只读评估当前项目。",
                    "tools": [{"type": "function", "name": "shell"}],
                },
                dictionary=dictionary,
            )

        payload = result["payload"]
        metadata = result["metadata"]
        self.assertEqual(metadata["root_opcode"], "查")
        self.assertTrue(metadata["native_context_injection"]["applied"])
        self.assertIn("Native Inspect Context", payload["instructions"])
        self.assertIn("[State]: 101-INSPECT", payload["instructions"])
        self.assertEqual(payload["tools"], [])
        self.assertEqual(result["chat_payload"]["tools"], [])

    def test_openai_responses_response_payload_attaches_gateway_metadata(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        result = gateway_server.openai_responses_payload(
            {
                "model": "gpt-5.5",
                "input": "问：只回复 ok。",
            },
            dictionary=dictionary,
        )

        payload, status_code = gateway_server.openai_responses_response_payload(
            {
                "id": "resp_test",
                "object": "response",
                "output_text": "ok",
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            },
            result["metadata"],
            dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["output_text"], "ok")
        self.assertTrue(payload["yizijue_gateway"]["zero_tool_fast_path"])
        self.assertEqual(
            payload["yizijue_gateway"]["tool_guard"]["mode"],
            "bypassed_zero_tool",
        )

    def test_openai_responses_response_payload_executes_build_mode_function_call(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            payload, status_code = gateway_server.openai_responses_response_payload(
                {
                    "id": "resp_build_tool",
                    "object": "response",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "write_file",
                            "arguments": '{"path":"app/main.py","content":"VALUE = 2\\n"}',
                        }
                    ],
                    "output_text": "",
                },
                {
                    "active_code": "造",
                    "root_opcode": "造",
                    "workspace": str(workspace),
                    "oneword_build_mode": {"hexagram": "111"},
                    "protocol": "openai_responses",
                },
                dictionary,
            )

            self.assertEqual(status_code, 200)
            self.assertTrue((workspace / "app" / "main.py").exists())
            self.assertEqual(payload["output"][0]["type"], "message")
            self.assertIn("Build Mode Evidence", payload["output_text"])
            self.assertNotIn("function_call", str(payload["output"]))
            results = payload["yizijue_gateway"]["build_mode_tool_results"]
            self.assertEqual(results[0]["status"], "ok")
            self.assertEqual(results[0]["next_hexagram"], "001")

    def test_openai_responses_payload_applies_build_mode_request_policy(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "写一个 responses build 文件",
                    "tools": [
                        {"type": "function", "name": "write_file"},
                        {"type": "function", "name": "run_pytest"},
                    ],
                },
                dictionary,
            )

        self.assertEqual(result["metadata"]["oneword_build_mode"]["hexagram"], "111")
        self.assertEqual([tool["name"] for tool in result["payload"]["tools"]], ["write_file"])
        self.assertEqual(
            [tool["function"]["name"] for tool in result["chat_payload"]["tools"]],
            ["write_file"],
        )

    def test_openai_responses_build_mode_write_tool_requires_path_and_content(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "写一个小游戏项目",
                    "tools": [
                        {
                            "type": "function",
                            "name": "write_file",
                            "parameters": {"type": "object"},
                        }
                    ],
                },
                dictionary,
            )

        response_tool = result["payload"]["tools"][0]
        chat_tool = result["chat_payload"]["tools"][0]["function"]
        self.assertEqual(response_tool["name"], "write_file")
        self.assertEqual(response_tool["parameters"]["required"], ["path", "content"])
        self.assertEqual(chat_tool["parameters"]["required"], ["path", "content"])

    def test_openai_responses_build_mode_apply_patch_tool_requires_patch(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        with TemporaryDirectory() as tmpdir, patch.dict(
            gateway_server.os.environ,
            {
                "ONEWORD_WORKSPACE_ROOT": tmpdir,
                "ONEWORD_BUILD_MODE": "1",
            },
            clear=False,
        ):
            result = gateway_server.openai_responses_payload(
                {
                    "model": "gpt-test",
                    "input": "写一个小游戏项目",
                    "tools": [
                        {
                            "type": "function",
                            "name": "apply_patch",
                            "parameters": {"type": "object"},
                        }
                    ],
                },
                dictionary,
            )

        response_tool = result["payload"]["tools"][0]
        chat_tool = result["chat_payload"]["tools"][0]["function"]
        self.assertEqual(response_tool["name"], "apply_patch")
        self.assertEqual(response_tool["parameters"]["required"], ["patch"])
        self.assertEqual(chat_tool["parameters"]["required"], ["patch"])

    def test_openai_responses_chat_upstream_payload_round_trips_to_responses_shape(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        dictionary = gateway_server.load_dictionary(gateway_server.DICTIONARY_PATH)
        result = gateway_server.openai_responses_payload(
            {
                "model": "gpt-5.5",
                "input": "问：只回复 ok。",
                "max_output_tokens": 512,
            },
            dictionary=dictionary,
        )

        chat_payload = result["chat_payload"]
        self.assertEqual(chat_payload["model"], "gpt-5.5")
        self.assertEqual(chat_payload["max_tokens"], gateway_server.ZERO_TOOL_MAX_TOKENS)
        self.assertEqual(chat_payload["tools"], [])

        payload, status_code = gateway_server.openai_responses_response_payload(
            {
                "id": "chatcmpl_test",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            },
            result["metadata"],
            dictionary,
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["object"], "response")
        self.assertEqual(payload["output_text"], "ok")
        self.assertEqual(payload["usage"]["input_tokens"], 10)
        self.assertEqual(payload["usage"]["output_tokens"], 2)

    def test_openai_responses_stream_chunks_end_with_completed_event(self):
        import agent_skill_dictionary.gateway_server as gateway_server

        chunks = list(
            gateway_server.openai_responses_stream_chunks(
                {
                    "id": "resp_test",
                    "object": "response",
                    "status": "completed",
                    "output_text": "ok",
                }
            )
        )

        text = b"".join(chunks).decode("utf-8")
        self.assertIn("event: response.created", text)
        self.assertIn("event: response.output_item.added", text)
        self.assertIn("event: response.content_part.added", text)
        self.assertIn("event: response.output_text.delta", text)
        self.assertIn("event: response.content_part.done", text)
        self.assertIn("event: response.output_item.done", text)
        self.assertIn("event: response.completed", text)
        self.assertTrue(text.endswith("data: [DONE]\n\n"))


if __name__ == "__main__":
    unittest.main()
