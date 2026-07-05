#!/usr/bin/env python3
import argparse
import contextlib
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_hardened_mlx_dataset import STRICT_SYSTEM_PROMPT
from scripts.eval_mlx_predictions import (
    action_from_object,
    extract_first_json_object,
    guard_prediction_for_row,
)
from scripts.generate_mlx_predictions import greedy_sampler


DEFAULT_MODEL = "Qwen/Qwen3-0.6b"
ADAPTER_PATH_ENV = "YIZIJUE_ADAPTER_PATH"
MAX_REQUEST_BODY_BYTES = 64 * 1024
MAX_REQUEST_TOKENS = 512


def build_prompt(user_input: str) -> str:
    return f"{STRICT_SYSTEM_PROMPT}\n\nUser: {user_input}\nAssistant:"


def row_for_input(user_input: str) -> dict[str, Any]:
    return {
        "id": "request",
        "messages": [
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    }


def build_prediction_response(user_input: str, raw_prediction: str) -> dict[str, Any]:
    guarded_prediction = guard_prediction_for_row(row_for_input(user_input), raw_prediction)
    parsed = normalize_action_json(extract_first_json_object(guarded_prediction))
    action = action_from_object(parsed)
    return {
        "input": user_input,
        "action": action,
        "json": parsed,
        "guarded_prediction": guarded_prediction,
        "raw_prediction": raw_prediction,
    }


def normalize_action_json(parsed: dict[str, Any] | None) -> dict[str, Any] | None:
    if not parsed:
        return None
    action = parsed.get("action")
    if isinstance(action, str):
        return {
            "action": parsed,
            "output_type": "action_json",
        }
    return parsed


def default_adapter_path() -> str | None:
    return os.environ.get(ADAPTER_PATH_ENV) or None


def validate_request_max_tokens(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if type(value) is not int:
        raise TypeError("max_tokens_must_be_int")
    if value < 1 or value > MAX_REQUEST_TOKENS:
        raise ValueError(f"max_tokens must be between 1 and {MAX_REQUEST_TOKENS}")
    return value


def parse_max_tokens(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    try:
        return validate_request_max_tokens(parsed, default=220)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_port(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0 or parsed > 65535:
        raise argparse.ArgumentTypeError("must be between 0 and 65535")
    return parsed


class MlxRunner:
    def __init__(self, model_name: str, adapter_path: str, max_tokens: int) -> None:
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.max_tokens = max_tokens
        self._model = None
        self._tokenizer = None
        self._generate_lock = Lock()

    def load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        from mlx_lm import load

        self._model, self._tokenizer = load(self.model_name, adapter_path=self.adapter_path)

    def generate(self, user_input: str, *, max_tokens: int | None = None) -> str:
        self.load()
        from mlx_lm import generate

        with self._generate_lock, contextlib.redirect_stdout(io.StringIO()):
            return generate(
                self._model,
                self._tokenizer,
                prompt=build_prompt(user_input),
                max_tokens=max_tokens or self.max_tokens,
                sampler=greedy_sampler,
                verbose=False,
            )


def render_index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YiZiJue-LM Local</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #17202a; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 20px; }
    h1 { font-size: 28px; line-height: 1.2; margin: 0 0 8px; letter-spacing: 0; }
    p { margin: 0 0 20px; color: #5f6b7a; }
    .panel { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 18px; }
    label { display: block; font-weight: 650; margin-bottom: 8px; }
    textarea { box-sizing: border-box; width: 100%; min-height: 120px; resize: vertical; border: 1px solid #c7d0db; border-radius: 6px; padding: 12px; font: inherit; }
    button { margin-top: 12px; height: 38px; padding: 0 14px; border: 0; border-radius: 6px; background: #1565c0; color: white; font-weight: 650; cursor: pointer; }
    button:disabled { opacity: .6; cursor: wait; }
    pre { overflow: auto; min-height: 180px; margin: 16px 0 0; padding: 12px; border-radius: 6px; background: #101820; color: #e6edf3; font-size: 13px; line-height: 1.45; }
    .meta { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
    .chip { border: 1px solid #d8dee6; border-radius: 999px; padding: 5px 9px; background: #fff; color: #394555; font-size: 13px; }
  </style>
</head>
<body>
  <main>
    <h1>YiZiJue-LM Local</h1>
    <p>本地 0.6B v5 proposal model 服务。根页面只用于查看模型输出，执行授权仍由 OneCode 负责。</p>
    <div class="meta">
      <span class="chip">GET /health</span>
      <span class="chip">POST /predict</span>
      <span class="chip">127.0.0.1:8090</span>
    </div>
    <section class="panel">
      <label for="input">输入</label>
      <textarea id="input">运行 pytest 验证一下</textarea>
      <button id="run" type="button">运行预测</button>
      <pre id="output">等待输入...</pre>
    </section>
  </main>
  <script>
    const button = document.querySelector("#run");
    const input = document.querySelector("#input");
    const output = document.querySelector("#output");
    button.addEventListener("click", async () => {
      button.disabled = true;
      output.textContent = "生成中...";
      try {
        const response = await fetch("/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: input.value, max_tokens: 220 })
        });
        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        output.textContent = String(error);
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


class YiZiJueHandler(BaseHTTPRequestHandler):
    runner: MlxRunner

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, body_text: str) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(200, render_index_html())
            return
        if self.path != "/health":
            self._send_json(404, {"error": "not_found"})
            return
        adapter_path = Path(self.runner.adapter_path)
        self._send_json(
            200,
            {
                "ok": True,
                "model": self.runner.model_name,
                "adapter_path": self.runner.adapter_path,
                "adapter_exists": adapter_path.exists(),
            },
        )

    def do_POST(self) -> None:
        if self.path != "/predict":
            self._send_json(404, {"error": "not_found"})
            return
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(411, {"error": "content_length_required"})
            return
        if not content_length.isdecimal():
            self._send_json(400, {"error": "invalid_content_length"})
            return
        try:
            length = int(content_length)
        except ValueError:
            self._send_json(400, {"error": "invalid_content_length"})
            return
        if length < 0:
            self._send_json(400, {"error": "invalid_content_length"})
            return
        if length > MAX_REQUEST_BODY_BYTES:
            self._send_json(413, {"error": "request_too_large"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": "invalid_json", "detail": str(exc)})
            return
        if not isinstance(body, dict):
            self._send_json(400, {"error": "json_object_required"})
            return
        user_input = body.get("input")
        if not isinstance(user_input, str) or not user_input.strip():
            self._send_json(400, {"error": "input_required"})
            return
        try:
            max_tokens = validate_request_max_tokens(body.get("max_tokens"), default=self.runner.max_tokens)
        except TypeError:
            self._send_json(400, {"error": "max_tokens_must_be_int"})
            return
        except ValueError as exc:
            self._send_json(400, {"error": "max_tokens_out_of_range", "detail": str(exc)})
            return
        try:
            raw_prediction = self.runner.generate(user_input, max_tokens=max_tokens)
            response = build_prediction_response(user_input, raw_prediction)
        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": "generation_failed",
                    "error_type": type(exc).__name__,
                },
            )
            return
        self._send_json(200, response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve YiZiJue-LM v5 locally over HTTP.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--adapter-path", default=default_adapter_path(), help=f"LoRA adapter path. Defaults to ${ADAPTER_PATH_ENV}.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=parse_port, default=8090)
    parser.add_argument("--max-tokens", type=parse_max_tokens, default=220)
    parser.add_argument("--preload", action="store_true")
    return parser


def make_server(host: str, port: int, runner: MlxRunner) -> ThreadingHTTPServer:
    handler = type("BoundYiZiJueHandler", (YiZiJueHandler,), {"runner": runner})
    return ThreadingHTTPServer((host, port), handler)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.adapter_path:
        parser.error(f"--adapter-path or {ADAPTER_PATH_ENV} is required")
    runner = MlxRunner(args.model, args.adapter_path, args.max_tokens)
    if args.preload:
        runner.load()
    server = make_server(args.host, args.port, runner)
    print(
        json.dumps(
            {
                "serving": True,
                "host": args.host,
                "port": args.port,
                "model": args.model,
                "adapter_path": args.adapter_path,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
