from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ActionType(StrEnum):
    NOOP = "noop"
    WRITE_TEXT = "write_text"
    PATCH_TEXT = "patch_text"
    EXECUTE_PYTEST = "execute_pytest"
    BASH_EXECUTION = "bash_execution"
    INVALID_INTENT = "invalid_intent"


@dataclass(frozen=True)
class ActionIntent:
    action_type: ActionType
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        action_type = self.action_type
        if not isinstance(action_type, ActionType):
            try:
                action_type = ActionType(str(action_type))
            except ValueError as exc:
                raise ValueError(f"unknown action type: {self.action_type!r}") from exc
            object.__setattr__(self, "action_type", action_type)

        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dictionary")

        if action_type == ActionType.WRITE_TEXT:
            self._require_string("path")
            self._require_string("content")
        elif action_type == ActionType.PATCH_TEXT:
            self._require_string("path")
            self._require_string("search_block")
            self._require_string("replace_block")
        elif action_type == ActionType.BASH_EXECUTION:
            self._require_string("command")
        elif action_type == ActionType.EXECUTE_PYTEST:
            self._require_string("target")

    def _require_string(self, key: str) -> None:
        value = self.payload.get(key)
        if not isinstance(value, str) or value == "":
            raise ValueError(f"{self.action_type.value} requires non-empty string payload field: {key}")

    @classmethod
    def noop(cls) -> "ActionIntent":
        return cls(ActionType.NOOP, {})

    @classmethod
    def write_text(cls, path: str, content: str) -> "ActionIntent":
        return cls(ActionType.WRITE_TEXT, {"path": path, "content": content})

    @classmethod
    def patch_text(cls, path: str, search_block: str, replace_block: str) -> "ActionIntent":
        return cls(
            ActionType.PATCH_TEXT,
            {
                "path": path,
                "search_block": search_block,
                "replace_block": replace_block,
            },
        )

    @classmethod
    def bash_execution(cls, command: str) -> "ActionIntent":
        return cls(ActionType.BASH_EXECUTION, {"command": command})

    @classmethod
    def execute_pytest(cls, target: str) -> "ActionIntent":
        return cls(ActionType.EXECUTE_PYTEST, {"target": target})

    @classmethod
    def invalid_intent(cls, intent_type: str) -> "ActionIntent":
        return cls(ActionType.INVALID_INTENT, {"intent_type": intent_type})
