from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    requires_approval: bool

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class WriteTextTool(ToolDefinition):
    name: str = "write_text"
    requires_approval: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        action = {
            "action_type": "write_text",
            "path": params.get("path", ""),
            "content": params.get("content", ""),
        }
        if "status_code" in params:
            action["status_code"] = params["status_code"]
        return action


@dataclass(frozen=True)
class PatchTextTool(ToolDefinition):
    name: str = "patch_text"
    requires_approval: bool = True

    def plan_action(self, params: dict[str, Any]) -> dict[str, Any]:
        action = {
            "action_type": "patch_text",
            "path": params.get("path", ""),
            "search_block": params.get("search_block", ""),
            "replace_block": params.get("replace_block", ""),
        }
        if "status_code" in params:
            action["status_code"] = params["status_code"]
        return action


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([WriteTextTool(), PatchTextTool()])
