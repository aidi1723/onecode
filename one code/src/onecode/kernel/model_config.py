from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from typing import Any


DEFAULT_ONECODE_MODEL = "gpt-5.5"
DEFAULT_MODEL_PROVIDER = "openai-compatible"
FALLBACK_MODELS = [
    "gpt-5.5",
    "gpt-5.4",
    "gpt-4.1",
    "gpt-4.1-mini",
    "qwen-plus",
    "deepseek-chat",
    "kimi-k2",
    "glm-4.5",
]


def onecode_home() -> Path:
    return Path(os.getenv("ONECODE_HOME", "~/.onecode")).expanduser()


def user_config_path() -> Path:
    return onecode_home() / "config.json"


def mask_api_key(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def endpoint_has_local_host(value: str) -> bool:
    host = value.split("/", 1)[0].split(":", 1)[0].lower()
    return (
        host in {"localhost", "127.0.0.1", "::1"}
        or host.startswith("10.")
        or host.startswith("192.168.")
        or any(host.startswith(f"172.{index}.") for index in range(16, 32))
    )


def normalize_endpoint_url(endpoint: str) -> str:
    value = endpoint.strip().rstrip("/")
    if value == "":
        raise ValueError("endpoint is required")
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    if "://" in value:
        raise ValueError("endpoint must use http or https")
    scheme = "http" if endpoint_has_local_host(value) else "https"
    return f"{scheme}://{value}"


def write_model_config(
    *,
    endpoint: str,
    api_key: str,
    model: str | None = None,
    provider: str = DEFAULT_MODEL_PROVIDER,
    models: list[str] | None = None,
    preserve_existing_secret: bool = False,
) -> dict[str, Any]:
    if not isinstance(endpoint, str) or endpoint.strip() == "":
        raise ValueError("endpoint is required")
    existing_secret = ""
    if preserve_existing_secret:
        try:
            existing_secret = read_model_config(include_secret=True).get("api_key", "")
        except (ValueError, json.JSONDecodeError):
            existing_secret = ""
    selected_api_key = api_key.strip() if isinstance(api_key, str) else ""
    if selected_api_key == "" and preserve_existing_secret:
        selected_api_key = existing_secret
    if selected_api_key == "":
        raise ValueError("api_key is required")
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "provider": provider,
        "endpoint": normalize_endpoint_url(endpoint),
        "api_key": selected_api_key,
        "model": model.strip() if isinstance(model, str) and model.strip() else DEFAULT_ONECODE_MODEL,
    }
    if models is not None:
        payload["models"] = sorted(dict.fromkeys(item for item in models if isinstance(item, str) and item.strip()))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return read_model_config()


def read_model_config(*, include_secret: bool = False) -> dict[str, Any]:
    path = user_config_path()
    if not path.exists():
        return {
            "configured": False,
            "path": str(path),
            "provider": DEFAULT_MODEL_PROVIDER,
            "endpoint": "",
            "model": DEFAULT_ONECODE_MODEL,
            "models": [],
            "api_key_configured": False,
            "api_key_preview": None,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("model config must be a JSON object")
    api_key = payload.get("api_key") if isinstance(payload.get("api_key"), str) else ""
    result: dict[str, Any] = {
        "configured": bool(api_key and payload.get("endpoint")),
        "path": str(path),
        "provider": payload.get("provider") if isinstance(payload.get("provider"), str) else DEFAULT_MODEL_PROVIDER,
        "endpoint": normalize_endpoint_url(payload.get("endpoint")) if isinstance(payload.get("endpoint"), str) else "",
        "model": payload.get("model") if isinstance(payload.get("model"), str) else DEFAULT_ONECODE_MODEL,
        "models": payload.get("models") if isinstance(payload.get("models"), list) else [],
        "api_key_configured": bool(api_key),
        "api_key_preview": mask_api_key(api_key),
    }
    if include_secret:
        result["api_key"] = api_key
    return result


def models_url_from_endpoint(endpoint: str) -> str:
    value = normalize_endpoint_url(endpoint)
    if value.endswith("/chat/completions"):
        value = value[: -len("/chat/completions")]
    if value.endswith("/responses"):
        value = value[: -len("/responses")]
    return f"{value}/models"


def discover_models(endpoint: str, api_key: str, timeout_seconds: float = 10) -> dict[str, Any]:
    request = urllib.request.Request(
        models_url_from_endpoint(endpoint),
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {
            "source": "fallback",
            "models": FALLBACK_MODELS,
            "error": str(exc),
        }
    models = parse_models_payload(payload)
    if not models:
        return {
            "source": "fallback",
            "models": FALLBACK_MODELS,
            "error": "models response did not include model ids",
        }
    return {
        "source": "remote",
        "models": models,
    }


def parse_models_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    models: list[str] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
            models.append(item["id"].strip())
    return list(dict.fromkeys(models))
