import ast
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from onecode.kernel.http_safety import StripAuthRedirectHandler

_SAFE_OPENER = urllib.request.build_opener(StripAuthRedirectHandler())

from dataclasses import dataclass, field
from typing import Any

from onecode.kernel.model_config import read_bounded_response
from onecode.kernel.preset_tests import is_preset_test_path, new_test_asset_allowed


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


class ModelProviderTimeout(ModelProviderError):
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
    no_action_reason: str | None = None


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
        "no_action": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reason"],
            "properties": {"reason": {"type": "string", "minLength": 1}},
        },
    },
}

MODEL_TOOL_CONTRACTS = {
    "list_files": {"approval": False, "params": {"path": "string", "max_entries": "integer", "max_depth": "integer"}},
    "read_text": {
        "approval": False,
        "params": {
            "path": "string",
            "max_bytes": "integer",
            "max_lines": "integer",
            "start_line": "integer",
            "end_line": "integer",
            "line_numbers": "boolean",
        },
    },
    "search_text": {
        "approval": False,
        "params": {
            "query": "literal string or regex",
            "regex": "boolean",
            "path": "string",
            "max_matches": "integer",
            "max_depth": "integer",
            "max_files": "integer",
            "max_file_bytes": "integer",
            "max_total_bytes": "integer",
        },
    },
    "glob_files": {"approval": False, "params": {"pattern": "string", "path": "string", "max_matches": "integer"}},
    "outline": {"approval": False, "params": {"path": "string"}},
    "git_status": {"approval": False, "params": {}},
    "git_diff": {"approval": False, "params": {}},
    "git_commit": {"approval": True, "params": {"message": "string", "paths": "string[]"}},
    "run_command": {"approval": True, "params": {"argv": "string[]", "timeout_seconds": "integer"}},
    "write_text": {"approval": True, "params": {"path": "string", "content": "string"}},
    "patch_text": {
        "approval": True,
        "params": {"path": "string", "search_block": "string", "replace_block": "string"},
    },
}
SUPPORTED_MODEL_TOOLS = frozenset(MODEL_TOOL_CONTRACTS)


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


def resumable_model_status(code: int) -> bool:
    return code in {408, 429, 502, 503, 504}


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


def validate_model_plan(
    data: dict[str, Any],
    known_modules: set[str] | None = None,
    existing_preset_tests: set[str] | None = None,
) -> ModelPlan:
    task = data.get("task")
    if not isinstance(task, str) or task == "":
        raise ValueError("task must be a non-empty string")
    assets = data.get("assets", [])
    patches = data.get("patches", [])
    execution_plan = data.get("execution_plan")
    no_action = data.get("no_action")
    if not isinstance(assets, list):
        raise ValueError("assets must be a list")
    if not isinstance(patches, list):
        raise ValueError("patches must be a list")
    execution_steps = validate_execution_plan(execution_plan) if execution_plan is not None else []
    if no_action is not None and (assets or patches or execution_steps):
        raise ValueError("no_action cannot be combined with actions")
    no_action_reason = validate_no_action(no_action) if no_action is not None else None
    if not assets and not patches and not execution_steps and no_action_reason is None:
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
        if is_preset_test_path(path) and not new_test_asset_allowed(path, existing_preset_tests):
            raise ValueError(f"paths under tests/ are protected: {path}")
        if not isinstance(content, str) or content == "":
            raise ValueError(f"asset {index} content must be a non-empty string")
        if path in seen_paths:
            raise ValueError(f"asset {index} duplicate path: {path}")
        seen_paths.add(path)
        plan_assets.append(ModelPlanAsset(path=path, content=content))
    _reject_unusable_python_assets(plan_assets, known_modules)

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
        if is_preset_test_path(path):
            raise ValueError(f"paths under tests/ are protected: {path}")
        if not isinstance(search_block, str) or search_block == "":
            raise ValueError(f"patch {index} search_block must be a non-empty string")
        if not isinstance(replace_block, str) or replace_block == "":
            raise ValueError(f"patch {index} replace_block must be a non-empty string")
        plan_patches.append(
            ModelPlanPatch(path=path, search_block=search_block, replace_block=replace_block)
        )
    return ModelPlan(
        task=task,
        assets=plan_assets,
        patches=plan_patches,
        execution_steps=execution_steps,
        no_action_reason=no_action_reason,
    )


def _reject_unusable_python_assets(assets: list[ModelPlanAsset], known_modules: set[str] | None = None) -> None:
    module_names = set(known_modules or ())
    for asset in assets:
        if not asset.path.endswith(".py"):
            continue
        stem = asset.path.replace("\\", "/").rsplit("/", 1)[-1][:-3]
        if stem and stem != "__init__":
            module_names.add(stem)
    for asset in assets:
        if not asset.path.endswith(".py"):
            continue
        try:
            tree = ast.parse(asset.content)
        except SyntaxError as exc:
            raise ValueError(f"{asset.path} is not valid Python") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".", 1)[0]
                    if pkg == "pytest":
                        raise ValueError(f"{asset.path} must not import pytest")
                    if pkg == "unittest" and not is_preset_test_path(asset.path):
                        raise ValueError(f"{asset.path} must not import unittest")
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0 and known_modules is None:
                    raise ValueError(f"{asset.path} must not use a relative import")
                if not node.module:
                    continue
                pkg = node.module.split(".", 1)[0]
                if pkg == "pytest":
                    raise ValueError(f"{asset.path} must not import pytest")
                if pkg == "unittest" and not is_preset_test_path(asset.path):
                    raise ValueError(f"{asset.path} must not import unittest")
                parts = node.module.split(".")
                if parts[0] == "src" and (len(parts) < 2 or parts[1] not in module_names):
                    missing = parts[1] if len(parts) > 1 else "src"
                    raise ValueError(f"{asset.path} imports missing module {missing}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "_exit":
                    raise ValueError(f"{asset.path} must not call {func.id}")
                elif isinstance(func, ast.Attribute) and func.attr == "_exit":
                    raise ValueError(f"{asset.path} must not call {func.attr}")
                if framework := _imported_test_framework(node):
                    if framework == "pytest" or not is_preset_test_path(asset.path):
                        raise ValueError(f"{asset.path} must not import {framework}")


def _imported_test_framework(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "__import__":
        target = node.args[0] if node.args else None
    elif isinstance(func, ast.Attribute) and func.attr == "import_module":
        target = node.args[0] if node.args else None
    else:
        return None
    if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
        return None
    root = target.value.split(".", 1)[0]
    if root in {"unittest", "pytest"}:
        return root
    return None


def validate_no_action(value: Any) -> str:
    if not isinstance(value, dict) or set(value) != {"reason"}:
        raise ValueError("no_action must contain only reason")
    reason = value.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("no_action.reason must be a non-empty string")
    return reason.strip()


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
    if tool_name not in SUPPORTED_MODEL_TOOLS:
        raise ValueError(f"execution step {step_index} tool {call_index} unsupported tool: {tool_name}")
    if not isinstance(description, str):
        raise ValueError(f"execution step {step_index} tool {call_index} description must be a string")
    if not isinstance(params, dict):
        raise ValueError(f"execution step {step_index} tool {call_index} params must be an object")
    if tool_name in {"write_text", "patch_text"}:
        path_val = params.get("path")
        if isinstance(path_val, str) and is_preset_test_path(path_val):
            raise ValueError(f"paths under tests/ are protected: {path_val}")
    elif tool_name == "git_commit":
        paths_val = params.get("paths")
        if isinstance(paths_val, list):
            for p in paths_val:
                if isinstance(p, str) and is_preset_test_path(p):
                    raise ValueError(f"paths under tests/ are protected: {p}")
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


def json_object_from_model_text(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        if start == -1:
            raise
        try:
            payload, _end = json.JSONDecoder().raw_decode(stripped[start:])
        except json.JSONDecodeError:
            if not stripped.rstrip().endswith("}"):
                raise ValueError("model response was truncated") from exc
            raise
        return payload


def _message_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    if not parts:
        return None
    return "".join(parts)


def workspace_python_modules(workspace: Path) -> set[str]:
    names: set[str] = set()
    skip = {".git", ".onecode", ".venv", "venv", "__pycache__", "build", "dist", "node_modules"}
    for folder in ("src", "tests"):
        root = workspace / folder
        if root.is_dir():
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                stem = path.name[:-3]
                if stem and stem != "__init__":
                    names.add(stem)
    if workspace.is_dir():
        for item in workspace.iterdir():
            if item.is_dir() and item.name not in skip and not item.name.startswith("."):
                for path in item.glob("*.py"):
                    stem = path.name[:-3]
                    if stem and stem != "__init__":
                        names.add(stem)
    return names


def normalize_model_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    if not normalized.get("task") or not isinstance(normalized.get("task"), str):
        normalized["task"] = "workspace_task"
    if "assets" not in normalized and ("target" in normalized or "path" in normalized) and "content" in normalized:
        target_path = normalized.get("target") or normalized.get("path")
        if isinstance(target_path, str) and isinstance(normalized.get("content"), str):
            normalized["assets"] = [{"path": target_path, "content": normalized["content"]}]
    return normalized


def parse_response_plan(
    response: dict[str, Any],
    known_modules: set[str] | None = None,
    existing_preset_tests: set[str] | None = None,
) -> ModelPlan:
    try:
        payload = json_object_from_model_text(extract_response_text(response))
    except json.JSONDecodeError as exc:
        raise ValueError("model response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("model response JSON must be an object")
    return validate_model_plan(
        normalize_model_plan_payload(payload),
        known_modules=known_modules,
        existing_preset_tests=existing_preset_tests,
    )


def _responses_input_message(role: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "role": role,
        "content": [{"type": "input_text", "text": text}],
    }


def _responses_prompt_cache() -> dict[str, str]:
    value = os.environ.get("ONECODE_PROMPT_CACHE_KEY", "").strip()
    if value == "":
        return {}
    return {"prompt_cache_key": value}


def _responses_json_schema_enabled() -> bool:
    mode = os.environ.get("ONECODE_RESPONSES_TEXT_FORMAT", "json_schema").strip().casefold()
    return mode not in {"off", "text", "none", "false", "0"}


class OpenAIResponsesProvider:
    def __init__(self, api_key: str, *, endpoint: str = DEFAULT_OPENAI_RESPONSES_URL) -> None:
        if api_key.strip() == "":
            raise MissingModelApiKey("OPENAI_API_KEY is required for model-backed runs")
        self.api_key = api_key
        self.endpoint = endpoint

    def request_payload(
        self,
        task: str,
        *,
        model: str,
        planning_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "input": [
                _responses_input_message("system", canonical_planning_prompt(planning_context, task=task)),
                _responses_input_message("user", task),
            ],
        }
        payload.update(_responses_prompt_cache())
        if _responses_json_schema_enabled():
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "onecode_task_plan",
                    "strict": True,
                    "schema": MODEL_PLAN_SCHEMA,
                }
            }
        return payload

    def create_plan(
        self,
        task: str,
        *,
        model: str,
        http_timeout_seconds: float,
        planning_context: dict[str, Any] | None = None,
        known_modules: set[str] | None = None,
        existing_preset_tests: set[str] | None = None,
    ) -> ModelPlan:
        response_payload = _post_model_json(
            self.endpoint,
            self.api_key,
            self.request_payload(task, model=model, planning_context=planning_context),
            http_timeout_seconds,
        )
        return parse_response_plan(
            response_payload,
            known_modules=known_modules,
            existing_preset_tests=existing_preset_tests,
        )


class OpenAIChatCompletionsProvider:
    def __init__(self, api_key: str, *, endpoint: str = DEFAULT_OPENAI_CHAT_COMPLETIONS_URL) -> None:
        if api_key.strip() == "":
            raise MissingModelApiKey("OPENAI_API_KEY is required for model-backed runs")
        self.api_key = api_key
        self.endpoint = endpoint

    def request_payload(
        self,
        task: str,
        *,
        model: str,
        planning_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": canonical_planning_prompt(planning_context, task=task),
                },
                {"role": "user", "content": task},
            ],
            "response_format": {"type": "json_object"},
        }

    def parse_response(
        self,
        response: dict[str, Any],
        known_modules: set[str] | None = None,
        existing_preset_tests: set[str] | None = None,
    ) -> ModelPlan:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelProviderError("missing chat completion choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ModelProviderError("invalid chat completion choice")
        message = first_choice.get("message")
        content = _message_text(message.get("content")) if isinstance(message, dict) else None
        if content is None:
            raise ModelProviderError("missing chat completion message content")
        try:
            payload = json_object_from_model_text(content)
        except json.JSONDecodeError as exc:
            if first_choice.get("finish_reason") in {"length", "max_tokens"}:
                raise ValueError("model response was truncated") from exc
            raise ValueError("model response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("model response JSON must be an object")
        return validate_model_plan(
            normalize_model_plan_payload(payload),
            known_modules=known_modules,
            existing_preset_tests=existing_preset_tests,
        )

    def create_plan(
        self,
        task: str,
        *,
        model: str,
        http_timeout_seconds: float,
        planning_context: dict[str, Any] | None = None,
        known_modules: set[str] | None = None,
        existing_preset_tests: set[str] | None = None,
    ) -> ModelPlan:
        body = json.dumps(self.request_payload(task, model=model, planning_context=planning_context)).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "onecode/0.8",
            },
            method="POST",
        )
        try:
            with _SAFE_OPENER.open(request, timeout=http_timeout_seconds) as response:
                response_payload = json.loads(read_bounded_response(response).decode("utf-8"))
        except TimeoutError as exc:
            raise ModelProviderTimeout("model request timed out") from exc
        except urllib.error.HTTPError as exc:
            if resumable_model_status(exc.code):
                raise ModelProviderTimeout(f"model request can be resumed: {exc.code}") from exc
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ModelProviderError("model response envelope was not valid JSON") from exc
        except ValueError as exc:
            raise ModelProviderError("model response exceeds maximum size") from exc
        if not isinstance(response_payload, dict):
            raise ModelProviderError("model response envelope must be an object")
        return self.parse_response(
            response_payload,
            known_modules=known_modules,
            existing_preset_tests=existing_preset_tests,
        )


def complete_model_text(
    *,
    provider_kind: str,
    endpoint: str | None,
    model: str | None,
    api_key: str | None,
    prompt: str,
    timeout_seconds: float,
) -> str:
    config = build_provider_config(provider_kind, endpoint=endpoint, model=model)
    if api_key is None or api_key.strip() == "":
        raise MissingModelApiKey(f"{config.env_key} is required for model-backed runs")
    if config.provider_kind == "responses":
        body = {
            "model": config.model,
            "stream": False,
            "input": [_responses_input_message("user", prompt)],
        }
        body.update(_responses_prompt_cache())
    else:
        body = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
    payload = _post_model_json(config.endpoint, api_key, body, timeout_seconds)
    if config.provider_kind == "responses":
        return extract_response_text(payload)
    return _chat_message_text(payload)


def _chat_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ModelProviderError("missing chat completion choices")
    message = choices[0].get("message")
    content = _message_text(message.get("content")) if isinstance(message, dict) else None
    if not isinstance(content, str) or content.strip() == "":
        raise ModelProviderError("missing chat completion message content")
    return content


def _post_model_json(endpoint: str, api_key: str, body: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "onecode/0.8",
        },
        method="POST",
    )
    last_url_error: urllib.error.URLError | None = None
    for attempt in range(3):
        try:
            with _SAFE_OPENER.open(request, timeout=timeout_seconds) as response:
                payload = json.loads(read_bounded_response(response).decode("utf-8"))
            break
        except TimeoutError as exc:
            raise ModelProviderTimeout("model request timed out") from exc
        except urllib.error.HTTPError as exc:
            if resumable_model_status(exc.code):
                raise ModelProviderTimeout(f"model request can be resumed: {exc.code}") from exc
            if exc.code == 520 and attempt < 2:
                continue
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            last_url_error = exc
            if attempt == 0:
                continue
            raise ModelProviderError(f"model request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ModelProviderError("model response envelope was not valid JSON") from exc
        except ValueError as exc:
            raise ModelProviderError("model response exceeds maximum size") from exc
    else:
        raise ModelProviderError("model request failed: connection failed") from last_url_error
    if not isinstance(payload, dict):
        raise ModelProviderError("model response envelope must be an object")
    return payload


def canonical_planning_prompt(planning_context: dict[str, Any] | None = None, task: str | None = None) -> str:
    context = planning_context if isinstance(planning_context, dict) else {}
    contract = {
        "task_mode": context.get("task_mode"),
        "safe_agent": context.get("safe_agent", {"status": "not_requested", "safety_boundary": "method_only"}),
        "tools": MODEL_TOOL_CONTRACTS,
        "output_schema": MODEL_PLAN_SCHEMA,
    }
    user_task = task if isinstance(task, str) else ""
    lowered = user_task.lower()
    forbid_execution_plan = (
        "do not include execution_plan" in lowered
        or "do not return patches, execution_plan" in lowered
        or "do not return assets or execution_plan" in lowered
    )
    forbid_unittest = "do not import unittest" in lowered
    tool_sentence = "" if forbid_execution_plan else "Use execution_plan.steps for tool calls. "
    unittest_sentence = "" if forbid_unittest else "Tests must use the standard-library unittest module, not pytest. "
    return (
        "Return only one JSON object matching output_schema. Do not emit tool calling markup or special tokens. "
        + tool_sentence
        + "Read-only tools may be planned automatically. Tools with approval=true must only be planned; "
        "the OneCode host decides approval and execution. Safe-Agent context provides method guidance only. "
        "If no valid workspace action can be planned, return no_action with a concrete reason. "
        "Every asset content must be the complete non-empty file. "
        + unittest_sentence
        + "Do not include commentary or markdown fences. Contract: "
        + json.dumps(contract, ensure_ascii=False, sort_keys=True)
    )
