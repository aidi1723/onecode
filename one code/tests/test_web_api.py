import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class OneCodeWebApiTests(unittest.TestCase):
    def test_models_payload_exposes_onecode_agent(self):
        from onecode.web.api import build_models_payload

        payload = build_models_payload()

        self.assertEqual(payload["object"], "list")
        self.assertEqual(payload["data"][0]["id"], "onecode-agent")

    def test_bearer_auth_rejects_missing_token_when_configured(self):
        from onecode.web.api import request_authorized

        self.assertFalse(request_authorized({}, "secret-token"))

    def test_bearer_auth_accepts_matching_token(self):
        from onecode.web.api import request_authorized

        self.assertTrue(request_authorized({"authorization": "Bearer secret-token"}, "secret-token"))

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

    def test_chat_completion_falls_back_to_rule_run_without_model_key(self):
        from onecode.web.api import handle_chat_completion

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
            },
            clear=True,
        ):
            payload, status_code = handle_chat_completion(
                {
                    "model": "onecode-agent",
                    "messages": [{"role": "user", "content": "查：看看项目"}],
                }
            )
            ledger_exists = Path(payload["onecode"]["result"]["ledger_path"]).exists()

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["object"], "chat.completion")
        self.assertEqual(payload["choices"][0]["message"]["role"], "assistant")
        self.assertIn("OneCode run", payload["choices"][0]["message"]["content"])
        self.assertEqual(payload["onecode"]["mode"], "rule_fallback")
        self.assertTrue(ledger_exists)

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

    def test_http_server_serves_models_and_chat_completion(self):
        from onecode.web.api import OneCodeRequestHandler

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_API_TOKEN": "test-token",
            },
            clear=True,
        ):
            server = ThreadingHTTPServer(("127.0.0.1", 0), OneCodeRequestHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
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
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

        self.assertEqual(models_payload["data"][0]["id"], "onecode-agent")
        self.assertEqual(chat_payload["choices"][0]["message"]["role"], "assistant")
        self.assertEqual(chat_payload["onecode"]["mode"], "rule_fallback")

    def test_http_server_rejects_unauthorized_models_request(self):
        from onecode.web.api import OneCodeRequestHandler

        with patch.dict("os.environ", {"ONECODE_API_TOKEN": "test-token"}, clear=True):
            server = ThreadingHTTPServer(("127.0.0.1", 0), OneCodeRequestHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"{base_url}/v1/models", timeout=5)
                raised.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

        self.assertEqual(raised.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
