from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


class DelayedModelServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        delay_seconds: float,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must not be negative")
        self.delay_seconds = delay_seconds
        self._request_count = 0
        self._request_count_lock = threading.Lock()
        super().__init__(server_address, DelayedModelRequestHandler)

    @property
    def request_count(self) -> int:
        with self._request_count_lock:
            return self._request_count

    def record_request(self) -> None:
        with self._request_count_lock:
            self._request_count += 1


class DelayedModelRequestHandler(BaseHTTPRequestHandler):
    server: DelayedModelServer

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/v1/models":
            self._send_json({"error": "not_found"}, status_code=404)
            return
        self._send_json(
            {
                "object": "list",
                "data": [
                    {
                        "id": "stub-model",
                        "object": "model",
                        "owned_by": "onecode-test",
                    }
                ],
            }
        )

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/v1/chat/completions":
            self._send_json({"error": "not_found"}, status_code=404)
            return
        self._read_request_body()
        self.server.record_request()
        time.sleep(self.server.delay_seconds)
        plan = {
            "task": "delayed model fixture",
            "no_action": {"reason": "fixture response completed after delay"},
        }
        self._send_json(
            {
                "id": "chatcmpl-onecode-delayed-model",
                "object": "chat.completion",
                "model": "stub-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(plan),
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        )

    def _read_request_body(self) -> None:
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length > 0:
            self.rfile.read(length)

    def _send_json(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format: str, *args: Any) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a delayed OpenAI-compatible model fixture")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--delay-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if not 0 < args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must not be negative")
    return args


def main() -> None:
    args = parse_args()
    server = DelayedModelServer(
        ("127.0.0.1", args.port), delay_seconds=args.delay_seconds
    )
    print(f"http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
