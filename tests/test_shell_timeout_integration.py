import hashlib
import json
import os
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from onecode.web.api import OneCodeRequestHandler
from tests.fixtures.delayed_model_server import DelayedModelServer


@contextmanager
def running_server(server: ThreadingHTTPServer):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class ShellTimeoutIntegrationTests(unittest.TestCase):
    def test_one_http_request_returns_504_with_terminal_evidence(self):
        task = "Inspect the current project structure"
        delayed_model = DelayedModelServer(
            ("127.0.0.1", 0), delay_seconds=0.3
        )

        with tempfile.TemporaryDirectory() as tmp, running_server(
            delayed_model
        ) as model_url, patch.dict(
            os.environ,
            {
                "ONECODE_MODEL_PROVIDER": "chat",
                "ONECODE_MODEL_ENDPOINT": f"{model_url}/v1/chat/completions",
                "ONECODE_MODEL": "stub-model",
                "OPENAI_API_KEY": "test-key",
                "ONECODE_MODEL_TIMEOUT_SECONDS": "0.1",
                "ONECODE_ALLOW_UNAUTHENTICATED": "true",
                "ONECODE_WORKSPACE_ROOT": tmp,
                "ONECODE_ALLOWED_WORKSPACE_ROOTS": tmp,
                "ONECODE_HOME": str(Path(tmp) / "home"),
            },
            clear=True,
        ), running_server(ThreadingHTTPServer(("127.0.0.1", 0), OneCodeRequestHandler)) as onecode_url:
            request = Request(
                f"{onecode_url}/v1/chat/completions",
                data=json.dumps(
                    {
                        "model": "onecode-agent",
                        "messages": [
                            {
                                "role": "user",
                                "content": task,
                            }
                        ],
                        "stream": False,
                        "metadata": {
                            "workspace": tmp,
                            "run_id": "shell-timeout-integration",
                            "onecode_mode": "read_task",
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with self.assertRaises(HTTPError) as raised:
                urlopen(request, timeout=5)
            response = raised.exception
            try:
                payload = json.loads(response.read().decode("utf-8"))
            finally:
                response.close()

            result = payload["onecode"]["result"]
            events = [
                json.loads(line)
                for line in Path(result["trace_path"])
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            model_event_types = [
                event["event_type"]
                for event in events
                if event["span_id"] == "model-call"
            ]
            failed_event = next(
                event
                for event in events
                if event["event_type"] == "model_call_failed"
            )

            self.assertEqual(response.code, 504)
            self.assertEqual(
                payload["error"]["type"], "model_provider_timeout"
            )
            self.assertEqual(delayed_model.request_count, 1)
            self.assertEqual(
                model_event_types,
                ["model_call_started", "model_call_failed"],
            )
            self.assertEqual(
                failed_event["payload"]["task_sha256"],
                hashlib.sha256(task.encode("utf-8")).hexdigest(),
            )
            self.assertTrue(Path(result["ledger_path"]).is_file())
            self.assertTrue(Path(result["manifest_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
