from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .build_mode_types import HEX_CREATE, HEX_HALT, HEX_INSPECT, HEX_ISOLATE, HEX_PROMPT, HEX_VERIFY

INSPECT_TOOLS = {"native_inspect_card"}
CREATE_TOOLS = {"make_dir", "write_file", "patch", "apply_patch", "edit_scoped_file", "create_new_file"}
VERIFY_TOOLS = {"run_pytest", "run_npm_test", "run_build"}
PROMPT_TOOLS: set[str] = set()
HALT_TOOLS: set[str] = set()
ISOLATE_TOOLS: set[str] = set()
DEFAULT_PYTHON_TEST_COMMAND = "python3 -m unittest discover -s tests -v"

READ_PATTERNS = ("cat ", "grep ", "rg ", "sed -n")
WRITE_PATTERNS = ("mkdir", "tee ", "cat >", "python - <<", "apply_patch")
TEST_PATTERNS = ("pytest", "npm test", "python -m pytest")
DANGEROUS_PATTERNS = ("rm -rf", "curl | sh", "chmod", "/etc/passwd", "~/.ssh", "~/.codex", "~/.claude")


@dataclass(frozen=True)
class ShadowToolMapping:
    original_tool: str
    hexagram: str
    shadow_action: str
    reason: str


def filter_tools_schema(hexagram: str, original_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = _allowed_tool_names(hexagram)
    if not allowed:
        return []
    filtered = []
    for item in original_tools:
        name = _tool_name(item)
        if name in allowed:
            filtered.append(_compact_tool(item))
    return filtered


def write_file_fallback_schema(original_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in original_tools:
        if _tool_name(item) == "write_file":
            return [_compact_tool(item)]
    if any("function" in item and isinstance(item.get("function"), dict) for item in original_tools):
        return [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Build Mode fallback tool: write full UTF-8 file contents inside the scoped sandbox.",
                    "parameters": _build_mode_parameters("write_file", None),
                },
            }
        ]
    return [
        {
            "type": "function",
            "name": "write_file",
            "description": "Build Mode fallback tool: write full UTF-8 file contents inside the scoped sandbox.",
            "parameters": _build_mode_parameters("write_file", None),
        }
    ]


def canonical_tool_schema(hexagram: str, original_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if hexagram == HEX_VERIFY:
        return [_canonical_tool("run_pytest", original_tools)]
    if hexagram == HEX_CREATE:
        return [_canonical_tool("write_file", original_tools)]
    return []


def _canonical_tool(name: str, original_tools: list[dict[str, Any]]) -> dict[str, Any]:
    if any("function" in item and isinstance(item.get("function"), dict) for item in original_tools):
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Build Mode canonical tool: {name}",
                "parameters": _build_mode_parameters(name, None),
            },
        }
    return {
        "type": "function",
        "name": name,
        "description": f"Build Mode canonical tool: {name}",
        "parameters": _build_mode_parameters(name, None),
    }


def map_shadow_tool(tool_name: str, arguments: Any) -> ShadowToolMapping:
    command = _command_text(tool_name, arguments)
    lowered = command.lower()
    if any(pattern in lowered for pattern in DANGEROUS_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_HALT, "halt", "dangerous_command")
    if tool_name in {"write_file", "edit_file", "apply_patch", "edit_scoped_file"}:
        return ShadowToolMapping(tool_name, HEX_CREATE, "scoped_writer", "native_write_tool")
    if tool_name in {"run_pytest", "run_npm_test", "run_build"} or any(pattern in lowered for pattern in TEST_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_VERIFY, "sandbox_runner", "test_command")
    if any(pattern in lowered for pattern in WRITE_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_CREATE, "scoped_writer", "write_command")
    if tool_name in {"view_file", "read_file", "grep", "native_inspect_card"} or any(pattern in lowered for pattern in READ_PATTERNS):
        return ShadowToolMapping(tool_name, HEX_INSPECT, "native_inspect_card", "read_command")
    if tool_name:
        return ShadowToolMapping(tool_name, HEX_ISOLATE, "shadow_buffer", "unknown_io")
    return ShadowToolMapping(tool_name, HEX_PROMPT, "zero_tool", "no_tool")


def _allowed_tool_names(hexagram: str) -> set[str]:
    if hexagram == HEX_INSPECT:
        return INSPECT_TOOLS
    if hexagram == HEX_CREATE:
        return CREATE_TOOLS
    if hexagram == HEX_VERIFY:
        return VERIFY_TOOLS
    if hexagram == HEX_PROMPT:
        return PROMPT_TOOLS
    if hexagram == HEX_HALT:
        return HALT_TOOLS
    if hexagram == HEX_ISOLATE:
        return ISOLATE_TOOLS
    return set()


def _tool_name(item: dict[str, Any]) -> str:
    if "function" in item and isinstance(item["function"], dict):
        return str(item["function"].get("name", ""))
    if str(item.get("type", "")) == "function" and item.get("name"):
        return str(item.get("name", ""))
    return str(item.get("name", ""))


def _compact_tool(item: dict[str, Any]) -> dict[str, Any]:
    name = _tool_name(item)
    if "function" in item:
        compact = dict(item)
        function = dict(compact["function"])
        function["description"] = f"Build Mode allowed tool: {name}"
        function["parameters"] = _build_mode_parameters(name, function.get("parameters"))
        compact["function"] = function
        return compact
    compact = dict(item)
    compact["description"] = f"Build Mode allowed tool: {name}"
    if "input_schema" in compact:
        compact["input_schema"] = _build_mode_parameters(name, compact.get("input_schema"))
    else:
        compact["parameters"] = _build_mode_parameters(name, compact.get("parameters"))
    return compact


def _build_mode_parameters(name: str, existing: Any) -> dict[str, Any]:
    if name in {"write_file", "edit_file", "edit_scoped_file", "create_new_file"}:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace-relative path inside the scoped sandbox.",
                },
                "content": {
                    "type": "string",
                    "description": "Full UTF-8 file contents to write.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        }
    if name in {"apply_patch", "patch"}:
        return {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified apply_patch text. Build Mode supports scoped Add File hunks inside the workspace.",
                }
            },
            "required": ["patch"],
            "additionalProperties": False,
        }
    if name in {"run_pytest", "run_npm_test", "run_build"}:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Test command to run in the isolated Build Mode runner.",
                    "default": DEFAULT_PYTHON_TEST_COMMAND,
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        }
    if name == "native_inspect_card":
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional workspace-relative file or directory to inspect.",
                }
            },
            "additionalProperties": False,
        }
    return existing if isinstance(existing, dict) else {"type": "object"}


def _command_text(tool_name: str, arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("command") or arguments.get("cmd") or arguments.get("path") or "")
    return str(arguments or tool_name)
