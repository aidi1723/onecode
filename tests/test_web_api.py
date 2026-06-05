import json
import os
import socket
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@contextmanager
def local_test_server(handler_cls):
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    except PermissionError as exc:
        raise unittest.SkipTest(f"local socket bind unavailable: {exc}") from exc
    except OSError as exc:
        if exc.errno in {getattr(socket, "EACCES", 13), getattr(socket, "EPERM", 1)}:
            raise unittest.SkipTest(f"local socket bind unavailable: {exc}") from exc
        raise
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class OneCodeWebApiTests(unittest.TestCase):
    def test_models_payload_exposes_onecode_agent(self):
        from onecode.web.api import build_models_payload

        payload = build_models_payload()

        self.assertEqual(payload["object"], "list")
        self.assertEqual(payload["data"][0]["id"], "onecode-agent")

    def test_onecode_shell_schema_endpoint_returns_projection_contract(self):
        from onecode.web.api import handle_onecode_shell_schema

        payload, status = handle_onecode_shell_schema()

        self.assertEqual(status, 200)
        self.assertEqual(payload["name"], "onecode.shell_projection")
        self.assertEqual(payload["version"], 1)
        self.assertIn("compact_message", payload["fields"])
        self.assertEqual(payload["nested_fields"]["evidence_ref"][0], "mode")

    def test_bearer_auth_rejects_missing_token_when_configured(self):
        from onecode.web.api import request_authorized

        self.assertFalse(request_authorized({}, "secret-token"))

    def test_bearer_auth_rejects_missing_token_by_default(self):
        from onecode.web.api import request_authorized

        self.assertFalse(request_authorized({}, None))

    def test_bearer_auth_allows_explicit_unauthenticated_loopback(self):
        from onecode.web.api import request_authorized

        self.assertTrue(request_authorized({}, None, allow_unauthenticated=True, host="127.0.0.1"))

    def test_bearer_auth_rejects_explicit_unauthenticated_non_loopback(self):
        from onecode.web.api import request_authorized

        self.assertFalse(request_authorized({}, None, allow_unauthenticated=True, host="0.0.0.0"))

    def test_bearer_auth_accepts_matching_token(self):
        from onecode.web.api import request_authorized

        self.assertTrue(request_authorized({"authorization": "Bearer secret-token"}, "secret-token"))

    def test_bearer_auth_uses_constant_time_compare(self):
        from onecode.web.api import request_authorized

        with patch("onecode.web.api.secrets.compare_digest", return_value=True) as compare_digest:
            authorized = request_authorized({"authorization": "Bearer secret-token"}, "secret-token")

        self.assertTrue(authorized)
        compare_digest.assert_called_once_with("Bearer secret-token", "Bearer secret-token")

    def test_latest_user_message_extracts_last_user_content(self):
        from onecode.web.api import latest_user_message

        self.assertEqual(
            latest_user_message(
                [
                    {"role": "user", "content": "first"},
                    {"role": "assistant", "content": "reply"},
                    {"role": "user", "content": [{"type": "text", "text": "second"}]},
                ]
            ),
            "second",
        )

    def test_math_capability_question_is_classified_as_chat(self):
        from onecode.web.api import should_run_onecode_task

        self.assertFalse(should_run_onecode_task("你会执行数学任务吗？能够用数学公式把八卦的规则写出来吗"))

    def test_chat_completion_falls_back_to_rule_run_without_model_key(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_HOME": str(Path(tmp) / "home"),
            },
            clear=True,
        ):
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "查：看看项目"}],
                }
            )
            result = payload["onecode"]["result"]
            summary = payload["onecode"]["summary"]
            wal_exists = Path(result["wal_path"]).exists()

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["object"], "chat.completion")
        self.assertEqual(payload["choices"][0]["message"]["role"], "assistant")
        self.assertIn("OneCode run", payload["choices"][0]["message"]["content"])
        self.assertEqual(payload["onecode"]["mode"], "rule_fallback")
        self.assertEqual(summary["run_id"], result["run_id"])
        self.assertEqual(summary["severity"], "ok")
        self.assertEqual(summary["evidence_ref"]["mode"], "wal")
        self.assertEqual(summary["rule_state"]["status_code"], result["iching_status_code"])
        self.assertEqual(result["evidence_mode"], "wal")
        self.assertIsNone(result["ledger_path"])
        self.assertTrue(wal_exists)

    def test_error_payload_uses_openai_style_error(self):
        from onecode.web.api import error_payload

        payload = error_payload("invalid_request", "bad request")

        self.assertEqual(payload["error"]["type"], "invalid_request")
        self.assertEqual(payload["error"]["message"], "bad request")

    def test_chat_completion_rejects_missing_user_message(self):
        from onecode.web.api import handle_chat_completion

        payload, status_code = handle_chat_completion({"model": "onecode-agent", "messages": []})

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"]["type"], "invalid_request")

    def test_chat_completion_returns_json_error_when_model_provider_fails(self):
        from onecode.kernel.model_provider import ModelProviderError
        from onecode.web.api import handle_chat_completion

        with patch("onecode.web.api.run_model_task", side_effect=ModelProviderError("model request failed: Unauthorized")):
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "造：demo"}],
                }
            )

        self.assertEqual(status_code, 502)
        self.assertEqual(payload["error"]["type"], "model_provider_error")
        self.assertIn("Unauthorized", payload["error"]["message"])

    def test_chat_completion_handles_empty_model_plan_as_visible_reply(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_HOME": str(Path(tmp) / "home"),
                "ONECODE_MODEL_PROVIDER": "chat",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ), patch("onecode.web.api.run_model_task", side_effect=ValueError("plan must include at least one asset")):
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "你好"}],
                }
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["onecode"]["mode"], "chat_fallback")
        self.assertEqual(payload["onecode"]["result"]["status"], "completed")
        self.assertIn("没有生成文件变更", payload["choices"][0]["message"]["content"])

    def test_general_math_question_uses_direct_chat_answer_not_run_summary(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model, patch(
            "onecode.web.api.direct_chat_completion",
            return_value="可以。八卦可用三位二进制向量表示，例如乾=(1,1,1)，坤=(0,0,0)。",
        ) as direct_chat:
            run_model.return_value = {
                "run_id": "model-run",
                "status": "completed",
                "ledger_path": str(Path(tmp) / "ledger.json"),
            }
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "你会执行数学任务吗？能够用数学公式把八卦的规则写出来吗"}],
                }
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["onecode"]["mode"], "chat")
        self.assertEqual(payload["choices"][0]["message"]["content"], "可以。八卦可用三位二进制向量表示，例如乾=(1,1,1)，坤=(0,0,0)。")
        self.assertEqual(direct_chat.call_count, 1)
        self.assertEqual(run_model.call_count, 0)

    def test_onecode_agent_alias_uses_configured_openai_model(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_MODEL": "gpt-5.5",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model:
            run_model.return_value = {
                "run_id": "model-run",
                "status": "completed",
                "ledger_path": str(Path(tmp) / "ledger.json"),
            }
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "造：demo"}],
                }
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["onecode"]["mode"], "model")
        self.assertEqual(run_model.call_args.kwargs["model"], "gpt-5.5")

    def test_chat_completion_uses_metadata_workspace_for_onecode_runs(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as default_tmp, tempfile.TemporaryDirectory() as selected_tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": default_tmp,
                "ONECODE_ALLOWED_WORKSPACE_ROOTS": os.pathsep.join([default_tmp, selected_tmp]),
                "ONECODE_MODEL_PROVIDER": "chat",
                "OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model:
            run_model.return_value = {
                "run_id": "selected-workspace-run",
                "status": "completed",
                "ledger_path": str(Path(selected_tmp) / ".onecode" / "runs" / "selected-workspace-run" / "ledger.json"),
            }
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "查：看看项目"}],
                    "metadata": {"workspace": selected_tmp},
                }
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["onecode"]["mode"], "model")
        self.assertEqual(run_model.call_args.kwargs["workspace"], Path(selected_tmp).resolve())

    def test_workspace_from_request_rejects_workspace_outside_allowed_roots(self):
        from onecode.web.api import workspace_from_request

        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": allowed,
                "ONECODE_ALLOWED_WORKSPACE_ROOTS": allowed,
            },
            clear=True,
        ):
            with self.assertRaises(ValueError) as raised:
                workspace_from_request({"metadata": {"workspace": outside}})

        self.assertIn("outside allowed workspace roots", str(raised.exception))

    def test_workspace_from_request_accepts_workspace_inside_allowed_root(self):
        from onecode.web.api import workspace_from_request

        with tempfile.TemporaryDirectory() as allowed:
            child = Path(allowed) / "child"
            child.mkdir()
            with patch.dict(
                "os.environ",
                {
                    "ONECODE_WORKSPACE_ROOT": allowed,
                    "ONECODE_ALLOWED_WORKSPACE_ROOTS": allowed,
                },
                clear=True,
            ):
                workspace = workspace_from_request({"metadata": {"workspace": str(child)}})

        self.assertEqual(workspace, child.resolve())

    def test_project_status_reports_git_and_verifier_policy(self):
        from onecode.web.api import handle_onecode_project_status

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            workspace = Path(tmp)
            (workspace / ".git").mkdir()
            (workspace / ".onecode").mkdir()
            (workspace / ".onecode" / "verifier-policy.json").write_text(
                json.dumps({"verifiers": []}),
                encoding="utf-8",
            )

            payload, status = handle_onecode_project_status({"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertTrue(payload["allowed"])
        self.assertTrue(payload["exists"])
        self.assertTrue(payload["git"]["present"])
        self.assertTrue(payload["verifier_policy"]["present"])

    def test_project_status_includes_context_and_config_summaries_without_raw_rule_content(self):
        from onecode.web.api import project_status_payload

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("private instruction body\n", encoding="utf-8")
            payload = project_status_payload(workspace)

        self.assertIn("project_context", payload)
        self.assertIn("runtime_config", payload)
        self.assertEqual(payload["project_context"]["summary"]["element"], "wood")
        self.assertEqual(payload["runtime_config"]["summary"]["element"], "earth")
        self.assertNotIn("private instruction body", json.dumps(payload["project_context"]))
        self.assertIn("content_sha256", payload["project_context"]["memory_files"][0])

    def test_project_status_projects_latest_run_for_shell_consumers(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_project_status

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="status-latest", write_path="seed.txt", write_content="ok\n")
            payload, status = handle_onecode_project_status({"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertEqual(payload["latest_run"]["run_id"], "status-latest")
        self.assertEqual(payload["latest_run"]["shell_projection"]["run_id"], "status-latest")
        self.assertEqual(payload["latest_run"]["shell_projection"]["severity"], "ok")

    def test_project_init_creates_git_and_default_verifier_policy(self):
        from onecode.web.api import handle_onecode_project_init

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            workspace = Path(tmp) / "demo"
            workspace.mkdir()

            payload, status = handle_onecode_project_init(
                {"workspace": str(workspace), "git": True, "verifierPolicy": True}
            )
            git_exists = (workspace / ".git").exists()
            verifier_policy_exists = (workspace / ".onecode" / "verifier-policy.json").exists()

        self.assertEqual(status, 200)
        self.assertEqual(payload["workspace"], str(workspace.resolve()))
        self.assertTrue(git_exists)
        self.assertTrue(verifier_policy_exists)
        self.assertTrue(payload["git"]["present"])
        self.assertTrue(payload["verifier_policy"]["present"])

    def test_onecode_runs_endpoint_lists_existing_run_summaries(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_runs_list

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="api-run", write_path="seed.txt", write_content="ok\n")
            payload, status = handle_onecode_runs_list({"workspace": tmp, "limit": "10"})

        self.assertEqual(status, 200)
        self.assertEqual(payload["runs"][0]["run_id"], "api-run")
        self.assertIn("ledger_path", payload["runs"][0])
        self.assertEqual(payload["runs"][0]["shell_projection"]["severity"], "ok")
        self.assertEqual(payload["runs"][0]["shell_projection"]["evidence_ref"]["mode"], "full")

    def test_onecode_inspect_endpoint_returns_cli_inspect_summary_with_shell_projection(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_inspect

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="inspect-api", write_path="seed.txt", write_content="ok\n")
            payload, status = handle_onecode_run_inspect("inspect-api", {"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertEqual(payload["run_id"], "inspect-api")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["delivery_status"], "deliverable")
        self.assertEqual(payload["shell_projection"]["run_id"], "inspect-api")
        self.assertEqual(payload["shell_projection"]["delivery_state"]["status"], "deliverable")
        self.assertEqual(payload["shell_projection"]["rule_state"]["status_code"], payload["iching_status_code"])

    def test_onecode_resume_endpoint_runs_model_with_resume_from_run_id(self):
        from onecode.web.api import handle_onecode_run_resume

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model:
            run_model.return_value = {"run_id": "resumed-api", "status": "completed"}
            payload, status = handle_onecode_run_resume(
                "source-api",
                {"workspace": tmp, "message": "继续完成"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["run_id"], "resumed-api")
        self.assertEqual(run_model.call_args.kwargs["resume_from_run_id"], "source-api")
        self.assertEqual(run_model.call_args.kwargs["workspace"], Path(tmp).resolve())

    def test_onecode_resume_endpoint_projects_result_for_shell_consumers(self):
        from onecode.web.api import handle_onecode_run_resume

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ), patch("onecode.web.api.run_model_task") as run_model:
            run_model.return_value = {
                "run_id": "resumed-api",
                "status": "completed",
                "iching_status_code": 63,
                "iching_transition_action": "complete",
            }
            payload, status = handle_onecode_run_resume(
                "source-api",
                {"workspace": tmp, "message": "继续完成"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["shell_projection"]["run_id"], "resumed-api")
        self.assertEqual(payload["shell_projection"]["severity"], "ok")
        self.assertEqual(payload["shell_projection"]["rule_state"]["status_code"], 63)

    def test_onecode_verifier_presets_endpoint_returns_presets(self):
        from onecode.web.api import handle_onecode_verifier_presets

        payload, status = handle_onecode_verifier_presets()

        self.assertEqual(status, 200)
        self.assertIn("presets", payload)
        self.assertGreaterEqual(len(payload["presets"]), 1)

    def test_onecode_verifier_policy_reports_missing_policy(self):
        from onecode.web.api import handle_onecode_verifier_policy_get

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            payload, status = handle_onecode_verifier_policy_get({"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertFalse(payload["exists"])
        self.assertFalse(payload["valid"])

    def test_onecode_verifier_policy_writes_and_reads_policy(self):
        from onecode.web.api import handle_onecode_verifier_policy_get, handle_onecode_verifier_policy_write

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            write_payload, write_status = handle_onecode_verifier_policy_write(
                {"workspace": tmp, "presetIds": ["python-unittest"], "force": False}
            )
            read_payload, read_status = handle_onecode_verifier_policy_get({"workspace": tmp})

        self.assertEqual(write_status, 200)
        self.assertEqual(read_status, 200)
        self.assertTrue(write_payload["exists"])
        self.assertTrue(read_payload["valid"])
        self.assertEqual(read_payload["policy"]["verifiers"][0]["id"], "python-unittest")

    def test_onecode_verifier_policy_rejects_overwrite_without_force(self):
        from onecode.web.api import handle_onecode_verifier_policy_write

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            handle_onecode_verifier_policy_write({"workspace": tmp, "presetIds": ["python-unittest"]})
            payload, status = handle_onecode_verifier_policy_write(
                {"workspace": tmp, "presetIds": ["python-unittest"], "force": False}
            )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["type"], "invalid_verifier_policy")

    def test_onecode_model_config_write_and_get_masks_api_key(self):
        from onecode.web.api import handle_onecode_model_config_get, handle_onecode_model_config_write

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            write_payload, write_status = handle_onecode_model_config_write(
                {
                    "endpoint": "http://127.0.0.1:6780/v1",
                    "apiKey": "sk-test-secret",
                    "model": "gpt-5.5",
                }
            )
            read_payload, read_status = handle_onecode_model_config_get()

        self.assertEqual(write_status, 200)
        self.assertEqual(read_status, 200)
        self.assertTrue(write_payload["configured"])
        self.assertEqual(read_payload["endpoint"], "http://127.0.0.1:6780/v1")
        self.assertEqual(read_payload["model"], "gpt-5.5")
        self.assertTrue(read_payload["api_key_configured"])
        self.assertNotIn("api_key", read_payload)

    def test_onecode_model_discover_returns_models_and_can_save_config(self):
        from onecode.web.api import handle_onecode_models_discover

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True), patch(
            "onecode.web.api.discover_models",
            return_value={"source": "remote", "models": ["gpt-5.5", "gpt-4.1"]},
        ):
            payload, status = handle_onecode_models_discover(
                {
                    "endpoint": "http://127.0.0.1:6780/v1",
                    "apiKey": "sk-test-secret",
                    "model": "gpt-4.1",
                    "save": True,
                }
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["models"], ["gpt-5.5", "gpt-4.1"])
        self.assertEqual(payload["selected_model"], "gpt-4.1")
        self.assertTrue(payload["config"]["configured"])

    def test_onecode_model_config_write_can_preserve_existing_secret(self):
        from onecode.web.api import handle_onecode_model_config_write
        from onecode.kernel.model_config import read_model_config

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"ONECODE_HOME": tmp}, clear=True):
            handle_onecode_model_config_write(
                {
                    "endpoint": "http://127.0.0.1:6780/v1",
                    "apiKey": "sk-test-secret",
                    "model": "gpt-5.5",
                }
            )
            payload, status = handle_onecode_model_config_write(
                {
                    "endpoint": "http://127.0.0.1:6780/v1/chat/completions",
                    "apiKey": "",
                    "model": "gpt-4.1",
                }
            )
            read_back = read_model_config(include_secret=True)

        self.assertEqual(status, 200)
        self.assertTrue(payload["configured"])
        self.assertEqual(read_back["api_key"], "sk-test-secret")
        self.assertEqual(read_back["model"], "gpt-4.1")

    def test_onecode_doctor_endpoint_returns_doctor_result(self):
        from onecode.web.api import handle_onecode_doctor

        with patch("onecode.web.api.run_doctor", return_value={"status": "ok", "checks": []}) as doctor:
            payload, status = handle_onecode_doctor()

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(doctor.call_count, 1)

    def test_onecode_audit_self_endpoint_returns_audit_result(self):
        from onecode.web.api import handle_onecode_audit_self

        with patch("onecode.web.api.audit_self", return_value={"status": "ok", "checks": []}) as audit:
            payload, status = handle_onecode_audit_self()

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(audit.call_count, 1)

    def test_onecode_run_evidence_returns_raw_ledger_manifest_and_checkpoints(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_evidence

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task("seed", workspace=Path(tmp), run_id="evidence-api", write_path="seed.txt", write_content="ok\n")
            payload, status = handle_onecode_run_evidence("evidence-api", {"workspace": tmp})

        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["run_id"], "evidence-api")
        self.assertEqual(payload["summary"]["shell_projection"]["run_id"], "evidence-api")
        self.assertEqual(payload["summary"]["shell_projection"]["evidence_ref"]["mode"], "full")
        self.assertEqual(payload["ledger"]["run_id"], "evidence-api")
        self.assertEqual(payload["manifest"]["run_id"], "evidence-api")
        self.assertEqual(len(payload["checkpoints"]), 1)
        self.assertIn("document", payload["checkpoints"][0])

    def test_onecode_run_evidence_returns_wal_summary_for_wal_only_run(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_evidence

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"ONECODE_WORKSPACE_ROOT": tmp, "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp},
            clear=True,
        ):
            run_task(
                "wal evidence",
                workspace=Path(tmp),
                run_id="evidence-wal-api",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )
            payload, status = handle_onecode_run_evidence("evidence-wal-api", {"workspace": tmp})
            wal_exists = Path(payload["wal_path"]).exists()

        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["run_id"], "evidence-wal-api")
        self.assertEqual(payload["summary"]["evidence_mode"], "wal")
        self.assertEqual(payload["summary"]["shell_projection"]["evidence_ref"]["mode"], "wal")
        self.assertIsNone(payload["ledger"])
        self.assertEqual(payload["ledger_error"], "wal_only")
        self.assertIsNone(payload["manifest"])
        self.assertEqual(payload["manifest_error"], "wal_only")
        self.assertEqual(payload["checkpoints"], [])
        self.assertTrue(wal_exists)

    def test_onecode_run_evidence_returns_rotated_wal_segment_path(self):
        from onecode.kernel.runner import run_task
        from onecode.web.api import handle_onecode_run_evidence

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp,
                "ONECODE_WAL_ROTATE_BYTES": "1",
            },
            clear=True,
        ):
            run_task(
                "old wal evidence",
                workspace=Path(tmp),
                run_id="evidence-wal-old-api",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )
            run_task(
                "new wal evidence",
                workspace=Path(tmp),
                run_id="evidence-wal-new-api",
                completed_evidence_mode="wal",
                evidence_durability="relaxed",
            )
            payload, status = handle_onecode_run_evidence("evidence-wal-old-api", {"workspace": tmp})
            archive_path = Path(tmp) / ".onecode" / "global-ledger.1.jsonl"

        self.assertEqual(status, 200)
        self.assertEqual(payload["summary"]["run_id"], "evidence-wal-old-api")
        self.assertEqual(payload["wal_path"], str(archive_path.resolve()))

    def test_chat_completion_payload_is_json_serializable(self):
        from onecode.web.api import chat_completion_payload

        payload = chat_completion_payload(
            content="hello",
            model="onecode-agent",
            run_result={"status": "completed"},
            mode="rule_fallback",
        )

        json.dumps(payload)
        self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
        self.assertIn("summary", payload["onecode"])

    def test_streaming_chat_completion_returns_sse_chunks(self):
        from onecode.web.api import OneCodeRequestHandler

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_API_TOKEN": "test-token",
                "ONECODE_HOME": str(Path(tmp) / "home"),
            },
            clear=True,
        ):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                chat_body = json.dumps(
                    {
                        "model": "onecode-agent",
                        "messages": [{"role": "user", "content": "查：stream smoke"}],
                        "stream": True,
                    }
                ).encode("utf-8")
                chat_request = Request(
                    f"{base_url}/v1/chat/completions",
                    data=chat_body,
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(chat_request, timeout=5) as response:
                    content_type = response.headers.get("content-type")
                    text = response.read().decode("utf-8")

        self.assertEqual(content_type, "text/event-stream; charset=utf-8")
        self.assertIn("data: ", text)
        self.assertIn('"delta"', text)
        self.assertTrue(text.rstrip().endswith("data: [DONE]"))

    def test_http_server_serves_models_and_chat_completion(self):
        from onecode.web.api import OneCodeRequestHandler

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_API_TOKEN": "test-token",
                "ONECODE_HOME": str(Path(tmp) / "home"),
            },
            clear=True,
        ):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                models_request = Request(
                    f"{base_url}/v1/models",
                    headers={"Authorization": "Bearer test-token"},
                )
                with urlopen(models_request, timeout=5) as response:
                    models_payload = json.loads(response.read().decode("utf-8"))

                chat_body = json.dumps(
                    {
                        "model": "onecode-agent",
                        "messages": [{"role": "user", "content": "查：HTTP smoke"}],
                    }
                ).encode("utf-8")
                chat_request = Request(
                    f"{base_url}/v1/chat/completions",
                    data=chat_body,
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(chat_request, timeout=5) as response:
                    chat_payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(models_payload["data"][0]["id"], "onecode-agent")
        self.assertEqual(chat_payload["choices"][0]["message"]["role"], "assistant")
        self.assertEqual(chat_payload["onecode"]["mode"], "rule_fallback")

    def test_http_server_serves_shell_schema(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                request = Request(
                    f"{base_url}/v1/onecode/shell/schema",
                    headers={"Authorization": "Bearer test-token"},
                )
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["name"], "onecode.shell_projection")
        self.assertEqual(payload["version"], 1)
        self.assertIn("compact_message", payload["fields"])

    def test_http_server_serves_browser_gateway_console(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                request = Request(
                    f"{base_url}/",
                    headers={
                        "Authorization": "Bearer test-token",
                        "Accept": "text/html",
                    },
                )
                with urlopen(request, timeout=5) as response:
                    content_type = response.headers.get("content-type")
                    html = response.read().decode("utf-8")

        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("OneCode Shell", html)
        self.assertIn("Run demo adjudication", html)
        self.assertIn("/v1/onecode/gateway/adjudicate?demo=1", html)
        self.assertNotIn("一字诀", html)

    def test_http_server_adjudicates_gateway_candidate(self):
        from onecode.kernel.training_data import assistant_payload
        from onecode.web.api import OneCodeRequestHandler

        prediction = assistant_payload(
            facts={
                "intent_type": "patch_text",
                "path_scope": "workspace_relative",
                "sandbox_state": "not_required",
                "evidence_state": "required",
            },
            yizijue_state="111111",
            action="ALLOW_PATCH_WITH_SHA",
            reason="safe_workspace_patch",
        )

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                body = json.dumps(
                    {
                        "user": "随便处理一下这个项目",
                        "prediction": prediction,
                    }
                ).encode("utf-8")
                request = Request(
                    f"{base_url}/v1/onecode/gateway/adjudicate",
                    data=body,
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["raw_prediction"]["action"], "ALLOW_PATCH_WITH_SHA")
        self.assertEqual(payload["adjudicated_prediction"]["action"], "DENY_AND_LEDGER")
        self.assertTrue(payload["changed"])

    def test_http_server_describes_gateway_adjudicate_on_get(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                request = Request(
                    f"{base_url}/v1/onecode/gateway/adjudicate",
                    headers={"Authorization": "Bearer test-token"},
                )
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["method"], "POST")
        self.assertIn("user", payload["required_fields"])
        self.assertIn("prediction", payload["required_fields"])

    def test_http_server_can_demo_gateway_adjudicate_on_get(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                request = Request(
                    f"{base_url}/v1/onecode/gateway/adjudicate?demo=1",
                    headers={"Authorization": "Bearer test-token"},
                )
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["adjudicated_prediction"]["action"], "DENY_AND_LEDGER")
        self.assertTrue(payload["changed"])

    def test_http_server_rejects_unauthorized_models_request(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            with local_test_server(OneCodeRequestHandler) as (_server, base_url):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"{base_url}/v1/models", timeout=5)
                raised.exception.close()

        self.assertEqual(raised.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
