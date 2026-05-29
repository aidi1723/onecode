from __future__ import annotations

from typing import Any


def parse_upstream_json(response: Any, gateway_name: str) -> tuple[Any, int]:
    try:
        return response.json(), int(response.status_code)
    except ValueError:
        return (
            {
                "error": {
                    "type": "upstream_invalid_json",
                    "message": "Upstream returned a non-JSON response.",
                },
                gateway_name: {
                    "upstream_status_code": int(response.status_code),
                    "upstream_body_preview": str(getattr(response, "text", ""))[:500],
                },
            },
            502,
        )


def upstream_error_payload(exc: Exception, gateway_name: str) -> dict[str, Any]:
    return {
        "error": {
            "type": "upstream_request_failed",
            "message": "Failed to contact upstream model API.",
        },
        gateway_name: {
            "upstream_error": type(exc).__name__,
            "upstream_error_message": str(exc),
        },
    }
