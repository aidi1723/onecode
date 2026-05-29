from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal


StepMode = Literal["auto", "review", "manual"]
StepStatus = Literal["completed", "failed", "skipped"]


@dataclass(frozen=True)
class ToolCallSpec:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.tool_name, str) or self.tool_name == "":
            raise ValueError("tool_name must be a non-empty string")
        if not isinstance(self.params, dict):
            raise ValueError("tool params must be a dictionary")


@dataclass(frozen=True)
class ExecutionStep:
    id: str
    description: str
    tool_calls: list[ToolCallSpec]
    depends_on: list[str] = field(default_factory=list)
    mode: StepMode = "auto"

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or self.id == "":
            raise ValueError("step id must be a non-empty string")
        if not isinstance(self.description, str):
            raise ValueError("step description must be a string")
        if not isinstance(self.tool_calls, list):
            raise ValueError("tool_calls must be a list")
        if self.mode not in {"auto", "review", "manual"}:
            raise ValueError("step mode must be auto, review, or manual")


@dataclass(frozen=True)
class ExecutionPlan:
    task: str
    steps: list[ExecutionStep]

    def __post_init__(self) -> None:
        if not isinstance(self.task, str) or self.task == "":
            raise ValueError("plan task must be a non-empty string")
        if not isinstance(self.steps, list):
            raise ValueError("plan steps must be a list")


@dataclass(frozen=True)
class GuardrailConfig:
    max_steps: int = 10
    max_tool_calls_per_step: int = 5
    max_duration_ms: int = 300_000
    forbidden_tools: list[str] = field(default_factory=list)
    require_approval_for: list[str] = field(default_factory=lambda: ["write_text", "patch_text"])
    max_consecutive_failures: int = 3


@dataclass(frozen=True)
class GuardrailValidation:
    valid: bool
    reason: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    output: dict[str, Any] | None
    reason: str | None = None


@dataclass(frozen=True)
class StepResult:
    step_id: str
    status: StepStatus
    tool_results: list[ToolResult] = field(default_factory=list)
    reason: str | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class ExecutionTrace:
    task: str
    success: bool
    step_results: list[StepResult]
    runner_results: list[dict[str, Any]]
    reason: str | None = None


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]
ApprovalCallback = Callable[[ExecutionStep], bool]


@dataclass(frozen=True)
class ToolContext:
    workspace: Path
    run_id: str | None = None
    resume_from_run_id: str | None = None
