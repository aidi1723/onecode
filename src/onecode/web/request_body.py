from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, BinaryIO, Mapping


DEFAULT_MAX_REQUEST_BYTES = 1_000_000


@dataclass(frozen=True)
class JsonRequestBody:
    payload: dict[str, Any] | None
    status_code: int = 200
    error_type: str | None = None
    error_message: str | None = None


def max_request_bytes() -> int:
    try:
        value = int(os.getenv("ONECODE_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES)))
    except ValueError:
        return DEFAULT_MAX_REQUEST_BYTES
    return value if value > 0 else DEFAULT_MAX_REQUEST_BYTES


def read_json_request_body(headers: Mapping[str, str], rfile: BinaryIO) -> JsonRequestBody:
    raw_length = headers.get("content-length") or headers.get("Content-Length") or "0"
    try:
        length = int(raw_length or "0")
    except ValueError:
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_request_body",
            error_message="content-length must be an integer",
        )
    if length < 0:
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_request_body",
            error_message="content-length must not be negative",
        )
    limit = max_request_bytes()
    if length > limit:
        return JsonRequestBody(
            payload=None,
            status_code=413,
            error_type="request_too_large",
            error_message=f"request body exceeds maximum size of {limit} bytes",
        )
    raw = rfile.read(length)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_json",
            error_message="request body must be valid JSON",
        )
    if not isinstance(value, dict):
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_json",
            error_message="request body must be a JSON object",
        )
    return JsonRequestBody(payload=value)
