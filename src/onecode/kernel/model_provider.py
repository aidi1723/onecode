import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


DEFAULT_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class ProviderConfig:
    provider_kind: str
    endpoint: str
    env_key: str
    model: str


DEFAULT_DOMESTIC_PROVIDER_CONFIGS = {
    "qwen": ProviderConfig(
        provider_kind="qwen",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        env_key="DASHSCOPE_API_KEY",
        model="qwen-plus",
    ),
    "deepseek": ProviderConfig(
        provider_kind="deepseek",
        endpoint="https://api.deepseek.com/chat/completions",
        env_key="DEEPSEEK_API_KEY",
        model="deepseek-v4-flash",
    ),
    "kimi": ProviderConfig(
        provider_kind="kimi",
        endpoint="https://api.moonshot.ai/v1/chat/completions",
        env_key="MOONSHOT_API_KEY",
        model="kimi-k2",
    ),
    "zhipu": ProviderConfig(
        provider_kind="zhipu",
        endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        env_key="ZHIPUAI_API_KEY",
        model="glm-4.5",
    ),
}


PROVIDER_ALIASES = {
    "dashscope": "qwen",
    "moonshot": "kimi",
    "glm": "zhipu",
    "compatible": "openai-compatible",
}


class MissingModelApiKey(ValueError):
    pass


class ModelProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelPlanAsset:
    path: str
    content: str


@dataclass(frozen=True)
class ModelPlanPatch:
    path: str
    search_block: str
    replace_block: str


@dataclass(frozen=True)
class ModelToolCall:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class ModelExecutionStep:
    id: str
    description: str
    tool_calls: list[ModelToolCall]
    depends_on: list[str] = field(default_factory=list)
    mode: str = "auto"


@dataclass(frozen=True)
class ModelPlan:
    task: str
    assets: list[ModelPlanAsset] = field(default_factory=list)
    patches: list[ModelPlanPatch] = field(default_factory=list)
    execution_steps: list[ModelExecutionStep] = field(default_factory=list)


MODEL_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["task"],
    "properties": {
        "task": {"type": "string", "minLength": 1},
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "content"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "content": {"type": "string"},
                },
            },
        },
        "patches": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "search_block", "replace_block"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "search_block": {"type": "string", "minLength": 1},
                    "replace_block": {"type": "string"},
                },
            },
        },
        "execution_plan": {
            "type": "object",
            "additionalProperties": False,
            "required": ["steps"],
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "description", "tool_calls"],
                        "properties": {
                            "id": {"type": "string", "minLength": 1},
                            "description": {"type": "string"},
                            "depends_on": {"type": "array", "items": {"type": "string"}},
                            "mode": {"type": "string", "enum": ["auto", "review", "manual"]},
                            "tool_calls": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["tool_name", "params"],
                                    "properties": {
                                        "tool_name": {"type": "string", "minLength": 1},
                                        "description": {"type": "string"},
                                        "params": {"type": "object"},
                                    },
                                },
                            },
                        },
                    },
                }
            },
        },
    },
}


def canonical_provider_kind(provider_kind: str) -> str:
    return PROVIDER_ALIASES.get(provider_kind, provider_kind)


def normalize_chat_endpoint(endpoint_or_base_url: str) -> str:
    endpoint = endpoint_or_base_url.strip()
    if endpoint == "":
        raise ValueError("endpoint must be a non-empty string")
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return endpoint
    return f"{endpoint}/chat/completions"


def build_provider_config(
    provider_kind: str,
    endpoint: str | None,
    model: str | None,
) -> ProviderConfig:
    canonical_kind = canonical_provider_kind(provider_kind)
    if canonical_kind in DEFAULT_DOMESTIC_PROVIDER_CONFIGS:
        default = DEFAULT_DOMESTIC_PROVIDER_CONFIGS[canonical_kind]
        return ProviderConfig(
            provider_kind=canonical_kind,
            endpoint=normalize_chat_endpoint(endpoint) if endpoint is not None else default.endpoint,
            env_key=default.env_key,
            model=model if model is not None else default.model,
        )
    if canonical_kind in {"chat", "openai-compatible"}:
        return ProviderConfig(
            provider_kind=canonical_kind,
            endpoint=normalize_chat_endpoint(endpoint) if endpoint is not None else DEFAULT_OPENAI_CHAT_COMPLETIONS_URL,
            env_key="OPENAI_API_KEY",
            model=model if model is not None else DEFAULT_MODEL,
        )
    if canonical_kind == "responses":
        return ProviderConfig(
            provider_kind=canonical_kind,
            endpoint=endpoint if endpoint is not None else DEFAULT_OPENAI_RESPONSES_URL,
            env_key="OPENAI_API_KEY",
            model=model if model is not None else DEFAULT_MODEL,
        )
    raise ValueError(f"unknown model provider: {provider_kind}")


def api_key_from_env(env: dict[str, str] | None = None, provider_kind: str = "chat") -> str | None:
    source = env if env is not None else os.environ
    config = build_provider_config(provider_kind, endpoint=None, model=None)
    value = source.get(config.env_key)
    if (value is None or value.strip() == "") and config.env_key != "OPENAI_API_KEY":
        value = source.get("OPENAI_API_KEY")
    if value is None or value.strip() == "":
        return None
    return value


def validate_model_plan(data: dict[str, Any]) -> ModelPlan:
    task = data.get("task")
    if not isinstance(task, str) or task == "":
        raise ValueError("task must be a non-empty string")
    assets = data.get("assets", [])
    patches = data.get("patches", [])
    execution_plan = data.get("execution_plan")
    if not isinstance(assets, list):
        raise ValueError("assets must be a list")
    if not isinstance(patches, list):
        raise ValueError("patches must be a list")
    execution_steps = validate_execution_plan(execution_plan) if execution_plan is not None else []
    if not assets and not patches and not execution_steps:
        raise ValueError("plan must include at least one asset, patch, or execution step")

    plan_assets: list[ModelPlanAsset] = []
    seen_paths: set[str] = set()
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise ValueError(f"asset {index} must be an object")
        unknown_fields = sorted(set(asset) - {"path", "content"})
        if unknown_fields:
            raise ValueError(f"asset {index} has unknown fields: {', '.join(unknown_fields)}")
        path = asset.get("path")
        content = asset.get("content")
        if not isinstance(path, str) or path == "":
            raise ValueError(f"asset {index} path must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError(f"asset {index} content must be a string")
        if path in seen_paths:
            raise ValueError(f"asset {index} duplicate path: {path}")
        seen_paths.add(path)
        plan_assets.append(ModelPlanAsset(path=path, content=content))

    plan_patches: list[ModelPlanPatch] = []
    for index, patch in enumerate(patches, start=1):
        if not isinstance(patch, dict):
            raise ValueError(f"patch {index} must be an object")
        unknown_fields = sorted(set(patch) - {"path", "search_block", "replace_block"})
        if unknown_fields:
            raise ValueError(f"patch {index} has unknown fields: {', '.join(unknown_fields)}")
        path = patch.get("path")
        search_block = patch.get("search_block")
        replace_block = patch.get("replace_block")
        if not isinstance(path, str) or path == "":
            raise ValueError(f"patch {index} path must be a non-empty string")
        if not isinstance(search_block, str) or search_block == "":
            raise ValueError(f"patch {index} search_block must be a non-empty string")
        if not isinstance(replace_block, str):
            raise ValueError(f"patch {index} replace_block must be a string")
        plan_patches.append(
            ModelPlanPatch(path=path, search_block=search_block, replace_block=replace_block)
        )
    return ModelPlan(task=task, assets=plan_assets, patches=plan_patches, execution_steps=execution_steps)


def validate_execution_plan(execution_plan: Any) -> list[ModelExecutionStep]:
    if not isinstance(execution_plan, dict):
        raise ValueError("execution_plan must be an object")
    unknown_fields = sorted(set(execution_plan) - {"steps"})
    if unknown_fields:
        raise ValueError(f"execution_plan has unknown fields: {', '.join(unknown_fields)}")
    steps = execution_plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("execution_plan.steps must be a non-empty list")

    parsed_steps = []
    seen_step_ids: set[str] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"execution step {index} must be an object")
        unknown_step_fields = sorted(set(step) - {"id", "description", "depends_on", "mode", "tool_calls"})
        if unknown_step_fields:
            raise ValueError(f"execution step {index} has unknown fields: {', '.join(unknown_step_fields)}")
        step_id = step.get("id")
        description = step.get("description")
        depends_on = step.get("depends_on", [])
        mode = step.get("mode", "auto")
        tool_calls = step.get("tool_calls")
        if not isinstance(step_id, str) or step_id == "":
            raise ValueError(f"execution step {index} id must be a non-empty string")
        if step_id in seen_step_ids:
            raise ValueError(f"execution step {index} duplicate id: {step_id}")
        seen_step_ids.add(step_id)
        if not isinstance(description, str):
            raise ValueError(f"execution step {index} description must be a string")
        if not isinstance(depends_on, list) or not all(isinstance(item, str) for item in depends_on):
            raise ValueError(f"execution step {index} depends_on must be a string list")
        if mode not in {"auto", "review", "manual"}:
            raise ValueError(f"execution step {index} mode must be auto, review, or manual")
        if not isinstance(tool_calls, list) or not tool_calls:
            raise ValueError(f"execution step {index} tool_calls must be a non-empty list")
        parsed_steps.append(
            ModelExecutionStep(
                id=step_id,
                description=description,
                depends_on=depends_on,
                mode=mode,
                tool_calls=[
                    validate_tool_call(step_index=index, call_index=call_index, tool_call=tool_call)
                    for call_index, tool_call in enumerate(tool_calls, start=1)
                ],
            )
        )
    return parsed_steps


def validate_tool_call(step_index: int, call_index: int, tool_call: Any) -> ModelToolCall:
    if not isinstance(tool_call, dict):
        raise ValueError(f"execution step {step_index} tool {call_index} must be an object")
    unknown_fields = sorted(set(tool_call) - {"tool_name", "description", "params"})
    if unknown_fields:
        raise ValueError(
            f"execution step {step_index} tool {call_index} has unknown fields: {', '.join(unknown_fields)}"
        )
    tool_name = tool_call.get("tool_name")
    description = tool_call.get("description", "")
    params = tool_call.get("params")
    if not isinstance(tool_name, str) or tool_name == "":
        raise ValueError(f"execution step {step_index} tool {call_index} name must be a non-empty string")
    if not isinstance(description, str):
        raise ValueError(f"execution step {step_index} tool {call_index} description must be a string")
    if not isinstance(params, dict):
        raise ValueError(f"execution step {step_index} tool {call_index} params must be an object")
    return ModelToolCall(tool_name=tool_name, description=description, params=params)


def extract_response_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    chunks: list[str] = []
    for output in response.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if chunks:
        return "".join(chunks)
    raise ModelProviderError("missing response text")


def parse_response_plan(response: dict[str, Any]) -> ModelPlan:
    try:
        payload = json.loads(extract_response_text(response))
    except json.JSONDecodeError as exc:
        raise ValueError("model response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("model response JSON must be an object")
    return validate_model_plan(payload)


class OpenAIResponsesProvider:
    def __init__(self, api_key: str, *, endpoint: str = DEFAULT_OPENAI_RESPONSES_URL) -> None:
        if api_key.strip() == "":
            raise MissingModelApiKey("OPENAI_API_KEY is required for model-backed runs")
        self.api_key = api_key
        self.endpoint = endpoint

    def request_payload(self, task: str, *, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Return only a JSON task plan. Use assets for full-file writes and patches for exact "
                        "search/replace edits. Do not execute commands. Do not include commentary."
                    ),
                },
                {"role": "user", "content": task},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "onecode_task_plan",
                    "strict": True,
                    "schema": MODEL_PLAN_SCHEMA,
                }
            },
        }

    def create_plan(self, task: str, *, model: str, http_timeout_seconds: float) -> ModelPlan:
        body = json.dumps(self.request_payload(task, model=model)).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=http_timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise TimeoutError("model request timed out") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ModelProviderError("model response envelope was not valid JSON") from exc
        if not isinstance(response_payload, dict):
            raise ModelProviderError("model response envelope must be an object")
        return parse_response_plan(response_payload)


class OpenAIChatCompletionsProvider:
    def __init__(self, api_key: str, *, endpoint: str = DEFAULT_OPENAI_CHAT_COMPLETIONS_URL) -> None:
        if api_key.strip() == "":
            raise MissingModelApiKey("OPENAI_API_KEY is required for model-backed runs")
        self.api_key = api_key
        self.endpoint = endpoint

    def request_payload(self, task: str, *, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only JSON with this exact object shape: "
                        "{\"task\": string, \"assets\": [{\"path\": string, \"content\": string}], "
                        "\"patches\": [{\"path\": string, \"search_block\": string, \"replace_block\": string}]}. "
                        "Use assets for full-file writes, patches for exact search/replace edits, or "
                        "execution_plan.steps for multi-step tool plans. "
                        "Do not execute commands. Do not include commentary. Do not use markdown fences."
                    ),
                },
                {"role": "user", "content": task},
            ],
            "response_format": {"type": "json_object"},
        }

    def parse_response(self, response: dict[str, Any]) -> ModelPlan:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelProviderError("missing chat completion choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ModelProviderError("invalid chat completion choice")
        message = first_choice.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ModelProviderError("missing chat completion message content")
        try:
            payload = json.loads(message["content"])
        except json.JSONDecodeError as exc:
            raise ValueError("model response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("model response JSON must be an object")
        return validate_model_plan(payload)

    def create_plan(self, task: str, *, model: str, http_timeout_seconds: float) -> ModelPlan:
        body = json.dumps(self.request_payload(task, model=model)).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=http_timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise TimeoutError("model request timed out") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ModelProviderError("model response envelope was not valid JSON") from exc
        if not isinstance(response_payload, dict):
            raise ModelProviderError("model response envelope must be an object")
        return self.parse_response(response_payload)
