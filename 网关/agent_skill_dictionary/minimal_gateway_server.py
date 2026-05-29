from __future__ import annotations

import os
from typing import Any

from .minimal_gateway_core import load_oneword_dict, resolve_with_oneword_dict, rewrite_with_oneword_dict
from .upstream import parse_upstream_json, upstream_error_payload


ONEWORD_DICT_PATH = os.getenv(
    "ONEWORD_KERNEL_DICT_PATH",
    "agent_skill_dictionary/oneword_dict.json",
)
UPSTREAM_BASE_URL = os.getenv("ONEWORD_UPSTREAM_BASE_URL", "https://api.openai.com/v1")
UPSTREAM_API_KEY = os.getenv("ONEWORD_UPSTREAM_API_KEY") or os.getenv("OPENAI_API_KEY")


def create_app() -> Any:
    try:
        import httpx
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError as exc:
        raise RuntimeError(
            "Minimal gateway requires fastapi and httpx. Install with: "
            "python3 -m pip install -r requirements-gateway.txt"
        ) from exc

    app = FastAPI(title="OneWord Minimal Gateway", version="1.0.0")
    dictionary = load_oneword_dict(ONEWORD_DICT_PATH)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "dictionary": ONEWORD_DICT_PATH}

    @app.post("/v1/oneword/resolve")
    async def resolve(request: Request) -> dict[str, Any]:
        body = await request.json()
        message = body.get("input") or body.get("message") or ""
        return resolve_with_oneword_dict(str(message), dictionary)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        body = await request.json()
        rewritten, metadata = rewrite_with_oneword_dict(body, dictionary)
        if metadata["halt_model_forwarding"]:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "oneword_halt",
                        "message": "OneWord minimal gateway halted model forwarding.",
                    },
                    "oneword_gateway": {**metadata, "blocked": True},
                },
            )

        headers = _upstream_headers(request.headers)
        upstream_url = f"{UPSTREAM_BASE_URL.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(upstream_url, json=rewritten, headers=headers)
        except httpx.HTTPError as exc:
            return JSONResponse(
                content=upstream_error_payload(exc, "oneword_gateway"),
                status_code=502,
            )

        payload, status_code = parse_upstream_json(response, "oneword_gateway")
        if isinstance(payload, dict):
            payload["oneword_gateway"] = {
                **payload.get("oneword_gateway", {}),
                **metadata,
            }
        return JSONResponse(content=payload, status_code=status_code)

    return app


def _upstream_headers(inbound_headers: Any) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if UPSTREAM_API_KEY:
        headers["authorization"] = f"Bearer {UPSTREAM_API_KEY}"
    elif inbound_headers.get("authorization"):
        headers["authorization"] = inbound_headers["authorization"]
    return headers


app = create_app()
