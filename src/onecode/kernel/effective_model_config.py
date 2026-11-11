from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from onecode.kernel.model_config import DEFAULT_MODEL_PROVIDER, DEFAULT_ONECODE_MODEL


@dataclass(frozen=True)
class EffectiveModelConfig:
    provider: str
    endpoint: str | None
    model: str
    api_key: str | None
    public: dict[str, object]


def resolve_effective_model_config(
    environment: Mapping[str, str],
    stored_config: Mapping[str, Any],
) -> EffectiveModelConfig:
    provider, provider_source = _value_with_source(
        environment.get("ONECODE_MODEL_PROVIDER"),
        stored_config.get("provider"),
        DEFAULT_MODEL_PROVIDER,
    )
    endpoint, endpoint_source = _value_with_source(
        environment.get("ONECODE_MODEL_ENDPOINT"),
        stored_config.get("endpoint"),
        None,
    )
    model, model_source = _value_with_source(
        environment.get("ONECODE_MODEL") or environment.get("OPENAI_MODEL"),
        stored_config.get("model"),
        DEFAULT_ONECODE_MODEL,
    )
    env_key = _provider_api_key_name(str(provider))
    environment_key = environment.get(env_key)
    if (not isinstance(environment_key, str) or not environment_key.strip()) and env_key != "OPENAI_API_KEY":
        environment_key = environment.get("OPENAI_API_KEY")
    api_key, api_key_source = _value_with_source(
        environment_key,
        stored_config.get("api_key"),
        None,
    )
    return EffectiveModelConfig(
        provider=str(provider),
        endpoint=str(endpoint) if endpoint is not None else None,
        model=str(model),
        api_key=str(api_key) if api_key is not None else None,
        public={
            "provider": str(provider),
            "provider_source": provider_source,
            "endpoint": str(endpoint) if endpoint is not None else None,
            "endpoint_source": endpoint_source,
            "model": str(model),
            "model_source": model_source,
            "api_key_configured": api_key is not None,
            "api_key_source": api_key_source,
        },
    )


def _value_with_source(
    environment_value: Any,
    stored_value: Any,
    default_value: Any,
) -> tuple[Any, str]:
    if isinstance(environment_value, str) and environment_value.strip():
        return environment_value.strip(), "environment"
    if isinstance(stored_value, str) and stored_value.strip():
        return stored_value.strip(), "stored"
    return default_value, "default"


def _provider_api_key_name(provider: str) -> str:
    return {
        "qwen": "DASHSCOPE_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "kimi": "MOONSHOT_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "zhipu": "ZHIPUAI_API_KEY",
        "glm": "ZHIPUAI_API_KEY",
    }.get(provider, "OPENAI_API_KEY")
