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
    content_type = headers.get("content-type") or headers.get("Content-Type")
    if isinstance(content_type, str) and content_type.strip() != "":
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            return JsonRequestBody(
                payload=None,
                status_code=415,
                error_type="unsupported_media_type",
                error_message="content-type must be application/json",
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
    if _contains_null(value):
        return JsonRequestBody(
            payload=None,
            status_code=400,
            error_type="invalid_request_body",
            error_message="request body contains a null byte",
        )
    return JsonRequestBody(payload=value)


def _contains_null(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_contains_null(key) or _contains_null(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_null(item) for item in value)
    return False
