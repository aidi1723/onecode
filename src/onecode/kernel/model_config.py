from __future__ import annotations

import ipaddress
import json
import os
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from typing import Any


MAX_RESPONSE_BYTES = 2_000_000


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


def endpoint_host(value: str) -> str:
    raw = value.strip()
    if "://" in raw:
        return (urlparse(raw).hostname or "").lower()
    if raw.startswith("["):
        end = raw.find("]")
        return raw[1:end].lower() if end > 1 else ""
    host = raw.split("/", 1)[0]
    if host.count(":") == 1:
        host = host.split(":", 1)[0]
    return host.lower()


def endpoint_has_local_host(value: str) -> bool:
    host = endpoint_host(value)
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(address.is_loopback or address.is_private or address.is_link_local)


def read_bounded_response(response: Any, limit: int = MAX_RESPONSE_BYTES) -> bytes:
    raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("response exceeds maximum size")
    return raw


def normalize_endpoint_url(endpoint: str) -> str:
    if not isinstance(endpoint, str):
        raise ValueError("endpoint is required")
    if "\x00" in endpoint or len(endpoint) > 2_000:
        raise ValueError("endpoint is invalid")
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


def write_private_text(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", text=True)
    tmp_path = tmp_name
    try:
        os.chmod(tmp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
        path.chmod(0o600)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def endpoint_authority(endpoint: str) -> tuple[str, str, int | None]:
    parsed = urlparse(normalize_endpoint_url(endpoint))
    return (parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port)


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
    normalized_endpoint = normalize_endpoint_url(endpoint)
    existing_secret = ""
    existing_endpoint = ""
    if preserve_existing_secret:
        try:
            existing = read_model_config(include_secret=True)
            existing_secret = existing.get("api_key", "") if isinstance(existing.get("api_key"), str) else ""
            existing_endpoint = existing.get("endpoint", "") if isinstance(existing.get("endpoint"), str) else ""
        except (ValueError, json.JSONDecodeError):
            existing_secret = ""
            existing_endpoint = ""
    selected_api_key = api_key.strip() if isinstance(api_key, str) else ""
    if selected_api_key == "" and preserve_existing_secret:
        if existing_endpoint and endpoint_authority(existing_endpoint) != endpoint_authority(normalized_endpoint):
            raise ValueError("api_key is required when the endpoint host changes")
        selected_api_key = existing_secret
    if selected_api_key == "":
        raise ValueError("api_key is required")
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "provider": provider,
        "endpoint": normalized_endpoint,
        "api_key": selected_api_key,
        "model": model.strip() if isinstance(model, str) and model.strip() else DEFAULT_ONECODE_MODEL,
    }
    if models is not None:
        payload["models"] = sorted(dict.fromkeys(item for item in models if isinstance(item, str) and item.strip()))
    write_private_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
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
    payload = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("model config must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("model config must be a JSON object")
    config_payload = parsed
    api_key = config_payload.get("api_key") if isinstance(config_payload.get("api_key"), str) else ""
    result: dict[str, Any] = {
        "configured": bool(api_key and config_payload.get("endpoint")),
        "path": str(path),
        "provider": config_payload.get("provider") if isinstance(config_payload.get("provider"), str) else DEFAULT_MODEL_PROVIDER,
        "endpoint": normalize_endpoint_url(cast(str, config_payload.get("endpoint"))) if isinstance(config_payload.get("endpoint"), str) else "",  # type: ignore
        "model": config_payload.get("model") if isinstance(config_payload.get("model"), str) else DEFAULT_ONECODE_MODEL,
        "models": config_payload.get("models") if isinstance(config_payload.get("models"), list) else [],
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
    try:
        url = models_url_from_endpoint(endpoint)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("endpoint must use http or https")
        if parsed.scheme == "http" and not endpoint_has_local_host(parsed.hostname):
            raise ValueError("remote endpoint must use https")
    except ValueError:
        return {
            "source": "fallback",
            "models": FALLBACK_MODELS,
            "error": "model discovery failed",
        }
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(read_bounded_response(response).decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return {
            "source": "fallback",
            "models": FALLBACK_MODELS,
            "error": "model discovery failed",
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
